# -*- coding: utf-8 -*-
"""
自动点鼠标下载器(慧博桌面终端)—— 全自动
==========================================
思路(不依赖"下载后变红"):
  * 识别当前屏幕上的"下载"按钮,永远只点【最上面】那一个;
  * 点完后,按"相邻两篇的间距"精确地向下滚【正好一篇】的距离,
    于是下一篇顶上来成为新的最上面 → 逐篇往下,不重复、不遗漏。
  * 每篇之间距离是实时测量的,能适应不同篇幅的高度。

跑之前务必知道:
  * 跑的时候【不要动鼠标键盘】。
  * 【紧急停止】:鼠标猛甩到屏幕【左上角】。
  * 先用 TEST_ONE_PAGE = True 只跑当前一页试水,顺了再改 False 跑全部。
  * 关掉「下载管理器」里的"下载时弹出下载管理器窗口",别让它挡住列表。

需要准备:
  templates/download.png  —— "下载"按钮的小截图(截没下过的正常颜色那种)
  templates/save.png      —— 弹窗里蓝色"保存"按钮的小截图
  templates/next.png      —— "下一页"按钮的小截图(只跑一页可不用)
"""
import time
import os

try:
    import pyautogui
    from PIL import Image
except ImportError:
    raise SystemExit("缺少依赖,请先运行:pip install pyautogui opencv-python pillow")

# ============================ 可调参数 ============================
MODE = "full"            # "full"=全自动;"auto_save"=你点下载我点保存(备用)

TEST_ONE_PAGE = True     # True=只跑当前这一页试水;顺了改成 False 跑全部
TOTAL_PAGES   = 31
START_PAGE    = 1

CONFIDENCE    = 0.80     # 图像匹配相似度(找不到按钮就调低,如 0.75)
WAIT_DIALOG   = 1.3      # 点"下载"后等弹窗出现
WAIT_SAVE     = 1.6      # 点"保存"后等对话框关闭
WAIT_BETWEEN  = 0.6      # 每篇之间
WAIT_NEXTPAGE = 2.5      # 翻页后等刷新

DEFAULT_SPACING = 285    # 万一测不到间距时,默认一篇约多少像素高
MAX_STAGNANT  = 4        # 连续滚动几次都没有新按钮 = 本页到底
# ================================================================

pyautogui.FAILSAFE = True
TEMPLATES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
PPC = 40.0               # 每滚动1格≈多少像素,启动时自动校准


def _tpl(name):
    return os.path.join(TEMPLATES, name)


_CACHE = {}


def load_tpl(name):
    """用 PIL 读模板图(支持中文路径)。"""
    if name not in _CACHE:
        path = _tpl(name)
        if not os.path.exists(path):
            raise SystemExit(f"找不到模板图:{path}\n请确认 templates 里有这张图,文件名完全一致。")
        _CACHE[name] = Image.open(path).convert("RGB")
    return _CACHE[name]


def find_all(name):
    try:
        boxes = list(pyautogui.locateAllOnScreen(load_tpl(name), confidence=CONFIDENCE))
    except SystemExit:
        raise
    except Exception:
        boxes = []
    return sorted(boxes, key=lambda b: b.top)


def find_one(name):
    try:
        return pyautogui.locateOnScreen(load_tpl(name), confidence=CONFIDENCE)
    except SystemExit:
        raise
    except Exception:
        return None


def click_box(box):
    x, y = pyautogui.center(box)
    pyautogui.moveTo(x, y, duration=0.15)
    pyautogui.click()


def to_list_area():
    """把鼠标移到结果列表中间(滚动/校准都要鼠标在列表上方才有效)。"""
    w, h = pyautogui.size()
    pyautogui.moveTo(int(w * 0.42), int(h * 0.55), duration=0.15)


def scroll_px(pixels):
    """向下滚动大约 pixels 像素。"""
    clicks = max(1, int(round(pixels / PPC)))
    to_list_area()
    pyautogui.scroll(-clicks)
    time.sleep(0.9)


def calibrate():
    """测量'每滚动1格≈多少像素',让'滚一篇'更准。"""
    global PPC
    b0 = find_all("download.png")
    if not b0:
        print("   ! 校准:当前没找到'下载'按钮,先检查 download.png / CONFIDENCE。")
        return
    y0 = b0[0].top
    to_list_area()
    pyautogui.scroll(-2)
    time.sleep(0.9)
    b1 = find_all("download.png")
    if b1:
        moved = y0 - b1[0].top
        if moved > 4:
            PPC = moved / 2.0
    print(f"   校准完成:每滚动1格 ≈ {PPC:.0f} 像素")


def click_save():
    for _ in range(12):
        loc = find_one("save.png")
        if loc:
            click_box(loc)
            return True
        time.sleep(0.5)
    print("   ! 没找到'保存'按钮(弹窗没出现?save.png 没匹配上?)")
    return False


def process_current_page(page_no):
    print(f"===== 第 {page_no} 页,开始 =====")
    done = 0
    misses = 0
    last_spacing = DEFAULT_SPACING
    while True:
        btns = find_all("download.png")
        print(f"   [调试] 看到 {len(btns)} 个下载按钮")

        if not btns:
            scroll_px(last_spacing)      # 没看到,往下滚一篇看看
            misses += 1
            if misses >= MAX_STAGNANT:
                break
            continue

        misses = 0
        # 当前最上面这篇的高度 = 到下一篇的间距
        spacing = (btns[1].top - btns[0].top) if len(btns) >= 2 else last_spacing
        if spacing < 60:                 # 异常值兜底
            spacing = last_spacing
        last_spacing = spacing

        click_box(btns[0])               # 点最上面那篇的"下载"
        time.sleep(WAIT_DIALOG)
        if click_save():                 # 点弹窗"保存"
            done += 1
            print(f"   ✓ 已保存 {done} 篇")
        time.sleep(WAIT_SAVE)

        scroll_px(spacing)               # 精确下滚一篇 → 下一篇顶上来
        time.sleep(WAIT_BETWEEN)

    print(f"===== 第 {page_no} 页完成,本页下了 {done} 篇 =====")
    return done


def auto_save_loop():
    """备用半自动:你点'下载',脚本自动点'保存'。"""
    load_tpl("save.png")
    print("【自动保存模式】你在慧博里点每篇的'下载',我自动点'保存'。急停:鼠标甩左上角。")
    saved = 0
    while True:
        loc = find_one("save.png")
        if loc:
            click_box(loc)
            saved += 1
            print(f"   ✓ 已自动保存第 {saved} 个")
            time.sleep(1.5)
        time.sleep(0.3)


def main():
    if MODE == "auto_save":
        auto_save_loop()
        return

    needed = ["download.png", "save.png"] + ([] if TEST_ONE_PAGE else ["next.png"])
    for n in needed:
        load_tpl(n)
    print("模板图读取正常 ✓")
    print("3 秒后开始,请立刻把慧博窗口点到最前面,然后别再动鼠标……")
    print("(急停:鼠标甩到屏幕左上角)")
    time.sleep(3)

    calibrate()

    if TEST_ONE_PAGE:
        process_current_page(START_PAGE)
        print("试水结束。若正常,把脚本里 TEST_ONE_PAGE 改成 False 再跑全部。")
        return

    total = 0
    for page in range(START_PAGE, TOTAL_PAGES + 1):
        total += process_current_page(page)
        if page < TOTAL_PAGES:
            nxt = find_one("next.png")
            if not nxt:
                print("! 找不到'下一页'按钮,停在第 %d 页。" % page)
                break
            click_box(nxt)
            time.sleep(WAIT_NEXTPAGE)
            to_list_area()
            pyautogui.scroll(3000)           # 滚回顶部
            time.sleep(1.0)
    print(f"全部结束,共下载约 {total} 篇。请核对文件夹数量。")


if __name__ == "__main__":
    main()
