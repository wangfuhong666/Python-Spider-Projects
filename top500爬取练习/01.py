import requests
from lxml import etree
import re

url = "https://www.top500.org/lists/top500/2026/06/"

headers = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "Pragma": "no-cache",
    "Referer": "https://www.top500.org/",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36 Edg/152.0.0.0",
    "sec-ch-ua": '"Chromium";v="152", "Not?A_Brand";v="24", "Microsoft Edge";v="152"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
}

cookies = {
    "django_language": "en",
    "_gid": "GA1.2.2038237298.1788848420",
    "_gat_gtag_UA_325590_1": "1",
    "_ga_H28RHN95R9": "GS2.1.s1788848419$o1$g1$t1788848444$j35$l0$h0",
    "_ga": "GA1.2.272369929.1788848420",
}

response = requests.get(
    url,
    headers=headers,
    cookies=cookies
)

response.encoding='utf-8'

# print(response.status_code)
# print(response.url)
# print(response.text)

tree = etree.HTML(response.text)

res=""

ps = tree.xpath(".//p")

for p in ps:
    res += re.sub(r"\s+", " ", p.xpath('./text()')[0])

print(res)

with open("res1.txt","w",encoding="utf-8") as f:
    f.write(res)