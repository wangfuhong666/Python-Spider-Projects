# 外来物种入侵多网站政策文件采集

围绕「外来物种入侵」这一主题，从 **三个不同的政府站点** 采集相关政策文件，统一清洗成同一套字段后落盘 CSV，便于横向对照。

> 本项目侧重展示 **跨站点适配能力**：三个站点的检索入口、返回结构、字段命名完全不同，需要分别处理并归一到统一的输出格式。

## 一、覆盖的站点

| 站点 | 检索入口 | 数据来源 | 解析方式 |
|---|---|---|---|
| 农业农村部 | `fgs.moa.gov.cn` 站内搜索 | 第三方聚合搜索接口 `api.so-gov.cn/query/s`（POST） | 接口只返回 URL 列表，需逐篇二次请求原文，再用 **BeautifulSoup + 正则** 从正文中抽取字段 |
| 湖北省人民政府 | `www.hubei.gov.cn` 搜索页 | `igs/front/search/list.html`（GET，`siteId=50`） | 接口直接返回结构化 JSON，字段映射即可 |
| 湖北省林业局 | `lyj.hubei.gov.cn` 搜索页 | `igs/front/search/list.html`（GET，`siteId=39`） | 同上，并额外按域名白名单过滤非本站结果 |

两个湖北站点共用同一套 `igs` 搜索接口，仅 `siteId` / `index` 不同——这意味着同一份脚本可以很方便地扩展到更多厅局站点。

## 二、技术栈

| 项 | 说明 |
|---|---|
| 语言 | Python 3.9+ |
| 请求 | `requests`（Session 复用连接） |
| JSON 提取 | `jsonpath-ng`（从搜索接口响应里定位 URL 列表 / 内容数组） |
| HTML 解析 | `beautifulsoup4` + `lxml` |
| 文本抽取 | `re` 正则 |
| 存储 | CSV（`utf-8-sig`，Excel 直接打开不乱码） |

## 三、目录结构

```
外来物种入侵多网站/
├─ main.py               # 入口：按站点分发（argparse），依次调用下面的脚本
├─ moa.py                # 农业农村部
├─ hubei.py              # 湖北省人民政府
├─ hubei_forestry.py     # 湖北省林业局
├─ requirements.txt      # 依赖清单
└─ README.md
```

> 三个站点的采集脚本彼此独立、可单独运行；`main.py` 只负责参数分发与依次调用，不介入任何采集逻辑。
> 脚本按相对路径写 CSV，因此产出文件会落在项目目录下（`*.csv` 已被 `.gitignore` 排除，不进仓库）。

## 四、运行方式

```bash
pip install -r requirements.txt

python main.py             # 三个站点依次全部采集
python main.py moa         # 只采农业农村部
python main.py hubei       # 只采湖北省人民政府
python main.py forestry    # 只采湖北省林业局
```

三个脚本也可以单独运行：

```bash
python moa.py
python hubei.py
python hubei_forestry.py
```

## 五、输出字段

| 字段 | 说明 |
|---|---|
| 标题 | 政策文件标题 |
| 发文机关 | 发布该文件的机关 |
| 文号 | 公文字号，如 `农渔发〔2023〕5 号` |
| 年份 | 发布/成文年份 |
| url | 原文链接 |

## 六、实现要点

### 1. 正文抽取用「多级回退」，不赌单一选择器

政府网站模版老旧、各厅局不统一，`moa.py` 里标题按优先级依次尝试：

```
h1 → .title / .article-title / .article_title / .content-title / #title
  → <meta name="ArticleTitle"> → <meta property="og:title"> → <title>
```

发文机关、文号、年份同样各配多条正则；发文机关还额外做了「取正文最后 30 行、命中央/办/厅/局等关键字」的兜底扫描。

### 2. 文号正则要覆盖中文公文的各种写法

```
(?:文号|发文字号|文件编号)：xxx 号
xxx〔2023〕5 号 / xxx[2023]5 号
xxx令 2022 年第 3 号
```

### 3. 检索结果要过滤来源域名

`hubei_forestry.py` 的检索接口会混入其他站点的文件，代码里对 `DOCPUBURL` 做了 `lyj.hubei.gov.cn` 域名白名单过滤，避免把别家的文件算进林业局。

### 4. 字段名归一

三个站点的原始字段名完全不同（`FileName` / `publisher` / `fileNum` / `fileYear`），全部映射到统一的中文表头，三份 CSV 可以直接合并分析。

## 七、合规说明

- 采集内容为政府网站公开的政策文件信息，仅用于学习与研究
- 请求均携带规范的 `User-Agent` / `Referer`
- 未做高频请求，也未触碰任何需要登录才能访问的内容
