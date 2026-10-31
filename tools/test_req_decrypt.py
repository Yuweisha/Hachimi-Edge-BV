"""验证请求解密链：构造真实结构的加密请求 → 本地解密 → 校验。"""
import sys
sys.path.insert(0, r"C:/Users/Schwarz/projects/Hachimi-Edge/tools")

import importlib
import game_crypto
importlib.reload(game_crypto)
from game_crypto import encrypt_body, parse_request

import msgpack

KEY = bytes.fromhex("3D7E321F99F5E497BA9FA1884F1A6A1A")
IV16 = bytes.fromhex("84F5B7F191DDBE393B409A749ACE49BD")

common_header = bytes.fromhex(
    "5AEBF09DCC92BBB819C891356A114A3E98E62CC7FA9E1FE0A3CD06537EA5F388"
    "52C9B948725E8F79AC1E9195B458F6596911CD5C"
)
sid = bytes.fromhex("8eb29c8fec4b2e06527252d695a386c6")
udid = bytes.fromhex("00112233445566778899aabbccddeeff")
salt = bytes.fromhex("4F932040CC372749D60317BBAE43FB33199A48196676554E858685997B21A7BB")
authkey = bytes.fromhex("aabbccddeeff00112233445566778899")

mp = msgpack.packb({"dummy": 1, "test_key": "hello"}, use_bin_type=True)
payload = common_header + sid + udid + salt + authkey + mp
plain = len(payload).to_bytes(4, "little") + payload
print(f"构造明文 {len(plain)} B（msgpack {len(mp)} B）")

enc = encrypt_body(plain, KEY, IV16[:12], int.from_bytes(IV16[12:], "big"))
print(f"加密后 {len(enc)} B")

parsed = parse_request(enc, KEY, IV16)
print("\n=== 解密结果 ===")
print(f"  ok        = {parsed['ok']}")
print(f"  raw_dec   = {parsed['raw_dec']}")
print(f"  lz4_ok    = {parsed['lz4_ok']}")
print(f"  mp_offset = {parsed.get('mp_offset')}")
print(f"  error     = {parsed['error']}")
print(f"  msgpack   = {parsed['msgpack']}")

# 断言解析结果正确
if parsed["ok"] and parsed["msgpack"] == {"dummy": 1, "test_key": "hello"}:
    print("\n★★★ 解密链完整可用")
else:
    print("\n✗ 解密链有问题")

# LZ4 压缩版本
try:
    import lz4.frame
    lz4_plain = lz4.frame.compress(plain)
    enc2 = encrypt_body(lz4_plain, KEY, IV16[:12], int.from_bytes(IV16[12:], "big"))
    p2 = parse_request(enc2, KEY, IV16)
    print(f"\n=== LZ4 压缩版 ===")
    print(f"  lz4 输入 {len(lz4_plain)} B")
    print(f"  ok       = {p2['ok']}")
    print(f"  lz4_ok   = {p2['lz4_ok']}")
    print(f"  msgpack  = {p2['msgpack']}")
except Exception as e:
    print(f"\nLZ4 测试跳过: {e}")
