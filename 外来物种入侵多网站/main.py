"""外来物种入侵相关政策文件采集 —— 统一入口

三个站点各有一份互不依赖的独立脚本，既可以单独运行，也可以用本入口依次批量采集：

    python main.py moa        # 农业农村部
    python main.py hubei      # 湖北省人民政府
    python main.py forestry   # 湖北省林业局
    python main.py            # 不传参数 = all，依次采集全部三个站点

本文件只做「参数分发 + 依次调用」，不包含也不修改任何采集逻辑；
每个站点的实现分别是同目录下的 moa.py / hubei.py / hubei_forestry.py。
"""

import argparse
import os
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 站点标识 -> (中文名, 脚本文件名, 产出 CSV)
SITES = {
    "moa": ("农业农村部", "moa.py", "农业农村部官网政策文件.csv"),
    "hubei": ("湖北省人民政府", "hubei.py", "湖北政策文件.csv"),
    "forestry": ("湖北省林业局", "hubei_forestry.py", "湖北省林业局政策文件.csv"),
}


def run_site(key):
    """在项目目录下以子进程方式运行指定站点的采集脚本，返回是否成功。"""
    name, script, csv_name = SITES[key]

    print()
    print("=" * 64)
    print("[站点] {}  ({})".format(name, script))
    print("=" * 64)

    result = subprocess.run(
        [sys.executable, os.path.join(BASE_DIR, script)],
        cwd=BASE_DIR,
    )

    if result.returncode != 0:
        print("[失败] {} 异常退出（退出码 {}），继续后续站点".format(name, result.returncode))
        return False

    print("[完成] {}，产出：{}".format(name, csv_name))
    return True


def main():
    parser = argparse.ArgumentParser(
        description="外来物种入侵相关政策文件采集（多站点）"
    )
    parser.add_argument(
        "site",
        nargs="?",
        default="all",
        choices=list(SITES) + ["all"],
        help="要采集的站点，默认 all（全部依次采集）",
    )
    args = parser.parse_args()

    keys = list(SITES) if args.site == "all" else [args.site]

    done = sum(1 for key in keys if run_site(key))

    print()
    print("=" * 64)
    print("全部结束：成功 {} / 共 {} 个站点".format(done, len(keys)))


if __name__ == "__main__":
    main()
