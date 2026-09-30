import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

SITE_NAME = "哔哩哔哩热门榜单"
SITE_HOST = "https://www.bilibili.com"

RANK_URL = "https://www.bilibili.com/v/popular/rank/{part}"

PARTITIONS = {
    "all": "全站",
    "douga": "动画",
    "music": "音乐",
    "dance": "舞蹈",
    "game": "游戏",
    "knowledge": "知识",
    "tech": "科技",
    "sports": "运动",
    "car": "汽车",
    "life": "生活",
    "food": "美食",
    "animal": "动物圈",
    "kichiku": "鬼畜",
    "fashion": "时尚",
    "ent": "娱乐",
    "cinephile": "影视",
    "guochuang": "国创",
    "bangumi": "番剧",
    "movie": "电影",
    "tv": "电视剧",
}

DEFAULT_PARTITIONS = ["all", "douga", "game", "knowledge"]

MAX_PER_PARTITION = 30

PAGE_LOAD_WAIT = 2.5
ITEM_WAIT_TIMEOUT = 20
SCROLL_ROUNDS = 3
SCROLL_PAUSE = 1.0
PARTITION_GAP = 1.5

MAX_RETRY = 2
RETRY_WAIT = 3

BROWSER_HEADLESS = False
WINDOW_SIZE = "1440,900"

CSV_DETAIL = "榜单数据.csv"
CSV_LATEST = "最新榜单.csv"
CSV_CHANGE = "热度变动.csv"
CSV_SUMMARY = "统计报表.csv"
