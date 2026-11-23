import random
import time
import ctypes
from ctypes import windll

import cv2
import numpy as np
import pygetwindow as gw
import win32gui
import win32ui

WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
PostMessage = ctypes.windll.user32.PostMessageW
KEY_MAP = {str(i): 0x30 + i for i in range(1, 10)}  # '1'=0x31 ... '9'=0x39

REGION_W, REGION_H = 100, 50      # 只取窗口左上角 100*50
CONFIRM_POINTS = ((0, 0), (-1, -1), (1, 1))

RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLACK = (0, 0, 0)

# 与 CastIndicator.lua 的 colors 表一致（RGB）
COLOR_TABLE = [
    (255, 69, 69),
    (255, 135, 69),
    (255, 222, 69),
    (69, 255, 69),
    (69, 255, 222),
    (69, 135, 255),
    (171, 69, 255),
    (255, 69, 171),
    (255, 255, 255),
]


# ---------------- 原逻辑：截图 ----------------

def find_wow_window():
    windows = gw.getWindowsWithTitle("魔兽世界")
    if not windows:
        windows = gw.getWindowsWithTitle("World of Warcraft")
    if not windows:
        print("未找到魔兽世界窗口")
        return None
    return windows[0]


def capture_window(hwnd):
    w = REGION_W
    h = REGION_H

    hwnd_dc = win32gui.GetWindowDC(hwnd)
    mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
    save_dc = mfc_dc.CreateCompatibleDC()

    save_bitmap = win32ui.CreateBitmap()
    save_bitmap.CreateCompatibleBitmap(mfc_dc, w, h)
    save_dc.SelectObject(save_bitmap)

    windll.user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), 2)

    bmpinfo = save_bitmap.GetInfo()
    bmpstr = save_bitmap.GetBitmapBits(True)

    img = np.frombuffer(bmpstr, dtype=np.uint8).reshape((bmpinfo["bmHeight"], bmpinfo["bmWidth"], 4))
    img = np.ascontiguousarray(img)[..., :-1]

    win32gui.DeleteObject(save_bitmap.GetHandle())
    save_dc.DeleteDC()
    mfc_dc.DeleteDC()
    win32gui.ReleaseDC(hwnd, hwnd_dc)

    return img


def send_key(window_handle, key):
    vk = KEY_MAP.get(str(key), key)
    key_down = 0x00000001 | (0x00000001 << 30)
    key_up = 0x00000001 | (0x00000003 << 30) | (0x1 << 31)
    PostMessage(window_handle, WM_KEYDOWN, vk, key_down)
    time.sleep(random.uniform(0.05, 0.09))
    PostMessage(window_handle, WM_KEYUP, vk, key_up)


# ---------------- 取色 / 匹配 ----------------

def color_close(color, ref):
    if color is None:
        return False
    return (int(color[0]), int(color[1]), int(color[2])) == tuple(ref)


def sample3(img, x, y):
    h, w = img.shape[:2]
    vals = []
    for dx, dy in CONFIRM_POINTS:
        px, py = x + dx, y + dy
        if 0 <= px < w and 0 <= py < h:
            vals.append(img[py, px].astype(np.int32))
    if not vals:
        return None
    med = np.median(np.array(vals), axis=0)
    return (int(med[0]), int(med[1]), int(med[2]))


def match_color_table(color):
    if color is None:
        return None
    for i, ref in enumerate(COLOR_TABLE):
        if color_close(color, ref):
            return i + 1
    return None


def build_mask(img, refs):
    a = img.astype(np.int16)
    mask = np.zeros(img.shape[:2], dtype=bool)
    for ref in refs:
        mask |= (a == np.array(ref, dtype=np.int16)).all(axis=2)
    return mask


def find_components(mask, min_w=3, min_h=3, min_area=9, solid=0.6):
    h, w = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    comps = []
    for y in range(h):
        for x in range(w):
            if not mask[y, x] or seen[y, x]:
                continue
            stack = [(x, y)]
            seen[y, x] = True
            xs, ys = [], []
            while stack:
                cx, cy = stack.pop()
                xs.append(cx)
                ys.append(cy)
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if 0 <= nx < w and 0 <= ny < h and mask[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        stack.append((nx, ny))
            x0, x1 = min(xs), max(xs)
            y0, y1 = min(ys), max(ys)
            bw, bh = x1 - x0 + 1, y1 - y0 + 1
            if bw < min_w or bh < min_h or len(xs) < min_area:
                continue
            if len(xs) < solid * bw * bh:
                continue
            comps.append({
                "x0": x0, "y0": y0, "x1": x1, "y1": y1,
                "w": bw, "h": bh,
                "cx": (x0 + x1) // 2, "cy": (y0 + y1) // 2,
            })
    return comps


# ---------------- 定位 / 配置 ----------------

def locate(img):
    """先找红/绿状态点，再用 1.5 倍块宽算出九色块的位置"""
    h, w = img.shape[:2]

    status = None
    for ref in (RED, GREEN):
        comps = find_components(build_mask(img, [ref]))
        if comps:
            def to_corner(c):
                return (c["cx"] ** 2 + c["cy"] ** 2) ** 0.5
            status = min(comps, key=to_corner)  # 取最贴左上角的那个
            break
    if not status:
        return None

    sx, sy = status["cx"], status["cy"]
    # 两块中心间距 10 UI 单位 = 2 倍块宽，y 相同
    x2 = int(round(sx + 2.0 * status["w"]))

    kc = sample3(img, x2, sy)
    if match_color_table(kc) is not None or color_close(kc, BLACK):
        return ((sx, sy), (x2, sy))

    # 兜底：状态点同一行向右扫
    y0, y1 = status["y0"], status["y1"]
    x_start = status["x1"] + 1
    if x_start >= w or y0 > y1:
        return None
    mask = np.zeros((h, w), dtype=bool)
    mask[y0:y1 + 1, x_start:] = build_mask(img, COLOR_TABLE + [BLACK])[y0:y1 + 1, x_start:]

    for c in find_components(mask):
        if abs(c["cy"] - sy) > max(2, status["h"] // 4):
            continue
        if abs(c["cx"] - x2) > max(2, status["h"] // 2):
            continue
        if not (0.5 * status["h"] <= c["h"] <= 2 * status["h"]):
            continue
        if c["w"] > 3 * status["h"]:
            continue
        return ((sx, sy), (c["cx"], c["cy"]))
    return None


# ---------------- 主循环 ----------------

def main():
    windll.user32.SetProcessDPIAware()

    wow = find_wow_window()
    if not wow:
        input("按回车退出...")
        return
    hwnd = wow._hWnd

    try:
        while True:
            img = capture_window(hwnd)
            if img is None:
                continue

            region = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

            coords = locate(region)
            if not coords:
                time.sleep(0.2)
                continue

            status_color = sample3(region, *coords[0])

            if color_close(status_color, GREEN):
                time.sleep(random.uniform(0.15, 0.30))
                continue

            if color_close(status_color, RED):
                skill_color = sample3(region, *coords[1])
                key = match_color_table(skill_color)
                if key:
                    send_key(hwnd, str(key))

            time.sleep(random.uniform(0.15, 0.20))

    except KeyboardInterrupt:
        print("\n停止")

    input("按回车退出...")


if __name__ == "__main__":
    main()
