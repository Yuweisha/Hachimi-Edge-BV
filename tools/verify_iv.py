"""抓一个真实加密请求，用插件上报的 key/iv 尝试解密，定位不匹配原因。"""
import sys, os, json, re, base64, time
sys.path.insert(0, r"C:/Users/Schwarz/projects/Hachimi-Edge/tools")

from game_crypto import decrypt_body_iv16, _try_lz4_decompress

LOG = r"C:/Users/Schwarz/uma_replay/localsrv.log"


def load_reported_keys():
    """从服务器日志里取最近上报的 (key, iv)。"""
    if not os.path.exists(LOG):
        return []
    txt = open(LOG, encoding="utf-8", errors="replace").read()
    pat = re.compile(r"\[crypto\] 登记会话密钥 sid=(\S+) key=([0-9A-F]{8})… iv=([0-9A-F]{8})…")
    out = []
    for m in pat.finditer(txt):
        out.append((m.group(1), m.group(2), m.group(3)))
    return out[-8:]


keys = load_reported_keys()
print(f"日志里最近 {len(keys)} 条上报（截断值）：")
for sid, k8, iv8 in keys:
    print(f"  sid={sid:10} key={k8}… iv={iv8}…")

# 完整 key/iv 只在插件日志里
PLOG = r"C:/Program Files (x86)/Steam/steamapps/common/UmamusumePrettyderby_Jpn/hachimi.log"
ptxt = open(PLOG, encoding="utf-8", errors="replace").read()
full = re.findall(r"\[keyreport #\d+\] ok=true path=(\S*) key=([0-9A-F]{32}) iv=([0-9A-F]{32})", ptxt)
print(f"\n插件日志里完整记录 {len(full)} 条：")
for path, k, iv in full[-6:]:
    print(f"  {path:40} key={k[:8]}… iv={iv[:8]}…")

if not full:
    print("没有完整记录，无法验证")
    sys.exit(0)

# 用最新的一组去解一个真实请求
# 请求体在 reqwire 目录只存了前 96 字节，不够；改为直接构造验证
path, k_hex, iv_hex = full[-1]
KEY = bytes.fromhex(k_hex)
IV16 = bytes.fromhex(iv_hex)
print(f"\n用最后一组：path={path} key={k_hex[:8]}… iv={iv_hex[:8]}…")

# 关键验证：IV 的 16 字节里，前 12 是 IV12，后 4 是 ctr（大端）
iv12 = IV16[:12]
ctr = int.from_bytes(IV16[12:], "big")
print(f"  IV12 = {iv12.hex().upper()}")
print(f"  ctr  = 0x{ctr:08X}")

# 从 hachimi.log 的 [ctr] 日志找同一 IV 的记录，确认我们上报的就是客户端用的
ctr_logs = re.findall(r"iv@\+0x180 = ([0-9A-F]{32})", ptxt)
print(f"\n客户端 [ctr] 日志里出现的 IV（最近 5 个）：")
for iv in ctr_logs[-5:]:
    mark = "  ★ 与上报一致" if iv == iv_hex else ""
    print(f"  {iv}{mark}")

# 统计有多少个上报的 IV 出现在 [ctr] 日志里
hit = sum(1 for _, _, iv in full if iv in ctr_logs)
print(f"\n上报 {len(full)} 条，其中 {hit} 条的 IV 与客户端 [ctr] 日志一致")
