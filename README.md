# Python 爬虫项目

个人爬虫实战项目合集。每个子目录都是一个独立完成的小项目，覆盖 requests 静态抓取、xpath/jsonpath 解析、浏览器自动化（DrissionPage）、JS 逆向还原加签、音视频分离下载等方向。

配套的**章节笔记与知识点练习**在另一个仓库：[python-spider](https://github.com/wangfuhong666/python-spider)。
本仓库只放**综合实战项目**。

---

## 项目索引

| # | 项目 | 技术路线 | 核心内容 |
|---|---|---|---|
| 01 | [B站热门榜单采集与热度监控系统](./B站热门榜单采集与热度监控系统) | **DrissionPage 浏览器自动化** | 驱动真实 Chrome 采集 B站 20 个分区热门榜单（100 条/分区），落盘 CSV，两轮快照比对输出播放量增长与排名变化 |
| 02 | [唯品会商品数据采集与价格监控系统](./唯品会商品数据采集与价格监控系统) | **requests + JS 逆向** | PyExecJS 调用还原后的 `vip_apisign.js` 生成加签绕过风控，实现品牌商品分页采集与价格异动监控 |
| 03 | [第38届 IOI 2026 官方实时成绩排行榜](./第38届国际信息学奥林匹克%20IOI%202026%20官方实时成绩排行榜信息) | 两种实现**对照** | 同一目标下「普通爬虫（不行）」与「自动化爬虫」的对比，直观展示动态渲染页面下 requests 与浏览器自动化的差距 |
| 04 | [视频爬取练习](./视频爬取练习) | **JS 逆向 + 音视频处理** | 逆向视频站点的解密逻辑（`decrypt.js` / `decrypt_video.js`），分离下载音视频流后合并 |
| 05 | [外来物种入侵多网站](./外来物种入侵多网站) | requests + jsonpath + BeautifulSoup | 跨多个政府站点（农业农村部、湖北省、湖北省林业局）采集政策文件，统一清洗后输出 CSV |
| 06 | [摸头表情包自动处理](./摸头表情包自动处理) | DrissionPage | 批量把 `image/` 中的图片提交给在线 petpet 生成器，回存摸头 GIF 到 `output/` |
| 07 | [top500爬取练习](./top500爬取练习) | requests + lxml + 正则 | TOP500 超算榜单抓取练习 |
| 08 | [参考文献](./参考文献) | requests | 期刊 PDF 直链下载练习 |

---

## 目录约定

```
Python 爬虫项目/
├─ <项目名>/
│  ├─ README.md          # 项目说明（目标站点 / 难点 / 用法）
│  ├─ main.py            # 入口
│  ├─ config.py          # 站点参数与请求头
│  ├─ core.py / store.py # 采集逻辑 / 落盘与比对
│  ├─ requirements.txt   # 该项目依赖
│  └─ output/            # 采集产出（CSV、图片），不进仓库
└─ .gitignore
```

**仓库只保留代码。** 采集产出（CSV / XLSX / 图片 / 音视频）体积大且涉及版权，统一由 `.gitignore` 排除，需要数据请本地跑一遍脚本。

---

## 环境

- Python 3.9+
- 主要依赖：

| 依赖 | 用途 |
| --- | --- |
| `requests` | 静态接口抓取，用得最多 |
| `DrissionPage` | 浏览器自动化（需本机有 Chrome / Edge） |
| `PyExecJS` | 在 Python 中执行 JS，JS 逆向的核心工具（需本机装 Node.js） |
| `lxml` | xpath 解析 HTML |
| `jsonpath-ng` | 从 JSON 响应按表达式提取数据 |
| `beautifulsoup4` | HTML 解析 |
| `openpyxl` | 读写 Excel |

各项目依赖以其目录下的 `requirements.txt` 为准。

---

## 说明

- 所有项目仅用于个人技术学习，采集内容均为公开可访问信息，未触碰需要登录才能访问的私有内容。
- 代码中的请求频率均做了主动限制（`SLEEP_MIN` / `SLEEP_MAX`），避免对目标站点造成压力。
- 部分项目（如唯品会）依赖站点加签算法，站点改版后可能失效。
- 唯品会 `config.py` 中的默认 Cookie 仅为本地跑通用的历史值，已失效；实际使用时可用同目录 `cookie.txt` 覆盖。
