"""验证客户端请求体是否真的加密：直接尝试 LZ4 解压，不做解密。"""
import base64
import msgpack
from pathlib import Path

try:
    import lz4.frame
    HAVE_LZ4 = True
except ImportError:
    HAVE_LZ4 = False
    print("(lz4 未安装)")

D = Path(r"C:/Users/Schwarz/uma_replay/reqdump")
metas = sorted(D.glob("*.meta"), key=lambda p: p.stat().st_mtime, reverse=True)[:4]

for m in metas:
    body_f = m.with_suffix(".body")
    if not body_f.exists():
        continue
    body = body_f.read_bytes().strip()
    info = {k: v for k, v in (ln.split("=", 1) for ln in
                              m.read_text(encoding="utf-8", errors="replace").splitlines()
                              if "=" in ln)}
    print(f"=== {m.name}  path={info.get('path')} ===")

    pad = b"=" * ((4 - len(body) % 4) % 4)
    try:
        raw = base64.b64decode(body + pad)
    except Exception as e:
        print(f"  base64 失败: {e}\n")
        continue

    print(f"  解码 {len(raw)} B   LE32={int.from_bytes(raw[0:4],'little')}")

    payload = raw[36:]
    dec = None
    if HAVE_LZ4:
        # 尝试 1: 整个 payload 是 LZ4 frame
        try:
            dec = lz4.frame.decompress(payload)
            print(f"  ✓ 直接 LZ4 frame 解压: {len(payload)} → {len(dec)} B")
        except Exception as e:
            print(f"  ✗ LZ4 frame: {str(e)[:70]}")

        # 尝试 2: LZ4 block（无 frame 头）
        if dec is None:
            try:
                import lz4.block
                dec = lz4.block.decompress(payload, uncompressed_size=len(payload) * 64)
                print(f"  ✓ LZ4 block 解压: {len(payload)} → {len(dec)} B")
            except Exception as e:
                print(f"  ✗ LZ4 block: {str(e)[:70]}")

    if dec:
        print(f"    前 32: {dec[:32].hex().upper()}")
        try:
            o = msgpack.unpackb(dec, raw=False, strict_map_key=False)
            keys = list(o)[:8] if isinstance(o, dict) else type(o).__name__
            print(f"    ✓ msgpack 解析成功: {keys}")
        except Exception as e:
            print(f"    msgpack 失败: {str(e)[:60]}")
    else:
        print(f"  载荷前 16: {payload[:16].hex().upper()}")
    print()
