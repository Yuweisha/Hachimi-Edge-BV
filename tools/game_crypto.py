"""游戏 API 应用层加解密（已逆向验证）。

流密码：
    ks[i] = AES-128-ECB(key, IV12 ‖ BE32(ctr0 + i))
    cipher = plain XOR ks

响应封装：
    base64( LE32(明文长度) ‖ 32 字节头 ‖ 密文 )

其中：key = 16 字节，IV12 = 12 字节，ctr0 = 32 位大端计数器。
"""
from __future__ import annotations

import base64
import struct

try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
except ImportError as e:  # pragma: no cover
    raise ImportError("需要 cryptography：pip install cryptography") from e


def _ecb_encrypt_block(key: bytes, block: bytes) -> bytes:
    c = Cipher(algorithms.AES(key), modes.ECB())
    e = c.encryptor()
    return e.update(block) + e.finalize()


def keystream(key: bytes, iv12: bytes, ctr0: int, length: int) -> bytes:
    """生成 length 字节密钥流。

    args:
        key   16 字节
        iv12  12 字节
        ctr0  初始计数器（32 位无符号）
        length 需要的字节数
    """
    if len(key) != 16:
        raise ValueError(f"key 必须 16 字节，当前 {len(key)}")
    if len(iv12) != 12:
        raise ValueError(f"iv12 必须 12 字节，当前 {len(iv12)}")

    nblocks = (length + 15) // 16
    out = bytearray()
    for i in range(nblocks):
        blk = iv12 + ((ctr0 + i) & 0xFFFFFFFF).to_bytes(4, "big")
        out += _ecb_encrypt_block(key, blk)
    return bytes(out[:length])


def _xor(a: bytes, b: bytes) -> bytes:
    return bytes(x ^ y for x, y in zip(a, b))


def encrypt_body(plain: bytes, key: bytes, iv12: bytes, ctr0: int,
                 header32: bytes | None = None) -> bytes:
    """把明文加密成响应体（未 base64 前的原始字节）。

    header32 为 32 字节头部，默认全 0（实测客户端不校验内容）。
    """
    if header32 is None:
        header32 = b"\x00" * 32
    if len(header32) != 32:
        raise ValueError("header32 必须 32 字节")

    ks = keystream(key, iv12, ctr0, len(plain))
    cipher = _xor(plain, ks)
    return struct.pack("<I", len(plain)) + header32 + cipher


def encrypt_response_b64(plain: bytes, key: bytes, iv12: bytes, ctr0: int,
                         header32: bytes | None = None) -> bytes:
    """返回可直接作为 HTTP body 的 base64 字节串。"""
    return base64.b64encode(encrypt_body(plain, key, iv12, ctr0, header32))


def decrypt_body(body: bytes, key: bytes, iv12: bytes) -> bytes:
    """解密请求/响应体（已去掉 base64 的原始字节）。

    格式：LE32(明文长度) ‖ 32 字节头 ‖ 密文
    计数器从头部后 12 字节推导——实测请求的 ctr 需外部提供，
    此处的 iv12 参数即为 ctx+0x180 前 12 字节，ctr 从密文推导不了，
    故要求调用方把完整 16 字节 IV 传进来更稳妥（见 decrypt_body_iv16）。
    """
    if len(body) < 36:
        raise ValueError(f"body 太短：{len(body)}")
    plain_len = struct.unpack_from("<I", body, 0)[0]
    cipher = body[36:]
    if plain_len > len(cipher):
        plain_len = len(cipher)

    # 用 iv12 时，ctr 视为 0（仅适用于已知 ctr=0 的场景）
    ks = keystream(key, iv12, 0, len(cipher))
    return _xor(cipher, ks)[:plain_len]


def decrypt_body_iv16(body: bytes, key: bytes, iv16: bytes) -> bytes:
    """更稳妥的解密入口：iv16 = IV12 ‖ BE32(ctr0) 共 16 字节。"""
    if len(iv16) != 16:
        raise ValueError(f"iv16 必须 16 字节，当前 {len(iv16)}")
    if len(body) < 36:
        raise ValueError(f"body 太短：{len(body)}")
    plain_len = struct.unpack_from("<I", body, 0)[0]
    cipher = body[36:]
    iv12 = iv16[:12]
    ctr0 = int.from_bytes(iv16[12:], "big")
    ks = keystream(key, iv12, ctr0, len(cipher))
    plain = _xor(cipher, ks)
    return plain[:plain_len] if plain_len <= len(plain) else plain


def decrypt_response_b64(body_b64: bytes | str, key: bytes, iv16: bytes) -> bytes:
    if isinstance(body_b64, str):
        body_b64 = body_b64.encode()
    raw = base64.b64decode(body_b64)
    return decrypt_body_iv16(raw, key, iv16)


# ---------------------------------------------------------------------------
# 自检：用实测数据验证
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # 实测样本（某次会话，已失效）
    key = bytes.fromhex("3D7E321F99F5E497BA9FA1884F1A6A1A")
    iv16 = bytes.fromhex("84F5B7F191DDBE393B409A749ACE49BD")

    ks0 = keystream(key, iv16[:12], int.from_bytes(iv16[12:], "big"), 16)
    print("ks[0] =", ks0.hex().upper())
    print("期望   = 12631DB71969DC2BCB74A83E5404A655")
    assert ks0.hex().upper() == "12631DB71969DC2BCB74A83E5404A655", "ks[0] 不匹配"

    ks1 = keystream(key, iv16[:12], int.from_bytes(iv16[12:], "big"), 32)[16:]
    print("ks[1] =", ks1.hex().upper())
    print("期望   = 7ACB1BFABD012F8D7712E7CF8751B3A5")

    # 全零块
    z = _ecb_encrypt_block(key, b"\x00" * 16)
    print("AES(key,0) =", z.hex().upper())
    print("期望         = 769AA67762F0927486A80BB6FAD327A5")
    assert z.hex().upper() == "769AA67762F0927486A80BB6FAD327A5"

    # 往返测试
    plain = b"hello umamusume " * 10
    body = encrypt_body(plain, key, iv16[:12], int.from_bytes(iv16[12:], "big"))
    back = decrypt_body_iv16(body, key, iv16)
    assert back == plain, "往返失败"
    print("\n✓ 自检全部通过（含往返）")

# ---------------------------------------------------------------------------
# 请求侧：解密 + LZ4 解压 + 明文头解析
# ---------------------------------------------------------------------------

def _try_lz4_decompress(data: bytes) -> bytes:
    """尝试 LZ4 frame 解压；失败原样返回。"""
    try:
        import lz4.frame
        return lz4.frame.decompress(data)
    except Exception:
        pass
    try:
        import lz4.block
        # 无 size 前缀的 block 解压，给一个宽松上限
        return lz4.block.decompress(data, uncompressed_size=len(data) * 64)
    except Exception:
        return data


def _find_msgpack_start(data: bytes, start: int = 0, limit: int = 4096) -> int:
    """找 msgpack 载荷起点：逐个候选位置试解析，第一个成功的就是它。

    安全约束：
      - 只在 start..start+limit 内试（避免大 body 上 O(n²)）
      - 每个候选最多解析 4 MB（避免 unpackb 处理巨量数据）
      - 任何异常都被吞掉
    """
    try:
        import msgpack
    except ImportError:
        return -1

    n = len(data)
    if n == 0:
        return -1
    upper = min(n, start + limit)

    for i in range(start, upper):
        b = data[i]
        if not (0x80 <= b <= 0x8F or b in (0xDE, 0xDF)):
            continue
        chunk = data[i:i + 4 * 1024 * 1024]
        try:
            obj = msgpack.unpackb(chunk, raw=False, strict_map_key=False)
        except Exception:
            continue
        if isinstance(obj, (dict, list)) and obj:
            return i
    return -1


def parse_request(body: bytes, key: bytes, iv16: bytes) -> dict:
    """解密并解析客户端请求。

    返回 dict：
        ok         是否成功解密
        raw_dec    解密后原始字节长度
        lz4_ok     是否经过 LZ4
        plain      明文（LZ4 解压后）
        sid        明文头里的 SID（若能识别）
        body       推测的 msgpack 载荷（原始字节）
        msgpack    解析后的对象（失败为 None）
        error      失败原因
    """
    out = {
        "ok": False, "raw_dec": 0, "lz4_ok": False,
        "plain": b"", "sid": None, "body": b"",
        "msgpack": None, "error": None,
    }

    if not body or len(body) < 36:
        out["error"] = f"body 太短 {len(body) if body else 0}"
        return out

    # 客户端发来的 body 是 base64 文本（LE32 ‖ 32B ‖ 密文 的 base64），
    # 先解码；如果解不出合法长度就当作已经是二进制。
    raw = body
    head32 = body[:32].rstrip(b"\r\n")
    if all(32 <= b < 127 for b in head32):
        try:
            dec_b64 = base64.b64decode(body + b"=" * ((4 - len(body) % 4) % 4), validate=False)
            if len(dec_b64) >= 36:
                raw = dec_b64
                out["b64_decoded"] = True
        except Exception:
            pass

    try:
        dec = decrypt_body_iv16(raw, key, iv16)
    except Exception as e:
        out["error"] = f"解密失败: {e}"
        return out

    # 防御：异常大的 body 不解析（避免拖死服务器）
    if len(dec) > 64 * 1024 * 1024:
        out["error"] = f"解密后过大 {len(dec)}"
        out["raw_dec"] = len(dec)
        return out

    out["raw_dec"] = len(dec)
    plain = _try_lz4_decompress(dec)
    out["lz4_ok"] = len(plain) != len(dec) or plain != dec
    out["plain"] = plain

    # 明文头：跳过 [u32] + CommonHeader(52)，再尝试识别 SID（十六进制 ASCII）
    try:
        head = plain[:64]
        # 前 4 字节是长度
        declared = int.from_bytes(head[0:4], "little")
        out["declared"] = declared
    except Exception:
        pass

    # 找 msgpack 起点
    mp_start = _find_msgpack_start(plain, 56)
    if mp_start < 0:
        out["error"] = "未找到 msgpack 起点"
        out["body"] = plain
        return out

    out["mp_offset"] = mp_start
    out["body"] = plain[mp_start:]

    try:
        import msgpack
        obj = msgpack.unpackb(plain[mp_start:], raw=False, strict_map_key=False)
        out["msgpack"] = obj
        out["ok"] = True
    except Exception as e:
        out["error"] = f"msgpack 解析失败: {e}"

    return out


def summarize_request(parsed: dict, max_keys: int = 12) -> str:
    """把 parse_request 的结果压成一行可读摘要。"""
    if not parsed.get("ok"):
        return f"[req] 解密未完成: {parsed.get('error')}"
    obj = parsed["msgpack"]
    if isinstance(obj, dict):
        ks = list(obj)[:max_keys]
        return f"[req] {len(obj)} 键: {ks}"
    return f"[req] 类型 {type(obj).__name__} 长度 {len(obj) if hasattr(obj,'__len__') else '?'}"

