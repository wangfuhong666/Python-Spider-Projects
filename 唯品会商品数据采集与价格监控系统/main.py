import argparse
import csv
import json
import os
import random
import re
import time
from datetime import datetime

import execjs
import requests

JS_CODE = r"""
var crypto = require('crypto');

var AES_KEY = Buffer.from('weixin_smallmina', 'utf8');
var AES_IV = Buffer.concat([Buffer.from('weixin', 'utf8'), Buffer.alloc(10)]);

var SECRET_CIPHER = 'Ql4mW09F3urBNdzBLfK6UuRTqj22Bta7eEKTO7n5jFf9uU6FZZmcfe/gurOAOB+o';

function aesDecryptSecret(b64) {
    var d = crypto.createDecipheriv('aes-128-cbc', AES_KEY, AES_IV);
    return Buffer.concat([d.update(Buffer.from(b64, 'base64')), d.final()]).toString('utf8');
}

var SECRET = aesDecryptSecret(SECRET_CIPHER);

function sha1(s) {
    return crypto.createHash('sha1').update(s, 'utf8').digest('hex');
}

function toPath(url) {
    return url.replace(new RegExp('^http(s)?://.*?/', 'g'), '/').split('?')[0];
}

function getParamHash(params) {
    var str = Object.keys(params)
        .sort()
        .filter(function (k) { return k !== 'api_key'; })
        .map(function (k) {
            var v = params[k];
            if (v === null || v === undefined) { v = ''; }
            return k + '=' + (typeof v === 'object' ? JSON.stringify(v) : String(v));
        })
        .join('&');
    return sha1(str);
}

function getApiSign(urlOrPath, params, marsCid, vipTank) {
    var path = toPath(urlOrPath);
    var paramHash = getParamHash(params || {});
    return sha1(path + paramHash + (vipTank || '') + (marsCid || '') + SECRET);
}

function getAuthorization(urlOrPath, params, marsCid, vipTank) {
    return 'OAuth api_sign=' + getApiSign(urlOrPath, params, marsCid, vipTank);
}

if (typeof global !== 'undefined') {
    global.SECRET_VALUE = SECRET;
    global.sha1 = sha1;
    global.toPath = toPath;
    global.getParamHash = getParamHash;
    global.getApiSign = getApiSign;
    global.getAuthorization = getAuthorization;
}
"""

cry = execjs.compile(JS_CODE)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

DEFAULT_COOKIE = "mars_cid=1790741346908_c1dd5742e20004514226fccfc8ac746b; mars_sid=c1d49daf6efe254290d3550a71bb9175; visit_id=3B23194ED1D37F7F9264DD80F249CB73; vip_sec_fp_vvid=YzViMjAxMGMtMzhjYi00MjA2LWFmZGYtOTA4MWY1YWJkMGIxMTc5MDY5OTc3NTI4M0t91mM=; v_s_fp_switch=1; .thumbcache_f65dad1092aa9e66c73b4823b4493a2f=muR+F/Mxd5hBf58Sz2Yi/WWvlckEz8UAUir9I5uj7guPeux0JgoVq1Ng1tXYYH0aHjTl3PsZX+ukEXMdnWJzGA%3D%3D; vip_sec_fp_smtoken=BmuR+F/Mxd5hBf58Sz2Yi/WWvlckEz8UAUir9I5uj7guPeux0JgoVq1Ng1tXYYH0aHjTl3PsZX+ukEXMdnWJzGA==; vip_sec_fp_wtk=cwEAAzVqMaXV6gK8hPxwbd9bIZ29TutpHbLQ4qkfbt3G7_H2wPjp-Eiix8RjRkLm06V1UGqzP8VhVTpZtSC4KP8ClsOD9GI; mars_pid=18; tfs_fp_token=cwEAAzVqMaXV6gK8hPxwbd9bIZ29TutpHbLQ4qkfbt3G7_H2wPjp-Eiix8RjRkLm06V1UGqzP8VhVTpZtSC4KP8ClsOD9GI; tfs_fp_timestamp=1790741349402"

def load_cookie():
    path = os.path.join(BASE_DIR, "cookie.txt")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            value = f.read().strip()
        if value:
            return value
    return DEFAULT_COOKIE

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "zh-CN,zh-CN;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "Origin": "https://m.vip.com",
    "Pragma": "no-cache",
    "Referer": "https://m.vip.com/v3/index.html",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36 Edg/154.0.0.0",
    "X-Requested-With": "XMLHttpRequest",
    "sec-ch-ua": '"Chromium";v="154", "Microsoft Edge";v="154", "Not A(Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "Cookie": load_cookie(),
}

API_HOST = "https://mapi.vip.com"

API_KEY = "8cec5243ade04ed3a02c5972bcda0d3f"

PATH_CHANNEL = "/vips-mobile/rest/layout/h5/channel/data"
PATH_BRAND_RANK = "/vips-mobile/rest/shopping/wx/product/list/rank/v1"
PATH_PRODUCT_DETAIL = "/vips-mobile/rest/shopping/wx/share/product/v2"

def gen_mars_cid():
    return "%d_%s" % (
        int(time.time() * 1000),
        "".join(random.choice("0123456789abcdef") for _ in range(32)),
    )

def mars_cid_from_cookie(cookie_str):
    for item in cookie_str.split(";"):
        item = item.strip()
        if item.startswith("mars_cid="):
            return item.split("=", 1)[1].strip()
    return ""

def token_age_minutes(cookie_str):
    for item in cookie_str.split(";"):
        item = item.strip()
        if item.startswith("tfs_fp_timestamp="):
            try:
                return max(0.0, (time.time() * 1000 - float(item.split("=", 1)[1])) / 60000.0)
            except ValueError:
                return -1.0
    return -1.0

MARS_CID = mars_cid_from_cookie(HEADERS.get("Cookie", "")) or gen_mars_cid()

TOKEN_AGE = token_age_minutes(HEADERS.get("Cookie", ""))

VIP_TANK = ""

BRAND_IDS = []

DISCOVER_MENU_CODE = "bigbshouye"
DISCOVER_CHANNEL_NAME = "推荐"

MAX_PAGE_PER_BRAND = 2
BATCH_SIZE = 30

MAX_PRODUCTS = 30

SLEEP_MIN = 2.0
SLEEP_MAX = 4.0

MAX_RETRY = 3
RETRY_WAIT = 3

TIMEOUT = 15

PRODUCT_CSV = "商品数据.csv"
LATEST_CSV = "最新价格.csv"
CHANGE_CSV = "价格变动.csv"
SUMMARY_CSV = "统计报表.csv"


def get_param_hash(params):
    return cry.call("getParamHash", params)

def get_api_sign(path, params, mars_cid, vip_tank=""):
    return cry.call("getApiSign", path, params, mars_cid, vip_tank)

def get_authorization(path, params, mars_cid, vip_tank=""):
    return cry.call("getAuthorization", path, params, mars_cid, vip_tank)

tfs_blocked = False

def build_session():
    session = requests.Session()
    session.headers.update(HEADERS)
    return session

def sleep_random():
    time.sleep(random.uniform(SLEEP_MIN, SLEEP_MAX))

def get_json(session, path, params, mars_cid=None):
    mars_cid = mars_cid or MARS_CID

    data = dict(params)
    data["api_key"] = API_KEY
    data["mars_cid"] = mars_cid

    headers = {
        "Authorization": get_authorization(path, data, mars_cid, VIP_TANK),
        "Referer": "https://m.vip.com/",
    }

    for i in range(MAX_RETRY):
        try:
            sleep_random()
            response = session.get(
                API_HOST + path,
                params=data,
                headers=headers,
                timeout=TIMEOUT,
            )
            result = response.json()

            if result.get("code") == 1:
                return result.get("data", {})

            code = result.get("code")
            print(f"    [接口返回异常] {path} -> {result.get('msg')}({code})")

            if code == 11000:
                if i == MAX_RETRY - 1:
                    print("    [TFS 风控] 冷却后仍被拦截，本轮停止后续请求（已采数据照常保存）")
                    print("    [提示] IP 级累计限流，请隔一段时间再跑；若长期 11000 需重抓 tfs_fp_token")
                    globals()["tfs_blocked"] = True
                    return {}
                cooldown = RETRY_WAIT * 5 * (i + 1)
                print(f"    [TFS 风控] 冷却 {cooldown} 秒后重试（第 {i + 1}/{MAX_RETRY - 1} 次）...")
                time.sleep(cooldown)
                continue

            if code == 11001:
                return {}

            time.sleep(RETRY_WAIT)
        except Exception as e:
            print(f"    [请求失败 {i + 1}/{MAX_RETRY}] {path} -> {e}")
            time.sleep(RETRY_WAIT)

    return {}

def base_params():
    return {
        "app_name": "shop_wap",
        "client": "wap",
        "source_app": "shop_wap",
        "app_version": "4.0",
        "client_type": "wap",
        "format": "json",
        "mobile_platform": "2",
        "ver": "2.0",
        "standby_id": "other",
        "union_mark": "nature",
        "sd_tuijian": "0",
        "mobile_channel": "nature",
        "warehouse": "VIP_HZ",
        "fdc_area_id": "104102101",
        "province_id": "104102",
        "wap_consumer": "A1",
        "net": "WIFI",
        "width": "750",
        "height": "500",
        "phone_model": "PC",
        "phone_brand": "",
        "sys_version": "Windows 10 x64",
        "is_default_area": "1",
        "app_theme_mode": "0",
        "app_theme_action": "0",
    }

def discover_brands(session, menu_code=None, channel_name=None, limit=30):
    params = base_params()
    params.update({
        "menu_code": menu_code or DISCOVER_MENU_CODE,
        "channel_name": channel_name or DISCOVER_CHANNEL_NAME,
        "auto_refresh": "0",
        "user_group": "3105",
        "user_subdivide_group": "310505",
        "sex_type": "2",
        "open_id": "",
        "changeResolution": "7",
        "wxEntryGroup": "",
        "extProductIds": "",
        "shareProductIds": "",
        "laIgnoreNull": "1",
        "wx_scene": "1001",
        "device_platform": "windows",
    })

    print(f"[频道流] 正在从 {params['channel_name']} 发现品牌 ...")
    data = get_json(session, PATH_CHANNEL, params)
    if not data:
        return []

    raw = json.dumps(data, ensure_ascii=False)
    brand_ids = re.findall(r'"brand_id"\s*:\s*"(\d+)"', raw) + re.findall(r'"brandId"\s*:\s*"(\d+)"', raw)

    result = []
    seen = set()
    for bid in brand_ids:
        if bid in seen:
            continue
        seen.add(bid)
        result.append({"brand_id": bid, "brand_name": ""})
        if len(result) >= limit:
            break

    print(f"[频道流] 发现品牌 {len(result)} 个：{[b['brand_id'] for b in result][:10]} ...")
    return result

def fetch_brand_products(session, brand_id, page_offset=0, batch_size=None):
    params = base_params()
    params.update({
        "brandId": brand_id,
        "pageOffset": str(page_offset),
        "batchSize": str(batch_size or BATCH_SIZE),
    })

    data = get_json(session, PATH_BRAND_RANK, params)
    if not data:
        return [], {}, True

    pids = [p.get("pid") for p in (data.get("products") or []) if p.get("pid")]
    return pids, data.get("brand") or {}, bool(data.get("isLast", True))

def fetch_product_detail(session, product_id):
    params = base_params()
    params.pop("app_version", None)
    params.update({"product_id": str(product_id), "data_ver": "1"})
    return get_json(session, PATH_PRODUCT_DETAIL, params) or {}

HEAD = ["商品ID", "标题", "品牌", "售价", "原价", "折扣", "卖点", "主图", "详情链接"]

def _to_num(value):
    try:
        return float(str(value).replace(",", ""))
    except (ValueError, TypeError):
        return 0.0

def parse_product(product_id, detail_json, brand_name=""):
    card = detail_json.get("card") or {}
    timeline = detail_json.get("timeline") or {}

    title = (timeline.get("title") or "").strip()

    price_int = str(card.get("sale_price_int") or "").strip()
    price_dot = str(card.get("sale_price_dot") or "").strip().lstrip(".")
    sale_price = _to_num(f"{price_int}.{price_dot}" if price_dot else price_int)

    market_price = _to_num(card.get("sale_market_price"))

    discount = (timeline.get("sale_discount") or "").strip()
    if not discount and market_price > 0 and sale_price > 0:
        discount = f"{sale_price / market_price * 10:.1f}折"

    imgs = card.get("imgs") or []

    if not brand_name and "|" in title:
        brand_name = title.split("|")[0].strip()

    return {
        "商品ID": str(product_id),
        "标题": title,
        "品牌": brand_name,
        "售价": sale_price,
        "原价": market_price,
        "折扣": discount,
        "卖点": (timeline.get("sell_point") or "").strip(),
        "主图": imgs[0] if imgs else "",
        "详情链接": f"https://m.vip.com/v3/index.html#/detail?pid={product_id}",
    }

def parse_brand_name(brand_info):
    if not brand_info:
        return ""
    for key in ("brand_name", "name", "title", "en_name"):
        if brand_info.get(key):
            return str(brand_info[key])
    return ""


def ensure_output_dir():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    return OUTPUT_DIR

def _path(filename):
    return os.path.join(ensure_output_dir(), filename)

def save_rows(rows, filename):
    file = _path(filename)
    with open(file, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(HEAD)
        for row in rows:
            writer.writerow([row.get(k, "") for k in HEAD])
    print(f"[存储] 已写入 {len(rows)} 条 -> output/{filename}")
    return file

def load_rows(filename):
    file = _path(filename)
    if not os.path.exists(file):
        return {}

    result = {}
    with open(file, "r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if row.get("商品ID"):
                result[row["商品ID"]] = row
    return result

def save_changes(changes):
    head = ["商品ID", "标题", "品牌", "上次售价", "本次售价", "变动金额", "变动幅度", "详情链接"]
    file = _path(CHANGE_CSV)
    with open(file, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(head)
        for item in changes:
            writer.writerow([item.get(k, "") for k in head])
    print(f"[存储] 价格变动 {len(changes)} 条 -> output/{CHANGE_CSV}")
    return file

def save_summary(summary_rows):
    file = _path(SUMMARY_CSV)
    with open(file, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["统计项", "结果"])
        for k, v in summary_rows:
            writer.writerow([k, v])
    print(f"[存储] 统计报表 -> output/{SUMMARY_CSV}")
    return file

def compare_snapshots(old_rows, new_rows):
    changes = []

    for pid, new_row in new_rows.items():
        old_row = old_rows.get(pid)
        if not old_row:
            continue
        try:
            old_price = float(old_row.get("售价") or 0)
            new_price = float(new_row.get("售价") or 0)
        except ValueError:
            continue

        if old_price == new_price or old_price == 0 or new_price == 0:
            continue

        changes.append({
            "商品ID": pid,
            "标题": new_row.get("标题", ""),
            "品牌": new_row.get("品牌", ""),
            "上次售价": old_price,
            "本次售价": new_price,
            "变动金额": round(new_price - old_price, 2),
            "变动幅度": f"{(new_price - old_price) / old_price * 100:.1f}%",
            "详情链接": new_row.get("详情链接", ""),
        })

    changes.sort(key=lambda x: x["变动金额"])
    return changes

def build_summary(rows):
    summary = []
    if not rows:
        return summary

    prices = [float(r.get("售价") or 0) for r in rows]
    prices = [p for p in prices if p > 0]

    summary.append(("采集总数", len(rows)))
    summary.append(("品牌数量", len({r.get("品牌", "") for r in rows if r.get("品牌")})))

    if prices:
        summary.append(("最低价", min(prices)))
        summary.append(("最高价", max(prices)))
        summary.append(("平均价", round(sum(prices) / len(prices), 2)))

    for low, high in [(0, 100), (100, 300), (300, 800), (800, 2000), (2000, 999999)]:
        summary.append((f"价格区间 {low}~{high if high < 999999 else '以上'}",
                        len([p for p in prices if low < p <= high])))

    discount_list = []
    for r in rows:
        sale = float(r.get("售价") or 0)
        market = float(r.get("原价") or 0)
        if 0 < sale < market:
            discount_list.append((round(sale / market * 10, 2), r))

    discount_list.sort(key=lambda x: x[0])
    for i, (rate, r) in enumerate(discount_list[:5], 1):
        summary.append((f"折扣力度TOP{i}",
                        f"{r.get('标题', '')[:28]} {rate}折 现价{r.get('售价')} 原价{r.get('原价')}"))

    return summary

def print_report(rows, changes, summary):
    print("\n" + "=" * 60)
    print(" 唯品会商品价格监控 · 运行报告")
    print("=" * 60)
    print(f"\n本次采集商品：{len(rows)} 个")

    if summary:
        print("\n【统计概览】")
        for k, v in summary:
            print(f"  {k:<24} {v}")

    if changes:
        down = [c for c in changes if c["变动金额"] < 0]
        up = [c for c in changes if c["变动金额"] > 0]
        print(f"\n【价格变动】共 {len(changes)} 个商品变化：降价 {len(down)} 个 / 涨价 {len(up)} 个")
        for c in changes[:10]:
            flag = "↓降价" if c["变动金额"] < 0 else "↑涨价"
            print(f"  {flag} {c['上次售价']} -> {c['本次售价']} ({c['变动幅度']}) {c['标题'][:24]}")
    else:
        print("\n【价格变动】暂无变动（首次运行或价格未变化）")

    print("\n" + "=" * 60)

def run_report():
    new_rows = load_rows(PRODUCT_CSV)
    old_rows = load_rows(LATEST_CSV)

    changes = compare_snapshots(old_rows, new_rows)
    summary = build_summary(list(new_rows.values()))

    save_changes(changes)
    save_summary(summary)
    print_report(list(new_rows.values()), changes, summary)

    rows = list(new_rows.values())
    if rows:
        save_rows(rows, LATEST_CSV)

    return changes, summary


def collect_once(limit=None):
    limit = limit or MAX_PRODUCTS
    session = build_session()

    print("=" * 60)
    print(" 唯品会商品数据采集与价格监控系统")
    print("=" * 60)
    print(f"mars_cid: {MARS_CID}")
    if TOKEN_AGE < 0:
        print("[注意] Cookie 里没有 tfs_fp_timestamp，风控拦截概率高")
    else:
        print(f"tfs_fp_token 已生成 {TOKEN_AGE:.0f} 分钟")
        if TOKEN_AGE > 30:
            print("[注意] 指纹 token 偏旧，若被 TFS 拦截请重新抓一份 Cookie")

    brands = [{"brand_id": bid, "brand_name": ""} for bid in BRAND_IDS]
    if not brands:
        brands = discover_brands(session, limit=6)
    if not brands:
        print("[错误] 没有拿到任何品牌，程序结束")
        return []

    print(f"\n本次监控品牌 {len(brands)} 个：{[b['brand_id'] for b in brands]}")

    per_brand = max(5, limit // max(1, len(brands)))
    print(f"每个品牌最多取 {per_brand} 个商品")

    product_ids = []
    brand_names = {}

    for brand in brands:
        page = 0
        got = 0
        for _ in range(MAX_PAGE_PER_BRAND):
            if got >= per_brand:
                break
            pids, brand_info, is_last = fetch_brand_products(session, brand["brand_id"], page_offset=page * BATCH_SIZE)
            if not pids:
                break

            need = per_brand - got
            take = pids[:need]
            brand_names[brand["brand_id"]] = parse_brand_name(brand_info)
            product_ids.extend([(pid, brand["brand_id"]) for pid in take])
            got += len(take)
            print(f"[品牌 {brand['brand_id']}] 第 {page + 1} 页 拿到 {len(take)} 个商品（累计 {len(product_ids)}）")

            if is_last:
                break
            page += 1

        if len(product_ids) >= limit:
            break

    product_ids = product_ids[: limit]
    print(f"\n待采集详情商品数：{len(product_ids)}")

    rows = []
    seen = set()

    for i, (pid, brand_id) in enumerate(product_ids, 1):
        if pid in seen:
            continue
        seen.add(pid)

        if tfs_blocked:
            print(f"\n[TFS 风控] 在第 {i} 个商品处被拦截，本轮到此为止")
            break

        print(f"[详情 {i}/{len(product_ids)}] {pid}", end=" ")
        detail = fetch_product_detail(session, pid)
        if not detail:
            print("-> 无数据")
            continue

        row = parse_product(pid, detail, brand_names.get(brand_id, ""))
        rows.append(row)
        print(f"-> {row['售价']} 元 {row['标题'][:20]}")

    return rows

def run_once(limit=None):
    start = time.time()
    rows = collect_once(limit)

    if not rows:
        print("\n[结束] 本次没有采集到任何商品")
        return

    save_rows(rows, PRODUCT_CSV)
    run_report()
    print(f"\n[结束] 本次耗时 {time.time() - start:.1f} 秒")

def run_loop(interval, rounds):
    ensure_output_dir()
    print("=" * 60)
    print(" 唯品会商品价格监控 · 定时任务已启动")
    print(f" 采集间隔：{interval} 秒")
    print("=" * 60)

    round_no = 0
    while rounds == 0 or round_no < rounds:
        round_no += 1
        print(f"\n>>> 第 {round_no} 轮开始 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        try:
            run_once(args.limit)
        except Exception as e:
            print(f"[异常] 第 {round_no} 轮采集出错：{e}")
        print(f"<<< 第 {round_no} 轮结束，等待 {interval} 秒")
        time.sleep(interval)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="唯品会商品数据采集与价格监控系统")
    ap.add_argument("--loop", action="store_true", help="定时循环采集")
    ap.add_argument("--interval", type=int, default=3600, help="采集间隔秒数，默认 3600")
    ap.add_argument("--rounds", type=int, default=0, help="最多跑几轮，0 表示不限，默认 0")
    ap.add_argument("--limit", type=int, default=0, help="本轮最多采集几个商品，0 表示用配置中的默认采集量")
    args = ap.parse_args()

    if args.loop:
        run_loop(args.interval, args.rounds)
    else:
        run_once()
