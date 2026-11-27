# -*- coding: utf-8 -*-
import base64
import json
import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


CHINA_TZ = timezone(timedelta(hours=8))


def get_network_time(server="ntp.aliyun.com", timeout=6):
    import socket
    import struct

    packet = bytearray(48)
    packet[0] = 0x1B  # NTP client request

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


def generate_activation_code(player_identifier, days, private_key_path="license_private.pem"):
    player_identifier = player_identifier.strip().upper()
    if not re.fullmatch(r"WAC(?:-[0-9A-F]{4}){7}", player_identifier):
        raise ValueError("玩家标识格式错误，应为 WAC-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX")

    if not isinstance(days, int):
        raise ValueError("授权天数必须是整数；负数可用于测试过期激活码")

    private_bytes = Path(private_key_path).read_bytes()
    private_key = serialization.load_pem_private_key(private_bytes, password=None)
    if not isinstance(private_key, Ed25519PrivateKey):
        raise ValueError("私钥格式错误")

    now = get_network_time()
    # 按中国时区（UTC+8）的自然日计算，到期日中国时间 00:00 起失效。
    now_china = now.astimezone(CHINA_TZ)
    expires_date = now_china.date() + timedelta(days=days)
    expires_china = datetime.combine(
        expires_date, datetime.min.time(), tzinfo=CHINA_TZ
    )
    # payload 字段保留 UTC 格式，存储对应的真实 UTC 时刻。
    expires = expires_china.astimezone(timezone.utc)

    payload = {
        "version": 1,
        "player_id": player_identifier,
        "expires_utc": expires.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "license_id": str(uuid.uuid4())
    }
    payload_bytes = json.dumps(
        payload, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")

    signature = private_key.sign(payload_bytes)
    b64_payload = base64.urlsafe_b64encode(payload_bytes).decode("ascii").rstrip("=")
    b64_signature = base64.urlsafe_b64encode(signature).decode("ascii").rstrip("=")
    return "WAC-ACT1." + b64_payload + "." + b64_signature, now, expires


if __name__ == "__main__":
    print("====== WAC 管理员激活码生成器 ======")
    player_id = input("请输入玩家发来的机器标识：").strip()
    days_text = input("请输入授权整天数（可输入负数测试过期，例如 -1）：").strip()

    try:
        days = int(days_text)
        code, now, expires = generate_activation_code(player_id, days)
        print("\n签发网络时间(中国时间)：", now.astimezone(CHINA_TZ).strftime("%Y-%m-%d %H:%M:%S"))
        print("到期日期(中国时间)：", expires.astimezone(CHINA_TZ).strftime("%Y-%m-%d"), "（该日 00:00 起失效）")
        print("\n请把下面完整激活码发给玩家：\n")
        print(code)
    except Exception as exc:
        print("\n生成失败：", exc)
    input("\n按回车退出...")
