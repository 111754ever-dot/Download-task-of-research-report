# -*- coding: utf-8 -*-
"""
配置文件模板
============
用法:把本文件复制成 config.py,然后填写下面几处。
(config.py 已在 .gitignore 里,不会被提交,你的 Cookie 不会泄露。)

你只需要抓两个请求:
  ① 列表(搜索)接口 —— 在慧博里翻页时发出的那个请求
  ② 下载接口       —— 点"下载"时发出的那个请求
把它们填到对应位置即可。抓包方法见 README.md。
"""

# ===========================================================================
# 1) 登录凭证 —— 从抓到的任意一个请求的 "请求头(Request Headers)" 里复制
#    最关键的是 Cookie 整行。User-Agent 也照抄,让请求头和你平时一致。
# ===========================================================================
HEADERS = {
    "User-Agent": "把抓到的 User-Agent 粘到这里",
    "Cookie": "把抓到的整段 Cookie 粘到这里",
    "Referer": "https://www.hibor.com.cn/",   # 照抄抓到的 Referer,可留空
}

# ===========================================================================
# 2) 列表(搜索)接口 —— 翻页时抓到的那个请求
#    LIST_PARAMS 里,页码的位置写成 "{page}",程序会自动替换成 1,2,3…
#    其余参数(关键词、分类、时间等)照抄你抓到的,不确定的先原样保留。
# ===========================================================================
LIST_URL = "https://www.hibor.com.cn/……"     # ← 列表接口地址
LIST_METHOD = "GET"                            # ← "GET" 或 "POST",照抄抓到的
LIST_PARAMS = {
    # 下面都是示例键名,请改成你实际抓到的参数名和值
    "keyword": "华创证券",
    "page": "{page}",          # 页码占位符,保持 "{page}" 不要改
    # "type": "宏观经济",
    # "startDate": "2026-01-01",
    # "endDate": "2026-07-25",
}
TOTAL_PAGES = 31               # ← 一共多少页

# ===========================================================================
# 3) 解析列表返回 —— 告诉程序怎么从返回内容里取出每篇研报的信息
#    这一步依赖你抓到的"返回内容"长什么样,所以需要你(或让我帮你)对着改。
#    每篇必须给出:id / title / org / category / date / download_url
# ===========================================================================
def parse_list_response(resp, page):
    """
    参数 resp 是 requests 的响应对象。
    返回:一个列表,每个元素是一篇研报的字典。
    """
    result = []

    # -------- 情况 A:返回是 JSON(大多数接口是这种)--------
    data = resp.json()
    items = data["data"]["list"]          # ← 改成实际的层级路径
    for it in items:
        rid = it["id"]                    # ← 改成实际字段名
        result.append({
            "id":       rid,
            "title":    it["title"],       # ← 标题字段
            "org":      it.get("orgName", ""),      # ← 机构字段(如"华创证券")
            "category": it.get("category", ""),     # ← 分类字段(如"宏观经济")
            "date":     it.get("publishDate", ""),  # ← 发布日期,格式最好是 2026-01-11
            # 下载地址:很多站点是固定模板 + 报告 id 拼出来的,
            # 把你抓到的"下载接口"地址改成下面这样,{id} 会被替换:
            "download_url": f"https://www.hibor.com.cn/download.aspx?id={rid}",
        })

    # -------- 情况 B:返回是 HTML(如果不是 JSON,用这种)--------
    # 需要 pip install beautifulsoup4,然后把上面情况 A 注释掉,改用:
    # from bs4 import BeautifulSoup
    # soup = BeautifulSoup(resp.text, "html.parser")
    # for row in soup.select(".report-item"):        # ← 改成实际选择器
    #     a = row.select_one("a.title")
    #     result.append({
    #         "id":       row.get("data-id"),
    #         "title":    a.get_text(strip=True),
    #         "org":      row.select_one(".org").get_text(strip=True),
    #         "category": row.select_one(".cat").get_text(strip=True),
    #         "date":     row.select_one(".date").get_text(strip=True),
    #         "download_url": "https://www.hibor.com.cn" + a["href"],
    #     })

    return result


# ===========================================================================
# 4) 过滤条件 —— 只保留符合的研报(用"包含"匹配,不用写全)
# ===========================================================================
FILTER_ORG = "华创证券"        # 机构包含这个词才要;不想过滤就设为 ""
FILTER_CATEGORY = "宏观经济"   # 分类包含这个词才要;不想过滤就设为 ""
DATE_START = "2026-01-01"      # 起始日期(含)
DATE_END = "2026-07-25"       # 结束日期(含)

# ===========================================================================
# 5) 限速参数 —— 默认已经很稳,一般不用改。数字越大越慢越安全。
# ===========================================================================
MIN_DELAY = 8            # 每篇之间最少等几秒
MAX_DELAY = 20           # 每篇之间最多等几秒(在两者之间随机)
BATCH_SIZE = 12          # 每下这么多篇
BATCH_REST = (60, 180)   # 就多歇 60~180 秒
HOURLY_CAP = 120         # 每小时最多下多少篇
CIRCUIT_BREAK = 3        # 连续失败几次就自动整体停止

OUT_DIR = "downloads"    # 下载保存目录
