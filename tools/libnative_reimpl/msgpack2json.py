"""把抓到的响应明文转成 JSON，转完删除对应的 bin。

输出目录结构（插件自动创建）：
    <游戏目录>/hachimi/http/<YYYYmmdd_HHMMSS>/
        NNNN_resp_src.bin    响应密文
        NNNN_resp_dst.bin    响应明文 msgpack   ← 转成 NNNN_resp.json 后删除
        NNNN_resp_hdr.bin    36 字节头
        NNNN_lz4in.bin       解密后的 LZ4 流
        NNNN_req_in.bin      请求体

用法：
    python msgpack2json.py                  # 处理全部会话目录
    python msgpack2json.py --watch          # 监控新文件
    python msgpack2json.py --keep-bin       # 保留 bin（默认删 dst）
    python msgpack2json.py --root <目录>     # 指定 http 根目录
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time

import msgpack

DEFAULT_ROOT = r"C:/Program Files (x86)/Steam/steamapps/common/UmamusumePrettyDerby_Jpn/hachimi/http"


def to_jsonable(obj):
    """msgpack 的 bytes 无法直接 JSON 化，转成字符串或 hex。"""
    if isinstance(obj, bytes):
        try:
            return obj.decode("utf-8")
        except UnicodeDecodeError:
            return {"__bytes__": obj.hex()}
    if isinstance(obj, dict):
        return {(k.decode("utf-8", "replace") if isinstance(k, bytes) else str(k)): to_jsonable(v)
                for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(v) for v in obj]
    return obj


def convert(dst_path: str, remove_bin: bool):
    raw = open(dst_path, "rb").read()
    try:
        obj = msgpack.unpackb(raw, raw=False, strict_map_key=False)
    except Exception as e:
        return False, "msgpack 解析失败: %s" % e

    out = dst_path[:-len("_resp_dst.bin")] + "_resp.json"
    with open(out, "w", encoding="utf-8") as fp:
        json.dump(to_jsonable(obj), fp, ensure_ascii=False, indent=2)

    size_out = os.path.getsize(out)
    if remove_bin:
        try:
            os.remove(dst_path)
            return True, "%d -> %d 字节 JSON（bin 已删）" % (len(raw), size_out)
        except OSError as e:
            return True, "%d -> %d 字节 JSON（bin 删除失败: %s）" % (len(raw), size_out, e)
    return True, "%d -> %d 字节 JSON" % (len(raw), size_out)


def run_once(root: str, remove_bin: bool) -> int:
    n = 0
    sessions = sorted(d for d in glob.glob(os.path.join(root, "*")) if os.path.isdir(d))
    if not sessions:
        print("%s 下还没有会话目录" % root)
        return 0
    for sess in sessions:
        files = sorted(glob.glob(os.path.join(sess, "*_resp_dst.bin")))
        if not files:
            continue
        print("=== %s ===" % os.path.basename(sess))
        for f in files:
            seq = os.path.basename(f)[:4]
            ok, msg = convert(f, remove_bin)
            print("  %s: %s" % (seq, msg))
            if ok:
                n += 1
    print("\n共转换 %d 个" % n)
    return n


def watch(root: str, remove_bin: bool) -> None:
    print("监控 %s ..." % root)
    while True:
        for f in glob.glob(os.path.join(root, "*", "*_resp_dst.bin")):
            seq = os.path.basename(f)[:4]
            sess = os.path.basename(os.path.dirname(f))
            ok, msg = convert(f, remove_bin)
            print("  [%s] %s/%s: %s" % (time.strftime("%H:%M:%S"), sess, seq, msg if ok else "失败 " + msg))
        time.sleep(1.0)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=DEFAULT_ROOT)
    ap.add_argument("--watch", action="store_true")
    ap.add_argument("--keep-bin", action="store_true", help="保留 *_resp_dst.bin")
    args = ap.parse_args()
    remove_bin = not args.keep_bin
    if args.watch:
        try:
            watch(args.root, remove_bin)
        except KeyboardInterrupt:
            print("\n停止")
        return 0
    run_once(args.root, remove_bin)
    return 0


if __name__ == "__main__":
    sys.exit(main())
