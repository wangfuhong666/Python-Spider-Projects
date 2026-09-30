# 哔哩哔哩热门榜单采集与热度监控系统

基于 **DrissionPage 浏览器自动化** 的榜单数据采集与热度监控系统。驱动真实 Chrome 渲染页面，采集 B站 20 个分区的热门视频榜单，落盘 CSV，并对两轮采集做快照比对，输出播放量增长与排名变化。

> 本项目侧重展示 **自动化爬虫能力**：动态渲染等待、滚动加载、分区导航、真实浏览器环境驱动。

## 一、为什么必须用浏览器自动化

这不是"能用 requests 却故意用浏览器"，而是 **requests 在物理上拿不到数据**。实测对比：

| 方式 | 返回大小 | 页面内榜单条目 |
|---|---|---|
| `requests.get` 直接请求 | **4459 字节**（空壳页） | **0 条** |
| DrissionPage 驱动 Chrome 渲染后 | 1.3 MB | **100 条** |

榜单数据完全由前端 JS 在浏览器环境中渲染生成，服务端对非浏览器请求只返回骨架页面。
另外 B站 的数据接口带有 wbi 签名校验，直接构造请求需要额外逆向；**用真实浏览器驱动则天然携带完整运行环境，无需处理签名**——这正是自动化爬虫的核心价值。

## 二、技术栈

| 项 | 说明 |
|---|---|
| 语言 | Python 3.9+ |
| 核心库 | DrissionPage >= 4.1（驱动真实 Chrome） |
| 浏览器 | 本机 Google Chrome / Microsoft Edge |
| 存储 | CSV（`utf-8-sig`，Excel 直接打开不乱码） |
| 其他 | 仅标准库（csv / re / argparse / time） |

## 三、目录结构

```
B站热门榜单采集与热度监控系统/
├─ main.py               # 单文件实现：配置 + 浏览器驱动 + 字段解析 + 落盘比对 + 命令行入口
├─ requirements.txt      # 依赖清单
├─ output/               # 运行产出（不进仓库）
│  ├─ 榜单数据.csv        # 本轮采集明细
│  ├─ 最新榜单.csv        # 上一轮快照（用于下轮比对）
│  ├─ 热度变动.csv        # 播放量增长 / 排名变化
│  └─ 统计报表.csv        # 汇总指标
└─ README.md
```

> 全部逻辑收敛在单个 `main.py` 中（约 620 行），文件内按「配置 → 浏览器驱动 → 字段解析 → 落盘与比对 → 入口」分块组织，
> 既方便整体阅读，也便于单文件携带与迁移。

## 四、核心实现

### 1. 真实浏览器驱动

```python
options = ChromiumOptions()
options.headless(headless)
options.set_argument("--window-size=1440,900")
options.set_argument("--disable-blink-features=AutomationControlled")
page = ChromiumPage(options)
```

默认打开 **可见窗口**，便于观察采集过程与截图；`--headless` 可切换无头。

### 2. 动态渲染等待（关键）

不用固定 `sleep` 硬等，而是轮询条目数，**等它连续 3 次不再变化**才认为渲染完成：

```python
def wait_items(page, timeout=None, stable_rounds=3):
    deadline = time.time() + timeout
    last, hits = -1, 0
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
```

这一步是实测踩坑后加的：最初只等"条目数 > 0"就解析，导致冷启动的第一个分区只拿到 15 条（页面还在渲染）。改成等稳定后，每个分区稳定拿到完整 100 条。

### 3. 滚动加载

```python
def scroll_to_load(page, rounds=None):
    for _ in range(rounds):
        page.scroll.to_bottom()
        time.sleep(SCROLL_PAUSE)
    page.scroll.to_top()
```

驱动真实滚动触发懒加载图片与内容，采完回到顶部。

### 4. 分区导航

系统内置 20 个分区的标识与中文名映射，可自由组合采集：

```python
PARTITIONS = {"all": "全站", "douga": "动画", "music": "音乐", "dance": "舞蹈",
              "game": "游戏", "knowledge": "知识", "tech": "科技", ...}
```

`--parts all,douga,game,knowledge` 即采集全站 / 动画 / 游戏 / 知识四个分区。

### 5. 数值解析

B站 用中文单位展示数据，需要统一转成整数：

| 页面文本 | 解析结果 |
|---|---|
| `252.0万` | 2520000 |
| `1.2亿` | 120000000 |
| `2685` | 2685 |

### 6. 热度比对

以「**分区 + BV号**」为联合主键做两轮快照比对。

用联合主键是刻意的：同一条视频可能同时出现在多个分区的榜单上（例如某动画视频在「动画」分区排第 1、在「全站」排第 3），这两条是不同排名语境下的独立记录，不能用 BV号 单键合并。

```python
def record_key(row):
    return f"{row.get('分区', '')}|{row.get('BV号', '')}"
```

输出字段：播放量增量、排名变化。榜单排行本身按去重后的视频展示，避免同一视频重复占位。

## 五、采集字段

| 字段 | 说明 |
|---|---|
| 排名 | 该分区内的名次 |
| 分区 | 所属分区中文名 |
| 标题 | 视频标题 |
| UP主 | 上传者昵称 |
| 播放量 | 已解析为整数 |
| 弹幕数 | 已解析为整数 |
| 互动率 | 弹幕数 / 播放量（%），衡量内容互动密度 |
| BV号 | 视频唯一标识 |
| 封面 | 封面图地址 |
| 链接 | 视频详情页 |
| 采集时间 | 该条数据的采集时刻 |

## 六、运行方式

```bash
pip install -r requirements.txt

python main.py                                  # 默认 4 个分区，每区 30 条
python main.py --parts all,douga,game           # 指定分区
python main.py --top 50                          # 每区取 50 条
python main.py --headless                        # 无头模式
python main.py --loop --interval 1800 --rounds 4 # 每 30 分钟一轮，共 4 轮
```

**参数说明**

| 参数 | 默认 | 说明 |
|---|---|---|
| `--parts` | all,douga,game,knowledge | 分区标识，逗号分隔 |
| `--top` | 30 | 每个分区最多取多少条 |
| `--headless` | 关 | 开启无头模式（默认可见窗口） |
| `--loop` | 关 | 定时循环采集 |
| `--interval` | 1800 | 循环间隔秒数 |
| `--rounds` | 0 | 最多跑几轮，0 = 不限 |

**首次运行** `热度变动.csv` 只有表头是正常的——它需要上一轮快照做对比。
连跑第二次即可看到播放量增量；隔几小时再跑，排名变化也会显现。

## 七、容错设计

- 单个分区采集异常不影响其他分区，异常被捕获后继续
- 浏览器实例用 `try/finally` 保证退出时一定关闭，不残留进程
- 页面等待设超时上限，不会无限卡死
- 元素缺失返回空字符串而非抛异常，不会因个别字段缺失中断整轮

## 八、合规说明

- 全部数据来自 B站 公开的排行榜页面，仅供学习与研究使用
- 已内置滚动间隔与分区之间的停顿，避免对目标站造成压力
- 未触碰任何需要登录才能访问的内容
