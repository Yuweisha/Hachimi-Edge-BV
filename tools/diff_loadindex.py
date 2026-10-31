import msgpack

GD = r"C:/Program Files (x86)/Steam/steamapps/common/UmamusumePrettyDerby_Jpn"

a = msgpack.unpackb(open(GD + "/hachimi/snapshots/BEFORE/0001_load_index.msgpack", "rb").read(),
                    raw=False, strict_map_key=False)["data"]
b = msgpack.unpackb(open(GD + "/hachimi/snapshots/AFTER/0001_load_index.msgpack", "rb").read(),
                    raw=False, strict_map_key=False)["data"]

print("顶层键变化:", set(a) ^ set(b))

changed = []
for k in sorted(set(a) & set(b)):
    if a[k] != b[k]:
        va, vb = a[k], b[k]
        ta = f"list[{len(va)}]" if isinstance(va, list) else (f"dict[{len(va)}]" if isinstance(va, dict) else str(va)[:30])
        tb = f"list[{len(vb)}]" if isinstance(vb, list) else (f"dict[{len(vb)}]" if isinstance(vb, dict) else str(vb)[:30])
        changed.append((k, ta, tb))

print(f"\n变化的顶层字段: {len(changed)}")
for k, ta, tb in changed:
    print(f"  {k}: {ta} -> {tb}")

# 对每个变化的字段做细粒度 diff
for k, _, _ in changed:
    va, vb = a[k], b[k]
    if isinstance(va, list) and isinstance(vb, list):
        sa = {str(x.get("id", x.get("episode_id", x))) for x in va if isinstance(x, dict)}
        sb = {str(x.get("id", x.get("episode_id", x))) for x in vb if isinstance(x, dict)}
        if sa != sb:
            print(f"\n  [{k}] 新增: {sorted(sb - sa)[:10]}")
            print(f"  [{k}] 消失: {sorted(sa - sb)[:10]}")
    elif isinstance(va, dict) and isinstance(vb, dict):
        dk = [kk for kk in set(va) | set(vb) if va.get(kk) != vb.get(kk)]
        if dk:
            print(f"\n  [{k}] 变化键: {dk[:8]}")
            for kk in dk[:4]:
                print(f"      {kk}: {va.get(kk)} -> {vb.get(kk)}")
