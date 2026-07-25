# -*- coding: utf-8 -*-
"""
自动点鼠标下载器(慧博桌面终端)—— 全自动
==========================================
关键难点:慧博窗口对"鼠标滚轮"可能没反应。所以本脚本会:
  * 把当前屏幕上看到的"下载"按钮【全部点完】(点下载→点保存);
  * 然后【换几种方式尝试向下滚动一屏】,并【截图对比确认列表真的动了】,
    打印是哪种方式生效;三种都不动就报出来。
  * 逐屏往下,直到滚不动为止 = 本页结束。

跑前须知:
  * 跑时【别动鼠标键盘】;急停:鼠标甩到屏幕【左上角】。
  * 先 TEST_ONE_PAGE=True 只跑一页试;顺了改 False 跑全部。
  * 关掉「下载管理器」里"下载时弹出下载管理器窗口"的勾。

需要:
  templates/download.png  —— "下载"按钮小截图
  templates/save.png      —— 蓝色"保存"按钮小截图
  templates/next.png      —— "下一页"按钮小截图(只跑一页可不做)
"""
import time
import os

try:
    import pyautogui
    from PIL import Image, ImageChops
except ImportError:
    raise SystemExit("缺少依赖,请先运行:pip install pyautogui opencv-python pillow")

# ============================ 可调参数 ============================
TEST_ONE_PAGE = True
TOTAL_PAGES   = 31
START_PAGE    = 1

CONFIDENCE    = 0.80
WAIT_DIALOG   = 1.3      # 点"下载"后等弹窗
WAIT_SAVE     = 1.5      # 点"保存"后等对话框关闭
WAIT_BETWEEN  = 0.4
WAIT_NEXTPAGE = 2.5
# ================================================================

pyautogui.FAILSAFE = True
TEMPLATES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
_CACHE = {}


def _tpl(name):
    return os.path.join(TEMPLATES, name)


def load_tpl(name):
    if name not in _CACHE:
        p = _tpl(name)
        if not os.path.exists(p):
            raise SystemExit(f"找不到模板图:{p}\n请确认 templates 里有这张图,文件名完全一致。")
        _CACHE[name] = Image.open(p).convert("RGB")
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


def click_save():
    for _ in range(12):
        loc = find_one("save.png")
        if loc:
            click_box(loc)
            return True
        time.sleep(0.5)
    print("   ! 没找到'保存'按钮(弹窗没出现?save.png 没匹配上?)")
    return False


# ---- 滚动:换几种方式试,并截图确认是否真动了 ----
def _diff_region():
    w, h = pyautogui.size()
    # 取结果区左侧一小块(避开中间弹窗、右侧广告)
    return (int(w * 0.27), int(h * 0.38), int(w * 0.30), int(h * 0.34))


def _snap():
    return pyautogui.screenshot(region=_diff_region())


def _moved(before):
    after = _snap()
    diff = ImageChops.difference(before.convert("RGB"), after.convert("RGB"))
    return diff.getbbox() is not None    # 有差异=动了


def scroll_down():
    """尝试把列表往下滚一屏,返回是否真的动了(并打印哪种方式生效)。"""
    w, h = pyautogui.size()
    lx, ly = int(w * 0.42), int(h * 0.55)   # 列表中间
    before = _snap()

    # 方法1:鼠标滚轮
    pyautogui.moveTo(lx, ly, duration=0.15)
    pyautogui.scroll(-12)
    time.sleep(0.8)
    if _moved(before):
        print("   滚动:滚轮生效")
        return True

    # 方法2:键盘 PageDown(先在列表上点一下右侧空白获得焦点)
    pyautogui.click(int(w * 0.66), ly)      # 右侧通常是空白,不是链接
    time.sleep(0.2)
    pyautogui.press("pagedown")
    time.sleep(0.8)
    if _moved(before):
        print("   滚动:PageDown 生效")
        return True

    # 方法3:点最右侧滚动条下半部分(相当于向下翻页)
    pyautogui.click(w - 10, int(h * 0.78))
    time.sleep(0.8)
    if _moved(before):
        print("   滚动:点滚动条生效")
        return True

    print("   ! 三种滚动都没让列表动。")
    return False


def process_current_page(page_no):
    print(f"===== 第 {page_no} 页,开始 =====")
    done = 0
    stagnant = 0
    while True:
        btns = find_all("download.png")
        print(f"   [调试] 本屏看到 {len(btns)} 个下载按钮")

        # 把本屏可见的都点完(位置在点击期间不变,互不重复)
        clicked = []
        for b in btns:
            cy = b.top
            if any(abs(cy - y0) < 25 for y0 in clicked):
                continue
            click_box(b)
            time.sleep(WAIT_DIALOG)
            if click_save():
                done += 1
                print(f"   ✓ 已保存 {done} 篇")
            time.sleep(WAIT_SAVE)
            clicked.append(cy)

        # 翻到下一屏
        if scroll_down():
            stagnant = 0
        else:
            stagnant += 1
            if stagnant >= 2:
                break
        time.sleep(WAIT_BETWEEN)

    print(f"===== 第 {page_no} 页完成,本页下了 {done} 篇 =====")
    return done


def main():
    needed = ["download.png", "save.png"] + ([] if TEST_ONE_PAGE else ["next.png"])
    for n in needed:
        load_tpl(n)
    print("模板图读取正常 ✓")
    print("3 秒后开始,请把慧博窗口点到最前面,然后别再动鼠标……(急停:鼠标甩左上角)")
    time.sleep(3)

    if TEST_ONE_PAGE:
        process_current_page(START_PAGE)
        print("试水结束。若正常往下走了,把 TEST_ONE_PAGE 改成 False 再跑全部。")
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
    print(f"全部结束,共下载约 {total} 篇。请核对文件夹数量。")


if __name__ == "__main__":
    main()
