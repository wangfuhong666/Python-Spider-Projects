import csv
import os

import config

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
    if not os.path.exists(config.OUTPUT_DIR):
        os.makedirs(config.OUTPUT_DIR)
    return config.OUTPUT_DIR


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
    file = _path(config.CSV_CHANGE)
    with open(file, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(head)
        for item in changes:
            writer.writerow([item.get(k, "") for k in head])
    print(f"[存储] 热度变动 {len(changes)} 条 -> output/{config.CSV_CHANGE}")
    return file


def save_summary(summary_rows):
    file = _path(config.CSV_SUMMARY)
    with open(file, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["统计项", "结果"])
        for k, v in summary_rows:
            writer.writerow([k, v])
    print(f"[存储] 统计报表 -> output/{config.CSV_SUMMARY}")
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
    new_rows = load_rows(config.CSV_DETAIL)
    old_rows = load_rows(config.CSV_LATEST)

    changes = compare_snapshots(old_rows, new_rows)
    summary = build_summary(list(new_rows.values()))

    save_changes(changes)
    save_summary(summary)
    print_report(list(new_rows.values()), changes, summary)

    rows = list(new_rows.values())
    if rows:
        save_rows(rows, config.CSV_LATEST)

    return changes, summary
