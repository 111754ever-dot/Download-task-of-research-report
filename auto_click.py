# -*- coding: utf-8 -*-
"""
自动点鼠标下载器(用于慧博桌面终端)
=====================================
原理:让电脑自动在慧博窗口里,一篇篇地点"下载",再点弹窗里的"保存",
      下完一页自动点"下一页",绕开网页下载的"一次性口令"限制。

跑之前务必知道:
  * 跑的时候【不要动鼠标键盘】,它要用鼠标。
  * 【紧急停止】:把鼠标猛地甩到屏幕【左上角】,程序会立刻中止。
  * 先用 TEST_ONE_PAGE = True 只跑当前一页试水,顺了再改 False 跑全部。

需要准备(见 README_auto.md):
  templates/download.png  —— "下载"按钮的小截图
  templates/save.png      —— 弹窗里蓝色"保存"按钮的小截图
  templates/next.png      —— "下一页"按钮的小截图
"""
import time
import sys
import os

try:
    import pyautogui
except ImportError:
    raise SystemExit("缺少 pyautogui,请先运行:pip install pyautogui opencv-python pillow")

# ============================ 可调参数 ============================
TEST_ONE_PAGE = True     # True=只跑当前这一页试水;顺了改成 False 跑全部
TOTAL_PAGES   = 31       # 一共多少页
START_PAGE    = 1        # 从第几页开始(中断后可改这里接着跑)

CONFIDENCE    = 0.85     # 图像匹配的相似度(找不到按钮就调低到 0.8/0.75)
WAIT_DIALOG   = 1.5      # 点"下载"后,等弹窗出现的时间(秒)
WAIT_SAVE     = 2.5      # 点"保存"后,等它下完的时间(秒)
WAIT_BETWEEN  = 1.5      # 每篇之间的间隔(秒)
WAIT_NEXTPAGE = 2.5      # 点"下一页"后,等列表刷新的时间(秒)
SCROLL_CLICKS = -8       # 每次向下滚动的量(负数=向下;滚太多会漏、太少会重,可微调)
MAX_STAGNANT  = 3        # 连续滚动几次都没有新"下载"按钮,就认为本页到底
# ================================================================

pyautogui.FAILSAFE = True          # 鼠标甩到左上角 = 紧急停止
TEMPLATES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")


def _tpl(name):
    return os.path.join(TEMPLATES, name)


def find_all(name):
    """找出屏幕上所有匹配的按钮,按从上到下排序。"""
    try:
        boxes = list(pyautogui.locateAllOnScreen(_tpl(name), confidence=CONFIDENCE))
    except Exception:
        boxes = []
    return sorted(boxes, key=lambda b: b.top)


def find_one(name):
    try:
        return pyautogui.locateOnScreen(_tpl(name), confidence=CONFIDENCE)
    except Exception:
        return None


def click_box(box):
    x, y = pyautogui.center(box)
    pyautogui.moveTo(x, y, duration=0.2)
    pyautogui.click()


def click_save():
    """弹窗出现后点'保存';最多等 6 秒。"""
    for _ in range(12):
        loc = find_one("save.png")
        if loc:
            click_box(loc)
            return True
        time.sleep(0.5)
    print("   ! 没找到'保存'按钮(可能弹窗没出现或没匹配上)")
    return False


def process_current_page(page_no):
    print(f"===== 第 {page_no} 页,开始 =====")
    done = 0
    last_y = -10000
    stagnant = 0
    while True:
        btns = find_all("download.png")
        target = next((b for b in btns if (b.top + b.height / 2) > last_y + 20), None)

        if target is None:
            # 当前可见的都点完了,向下滚动看还有没有
            pyautogui.scroll(SCROLL_CLICKS)
            time.sleep(1.0)
            last_y = -10000
            stagnant += 1
            if stagnant >= MAX_STAGNANT:
                print(f"===== 第 {page_no} 页完成,本页下了 {done} 篇 =====")
                return done
            continue

        stagnant = 0
        click_box(target)                     # 点"下载"
        time.sleep(WAIT_DIALOG)
        if click_save():                      # 点"保存"
            done += 1
            print(f"   ✓ 第 {done} 篇已保存")
        time.sleep(WAIT_SAVE)
        last_y = target.top + target.height / 2
        time.sleep(WAIT_BETWEEN)


def main():
    print("3 秒后开始,请立刻把鼠标点到慧博窗口上、然后别再动它……")
    print("(想中止:把鼠标甩到屏幕左上角)")
    time.sleep(3)

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
            pyautogui.scroll(3000)            # 滚回顶部
            time.sleep(1.0)
    print(f"全部结束,共下载约 {total} 篇。请到文件夹里核对数量。")


if __name__ == "__main__":
    main()
