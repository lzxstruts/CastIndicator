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



# ---------------- 授权验证 ----------------
# 激活码首次由玩家输入，验证通过后保存在本脚本所在目录。
# 后续启动自动读取保存的激活码，并重新验证机器码、签名和网络时间。

import base64
import hashlib
import json
import os
import socket
import struct
import winreg
from datetime import datetime, timedelta, timezone

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

PUBLIC_KEY_B64 = "7HVjFtKP8BjdgC0N8Wt0YOEwGbv7v5srxgxav1uWQUo="
NTP_SERVER = "ntp.aliyun.com"
CHINA_TZ = timezone(timedelta(hours=8))
ACTIVATION_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "activation_code.txt"
)


def get_machine_guid():
    try:
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Cryptography"
        ) as key:
            value, _ = winreg.QueryValueEx(key, "MachineGuid")
    except OSError as exc:
        raise RuntimeError("无法读取 Windows MachineGuid") from exc

    value = str(value).strip().upper()
    if not value:
        raise RuntimeError("Windows MachineGuid 为空")
    return value


def make_player_identifier():
    machine_guid = get_machine_guid()
    digest = hashlib.sha256(machine_guid.encode("utf-8")).hexdigest().upper()[:28]
    groups = [digest[i:i + 4] for i in range(0, 28, 4)]
    return "WAC-" + "-".join(groups)


def get_network_time(server=NTP_SERVER, timeout=6):
    packet = bytearray(48)
    packet[0] = 0x1B

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(timeout)
        sock.sendto(packet, (server, 123))
        data, _ = sock.recvfrom(48)

    if len(data) < 48:
        raise RuntimeError("NTP服务器返回数据不完整")

    seconds, fraction = struct.unpack("!II", data[40:48])
    if seconds == 0:
        raise RuntimeError("NTP服务器返回无效时间")

    unix_time = seconds - 2208988800 + fraction / (2 ** 32)
    return datetime.fromtimestamp(unix_time, tz=timezone.utc)


def decode_b64url(value):
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


class LicenseExpiredError(Exception):
    pass


def verify_activation_code(activation_code):
    parts = activation_code.strip().split(".")
    if len(parts) != 3 or parts[0] != "WAC-ACT1":
        raise ValueError("激活码格式错误")

    payload_bytes = decode_b64url(parts[1])
    signature = decode_b64url(parts[2])

    public_key = Ed25519PublicKey.from_public_bytes(
        base64.b64decode(PUBLIC_KEY_B64)
    )
    public_key.verify(signature, payload_bytes)

    payload = json.loads(payload_bytes.decode("utf-8"))
    if payload.get("version") != 1:
        raise ValueError("不支持的激活码版本")

    local_id = make_player_identifier()
    licensed_id = str(payload.get("player_id", "")).upper()
    if licensed_id != local_id:
        raise PermissionError("机器码不匹配，此激活码不能在本电脑使用")

    expires = datetime.strptime(
        payload["expires_utc"], "%Y-%m-%dT%H:%M:%SZ"
    ).replace(tzinfo=timezone.utc)

    # 必须使用阿里云 NTP 网络时间；获取失败时不允许启动。
    now = get_network_time()
    now_china = now.astimezone(CHINA_TZ)
    expires_china = expires.astimezone(CHINA_TZ)

    # 按北京时间自然日判断，到期日当天 00:00:00 起失效。
    if now_china.date() >= expires_china.date():
        raise LicenseExpiredError("激活码已过期")

    return local_id, now_china, expires_china


def authorize_or_exit():
    """授权成功返回 True；失败返回 False，调用方应立即退出主程序。"""
    first_use = not os.path.exists(ACTIVATION_FILE)

    if first_use:
        #print("====== WAC 首次授权 ======")
        try:
            player_id = make_player_identifier()
        except Exception as exc:
            print("\n获取玩家机器码失败：", exc)
            return False

        print("你的玩家机器码：")
        print(player_id)
        print("\n请将上面的机器码完整发送给管理员。")
        print("管理员会根据机器码生成专属激活码。")
        print("收到激活码后，请粘贴到下面。\n")

        activation_code = input("请输入管理员发给你的激活码：").strip()
        if not activation_code:
            print("\n尚未输入激活码，程序退出。")
            return False
    else:
        #print("正在读取本地激活码并验证授权...")
        try:
            with open(ACTIVATION_FILE, "r", encoding="utf-8") as f:
                activation_code = f.read().strip()
        except OSError as exc:
            print("\n验证失败：无法读取本地激活码文件。")
            print("详细信息：", exc)
            return False

        if not activation_code:
            print("\n验证失败：本地激活码文件为空。")
            return False

    try:
        player_id, now_china, expires_china = verify_activation_code(
            activation_code
        )

        # 首次验证成功后才保存；后续启动不再要求玩家输入。
        if first_use:
            with open(ACTIVATION_FILE, "w", encoding="utf-8") as f:
                f.write(activation_code)
        #print("\n授权验证成功。")
        print("机器标识：", player_id)
        print("当前北京时间：", now_china.strftime("%Y-%m-%d %H:%M:%S"))
        print(
            "授权到期日期：",
            expires_china.strftime("%Y-%m-%d"),
            "（到期日 00:00:00 起失效）"
        )
        return True

    except LicenseExpiredError as exc:
        print("\n验证失败：", exc)
    except PermissionError as exc:
        print("\n验证失败：", exc)
    except InvalidSignature:
        print("\n验证失败：激活码签名错误或已被篡改。")
    except (socket.timeout, OSError) as exc:
        print("\n验证失败：无法获取阿里云网络时间，请检查网络后重试。")
        print("详细信息：", exc)
    except Exception as exc:
        print("\n验证失败：激活码无效或授权验证异常。")
        print("详细信息：", exc)

    return False


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
    # 授权未通过（包括过期、机器码不匹配、网络时间获取失败）时不启动主程序。
    if not authorize_or_exit():
        input("\n按回车退出...")
        return

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
