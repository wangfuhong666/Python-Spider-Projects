import json
import os
import random
import re
import time

import execjs
import requests

import config

JS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vip_apisign.js")

with open(JS_FILE, "r", encoding="utf-8") as f:
    js_code = f.read()
    cry = execjs.compile(js_code)

def get_param_hash(params):
    return cry.call("getParamHash", params)

def get_api_sign(path, params, mars_cid, vip_tank=""):
    return cry.call("getApiSign", path, params, mars_cid, vip_tank)

def get_authorization(path, params, mars_cid, vip_tank=""):
    return cry.call("getAuthorization", path, params, mars_cid, vip_tank)

tfs_blocked = False

def build_session():
    session = requests.Session()
    session.headers.update(config.HEADERS)
    return session

def sleep_random():
    time.sleep(random.uniform(config.SLEEP_MIN, config.SLEEP_MAX))

def get_json(session, path, params, mars_cid=None):
    mars_cid = mars_cid or config.MARS_CID

    data = dict(params)
    data["api_key"] = config.API_KEY
    data["mars_cid"] = mars_cid

    headers = {
        "Authorization": get_authorization(path, data, mars_cid, config.VIP_TANK),
        "Referer": "https://m.vip.com/",
    }

    for i in range(config.MAX_RETRY):
        try:
            sleep_random()
            response = session.get(
                config.API_HOST + path,
                params=data,
                headers=headers,
                timeout=config.TIMEOUT,
            )
            result = response.json()

            if result.get("code") == 1:
                return result.get("data", {})

            code = result.get("code")
            print(f"    [接口返回异常] {path} -> {result.get('msg')}({code})")

            if code == 11000:
                if i == config.MAX_RETRY - 1:
                    print("    [TFS 风控] 冷却后仍被拦截，本轮停止后续请求（已采数据照常保存）")
                    print("    [提示] IP 级累计限流，请隔一段时间再跑；若长期 11000 需重抓 tfs_fp_token")
                    globals()["tfs_blocked"] = True
                    return {}
                cooldown = config.RETRY_WAIT * 5 * (i + 1)
                print(f"    [TFS 风控] 冷却 {cooldown} 秒后重试（第 {i + 1}/{config.MAX_RETRY - 1} 次）...")
                time.sleep(cooldown)
                continue

            if code == 11001:
                return {}

            time.sleep(config.RETRY_WAIT)
        except Exception as e:
            print(f"    [请求失败 {i + 1}/{config.MAX_RETRY}] {path} -> {e}")
            time.sleep(config.RETRY_WAIT)

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
        "menu_code": menu_code or config.DISCOVER_MENU_CODE,
        "channel_name": channel_name or config.DISCOVER_CHANNEL_NAME,
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
    data = get_json(session, config.PATH_CHANNEL, params)
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
        "batchSize": str(batch_size or config.BATCH_SIZE),
    })

    data = get_json(session, config.PATH_BRAND_RANK, params)
    if not data:
        return [], {}, True

    pids = [p.get("pid") for p in (data.get("products") or []) if p.get("pid")]
    return pids, data.get("brand") or {}, bool(data.get("isLast", True))

def fetch_product_detail(session, product_id):
    params = base_params()
    params.pop("app_version", None)
    params.update({"product_id": str(product_id), "data_ver": "1"})
    return get_json(session, config.PATH_PRODUCT_DETAIL, params) or {}

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
