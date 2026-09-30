'''
https://fe.duyiedu.com/p/t_pc/course_pc_detail/video/v_674eb53ce4b0694c3c734913?product_id=course_2VKbErGXkTSzvbl9aQ9HgndEtIz

https://fe.duyiedu.com/p/t_pc/course_pc_detail/video/v_674eb5ece4b023c058afbbc8?product_id=course_2VKbErGXkTSzvbl9aQ9HgndEtIz

https://fe.duyiedu.com/p/t_pc/course_pc_detail/video/v_674eb655e4b0694c950c288c?product_id=course_2VKbErGXkTSzvbl9aQ9HgndEtIz
模版：
https://fe.duyiedu.com/p/t_pc/course_pc_detail/video/{resource_id}?product_id={course_id}}
https://fe.duyiedu.com/p/t_pc/course_pc_detail/video/v_674eb53ce4b0694c3c734913?product_id=course_2VKbErGXkTSzvbl9aQ9HgndEtIz
'''

import requests
import jsonpath
import execjs
import os
import re
import shutil

from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor


session = requests.Session()

session.headers.update({
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/x-www-form-urlencoded",
    "Origin": "https://fe.duyiedu.com",
    "Referer": "https://fe.duyiedu.com/p/t_pc/course_pc_detail/camp_pro/course_2VKbErGXkTSzvbl9aQ9HgndEtIz",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/154.0.0.0 Safari/537.36",
})


# 加载 video_urls 解码 JS
with open("decrypt.js", "r", encoding="utf-8") as f:
    js_code = f.read()
    cry = execjs.compile(js_code)


# 加载视频处理 JS
with open("decrypt_video.js", "r", encoding="utf-8") as f:
    video_js_code = f.read()
    video_cry = execjs.compile(video_js_code)


if not os.path.exists("result"):
    os.mkdir("result")


def safe_name(name):
    return re.sub(r'[\\/:*?"<>|]', "_", name)


def download_hls(m3u8_url, video_name, resource_id):

    temp_dir = os.path.join("result", "temp_" + resource_id)

    if not os.path.exists(temp_dir):
        os.mkdir(temp_dir)

    # 获取 m3u8
    resp = session.get(m3u8_url)
    resp.raise_for_status()

    m3u8_text = resp.text
    lines = m3u8_text.splitlines()

    # 提取 TS
    ts_list = []

    for line in lines:
        line = line.strip()

        if line and not line.startswith("#"):
            ts_list.append(line)

    print(f"{video_name} 共 {len(ts_list)} 个 TS 分片")


    # 单个下载任务
    def task(n, ts):

        ts_url = urljoin(m3u8_url, ts)
        ts_path = os.path.join(temp_dir, f"{n:06d}.ts")

        if os.path.exists(ts_path) and os.path.getsize(ts_path) > 0:
            return

        for i in range(5):

            try:
                r = session.get(ts_url, timeout=30)
                r.raise_for_status()

                with open(ts_path, "wb") as f:
                    f.write(r.content)

                return

            except Exception as e:
                print(f"task{n} 下载失败，第 {i + 1} 次重试：{e}")

        raise Exception(f"TS 分片 {n} 下载失败")


    # 线程池下载
    with ThreadPoolExecutor(max_workers=5) as executor:

        futures = []

        for i in range(len(ts_list)):
            future = executor.submit(task, i, ts_list[i])
            futures.append(future)

        for future in futures:
            future.result()

    print("所有 TS 下载完成")


    # 生成本地 m3u8
    local_lines = []
    index = 0

    for line in lines:
        stripped = line.strip()

        if stripped and not stripped.startswith("#"):
            ts_path = os.path.abspath(os.path.join(temp_dir, f"{index:06d}.ts"))
            ts_path = ts_path.replace("\\", "/")

            local_lines.append(ts_path)
            index += 1

        else:
            local_lines.append(line)


    local_m3u8 = os.path.abspath(os.path.join(temp_dir, "local.m3u8"))

    with open(local_m3u8, "w", encoding="utf-8") as f:
        f.write("\n".join(local_lines))


    # 最终输出路径
    video_name = safe_name(video_name)
    output = os.path.abspath(os.path.join("result", video_name + ".mp4"))

    print("开始处理视频")

    # 调用 decrypt_video.js
    result = video_cry.call("decrypt_video", local_m3u8, output)

    print(result)

    # 成功以后删除临时 TS
    shutil.rmtree(temp_dir, ignore_errors=True)

    print(f"{video_name} 下载完成")


# ==========================================
# 获取课程目录
# ==========================================

url = "https://fe.duyiedu.com/xe.course.business_go.avoidlogin.e_course.resource_catalog_list.get/1.0.0"

data = {
    "app_id": "appdy3bnnsj9558",
    "course_id": "course_2VKbErGXkTSzvbl9aQ9HgndEtIz",
    "order": "asc",
    "p_id": "0",
    "page": 1,
    "page_size": 50,
    "sub_course_id": "",
    "resource_id": "",
    "is_display_auth_sections": 0,
}

resp = session.post(url, data=data)
resp.raise_for_status()

chapter_list = resp.json()["data"]["list"]


for chapter in chapter_list:

    name = chapter["chapter_title"]
    chapter_id = chapter["resource_id"]
    course_id = chapter["course_id"]

    data["p_id"] = chapter_id

    resp2 = session.post(url, data=data)
    resp2.raise_for_status()

    video_list = resp2.json()["data"]["list"]


    for video in video_list:

        resource_id = video["resource_id"]
        video_name = video["resource_title"]

        print(video_name, resource_id, course_id)

        detail_url = "https://fe.duyiedu.com/xe.course.business.video.detail_info.get/2.0.0"

        detail_data = {
            "resource_id": resource_id,
            "opr_sys": "Win32",
            "product_id": course_id,
            "content_app_id": "",
        }

        resp3 = session.post(detail_url, data=detail_data)
        resp3.raise_for_status()

        # 获取 video_urls
        video_url = jsonpath.jsonpath(resp3.json(), "$..video_urls")[0]

        # 第一层 JS 解码
        video_url = cry.call("decrypt_url", video_url)

        print(video_url)

        output = os.path.join("result", safe_name(video_name) + ".mp4")

        if os.path.exists(output):
            print(f"{video_name} 已存在，跳过")
            continue

        download_hls(video_url, video_name, resource_id)