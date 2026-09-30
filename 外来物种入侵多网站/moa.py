import requests
from jsonpath_ng import parse
import csv
import re
from bs4 import BeautifulSoup
def clean_text(text):
    if not text:
        return ''
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def get_title(soup):
    h1 = soup.find('h1')
    if h1:
        title = clean_text(h1.get_text())
        if title:
            return title

    selectors = [
        '.title',
        '.article-title',
        '.article_title',
        '.content-title',
        '.content_title',
        '#title'
    ]

    for selector in selectors:
        node = soup.select_one(selector)
        if node:
            title = clean_text(node.get_text())
            if title:
                return title

    meta = soup.find('meta', attrs={'name': 'ArticleTitle'})
    if meta and meta.get('content'):
        return clean_text(meta['content'])

    meta = soup.find('meta', attrs={'property': 'og:title'})
    if meta and meta.get('content'):
        return clean_text(meta['content'])

    if soup.title:
        return clean_text(soup.title.get_text())

    return ''


def get_doc_number(text):
    patterns = [
        r'(?:文号|发文字号|文件编号)\s*[：:]\s*([^\n，。；]{2,50}号)',

        r'([A-Za-z\u4e00-\u9fa5]{0,20}'
        r'[〔\[][^〕\]\n]{1,20}[〕\]]'
        r'\s*(?:第)?[A-Za-z0-9一二三四五六七八九十百千万]+号)',

        r'([〔\[][^〕\]\n]{1,20}[〕\]]'
        r'\s*第[A-Za-z0-9一二三四五六七八九十百千万]+号)',

        r'([A-Za-z\u4e00-\u9fa5]{2,30}令\s*'
        r'(?:20\d{2}年)?\s*第'
        r'[A-Za-z0-9一二三四五六七八九十百千万]+号)'
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return clean_text(match.group(1))

    return ''


def get_agency(text):
    patterns = [
        r'(?:发文机关|发布机构|制定机关|颁布机关)\s*[：:]\s*([^\n，。；]{2,60})',

        r'([^\n，。；]{2,50}'
        r'(?:人民代表大会常务委员会|人民政府|委员会|国务院|'
        r'农业农村部|办公厅|办公室|厅|局))\s*(?:公告|通告|通知|令)'
    ]

    for pattern in patterns:
        match = re.search(pattern, text)

        if match:
            agency = clean_text(match.group(1))

            if len(agency) <= 60:
                return agency

    lines = text.splitlines()

    keywords = [
        '人民代表大会常务委员会',
        '人民政府',
        '委员会',
        '国务院',
        '农业农村部',
        '办公厅',
        '办公室',
        '厅',
        '局'
    ]

    for line in reversed(lines[-30:]):
        line = clean_text(line)

        if 2 <= len(line) <= 50:
            for keyword in keywords:
                if keyword in line:
                    return line

    return ''


def get_year(text, url):
    patterns = [
        r'(?:发布时间|发布日期|成文日期|印发日期)\s*[：:]?\s*(20\d{2})',
        r'(20\d{2})年\d{1,2}月\d{1,2}日'
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)

    match = re.search(r'(20\d{2})\d{2}', url)

    if match:
        return match.group(1)

    return ''

def jsonpath(data, expr):
    return [x.value for x in parse(expr).find(data)]
url = "https://api.so-gov.cn/query/s"

headers = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Origin": "https://fgs.moa.gov.cn",
    "Referer": "https://fgs.moa.gov.cn/",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/153.0.0.0 Safari/537.36"
    ),
}

data = {
    "siteCode": "fgs_moa",
    "tab": "all",
    "qt": "外来物种入侵",
    "keyPlace": "0",
    "sort": "relevance",
    "fileType": "",
    "timeOption": "0",
    "page": "1",
    "pageSize": "20",
    "ie": "31b38b02-1661-448c-b812-4f745b3c77b5",
}

session = requests.Session()

response = session.post(
    url,
    headers=headers,
    data=data,
    timeout=10,
)

print(response.status_code)
print(response.text)
res = response.json()
data = jsonpath(res,'$..url')
data = list(set(data))
result = []

for url in data:
    try:
        response = session.get(
            url,
            headers=headers,
            timeout=10
        )

        response.encoding = response.apparent_encoding

        soup = BeautifulSoup(
            response.text,
            'lxml'
        )

        text = soup.get_text(
            '\n',
            strip=True
        )

        title = get_title(soup)
        agency = get_agency(text)
        doc_number = get_doc_number(text)
        year = get_year(text, url)

        item = {
            '标题': title,
            '发文机关': agency,
            '文号': doc_number,
            '年份': year,
            'url': url
        }

        result.append(item)

        print(item)

    except Exception as e:
        print(url, '获取失败：', e)
with open(
    '农业农村部官网政策文件.csv',
    'w',
    newline='',
    encoding='utf-8-sig'
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=[
            '标题',
            '发文机关',
            '文号',
            '年份',
            'url'
        ]
    )

    writer.writeheader()
    writer.writerows(result)