"""把 C:/FiddlerDump/*.txt 整理成离线服务器用的录制库。

每个 dump 的格式：
    URL=https://api.games.umamusume.jp/umamusume/load/index
    RESPCODE=200
    ---REQB64---
    <base64>
    ---RSPB64---
    <base64>

产出：
    C:/Users/Schwarz/uma_replay/
        index.json            接口 -> 文件列表
        <path>/req_N.b64      请求体（base64，已加密）
        <path>/resp_N.b64     响应体（base64，已加密）
        <path>/resp_N.bin     响应解密后的 msgpack（如果插件抓到过）
        <path>/resp_N.json    转好的 JSON
"""
from __future__ import annotations

import base64
import glob
import json
import os
import re
import sys

DUMP_DIR = r"C:/FiddlerDump"
OUT_ROOT = r"C:/Users/Schwarz/uma_replay"


def parse_dump(path: str):
    raw = open(path, "rb").read().decode("utf-8", "replace")
    url = re.search(r"^URL=(.+)$", raw, re.M)
    code = re.search(r"^RESPCODE=(\d+)", raw, re.M)
    parts = raw.split("---REQB64---")
    if len(parts) < 2:
        return None
    rest = parts[1]
    seg = rest.split("---RSPB64---")
    req = seg[0].strip()
    resp = seg[1].strip() if len(seg) > 1 else ""

    url = url.group(1).strip() if url else ""
    if "/umamusume/" not in url:
        return None
    path = url.split("/umamusume/", 1)[1].strip("/")
    return {
        "url": url,
        "path": path,
        "code": int(code.group(1)) if code else 0,
        "req": req,
        "resp": resp,
        "src": os.path.basename(path),
    }


def safe_dir(path: str) -> str:
    return path.replace("/", "__")


def main() -> int:
    records = []
    for f in sorted(glob.glob(os.path.join(DUMP_DIR, "*.txt"))):
        r = parse_dump(f)
        if r:
            r["file"] = os.path.basename(f)
            records.append(r)

    if not records:
        print("没有可用的 dump")
        return 1

    # 每个接口只保留响应最大的那一条（通常是内容最全的）
    best = {}
    for r in records:
        key = r["path"]
        size = len(r["resp"])
        if key not in best or size > len(best[key]["resp"]):
            best[key] = r

    os.makedirs(OUT_ROOT, exist_ok=True)
    index = {"interfaces": [], "total_dumps": len(records)}

    for path, r in sorted(best.items()):
        d = os.path.join(OUT_ROOT, safe_dir(path))
        os.makedirs(d, exist_ok=True)

        with open(os.path.join(d, "req.b64"), "w") as fp:
            fp.write(r["req"])
        with open(os.path.join(d, "resp.b64"), "w") as fp:
            fp.write(r["resp"])

        # 顺手解一份原始二进制，方便后续处理
        req_raw = None
        resp_raw = None
        try:
            req_raw = base64.b64decode(r["req"])
            with open(os.path.join(d, "req.bin"), "wb") as fp:
                fp.write(req_raw)
        except Exception:
            pass
        try:
            resp_raw = base64.b64decode(r["resp"])
            with open(os.path.join(d, "resp.bin"), "wb") as fp:
                fp.write(resp_raw)
        except Exception:
            pass

        index["interfaces"].append({
            "path": path,
            "url": r["url"],
            "code": r["code"],
            "dump": r["file"],
            "req_len": len(req_raw) if req_raw else 0,
            "resp_len": len(resp_raw) if resp_raw else 0,
            "dir": safe_dir(path),
        })

    with open(os.path.join(OUT_ROOT, "index.json"), "w", encoding="utf-8") as fp:
        json.dump(index, fp, ensure_ascii=False, indent=2)

    print("共 %d 条 dump，%d 个接口" % (len(records), len(best)))
    print("%-42s %8s %8s" % ("PATH", "REQ", "RESP"))
    for it in index["interfaces"]:
        print("%-42s %8d %8d" % (it["path"], it["req_len"], it["resp_len"]))
    print("\n输出: %s" % OUT_ROOT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
