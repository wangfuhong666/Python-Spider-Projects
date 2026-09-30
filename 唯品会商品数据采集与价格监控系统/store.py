import csv
import os

import config
import core

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
        writer.writerow(core.HEAD)
        for row in rows:
            writer.writerow([row.get(k, "") for k in core.HEAD])
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
    file = _path(config.CHANGE_CSV)
    with open(file, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(head)
        for item in changes:
            writer.writerow([item.get(k, "") for k in head])
    print(f"[存储] 价格变动 {len(changes)} 条 -> output/{config.CHANGE_CSV}")
    return file

def save_summary(summary_rows):
    file = _path(config.SUMMARY_CSV)
    with open(file, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["统计项", "结果"])
        for k, v in summary_rows:
            writer.writerow([k, v])
    print(f"[存储] 统计报表 -> output/{config.SUMMARY_CSV}")
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
    new_rows = load_rows(config.PRODUCT_CSV)
    old_rows = load_rows(config.LATEST_CSV)

    changes = compare_snapshots(old_rows, new_rows)
    summary = build_summary(list(new_rows.values()))

    save_changes(changes)
    save_summary(summary)
    print_report(list(new_rows.values()), changes, summary)

    rows = list(new_rows.values())
    if rows:
        save_rows(rows, config.LATEST_CSV)

    return changes, summary
