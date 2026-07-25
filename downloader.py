# -*- coding: utf-8 -*-
"""
慧博研报批量下载器 —— 下载引擎
=================================
特点:
  1. 单线程、慢速、随机间隔  —— 行为接近真人手动操作,不给服务器压力
  2. 先建目录(manifest)再下载 —— 可先核对数量和范围,避免下错下多
  3. 断点续传               —— 中断后重跑,自动跳过已下载的
  4. 自动重试 + 熔断         —— 连续出错立即停止,保护账号
  5. 全过程写日志            —— run.log 里可回溯每一步

你一般不需要改这个文件。所有要改的东西都在 config.py。

用法:
    python downloader.py manifest   # 第一步:只建目录,不下载(先核对 manifest.csv)
    python downloader.py download   # 第二步:按目录慢速下载(可反复运行,自动续传)
    python downloader.py verify     # 第三步:校验已下载文件是否完整
"""
import os
import re
import csv
import sys
import time
import random
import logging
from collections import deque

import requests

import config

# ---------------------------------------------------------------------------
# 日志:同时输出到屏幕和 run.log
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.FileHandler("run.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("hibor")

MANIFEST = "manifest.csv"
FIELDS = ["id", "title", "org", "category", "date",
          "download_url", "status", "filename", "error"]


# ---------------------------------------------------------------------------
# 限速 + 熔断:这就是"严谨"的核心
# ---------------------------------------------------------------------------
class Guard:
    """让下载行为接近真人;异常时自动刹车。"""

    def __init__(self):
        self.times = deque()          # 最近一小时的请求时间戳
        self.consecutive_errors = 0   # 连续失败计数
        self.count_since_rest = 0     # 距上次分批休息已下多少篇

    def before_request(self):
        """每小时不超过上限,超了就等。"""
        now = time.time()
        while self.times and now - self.times[0] > 3600:
            self.times.popleft()
        if len(self.times) >= config.HOURLY_CAP:
            wait = 3600 - (now - self.times[0]) + 1
            log.warning("已达每小时上限 %d 篇,休息 %.0f 秒 …", config.HOURLY_CAP, wait)
            time.sleep(wait)
        self.times.append(time.time())

    def after_ok(self):
        """一篇成功后:正常等待;每 BATCH_SIZE 篇多歇一会儿。"""
        self.consecutive_errors = 0
        self.count_since_rest += 1
        if self.count_since_rest >= config.BATCH_SIZE:
            rest = random.uniform(*config.BATCH_REST)
            log.info("已连续下载 %d 篇,分批休息 %.0f 秒 …", self.count_since_rest, rest)
            time.sleep(rest)
            self.count_since_rest = 0
        else:
            delay = random.uniform(config.MIN_DELAY, config.MAX_DELAY)
            log.info("等待 %.1f 秒后继续 …", delay)
            time.sleep(delay)

    def after_error(self):
        """一篇彻底失败后:累计;连续失败太多次就整体停止。"""
        self.consecutive_errors += 1
        if self.consecutive_errors >= config.CIRCUIT_BREAK:
            raise SystemExit(
                f"\n连续 {self.consecutive_errors} 次失败,已自动停止以保护账号。\n"
                "常见原因:① 登录过期了(重新登录、更新 config.py 里的 Cookie);"
                "② 被临时限速了(等一两个小时再跑)。\n"
                "直接重跑 download 即可,会自动从断点继续。"
            )
        # 失败之间也拉长间隔,不硬刚
        time.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY) * 2)


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------
def sanitize(name, maxlen=120):
    name = re.sub(r'[\\/:*?"<>|\r\n\t]+', "_", str(name)).strip(" ._")
    return name[:maxlen] or "untitled"


def default_name(r):
    return sanitize(f"{str(r.get('date',''))[:10]}_{r.get('org','')}_{r.get('title','')}") + ".pdf"


def is_pdf(path):
    """简单校验:文件够大且以 %PDF 开头。"""
    try:
        if os.path.getsize(path) < 1024:
            return False
        with open(path, "rb") as f:
            return f.read(5).startswith(b"%PDF")
    except OSError:
        return False


def in_range(date_str):
    d = str(date_str)[:10]
    return config.DATE_START <= d <= config.DATE_END


def make_session():
    s = requests.Session()
    s.headers.update(config.HEADERS)
    return s


def load_manifest():
    rows = {}
    if os.path.exists(MANIFEST):
        with open(MANIFEST, encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                rows[str(r["id"])] = r
    return rows


def save_manifest(rows):
    with open(MANIFEST, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in rows.values():
            w.writerow({k: r.get(k, "") for k in FIELDS})


# ---------------------------------------------------------------------------
# 第一步:建目录(只请求列表接口,不下载 PDF)
# ---------------------------------------------------------------------------
def do_list_request(s, page):
    params = {k: str(v).replace("{page}", str(page)) for k, v in config.LIST_PARAMS.items()}
    if config.LIST_METHOD.upper() == "POST":
        resp = s.post(config.LIST_URL, data=params, timeout=(10, 60))
    else:
        resp = s.get(config.LIST_URL, params=params, timeout=(10, 60))
    resp.raise_for_status()
    return resp


def build_manifest():
    s = make_session()
    guard = Guard()
    rows = load_manifest()
    added = 0
    for page in range(1, config.TOTAL_PAGES + 1):
        guard.before_request()
        try:
            resp = do_list_request(s, page)
            items = config.parse_list_response(resp, page)
        except Exception as e:
            log.error("第 %d 页请求/解析失败:%s", page, e)
            guard.after_error()
            continue

        for it in items:
            if config.FILTER_ORG and config.FILTER_ORG not in str(it.get("org", "")):
                continue
            if config.FILTER_CATEGORY and config.FILTER_CATEGORY not in str(it.get("category", "")):
                continue
            if not in_range(it.get("date", "")):
                continue
            rid = str(it["id"])
            if rid in rows:
                continue
            rows[rid] = {
                "id": rid,
                "title": it.get("title", ""),
                "org": it.get("org", ""),
                "category": it.get("category", ""),
                "date": it.get("date", ""),
                "download_url": it.get("download_url", ""),
                "status": "pending",
                "filename": "",
                "error": "",
            }
            added += 1

        log.info("第 %d/%d 页处理完,累计符合条件 %d 篇", page, config.TOTAL_PAGES, len(rows))
        guard.after_ok()

    save_manifest(rows)
    log.info("目录建立完成:共 %d 篇符合条件(本次新增 %d)。", len(rows), added)
    log.info("请先打开 manifest.csv 核对数量和范围,确认没问题再运行:python downloader.py download")


# ---------------------------------------------------------------------------
# 第二步:按目录慢速下载
# ---------------------------------------------------------------------------
def try_download(s, r, fpath):
    os.makedirs(config.OUT_DIR, exist_ok=True)
    url = r["download_url"]
    if not url:
        return False, "没有下载链接(检查 parse_list_response 是否正确填了 download_url)"
    backoffs = [5, 20, 60]
    last = ""
    for attempt in range(len(backoffs) + 1):
        try:
            with s.get(url, timeout=(10, 120), stream=True) as resp:
                if resp.status_code in (401, 403, 429):
                    raise RuntimeError(f"HTTP {resp.status_code}(可能登录过期或被限速)")
                resp.raise_for_status()
                ctype = resp.headers.get("Content-Type", "")
                tmp = fpath + ".part"
                with open(tmp, "wb") as f:
                    for chunk in resp.iter_content(8192):
                        if chunk:
                            f.write(chunk)
                if not is_pdf(tmp):
                    os.remove(tmp)
                    raise RuntimeError(f"下载内容不是有效 PDF(Content-Type={ctype})")
                os.replace(tmp, fpath)
                return True, ""
        except Exception as e:
            last = str(e)
            if attempt < len(backoffs):
                wait = backoffs[attempt]
                log.warning("  下载失败,%d 秒后重试(%d/%d):%s", wait, attempt + 1, len(backoffs), last)
                time.sleep(wait)
    return False, last


def download_all():
    rows = load_manifest()
    if not rows:
        raise SystemExit("manifest.csv 为空。请先运行:python downloader.py manifest")
    s = make_session()
    guard = Guard()
    todo = [r for r in rows.values() if r.get("status") != "done"]
    log.info("待下载 %d 篇(总目录 %d 篇)", len(todo), len(rows))

    for i, r in enumerate(todo, 1):
        fname = r.get("filename") or default_name(r)
        fpath = os.path.join(config.OUT_DIR, fname)

        # 断点续传:文件已在且合法 → 直接标记完成
        if os.path.exists(fpath) and is_pdf(fpath):
            r["status"], r["filename"] = "done", fname
            continue

        guard.before_request()
        log.info("[%d/%d] 下载:%s", i, len(todo), r.get("title", ""))
        ok, info = try_download(s, r, fpath)
        if ok:
            r["status"], r["filename"], r["error"] = "done", fname, ""
            log.info("  ✓ 完成:%s", fname)
            save_manifest(rows)
            guard.after_ok()
        else:
            r["status"], r["error"] = "failed", info
            log.error("  ✗ 失败:%s", info)
            save_manifest(rows)
            guard.after_error()

    save_manifest(rows)
    done = sum(1 for r in rows.values() if r["status"] == "done")
    failed = sum(1 for r in rows.values() if r["status"] == "failed")
    log.info("下载结束:成功 %d / 失败 %d / 共 %d。", done, failed, len(rows))
    if failed:
        log.info("失败的可直接重跑(自动续传):python downloader.py download")


# ---------------------------------------------------------------------------
# 第三步:校验
# ---------------------------------------------------------------------------
def verify():
    rows = load_manifest()
    if not rows:
        raise SystemExit("manifest.csv 为空。")
    bad = []
    for r in rows.values():
        if r.get("status") != "done":
            continue
        fname = r.get("filename") or default_name(r)
        fpath = os.path.join(config.OUT_DIR, fname)
        if not (os.path.exists(fpath) and is_pdf(fpath)):
            bad.append(fname)
            r["status"] = "pending"      # 重新标记,重跑 download 会补下
    save_manifest(rows)
    if bad:
        log.warning("发现 %d 个文件缺失或损坏,已标记为待下载,请重跑:python downloader.py download\n  - %s",
                    len(bad), "\n  - ".join(bad))
    else:
        log.info("校验通过:所有标记完成的文件都是有效 PDF。")


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "help"
    if mode == "manifest":
        build_manifest()
    elif mode == "download":
        download_all()
    elif mode == "verify":
        verify()
    else:
        print(__doc__)
