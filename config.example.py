# -*- coding: utf-8 -*-
"""
配置文件模板(已按慧博 sysdw.hibor.com.cn 的实际结构写好)
=========================================================
用法:把本文件复制成 config.py,只需要填最上面 ★ 那几项(从抓包里拿)。
其余(接口地址、参数、网页解析)都已经配好,一般不用动。

config.py 已在 .gitignore 里,不会被上传,你的 Cookie / token 不会泄露。
"""

# ===========================================================================
# ★ 需要你从抓包里填的东西(这些会过期,如果哪天跑不动了,重抓一次这几项即可)
#   都在你之前抓到的那条请求里:
#   - Cookie:      在"请求头"里的 Cookie: 后面那一整段
#   - abc/def/...: 在"请求体(最底下那行)"里,形如 abc=... def=... 的值
# ===========================================================================
COOKIE = "safedog-flow-item=在这里粘贴你的Cookie值"
ABC  = "填 abc 的值"
DEF  = "填 def 的值"
VIDD = "填 vidd 的值"       # 你抓到的是 5
KEYY = "填 keyy 的值"
XYZ  = "填 xyz 的值"

# ===========================================================================
# 搜索条件(和你在慧博里搜的保持一致)
# ===========================================================================
KEYWORD = "华创证券"          # 关键词
DATE_START = "2026-01-01"     # 起始日期
DATE_END = "2026-07-25"       # 结束日期
TOTAL_PAGES = 31              # 一共多少页(你的是 31)

# 过滤(安全网,防止个别不相关结果混进来;用"包含"匹配,不想过滤就设 "")
FILTER_ORG = "华创证券"
FILTER_CATEGORY = "宏观经济"

# ===========================================================================
# 以下一般不用改
# ===========================================================================
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/66.0.3359.181 Safari/537.36",
    "Accept": "*/*",
    "Origin": "https://sysdw.hibor.com.cn",
    "Referer": "https://sysdw.hibor.com.cn/huisouchrome/s",
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Cookie": COOKIE,
}

LIST_URL = "https://sysdw.hibor.com.cn/huisouchrome/sa"
LIST_METHOD = "POST"
LIST_PARAMS = {
    "gjc":  KEYWORD,
    "sslb": "1",
    "sjfw": f"zdy|{DATE_START}|{DATE_END}",
    "ys":   "{page}",            # 页码占位符,程序自动替换成 1,2,3…,别改
    "cxzd": "qb(qw)",
    "px":   "zh",
    "bgfl": "13",                # 宏观经济分类
    "bgys": "", "gs": "", "sdgs": "", "sdhy": "", "sdhgcl": "",
    "mhss": "", "hy": "", "gp": "", "jg": "",
    "abc": ABC, "def": DEF, "vidd": VIDD, "keyy": KEYY, "xyz": XYZ,
    "op": "0",
}


def parse_list_response(resp, page):
    """
    从搜索返回的网页里,解析出这一页每篇研报的信息。
    (已按 sysdw.hibor.com.cn 返回的 HTML 结构写好,一般不用动。)
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        raise SystemExit("缺少 beautifulsoup4,请先运行:pip install beautifulsoup4")

    resp.encoding = "utf-8"
    soup = BeautifulSoup(resp.text, "html.parser")
    result = []

    for item in soup.select("div.result-dataitem"):
        a = item.select_one("a.doc-title")
        if not a:
            continue

        # 报告 id:标题链接的 id 形如 "yue5154971"
        rid = (a.get("id") or "").replace("yue", "").strip()
        title = a.get_text(strip=True)

        # 两个 result-data1:第一个含分类,第二个含发布日期
        data1 = item.select("div.result-data1")
        category = ""
        if data1:
            sp = data1[0].select_one("span.right30")
            category = sp.get_text(strip=True) if sp else ""
        date = ""
        if len(data1) > 1:
            sp = data1[1].select_one("span.right30")
            date = sp.get_text(strip=True) if sp else ""

        # 机构:作者图标的 data 属性形如 "张瑜|华创证券"
        org = ""
        ai = item.select_one("i.author-img")
        if ai and ai.get("data"):
            org = ai["data"].split("|")[-1].strip()
        if not org and "-" in title:
            org = title.split("-", 1)[0]

        # 下载链接:rdc-wrap 里 onclick 含 downloadClick 的那个 <a>
        download_url = ""
        for link in item.select("div.rdc-wrap a"):
            if "downloadClick" in (link.get("onclick") or ""):
                download_url = link.get("href", "")   # 该地址会 302 跳转到真正的 PDF
                break

        if rid and download_url:
            result.append({
                "id": rid,
                "title": title,
                "org": org,
                "category": category,
                "date": date,
                "download_url": download_url,
            })

    return result


# ===========================================================================
# 限速参数 —— 默认已经很稳,数字越大越慢越安全
# ===========================================================================
MIN_DELAY = 8            # 每篇之间最少等几秒
MAX_DELAY = 20           # 每篇之间最多等几秒(在两者之间随机)
BATCH_SIZE = 12          # 每下这么多篇
BATCH_REST = (60, 180)   # 就多歇 60~180 秒
HOURLY_CAP = 120         # 每小时最多下多少篇
CIRCUIT_BREAK = 3        # 连续失败几次就自动整体停止

# 下载保存目录:
#   - 默认存到程序所在文件夹下的 downloads 里。
#   - 想存到别的位置,写"绝对路径",并且在引号前加一个 r
#     (r 表示原样处理,别让路径里的反斜杠 \ 捣乱)。例如:
#         OUT_DIR = r"D:\研报\华创宏观"
#   - 文件夹不存在会自动创建,不用手动新建。
OUT_DIR = "downloads"
