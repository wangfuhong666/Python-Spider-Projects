# 视频课程资源下载与 HLS 合并

按课程目录逐章遍历，拿到每节课的 `video_urls` 后 **先做一层 JS 逆向**还原出真实 m3u8 地址，再把 TS 分片 **并发下载**到本地，最后交给 **ffmpeg 无损合流**成 mp4。

> 本项目侧重展示 **JS 逆向 + 音视频处理**：URL 解码算法还原、HLS 分片并发下载、本地 m3u8 重建 + ffmpeg 合流。

## 一、目录结构

```
视频爬取练习/
├─ main.py            # 入口：目录遍历 + 解码 + 分片并发下载 + 合流
├─ decrypt.js         # 第一层解密：video_urls → 真实 m3u8 地址
├─ decrypt_video.js   # 第二层：调用 ffmpeg 把本地 m3u8 合成 mp4
├─ requirements.txt   # 依赖清单
└─ README.md
```

> `decrypt.js` / `decrypt_video.js` 是本项目的逆向产物，由 `main.py` 通过 execjs 调用。

## 二、环境要求

- Python 3.9+
- **Node.js**（execjs 的 JS 运行时，`decrypt.js` 里用到 `Buffer`）
- **ffmpeg**（必须可在命令行直接调用；`decrypt_video.js` 用 `spawnSync("ffmpeg")` 启动它）

```bash
pip install -r requirements.txt
python main.py
```

脚本在 import 阶段即开始执行，直接在项目目录下运行 `main.py` 即可。

## 三、两层逆向 / 处理链路

```
课程目录接口 → 每节课的 video_urls
      │  decrypt.js（第一层）
      ▼
   真实 m3u8 地址
      │  requests 拉取 m3u8，解析出 TS 分片列表
      ▼
  ThreadPoolExecutor 并发下载分片 → result/temp_<resource_id>/
      │  生成本地 m3u8（分片路径改写为本地绝对路径）
      ▼
  decrypt_video.js → ffmpeg -c copy 合流
      ▼
   result/<课程名>.mp4
```

### 1. 第一层解密（`decrypt.js`）

`video_urls` 不是明文地址，做了「字符映射 + Base64 + JSON」三层包装：

- 去掉固定前缀 `__ba`
- 自定义字符映射还原：`@→1`、`#→2`、`$→3`、`%→4`
- URL-safe 变体还原：`-` → `+`、`_` → `/`
- Base64 解码后再 `JSON.parse`，取 `data[0].url`

### 2. 第二层处理（`decrypt_video.js`）

**不自己拼接二进制**，而是把本地分片重新写成一个本地 m3u8，再让 ffmpeg 以 `-c copy` 无损合流：

```js
const args = ["-y", "-protocol_whitelist", "file,http,https,tcp,tls,crypto",
              "-i", m3u8_path, "-c", "copy", output_path];
```

好处是：不重编码（快且无画质损失），且 `-protocol_whitelist` 放开 `file` / `crypto` 后，本地 m3u8 也能正确处理带 AES 加密的分片。

## 四、容错与断点续传

| 机制 | 说明 |
|---|---|
| 分片重试 | 单个 TS 分片最多重试 5 次，全部失败才抛错 |
| 断点续传 | 分片文件已存在且非空则直接跳过，中断后重跑只补缺失的分片 |
| 课程级跳过 | 最终 `result/<课程名>.mp4` 已存在则整节课跳过 |
| 文件名安全 | 所有落盘路径都先过 `safe_name()`，把 `\ / : * ? " < > |` 替换为 `_`，避免课程标题含斜杠导致建文件失败 |
| 临时文件回收 | 合流成功后 `shutil.rmtree` 清理 `temp_<resource_id>` 分片目录 |

并发度固定为 `max_workers=5`，既保证速度，也避免对目标站造成过大压力。

## 五、产出

- `result/<课程名>.mp4`：最终视频
- `result/temp_<resource_id>/`：分片临时目录（合流成功后自动清理）

产出目录与音视频文件均由 `.gitignore` 排除，仓库里只保留代码。

## 六、合规说明

- 仅用于个人学习研究，代码中写死的示例课程 ID 不代表对任何内容的授权
- 下载内容版权归原作者与平台所有，不对外分发、不用于商业用途
