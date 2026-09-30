import os
import random
import time

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
