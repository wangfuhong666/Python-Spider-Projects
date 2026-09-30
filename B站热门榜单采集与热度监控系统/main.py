import argparse
import csv
import os
import re
import time
from datetime import datetime

from DrissionPage import ChromiumOptions, ChromiumPage


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


def build_page(headless=None):
    if headless is None:
        headless = BROWSER_HEADLESS

    options = ChromiumOptions()
    options.headless(headless)
    options.set_argument("--window-size=" + WINDOW_SIZE)
    options.set_argument("--disable-gpu")
    options.set_argument("--mute-audio")
    options.set_argument("--no-first-run")
    options.set_argument("--disable-blink-features=AutomationControlled")

    page = ChromiumPage(options)
    page.set.timeouts(base=ITEM_WAIT_TIMEOUT)
    return page


def count_items(page):
    try:
        return int(page.run_js("return document.querySelectorAll('.rank-item').length") or 0)
    except Exception:
        return 0


def wait_items(page, timeout=None, stable_rounds=3):
    timeout = timeout or ITEM_WAIT_TIMEOUT
    deadline = time.time() + timeout
    last = -1
    hits = 0
    while time.time() < deadline:
        current = count_items(page)
        if current > 0 and current == last:
            hits += 1
            if hits >= stable_rounds:
                return current
        else:
            hits = 0
        last = current
        time.sleep(0.6)
    return last if last > 0 else 0


def scroll_to_load(page, rounds=None):
    rounds = rounds or SCROLL_ROUNDS
    for _ in range(rounds):
        try:
            page.scroll.to_bottom()
        except Exception:
            pass
        time.sleep(SCROLL_PAUSE)
    try:
        page.scroll.to_top()
    except Exception:
        pass
    time.sleep(0.5)


def _first(root, loc):
    try:
        found = root.eles(loc)
    except Exception:
        return None
    return found[0] if found else None


def _text(root, loc):
    ele = _first(root, loc)
    if ele is None:
        return ""
    try:
        return (ele.text or "").strip()
    except Exception:
        return ""


def _attr(root, loc, name, fallback=""):
    ele = _first(root, loc)
    if ele is None:
        return fallback
    try:
        return ele.attr(name) or fallback
    except Exception:
        return fallback


def parse_count(text):
    if not text:
        return 0
    text = str(text).strip().replace(",", "").replace(" ", "")
    if not text or text in ("-", "--", "无"):
        return 0
    if text.endswith("亿"):
        return int(float(text[:-1]) * 100000000)
    if text.endswith("万"):
        return int(float(text[:-1]) * 10000)
    match = re.search(r"\d+(\.\d+)?", text)
    return int(float(match.group(0))) if match else 0


def full_url(url):
    if not url:
        return ""
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        return SITE_HOST + url
    return url


def parse_card(item, part_code, part_name):
    title_ele = _first(item, "css:.info .title")
    title = ""
    href = ""
    if title_ele is not None:
        try:
            title = (title_ele.attr("title") or title_ele.text or "").strip()
        except Exception:
            title = ""
        try:
            href = title_ele.attr("href") or ""
        except Exception:
            href = ""

    if not title:
        title = _text(item, "css:.info .title")

    numbers = item.eles("css:.detail-state .data-box") or []
    values = []
    for node in numbers:
        try:
            values.append((node.text or "").strip())
        except Exception:
            values.append("")

    view_text = values[0] if len(values) > 0 else ""
    danmaku_text = values[1] if len(values) > 1 else ""

    views = parse_count(view_text)
    danmaku = parse_count(danmaku_text)
    rate = round(danmaku / views * 100, 3) if views else 0.0

    cover = _attr(item, "css:img.cover", "data-src")
    if not cover:
        cover = _attr(item, "css:img.cover", "src")

    bv = ""
    matched = re.search(r"(BV[0-9A-Za-z]+)", href or "")
    if matched:
        bv = matched.group(1)

    return {
        "排名": int(item.attr("data-rank") or 0),
        "分区": part_name,
        "标题": title,
        "UP主": _text(item, "css:.up-name"),
        "播放量": views,
        "弹幕数": danmaku,
        "互动率": rate,
        "BV号": bv,
        "封面": full_url(cover),
        "链接": full_url(href),
        "采集时间": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


def fetch_partition(page, part_code, limit=None, part_name=None):
    part_name = part_name or PARTITIONS.get(part_code, part_code)
    limit = limit or MAX_PER_PARTITION
    url = RANK_URL.format(part=part_code)

    print(f"[分区 {part_name}] 打开 {url}")
    page.get(url)
    time.sleep(PAGE_LOAD_WAIT)

    total = wait_items(page)
    if not total:
        print(f"[分区 {part_name}] 未等到榜单条目，跳过")
        return []

    print(f"[分区 {part_name}] 页面渲染出 {total} 条，滚动加载中 ...")
    scroll_to_load(page)

    items = page.eles("css:li.rank-item") or []
    print(f"[分区 {part_name}] 滚动后 DOM 内共 {len(items)} 条，取前 {min(limit, len(items))} 条")
    rows = []
    for item in items[:limit]:
        try:
            rows.append(parse_card(item, part_code, part_name))
        except Exception as exc:
            print(f"[分区 {part_name}] 某条解析失败：{exc}")

    print(f"[分区 {part_name}] 解析完成 {len(rows)} 条")
    return rows


def close_page(page):
    try:
        page.quit()
    except Exception:
        pass


HEAD = ["排名", "分区", "标题", "UP主", "播放量", "弹幕数", "互动率", "BV号", "封面", "链接", "采集时间"]


def format_count(value):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return str(value)
    if value >= 100000000:
        return f"{value / 100000000:.2f}亿"
    if value >= 10000:
        return f"{value / 10000:.1f}万"
    return str(value)


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


def record_key(row):
    return f"{row.get('分区', '')}|{row.get('BV号', '')}"


def load_rows(filename):
    file = _path(filename)
    if not os.path.exists(file):
        return {}

    result = {}
    with open(file, "r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if row.get("BV号"):
                result[record_key(row)] = row
    return result


def save_changes(changes):
    head = ["BV号", "标题", "分区", "UP主", "上次播放量", "本次播放量", "播放增量",
            "上次排名", "本次排名", "排名变化", "链接"]
    file = _path(CSV_CHANGE)
    with open(file, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(head)
        for item in changes:
            writer.writerow([item.get(k, "") for k in head])
    print(f"[存储] 热度变动 {len(changes)} 条 -> output/{CSV_CHANGE}")
    return file


def save_summary(summary_rows):
    file = _path(CSV_SUMMARY)
    with open(file, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["统计项", "结果"])
        for k, v in summary_rows:
            writer.writerow([k, v])
    print(f"[存储] 统计报表 -> output/{CSV_SUMMARY}")
    return file


def _to_int(value):
    try:
        return int(float(str(value).replace(",", "")))
    except (TypeError, ValueError):
        return 0


def compare_snapshots(old_rows, new_rows):
    changes = []

    for key, new_row in new_rows.items():
        old_row = old_rows.get(key)
        if not old_row:
            continue

        old_view = _to_int(old_row.get("播放量"))
        new_view = _to_int(new_row.get("播放量"))
        old_rank = _to_int(old_row.get("排名")) or 0
        new_rank = _to_int(new_row.get("排名")) or 0

        view_delta = new_view - old_view
        rank_delta = old_rank - new_rank

        if view_delta == 0 and rank_delta == 0:
            continue

        changes.append({
            "BV号": new_row.get("BV号", ""),
            "标题": new_row.get("标题", ""),
            "分区": new_row.get("分区", ""),
            "UP主": new_row.get("UP主", ""),
            "上次播放量": old_view,
            "本次播放量": new_view,
            "播放增量": view_delta,
            "上次排名": old_rank,
            "本次排名": new_rank,
            "排名变化": rank_delta,
            "链接": new_row.get("链接", ""),
        })

    changes.sort(key=lambda x: x["播放增量"], reverse=True)

    seen = set()
    unique = []
    for item in changes:
        bv = item.get("BV号") or item.get("标题", "")
        if bv in seen:
            continue
        seen.add(bv)
        unique.append(item)
    return unique


def _to_float(value):
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return 0.0


def normalize_rows(rows):
    result = []
    for r in rows:
        item = dict(r)
        item["播放量"] = _to_int(r.get("播放量"))
        item["弹幕数"] = _to_int(r.get("弹幕数"))
        item["排名"] = _to_int(r.get("排名"))
        item["互动率"] = _to_float(r.get("互动率"))
        result.append(item)
    return result


def dedup_by_bv(rows):
    seen = set()
    result = []
    for r in rows:
        key = r.get("BV号") or r.get("标题", "")
        if key in seen:
            continue
        seen.add(key)
        result.append(r)
    return result


def build_summary(rows):
    summary = []
    rows = normalize_rows(rows)
    if not rows:
        return summary

    views = [r["播放量"] for r in rows]
    views = [v for v in views if v > 0]
    danmaku = [r["弹幕数"] for r in rows]

    summary.append(("采集总数", len(rows)))
    summary.append(("覆盖分区数", len({r.get("分区", "") for r in rows if r.get("分区")})))
    summary.append(("UP主数量", len({r.get("UP主", "") for r in rows if r.get("UP主")})))

    if views:
        total = sum(views)
        summary.append(("总播放量", format_count(total)))
        summary.append(("平均播放量", format_count(int(total / len(views)))))
        summary.append(("最高播放量", format_count(max(views))))
        summary.append(("最低播放量", format_count(min(views))))

    summary.append(("总弹幕数", format_count(sum(danmaku))))

    for low, high, label in [(0, 100000, "0~10万"), (100000, 500000, "10万~50万"),
                             (500000, 1000000, "50万~100万"), (1000000, 5000000, "100万~500万"),
                             (5000000, 999999999999, "500万以上")]:
        summary.append((f"播放量区间 {label}", len([v for v in views if low < v <= high])))

    part_stat = {}
    for r in rows:
        part = r.get("分区", "")
        view = r.get("播放量", 0)
        if not part:
            continue
        item = part_stat.setdefault(part, {"count": 0, "total": 0})
        item["count"] += 1
        item["total"] += view

    ranked = sorted(part_stat.items(), key=lambda x: x[1]["total"], reverse=True)
    for i, (part, stat) in enumerate(ranked[:5], 1):
        avg = int(stat["total"] / stat["count"]) if stat["count"] else 0
        summary.append((f"分区热度TOP{i}", f"{part} 共{stat['count']}条 总播放{format_count(stat['total'])} 均{format_count(avg)}"))

    top_view = sorted(dedup_by_bv(rows), key=lambda x: x.get("播放量", 0), reverse=True)[:5]
    for i, r in enumerate(top_view, 1):
        summary.append((f"播放量TOP{i}", f"[{r.get('分区')}] {r.get('标题', '')[:26]} | {r.get('UP主')} | {format_count(r.get('播放量', 0))}"))

    top_rate = [r for r in dedup_by_bv(rows) if r.get("播放量", 0) > 100000]
    top_rate.sort(key=lambda x: x.get("互动率", 0), reverse=True)
    for i, r in enumerate(top_rate[:5], 1):
        summary.append((f"弹幕互动率TOP{i}", f"{r.get('标题', '')[:26]} | {r.get('互动率')}% | 弹幕{format_count(r.get('弹幕数', 0))}"))

    return summary


def print_report(rows, changes, summary):
    print("\n" + "=" * 64)
    print(" 哔哩哔哩热门榜单 · 热度监控运行报告")
    print("=" * 64)
    print(f"\n本次采集记录：{len(rows)} 条（去重后 {len(dedup_by_bv(rows))} 个视频）")

    if summary:
        print("\n【统计概览】")
        for k, v in summary:
            print(f"  {k:<18} {v}")

    if changes:
        up = [c for c in changes if c["播放增量"] > 0]
        rank_up = [c for c in changes if c["排名变化"] > 0]
        print(f"\n【热度变动】共 {len(changes)} 个视频变化：播放增长 {len(up)} 个 / 排名上升 {len(rank_up)} 个")
        for c in changes[:10]:
            rank_flag = f" 排名{c['上次排名']}→{c['本次排名']}" if c["排名变化"] else ""
            print(f"  +{format_count(c['播放增量'])} 播放{rank_flag} | {c['标题'][:22]}")
    else:
        print("\n【热度变动】暂无变动（首次运行或榜单未变化）")

    print("\n" + "=" * 64)


def run_report():
    new_rows = load_rows(CSV_DETAIL)
    old_rows = load_rows(CSV_LATEST)

    changes = compare_snapshots(old_rows, new_rows)
    summary = build_summary(list(new_rows.values()))

    save_changes(changes)
    save_summary(summary)
    print_report(list(new_rows.values()), changes, summary)

    rows = list(new_rows.values())
    if rows:
        save_rows(rows, CSV_LATEST)

    return changes, summary


def collect_once(parts=None, limit=None, headless=None):
    parts = parts or DEFAULT_PARTITIONS
    limit = limit or MAX_PER_PARTITION
    if headless is None:
        headless = BROWSER_HEADLESS

    print("=" * 64)
    print(" 哔哩哔哩热门榜单采集与热度监控系统")
    print("=" * 64)
    print(f"目标分区 {len(parts)} 个：{[PARTITIONS.get(p, p) for p in parts]}")
    print(f"每区最多取 {limit} 条")
    print(f"浏览器模式：{'无头' if headless else '可见窗口'}")

    page = build_page(headless)
    rows = []
    try:
        for i, part in enumerate(parts, 1):
            name = PARTITIONS.get(part, part)
            print(f"\n>>> [{i}/{len(parts)}] 分区 {name}")
            try:
                rows.extend(fetch_partition(page, part, limit=limit, part_name=name))
            except Exception as exc:
                print(f"[分区 {name}] 采集异常：{exc}")
            if i < len(parts):
                time.sleep(PARTITION_GAP)
    finally:
        close_page(page)

    return rows


def run_once(parts=None, limit=None, headless=None):
    start = time.time()
    rows = collect_once(parts, limit, headless)

    if not rows:
        print("\n[结束] 本次没有采集到任何数据")
        return

    save_rows(rows, CSV_DETAIL)
    run_report()
    print(f"\n[结束] 本次耗时 {time.time() - start:.1f} 秒")


def run_loop(interval, rounds, parts, limit, headless):
    ensure_output_dir()
    print("=" * 64)
    print(" 哔哩哔哩热门榜单 · 定时监控任务已启动")
    print(f" 采集间隔：{interval} 秒")
    print("=" * 64)

    round_no = 0
    while rounds == 0 or round_no < rounds:
        round_no += 1
        print(f"\n>>> 第 {round_no} 轮开始 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        try:
            run_once(parts, limit, headless)
        except Exception as exc:
            print(f"[异常] 第 {round_no} 轮采集出错：{exc}")
        print(f"<<< 第 {round_no} 轮结束，等待 {interval} 秒")
        time.sleep(interval)


def parse_parts(text):
    if not text:
        return list(DEFAULT_PARTITIONS)

    result = []
    for item in text.split(","):
        item = item.strip()
        if not item:
            continue
        if item in PARTITIONS:
            result.append(item)
        else:
            print(f"[警告] 未知分区标识 {item}，已忽略")
    return result or list(DEFAULT_PARTITIONS)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="哔哩哔哩热门榜单采集与热度监控系统")
    ap.add_argument("--loop", action="store_true", help="定时循环采集")
    ap.add_argument("--interval", type=int, default=1800, help="采集间隔秒数，默认 1800")
    ap.add_argument("--rounds", type=int, default=0, help="最多跑几轮，0 表示不限，默认 0")
    ap.add_argument("--top", type=int, default=0, help="每个分区最多取多少条，0 表示用配置默认值")
    ap.add_argument("--parts", type=str, default="", help="分区标识，逗号分隔，如 all,douga,game")
    ap.add_argument("--headless", action="store_true", help="无头模式运行（默认打开可见窗口）")
    args = ap.parse_args()

    chosen = parse_parts(args.parts)
    top_n = args.top or MAX_PER_PARTITION

    if args.loop:
        run_loop(args.interval, args.rounds, chosen, top_n, args.headless)
    else:
        run_once(chosen, top_n, args.headless)
