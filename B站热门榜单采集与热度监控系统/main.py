import argparse
import time
from datetime import datetime

import config
import core
import store


def collect_once(parts=None, limit=None, headless=None):
    parts = parts or config.DEFAULT_PARTITIONS
    limit = limit or config.MAX_PER_PARTITION
    if headless is None:
        headless = config.BROWSER_HEADLESS

    print("=" * 64)
    print(" 哔哩哔哩热门榜单采集与热度监控系统")
    print("=" * 64)
    print(f"目标分区 {len(parts)} 个：{[config.PARTITIONS.get(p, p) for p in parts]}")
    print(f"每区最多取 {limit} 条")
    print(f"浏览器模式：{'无头' if headless else '可见窗口'}")

    page = core.build_page(headless)
    rows = []
    try:
        for i, part in enumerate(parts, 1):
            name = config.PARTITIONS.get(part, part)
            print(f"\n>>> [{i}/{len(parts)}] 分区 {name}")
            try:
                rows.extend(core.fetch_partition(page, part, limit=limit, part_name=name))
            except Exception as exc:
                print(f"[分区 {name}] 采集异常：{exc}")
            if i < len(parts):
                time.sleep(config.PARTITION_GAP)
    finally:
        core.close_page(page)

    return rows


def run_once(parts=None, limit=None, headless=None):
    start = time.time()
    rows = collect_once(parts, limit, headless)

    if not rows:
        print("\n[结束] 本次没有采集到任何数据")
        return

    store.save_rows(rows, config.CSV_DETAIL)
    store.run_report()
    print(f"\n[结束] 本次耗时 {time.time() - start:.1f} 秒")


def run_loop(interval, rounds, parts, limit, headless):
    store.ensure_output_dir()
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
        return list(config.DEFAULT_PARTITIONS)

    result = []
    for item in text.split(","):
        item = item.strip()
        if not item:
            continue
        if item in config.PARTITIONS:
            result.append(item)
        else:
            print(f"[警告] 未知分区标识 {item}，已忽略")
    return result or list(config.DEFAULT_PARTITIONS)


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
    top_n = args.top or config.MAX_PER_PARTITION

    if args.loop:
        run_loop(args.interval, args.rounds, chosen, top_n, args.headless)
    else:
        run_once(chosen, top_n, args.headless)
