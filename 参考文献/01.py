import requests
url = "https://www.geophy.cn/dzdqs-data/cjg/2020/5/PDF/dqwlxb-63-5-2036.pdf"
res = requests.get(url)
print(res.status_code)