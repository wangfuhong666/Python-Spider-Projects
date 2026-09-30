import requests
import csv
from jsonpath_ng import parse


def jsonpath(data, expr):
    return [x.value for x in parse(expr).find(data)]


session = requests.Session()

url = "https://lyj.hubei.gov.cn/igs/front/search/list.html"

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/153.0.0.0 Safari/537.36"
    ),
    "Referer": "https://lyj.hubei.gov.cn/site/lyj/search.html"
}

params = {
    "filter[FileName,DOCCONTENT,fileNum-or]": "外来物种入侵",
    "pageNumber": "1",
    "pageSize": "100",
    "siteId": "39",
    "index": "hbsrmzf-index-alias",
    "type": "governmentdocuments",
    "filter[CHNLDESC]": "",
    "filter[fileYear]": "",
    "filter[fileYear-lte]": "",
    "filter[SITEID]": "",
    "filter[CNAME]": "",
    "orderProperty": "PUBDATE",
    "orderDirection": "desc"
}

response = session.get(
    url,
    headers=headers,
    params=params,
    timeout=10
)

print(response.status_code)
print(response.text)

res = response.json()

data = jsonpath(res, "$..content[*]")

result = []

for item in data:

    policy_url = item.get("DOCPUBURL") or ""

    if "lyj.hubei.gov.cn" not in policy_url:
        continue

    title = item.get("FileName") or ""
    agency = item.get("publisher") or ""
    doc_number = item.get("fileNum") or ""
    year = item.get("fileYear") or ""

    row = {
        "标题": title,
        "发文机关": agency,
        "文号": doc_number,
        "年份": year,
        "url": policy_url
    }

    result.append(row)

    print(row)

with open(
    "湖北省林业局政策文件.csv",
    "w",
    newline="",
    encoding="utf-8-sig"
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=[
            "标题",
            "发文机关",
            "文号",
            "年份",
            "url"
        ]
    )

    writer.writeheader()
    writer.writerows(result)

print("完成，共保存", len(result), "条数据")