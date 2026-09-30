import re
import time

from DrissionPage import ChromiumOptions, ChromiumPage

import config


def build_page(headless=None):
    if headless is None:
        headless = config.BROWSER_HEADLESS

    options = ChromiumOptions()
    options.headless(headless)
    options.set_argument("--window-size=" + config.WINDOW_SIZE)
    options.set_argument("--disable-gpu")
    options.set_argument("--mute-audio")
    options.set_argument("--no-first-run")
    options.set_argument("--disable-blink-features=AutomationControlled")

    page = ChromiumPage(options)
    page.set.timeouts(base=config.ITEM_WAIT_TIMEOUT)
    return page


def count_items(page):
    try:
        return int(page.run_js("return document.querySelectorAll('.rank-item').length") or 0)
    except Exception:
        return 0


def wait_items(page, timeout=None, stable_rounds=3):
    timeout = timeout or config.ITEM_WAIT_TIMEOUT
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
    rounds = rounds or config.SCROLL_ROUNDS
    for _ in range(rounds):
        try:
            page.scroll.to_bottom()
        except Exception:
            pass
        time.sleep(config.SCROLL_PAUSE)
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
        return config.SITE_HOST + url
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
    part_name = part_name or config.PARTITIONS.get(part_code, part_code)
    limit = limit or config.MAX_PER_PARTITION
    url = config.RANK_URL.format(part=part_code)

    print(f"[分区 {part_name}] 打开 {url}")
    page.get(url)
    time.sleep(config.PAGE_LOAD_WAIT)

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
