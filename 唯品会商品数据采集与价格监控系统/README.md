# 唯品会商品数据采集与价格监控系统

> 单一站点（唯品会 vip.com）的商品数据采集与价格异动监控系统
> 技术路线：**requests + JS 逆向**，不使用任何浏览器自动化（无 Selenium / Playwright）

---

## 一、这个项目解决什么问题

电商运营、品牌供应商、代购分销群体都需要持续盯住**竞品价格**：谁降价了、降了多少、促销什么时候开始。人工看页效率极低，而商品价格藏在 App / WAP 的加密接口后面，直接请求会被风控拦

```
{"msg":"Forbidden by TFS","code":11000}
```

本项目通过**逆向还原前端加签算法**，用纯 Python 请求驱动整个链路，实现：

- 自动发现监控目标（从频道流抓取品牌 ID）
- 按品牌分页拉取商品列表
- 逐个拉取商品详情（标题 / 售价 / 原价 / 折扣 / 主图）
- 落盘 CSV，并与上一次采集自动比对，**产出降价榜与价格异常报表**
- 定时任务支持，天然可做"每日价格巡检"

---

## 二、目录结构

```
唯品会商品数据采集与价格监控系统/
├─ README.md              # 项目说明
├─ requirements.txt       # 依赖清单
├─ main.py                # 单文件实现：加签 + 请求 + 解析 + 落盘比价 + 入口
├─ vip_apisign.js         # ★ JS 逆向产物：加签算法源码（供独立查阅 / 复用）
└─ output/                # 运行结果（CSV 快照 / 价格变动 / 统计报表）
```

> 全部逻辑收敛在单个 `main.py` 中：加签算法以 `JS_CODE` 常量内嵌其中，
> 文件内按「配置 → 加签与请求 → 接口与解析 → 落盘与比价 → 入口」分块组织，便于整体阅读，也便于单文件携带与迁移。
> 同目录的 `vip_apisign.js` 是加签算法的独立源码文件，便于单独查阅与复用；`main.py` 运行时不依赖它。

---

## 三、快速开始

```bash
# 1. 安装依赖（需要本机有 Node.js 运行时，用于执行 JS）
pip install -r requirements.txt

# 2. 一键采集
python main.py

# 3. 定时监控（默认每 3600 秒一轮）
python main.py --loop --interval 3600
```

> 加签算法依赖 Node 的 `crypto` 模块，Python 侧通过 `execjs` 调用，因此运行环境需要 Node.js（已内嵌进 `main.py`，无需单独加载 JS 文件）。

产出文件在 `output/` 下：

| 文件 | 内容 |
|---|---|
| `商品数据.csv` | 本次采集到的商品明细 |
| `最新价格.csv` | 上一轮结果，作为比价基线 |
| `价格变动.csv` | 本次 vs 上次的降价 / 涨价明细 |
| `统计报表.csv` | 价格分布、折扣 TOP5 等统计结果 |

---

## 四、核心难点：接口加签（JS 逆向全过程）

这是本项目真正的技术含量所在。唯品会 WAP 端所有业务接口都要求带

```
Authorization: OAuth api_sign=xxxxxxxx
```

签名不对就返回 `API signature must not be empty` / `Invalid API signature`。

### 4.1 逆向链路

| 步骤 | 内容 | 来源 |
|---|---|---|
| 1 | 定位加签函数 | 前端打包文件 `index.eec28ca9.js`，webpack 模块 `e7ec`（`signReq`） |
| 2 | 拿到签名密钥密文 | 同一文件内的常量 `Ql4mW09F3urBNdzBLfK6UuRTqj22Bta7eEKTO7n5jFf9uU6FZZmcfe/gurOAOB+o` |
| 3 | 还原密钥解密方式 | 模块 `c71e`：`AES-CBC`，key = `weixin_smallmina`，iv = `weixin`（补零至 16 字节） |
| 4 | 解出明文密钥 | `34d522d657ed4badb86721f0ce6eaf52` |
| 5 | 还原参数哈希 | 模块 `e7ec` 的 `L / P` 函数：key 升序 → 剔除 `api_key` → `k=v` 拼接 → SHA1 |
| 6 | 拆解 VMP 虚拟机 | 模块 `7460` 的 `DynamicVM`，字节码只有 4 条指令：`读变量入栈 / 拼接 / SHA1 / 结束` |
| 7 | 得出最终公式 | `sign = SHA1(路径 + 参数哈希 + VIP_TANK + mars_cid + secret)` |

### 4.2 为什么 "VMP 加签" 也能被还原

前端为新版请求启用了 VMP（虚拟指令保护），字节码为：

```
AQN1cmwBCXBhcmFtSGFzaAIBB3ZpcHRhbmsCAQNjaWQCAQZzZWNyZXQCoQ==
```

解码后是四条指令的序列：`url → paramHash → viptank → cid → secret` 依次入栈并拼接，最后执行一次 SHA1。

也就是说：**虚拟机只是把明文公式藏成了字节码**，抽出指令表后，其行为与旧版 `SHA1(url + paramHash + viptank + cid + secret)` 完全等价。这也是本项目能脱离浏览器运行的原因。

### 4.3 踩到的坑

- **请求参数里的 `mars_cid` 必须和 Cookie 里的 `mars_cid` 一致**，否则风控直接判定伪造，返回 `Forbidden by TFS(11000)`。代码里通过 `config.mars_cid_from_cookie()` 自动同步。
- 采集频率过高会触发 TFS 风控，项目内实现了随机限速 + 触发后冷却重试 + 连续失败体面收工三层策略，**已经拿到的数据不会丢**。

---

## 五、用到的接口（单一站点，全部失败可降级）

| 用途 | 接口 | 说明 |
|---|---|---|
| 发现品牌 | `/vips-mobile/rest/layout/h5/channel/data` | 从频道楼层里提取 `brand_id` |
| 商品列表 | `/vips-mobile/rest/shopping/wx/product/list/rank/v1` | 按 `brandId` 分页返回商品 ID |
| 商品详情 | `/vips-mobile/rest/shopping/wx/share/product/v2` | 标题、售价、原价、折扣、主图 |
| 关键词联想 | `/vips-mobile/rest/shopping/wx/search/suggest` | 备用扩展点（同样复用本项目的加签） |

数据字段：`商品ID / 标题 / 品牌 / 售价 / 原价 / 折扣 / 卖点 / 主图 / 详情链接`

---

## 六、采集结果示例

```
[详情 1/60] 6920974265204806159 -> 94.0 元  安德玛 | 男士短袖T恤圆领舒适透气休闲
[详情 2/60] 6920801885475589662 -> 189.0 元 彪马 | PUMA彪马男装女装情侣户外运动
[详情 3/60] 6918902419279150167 -> 236.0 元 Nike | WEARALLDAY 轻便

【统计概览】
  采集总数                     30
  品牌数量                     21
  最低价                       36.0
  最高价                       473.0
  平均价                       178.63
  价格区间 0~100               9
  价格区间 100~300             13
  价格区间 300~800             8
  折扣力度TOP1    xxx 1.9折 现价47 原价249
```

---

## 七、合规声明

- 本项目为技术学习与接口协议研究用途，采集对象为唯品会 WAP 端公开展示的商品信息
- 内置限速策略，单次运行请求量可控，不对目标站点造成压力
- 不得用于任何商业用途或违反目标站点服务条款的行为，由此产生的责任由使用者自行承担
