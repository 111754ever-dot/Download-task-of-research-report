# -*- coding: utf-8 -*-
"""
下载诊断:只对 manifest 里的第一篇发一次下载请求,
把服务器到底返回了什么看清楚(便于判断为何不是 PDF)。
用法:python debug_download.py
"""
import csv
import requests
import config

url = title = None
with open("manifest.csv", encoding="utf-8-sig", newline="") as f:
    for r in csv.DictReader(f):
        url, title = r["download_url"], r["title"]
        break

if not url:
    raise SystemExit("manifest.csv 里没有记录,请先运行:python downloader.py manifest")

print("标题   :", title)
print("下载URL:", url)
print("=" * 70)

s = requests.Session()
s.headers.update(config.HEADERS)
resp = s.get(url, timeout=(10, 120), allow_redirects=True)

print("最终状态码:", resp.status_code)
print("最终地址  :", resp.url)
print("内容类型  :", resp.headers.get("Content-Type"))
print("内容长度  :", resp.headers.get("Content-Length"))
print("-- 跳转过程(每一跳)--")
for h in resp.history:
    print(f"   {h.status_code}  ->  {h.headers.get('Location', '')}")
if not resp.history:
    print("   (没有发生跳转)")
print("-- 本次会话拿到的 Cookie --")
for c in s.cookies:
    print(f"   {c.domain}  {c.name}={str(c.value)[:24]}...")
print("=" * 70)

body = resp.content
if body[:5].startswith(b"%PDF"):
    print(f"结果:这是 PDF!({len(body)} 字节)—— 说明可以下载,是别的原因")
else:
    resp.encoding = resp.apparent_encoding or "utf-8"
    text = resp.text
    with open("debug_response.html", "w", encoding="utf-8") as f:
        f.write(text)
    print("结果:不是 PDF。服务器返回的网页开头如下(前 1500 字):")
    print("-" * 70)
    print(text[:1500])
    print("-" * 70)
    print("完整内容已保存到 debug_response.html")
