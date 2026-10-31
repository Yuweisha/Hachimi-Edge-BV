"""录制合并后重新注入全部改动（幂等，可重复跑）。

背景：
  rebuild_merge.py 只添加新条目、不覆盖旧条目 → 旧的注入数据安全。
  但如果游戏更新导致 load/index 长度变化，插件会命中"新长度"的原版数据，
  之前的注入（金币/剧情/散步/角色）就失效了。
  所以每次录制合并后跑一遍本脚本，把改动重新写进"当前生效的那份 load/index"。

顺序有依赖：
  1. trim_no_event_chara  先砍掉没有事件数据的角色（砍完 chara_list 变小）
  2. align_note_cards     card_list 必须 ⊂ release_card_array
  3. restore_money        金币/宝石
  4. restore_story_7070   剧情 7/7
  5. unlock_walking       散步 12/12
  6. check_injected_ids   最后核对

用法：
  python reapply_all.py            # 自动找当前 load/index
  python reapply_all.py --dry-run  # 只检查不写
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

TOOLS = Path(__file__).parent
PY = sys.executable

STEPS = [
    ("trim_no_event_chara.py", "砍掉无事件数据的角色（图鉴软死根因）"),
    ("align_note_cards.py", "card_list 与 release_card_array 对齐（名鉴软死根因）"),
    ("restore_money.py", "金币 1 亿 + 宝石各 1 亿"),
    ("restore_story_7070.py", "剧情全角色 7/7"),
    ("unlock_walking.py", "散步全角色 12/12"),
    ("check_injected_ids.py", "核对注入结果"),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    ok = fail = 0
    for i, (script, desc) in enumerate(STEPS, 1):
        p = TOOLS / script
        if not p.exists():
            print(f"[{i}/{len(STEPS)}] 跳过 {script}（不存在）")
            continue
        print(f"\n{'=' * 56}")
        print(f"[{i}/{len(STEPS)}] {script}")
        print(f"  {desc}")
        print("=" * 56)
        if a.dry_run:
            print("  [dry-run] 不执行")
            continue
        r = subprocess.run([PY, str(p)], capture_output=True, text=True, timeout=300)
        out = (r.stdout or "").strip()
        err = (r.stderr or "").strip()
        if out:
            for ln in out.split("\n")[-12:]:
                print(f"  {ln}")
        if r.returncode != 0:
            fail += 1
            print(f"  [失败] exit={r.returncode}")
            if err:
                for ln in err.split("\n")[-8:]:
                    print(f"  ! {ln}")
        else:
            ok += 1

    print(f"\n{'=' * 56}")
    print(f"完成：成功 {ok} / 失败 {fail}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
