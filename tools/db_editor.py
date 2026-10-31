"""offline.db 图形化编辑器 —— 快速修改离线服务器的玩家状态。

功能：
  状态     user_state 所有键值（金币/宝石/钥匙等），双击编辑
  角色     owned_chara（亲爱度、粉丝、服装、觉醒等级）
  卡牌     owned_card（稀有度、天赋等级）
  服装     owned_cloth（增删）
  事件     unlocked_event（按角色筛选、批量删除）
  抽卡     gacha_log（历史记录）
  工具     一键操作：满金币/满钥匙/全解锁/清抽卡记录

用法：
  python db_editor.py                    # 自动找 C:/Users/Schwarz/uma_replay/offline.db
  python db_editor.py --db 路径           # 指定数据库

注意：改完必须重启离线服务器才生效（服务器启动时缓存了模板）。
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import struct
import sys
import time
from pathlib import Path

import msgpack

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

DEFAULT_DB = Path(r"C:/Users/Schwarz/uma_replay/offline.db")
GAME_DIR = os.environ.get(
    "UMA_GAME_DIR",
    r"C:/Program Files (x86)/Steam/steamapps/common/UmamusumePrettyDerby_Jpn")
UMALIB_JSON = os.path.join(GAME_DIR, "hachimi", "umalib.json")

MDB = r"C:/Program Files (x86)/Steam/steamapps/common/UmamusumePrettyDerby_Jpn/UmamusumePrettyDerby_Jpn_Data/Persistent/master/master.mdb"

COIN_MAX = 100_000_000
KEY_MAX = 9999


class _LayoutDialog(simpledialog.Dialog):
    """改角色/服装/颜色的小对话框。"""

    def __init__(self, parent, title, chara_id, dress_id, color_id):
        self._c0 = str(chara_id or "")
        self._d0 = str(dress_id or "")
        self._k0 = str(color_id or "0")
        super().__init__(parent, title)

    def body(self, master):
        ttk.Label(master, text="角色 ID").grid(row=0, column=0, sticky="e", padx=4, pady=3)
        self.e_chara = ttk.Entry(master, width=16)
        self.e_chara.grid(row=0, column=1, padx=4)
        self.e_chara.insert(0, self._c0)

        ttk.Label(master, text="服装 ID").grid(row=1, column=0, sticky="e", padx=4, pady=3)
        self.e_dress = ttk.Entry(master, width=16)
        self.e_dress.grid(row=1, column=1, padx=4)
        self.e_dress.insert(0, self._d0)

        ttk.Label(master, text="颜色").grid(row=2, column=0, sticky="e", padx=4, pady=3)
        self.e_color = ttk.Entry(master, width=16)
        self.e_color.grid(row=2, column=1, padx=4)
        self.e_color.insert(0, self._k0)
        return self.e_chara

    def validate(self):
        try:
            int(self.e_chara.get().strip() or 0)
            int(self.e_dress.get().strip() or 0)
            int(self.e_color.get().strip() or 0)
        except ValueError:
            messagebox.showerror("格式错误", "三个字段都必须是整数", parent=self)
            return False
        return True

    def apply(self):
        self.result = (
            int(self.e_chara.get().strip() or 0),
            int(self.e_dress.get().strip() or 0),
            int(self.e_color.get().strip() or 0),
        )


class SearchCombo(ttk.Frame):
    """可输入搜索的下拉：显示 "id 名称"，输入时实时过滤。"""

    def __init__(self, master, items, width=30, on_change=None):
        super().__init__(master)
        self._items = list(items)
        self._map = {d: i for i, d in self._items}
        self.cb = ttk.Combobox(self, width=width, values=[d for d in self._map])
        self.cb.pack(fill="x")
        self.cb.bind("<KeyRelease>", self._filter)
        if on_change:
            self.cb.bind("<<ComboboxSelected>>", lambda e: on_change())

    def _filter(self, ev):
        if ev.keysym in ("Up", "Down", "Return", "Escape", "Tab", "Left", "Right", "Home", "End"):
            return
        txt = self.cb.get().strip().lower()
        if not txt:
            self.cb["values"] = [d for d in self._map]
            return
        hits = [d for d in self._map if txt in d.lower()]
        self.cb["values"] = hits[:80]
        if hits:
            self.cb.event_generate("<Down>")

    def set_items(self, items):
        """运行期更新数据源（建立数据库连接后才能拿到真实列表）。"""
        items = list(items)
        # 内容没变就跳过（Live 页一次刷新会重复设置同一份列表）
        if getattr(self, "_items", None) == items:
            return
        self._items = items
        self._map = {lab: cid for cid, lab in items}      # label -> id（get_id 用）
        self._id2label = {cid: lab for cid, lab in items} # id -> label（set_id 用）
        self.cb["values"] = [lab for _cid, lab in items]

    def get_id(self) -> int:
        txt = self.cb.get().strip()
        if not txt:
            return 0
        if txt in self._map:
            return self._map[txt]
        # NPC xxxx → chara_id 记 0，由调用方从文本取 mob_id
        if txt.startswith("NPC "):
            return 0
        # 没选列表项时，尝试解析开头的数字
        head = txt.split()[0]
        if head.isdigit():
            return int(head)
        # 模糊命中第一个
        for d in self._map:
            if txt.lower() in d.lower():
                return self._map[d]
        return 0

    def set_id(self, cid: int):
        if not cid:
            self.cb.set("")
            return
        lab = getattr(self, "_id2label", {}).get(cid)
        self.cb.set(lab if lab is not None else str(cid))


def _proc_running(exe_name: str) -> bool:
    """用 ctypes 枚举进程判断 exe 是否在运行（毫秒级，不弹窗）。"""
    import ctypes
    from ctypes import wintypes

    class _PE32(ctypes.Structure):
        _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                    ("th32ProcessID", wintypes.DWORD),
                    ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
                    ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                    ("th32ParentProcessID", wintypes.DWORD),
                    ("pcPriClassBase", ctypes.c_long), ("dwFlags", wintypes.DWORD),
                    ("szExeFile", wintypes.WCHAR * 260)]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(_PE32)]
    kernel32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(_PE32)]

    snap = kernel32.CreateToolhelp32Snapshot(0x00000002, 0)
    if not snap or snap == wintypes.HANDLE(-1).value:
        return False
    try:
        e = _PE32()
        e.dwSize = ctypes.sizeof(_PE32)
        ok = kernel32.Process32FirstW(snap, ctypes.byref(e))
        tgt = exe_name.lower()
        while ok:
            if e.szExeFile.lower() == tgt:
                return True
            ok = kernel32.Process32NextW(snap, ctypes.byref(e))
        return False
    finally:
        kernel32.CloseHandle(snap)


class App:
    def __init__(self, root: tk.Tk, db_path: Path):
        self.root = root
        self.db_path = db_path
        self.con: sqlite3.Connection | None = None

        root.title("UmaOffline DB Editor")
        root.geometry("1080x720")

        # ---- 顶栏 ----
        top = ttk.Frame(root, padding=(8, 6))
        top.pack(fill="x")
        ttk.Label(top, text="数据库：").pack(side="left")
        self.var_db = tk.StringVar(value=str(db_path))
        ttk.Entry(top, textvariable=self.var_db, width=40).pack(side="left", padx=4)
        ttk.Button(top, text="打开", command=self.open_db).pack(side="left", padx=3)
        ttk.Button(top, text="选择…", command=self.pick_db).pack(side="left", padx=3)
        ttk.Button(top, text="刷新全部", command=self.refresh_all).pack(side="left", padx=8)

        # ---- 服务器控制（独立一行，避免被挤掉） ----
        bar = ttk.Frame(root, padding=(8, 0, 8, 4))
        bar.pack(fill="x")
        self.var_srv_state = tk.StringVar(value="○ 未启动")
        ttk.Label(bar, textvariable=self.var_srv_state,
                  font=("Microsoft YaHei UI", 9, "bold")).pack(side="left", padx=(0, 8))
        ttk.Label(bar, text="端口").pack(side="left")
        self.var_srv_port = tk.StringVar(value="826")
        ttk.Entry(bar, textvariable=self.var_srv_port, width=6).pack(side="left", padx=4)
        ttk.Button(bar, text="启动", command=self._srv_start).pack(side="left", padx=3)
        ttk.Button(bar, text="停止", command=self._srv_stop).pack(side="left", padx=3)
        ttk.Button(bar, text="重启", command=self._srv_restart).pack(side="left", padx=3)

        # ---- Notebook ----
        self.nb = ttk.Notebook(root)
        self.nb.pack(fill="both", expand=True, padx=8, pady=4)

        self.tab_chara = ttk.Frame(self.nb)
        self.tab_card = ttk.Frame(self.nb)
        self.tab_cloth = ttk.Frame(self.nb)
        self.tab_item = ttk.Frame(self.nb)
        self.tab_event = ttk.Frame(self.nb)
        self.tab_gacha = ttk.Frame(self.nb)
        self.tab_pool = ttk.Frame(self.nb)
        self.tab_tools = ttk.Frame(self.nb)
        self.tab_layout = ttk.Frame(self.nb)
        self.tab_trained = ttk.Frame(self.nb)
        self.tab_log = ttk.Frame(self.nb)
        self.tab_server = ttk.Frame(self.nb)
        self.tab_cache = ttk.Frame(self.nb)

        # ★ 最小服务器版：只保留「服务器」页
        #   其他页的 Frame 仍然创建（构造函数会引用），但不加入 notebook。
        # 完整版：显示所有页面（最小版另有一份拷贝给外部）
        self._MINIMAL = False
        if self._MINIMAL:
            self.nb.add(self.tab_trained, text="育成马娘")
            self.nb.add(self.tab_server, text="服务器")
            self.nb.add(self.tab_log, text="服务器日志")
        else:
            self.nb.add(self.tab_trained, text="育成马娘")
            self.nb.add(self.tab_chara, text="育成数据")
            self.nb.add(self.tab_card, text="天赋突破")
            self.nb.add(self.tab_cloth, text="服装")
            self.nb.add(self.tab_item, text="道具")
            self.nb.add(self.tab_event, text="事件")
            self.nb.add(self.tab_pool, text="卡池 ID")
            self.nb.add(self.tab_gacha, text="抽卡记录")
            self.nb.add(self.tab_layout, text="角色编组")
            self.nb.add(self.tab_tools, text="工具")
            self.nb.add(self.tab_cache, text="接口缓存")
            self.nb.add(self.tab_server, text="服务器")
            self.nb.add(self.tab_log, text="服务器日志")

        # 育成马娘页两种模式都要有
        self._build_trained_tab()
        self._build_log_tab()

        if not self._MINIMAL:
            self._build_chara_tab()
            self._build_card_tab()
            self._build_cloth_tab()
            self._build_item_tab()
            self._build_event_tab()
            self._build_pool_tab()
            self._build_gacha_tab()
            self._build_layout_tab()
            self._build_tools_tab()
            self._build_cache_tab()
        self._build_server_tab()

        # ---- 底栏 ----
        self.var_status = tk.StringVar(value="就绪")
        ttk.Label(root, textvariable=self.var_status, relief="sunken", anchor="w").pack(
            fill="x", side="bottom")

        self.open_db()
        try:
            self.refresh_trained()
        except Exception:
            pass
        try:
            self._log_tick()
        except Exception:
            pass
        # 默认停在「育成数据」页（延迟到窗口就绪后）
        try:
            # 最小服务器版只有「服务器」页，不能选索引 7
            _idx = self.nb.index(self.tab_log) if hasattr(self, "tab_log") else 0  # 默认停「服务器日志」
            self.root.after(200, lambda i=_idx: self.nb.select(i))
        except Exception:
            pass

    # ============ 数据库 ============
    def pick_db(self):
        p = filedialog.askopenfilename(
            title="选择 offline.db",
            filetypes=[("SQLite", "*.db"), ("所有文件", "*.*")],
            initialdir=str(self.db_path.parent) if self.db_path else None)
        if p:
            self.var_db.set(p)
            self.open_db()

    def open_db(self):
        p = Path(self.var_db.get())
        if not p.exists():
            messagebox.showerror("打不开", f"文件不存在：\n{p}")
            return
        try:
            if self.con:
                self.con.close()
            self.con = sqlite3.connect(str(p), timeout=10)
            self.db_path = p
            self.refresh_all()
            self.status(f"已连接 {p}  ({p.stat().st_size:,} B)")
        except Exception as e:
            messagebox.showerror("打不开", str(e))

    def q(self, sql: str, args=()):
        if not self.con:
            return []
        return self.con.execute(sql, args).fetchall()

    def ex(self, sql: str, args=()):
        if not self.con:
            return
        self.con.execute(sql, args)
        self.con.commit()

    def status(self, msg: str):
        self.var_status.set(f"{time.strftime('%H:%M:%S')}  {msg}")

    # ============ 通用表格 ============
    def _make_tree(self, parent, cols, widths=None, editable=False, on_edit=None):
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True, padx=4, pady=4)

        vsb = ttk.Scrollbar(frame, orient="vertical")
        hsb = ttk.Scrollbar(frame, orient="horizontal")
        tree = ttk.Treeview(frame, columns=cols, show="headings",
                            yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.config(command=tree.yview)
        hsb.config(command=tree.xview)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        tree.pack(side="left", fill="both", expand=True)

        # 三态排序状态：(列名 -> None默认 / False正序 / True倒序)
        tree._sort_state = {}
        tree._orig_order = []

        def _heading_cmd(colname):
            def cmd():
                self._sort_tree(tree, colname)
            return cmd

        for i, c in enumerate(cols):
            tree.heading(c, text=c, command=_heading_cmd(c))
            tree.column(c, width=(widths[i] if widths and i < len(widths) else 100),
                        anchor="w", stretch=True)

        if editable and on_edit:
            def _dbl(event):
                row = tree.identify_row(event.y)
                col = tree.identify_column(event.x)
                if not row or not col:
                    return
                cidx = int(col[1:]) - 1
                if cidx < 0 or cidx >= len(cols):
                    return
                x, y, w, h = tree.bbox(row, col)
                val = tree.set(row, cols[cidx])
                e = ttk.Entry(tree)
                e.place(x=x, y=y, width=w, height=h)
                e.insert(0, val)
                e.focus()

                def commit(ev=None):
                    new = e.get()
                    e.destroy()
                    on_edit(tree, row, cols[cidx], new)

                e.bind("<Return>", commit)
                e.bind("<FocusOut>", commit)
                e.bind("<Escape>", lambda ev: e.destroy())

            tree.bind("<Double-1>", _dbl)

        return tree

    def _sort_tree(self, tree, col):
        """点击表头三态排序：默认 → 正序 → 倒序 → 默认。"""
        state = tree._sort_state
        cur = state.get(col)
        if cur is None:
            new_state = False          # 正序
            arrow = " ↑"
        elif cur is False:
            new_state = True           # 倒序
            arrow = " ↓"
        else:
            new_state = None           # 恢复默认
            arrow = ""
        # 清掉其他列的状态
        for k in list(state.keys()):
            state[k] = None
            try:
                tree.heading(k, text=k)
            except Exception:
                pass
        state[col] = new_state
        tree.heading(col, text=col + arrow)

        kids = list(tree.get_children(""))
        if not kids:
            return

        # 记住首次的原始顺序
        if not tree._orig_order:
            tree._orig_order = kids[:]

        def key_of(iid):
            v = tree.set(iid, col)
            # 数字优先按数值排
            try:
                return (0, float(v))
            except (ValueError, TypeError):
                return (1, str(v))

        if new_state is None:
            ordered = [k for k in tree._orig_order if k in set(kids)]
            ordered += [k for k in kids if k not in set(ordered)]
        else:
            ordered = sorted(kids, key=key_of, reverse=new_state)

        for idx, iid in enumerate(ordered):
            tree.move(iid, "", idx)

    # ============ Tab: 状态 ============



    def _max_coin(self):
        self.ex("INSERT OR REPLACE INTO user_state(key,value) VALUES ('fcoin',?)", (str(COIN_MAX),))
        self.ex("INSERT OR REPLACE INTO user_state(key,value) VALUES ('coin',?)", (str(COIN_MAX),))
        self.ex("INSERT OR REPLACE INTO user_state(key,value) VALUES ('gold_item',?)", (str(COIN_MAX),))
        self.refresh_item() if hasattr(self, "refresh_item") else None
        self.status(f"金币/宝石 = {COIN_MAX:,}")

    def _max_key(self):
        self.ex("INSERT OR REPLACE INTO user_state(key,value) VALUES ('key_item',?)", (str(KEY_MAX),))
        self.refresh_item() if hasattr(self, "refresh_item") else None
        self.status(f"钥匙 = {KEY_MAX}")

    # ============ Tab: 角色 ============
    def _build_chara_tab(self):
        cols = ("角色ID", "中文名", "日文名", "育成次数", "好感度",
                "粉丝数", "评分 Rank", "服装ID")
        self.tree_chara = self._make_tree(
            self.tab_chara, cols, [70, 130, 190, 90, 90, 100, 90, 95], editable=True,
            on_edit=self._edit_chara)


        bar = ttk.Frame(self.tab_chara)
        bar.pack(fill="x", padx=4, pady=(0, 4))
        ttk.Label(bar, text="筛选角色 ID：").pack(side="left")
        self.var_chara_filter = tk.StringVar()
        e = ttk.Entry(bar, textvariable=self.var_chara_filter, width=12)
        e.pack(side="left", padx=4)
        e.bind("<Return>", lambda ev: self.refresh_chara())
        ttk.Button(bar, text="刷新", command=self.refresh_chara).pack(side="left", padx=2)
        ttk.Button(bar, text="好感度拉满", command=self._max_love).pack(side="left", padx=8)
        ttk.Button(bar, text="粉丝拉满", command=self._max_fan).pack(side="left", padx=2)

    def refresh_chara(self):
        t = self.tree_chara
        t.delete(*t.get_children())
        f = self.var_chara_filter.get().strip()
        sql = ("SELECT c.chara_id, "
               "COALESCE(cn.name,''), COALESCE(jn.name,''), "
               "c.training_num, c.love_point, c.fan, c.rank_score, c.dress_id "
               "FROM owned_chara c "
               "LEFT JOIN name_text jn ON jn.kind='chara' AND jn.id=c.chara_id "
               "LEFT JOIN name_text cn ON cn.kind='chara_cn' AND cn.id=c.chara_id ")
        if f:
            rows = self.q(sql + "WHERE c.chara_id LIKE ? OR cn.name LIKE ? "
                                 "ORDER BY c.chara_id", (f"%{f}%", f"%{f}%"))
        else:
            rows = self.q(sql + "ORDER BY c.chara_id")
        for r in rows:
            vals = list(r)
            # 第 7 列（索引 6）= 评分 → 显示成「字母 (分数)」
            rs = vals[6] or 0
            vals[6] = self._rank_label(int(rs)) if rs else "-"
            t.insert("", "end", iid=str(r[0]), values=vals)
        self.status(f"角色 {len(rows)} 个")

    # 评分区间 → 字母（读 master 的 single_mode_rank + text_data[415]）
    _RANK_BANDS = None
    _RANK_LETTERS = None

    def _load_rank_table(self):
        if self._RANK_BANDS is not None:
            return
        import sqlite3 as _s
        MDB = (r"C:/Program Files (x86)/Steam/steamapps/common/UmamusumePrettyderby_Jpn/"
               r"UmamusumePrettyderby_Jpn_Data/Persistent/master/master.mdb")
        try:
            mc = _s.connect(f"file:{MDB}?mode=ro", uri=True)
            self._RANK_BANDS = mc.execute(
                "SELECT id, min_value, max_value FROM single_mode_rank ORDER BY id").fetchall()
            self._RANK_LETTERS = [r[0] for r in mc.execute(
                "SELECT text FROM text_data WHERE category=415 ORDER BY [index]").fetchall()]
            mc.close()
        except Exception:
            self._RANK_BANDS, self._RANK_LETTERS = [], []

    # 实测校准的「大等级」分界（来自两张游戏内截图，分数下限 → 字母）
    # S/UG/UE/UB/UA 段已用真实数据校准；更低分段沿用 single_mode_rank 的区间起点
    _RANK_CUTS = [
        (0,      "G"),
        (300,    "F"),
        (600,    "E"),
        (900,    "D"),
        (1300,   "C"),
        (1800,   "B"),
        (2300,   "A"),
        (2900,   "SS"),
        (16176,  "S"),       # 实测：16,176 → S
        (21707,  "UG"),      # 实测：21,707 → UG4
        (29008,  "UE"),      # 实测：29,008 → UE3
        (34605,  "UB"),      # 实测：34,605 → UB2
        (60800,  "UA"),      # 实测：60,800 → UA7（48.3k~60.8k 仍是 UB）
        (175000, "US"),
    ]

    def _rank_label(self, score: int) -> str:
        """分数 → '字母 (分数)'；字母按实测分界，未校准区间只显示分数"""
        lab = ""
        for cut, name in self._RANK_CUTS:
            if score >= cut:
                lab = name
            else:
                break
        return f"{lab} ({score:,})" if lab else f"({score:,})"

    _RANK_COLORS = {
        "US": "#ffb703", "UA": "#4cc9f0", "UB": "#b388ff",
        "UC": "#f72585", "UD": "#4895ef", "UE": "#9d4edd",
        "UF": "#4ea8de", "UG": "#e0e0e0",
        "SS": "#ffd166", "S": "#ffd166",
        "A": "#8ecae6", "B": "#8ecae6", "C": "#8ecae6",
        "D": "#8ecae6", "E": "#8ecae6", "F": "#8ecae6", "G": "#8ecae6",
    }

    def _rank_tag(self, score: int) -> str:
        lab = ""
        for cut, name in self._RANK_CUTS:
            if score >= cut:
                lab = name
            else:
                break
        return f"rank_{lab}" if lab else "rank_none"

    # 表头中文 -> 数据库字段
    CHARA_COL = {
        "育成次数": "training_num",
        "好感度": "love_point",
        "粉丝数": "fan",
        "服装ID": "dress_id",
    }

    def _edit_chara(self, tree, row, col, new):
        field = self.CHARA_COL.get(col)
        if not field:
            return
        try:
            val = int(new)
        except ValueError:
            messagebox.showerror("格式错误", "必须是整数")
            return
        try:
            self.ex(f"UPDATE owned_chara SET {field}=? WHERE chara_id=?", (val, int(row)))
            tree.set(row, col, val)
            self.status(f"角色 {row} 的{col} = {val}")
        except Exception as e:
            messagebox.showerror("保存失败", str(e))

    def _max_love(self):
        self.ex("UPDATE owned_chara SET love_point=10000")
        self.refresh_chara()
        self.status("所有角色好感度 = 10000")

    def _max_fan(self):
        self.ex("UPDATE owned_chara SET fan=10000000")
        self.refresh_chara()
        self.status("所有角色粉丝 = 10,000,000")

    # ============ Tab: 卡牌 ============
    def _build_card_tab(self):
        cols = ("卡ID", "中文名", "日文名", "稀有度", "天赋等级", "获得时间")
        self.tree_card = self._make_tree(
            self.tab_card, cols, [90, 240, 280, 70, 90, 165], editable=True,
            on_edit=self._edit_card)

        bar = ttk.Frame(self.tab_card)
        bar.pack(fill="x", padx=4, pady=(0, 4))
        ttk.Label(bar, text="筛选卡 ID：").pack(side="left")
        self.var_card_filter = tk.StringVar()
        e = ttk.Entry(bar, textvariable=self.var_card_filter, width=12)
        e.pack(side="left", padx=4)
        e.bind("<Return>", lambda ev: self.refresh_card())
        ttk.Button(bar, text="刷新", command=self.refresh_card).pack(side="left", padx=2)
        ttk.Button(bar, text="全部天赋拉满", command=self._max_talent).pack(side="left", padx=8)

    def refresh_card(self):
        t = self.tree_card
        t.delete(*t.get_children())
        f = self.var_card_filter.get().strip()
        sql = ("SELECT c.card_id, COALESCE(cn.name,''), COALESCE(jn.name,''), "
               "c.rarity, c.talent_level, c.create_time "
               "FROM owned_card c "
               "LEFT JOIN name_text jn ON jn.kind='card' AND jn.id=c.card_id "
               "LEFT JOIN name_text cn ON cn.kind='card_cn' AND cn.id=c.card_id ")
        if f:
            rows = self.q(sql + "WHERE c.card_id LIKE ? OR cn.name LIKE ? "
                                 "ORDER BY c.card_id", (f"%{f}%", f"%{f}%"))
        else:
            rows = self.q(sql + "ORDER BY c.card_id")
        for r in rows:
            t.insert("", "end", iid=str(r[0]), values=r)
        self.status(f"卡牌 {len(rows)} 张")

    CARD_COL = {"稀有度": "rarity", "天赋等级": "talent_level"}

    def _edit_card(self, tree, row, col, new):
        field = self.CARD_COL.get(col)
        if not field:
            return
        try:
            val = int(new)
        except ValueError:
            messagebox.showerror("格式错误", "必须是整数")
            return
        try:
            self.ex(f"UPDATE owned_card SET {field}=? WHERE card_id=?", (val, int(row)))
            tree.set(row, col, val)
            self.status(f"卡 {row} 的{col} = {val}")
        except Exception as e:
            messagebox.showerror("保存失败", str(e))

    def _max_talent(self):
        self.ex("UPDATE owned_card SET talent_level=5")
        self.refresh_card()
        self.status("所有卡天赋 = 5")

    # ============ Tab: 服装 ============
    def _build_cloth_tab(self):
        cols = ("服装ID", "中文名", "日文名", "描述")
        self.tree_cloth = self._make_tree(
            self.tab_cloth, cols, [80, 180, 220, 400])

        bar = ttk.Frame(self.tab_cloth)
        bar.pack(fill="x", padx=4, pady=(0, 4))

        top = ttk.Frame(self.tab_cloth)
        top.pack(fill="x", padx=4, pady=(4, 0))
        ttk.Label(top, text="搜索名称或 ID：").pack(side="left")
        self.var_cloth_filter = tk.StringVar()
        e = ttk.Entry(top, textvariable=self.var_cloth_filter, width=18)
        e.pack(side="left", padx=4)
        e.bind("<Return>", lambda ev: self.refresh_cloth())
        ttk.Button(top, text="刷新", command=self.refresh_cloth).pack(side="left", padx=2)

        ttk.Label(bar, text="添加服装 ID：").pack(side="left")
        self.var_cloth = tk.StringVar()
        ttk.Entry(bar, textvariable=self.var_cloth, width=14).pack(side="left", padx=4)
        ttk.Button(bar, text="添加", command=self._add_cloth).pack(side="left", padx=2)
        ttk.Button(bar, text="删除选中", command=self._del_cloth).pack(side="left", padx=8)
        ttk.Button(bar, text="从游戏资料库补齐全部", command=self._fill_cloth).pack(side="left", padx=2)

    def refresh_cloth(self):
        t = self.tree_cloth
        t.delete(*t.get_children())
        f = self.var_cloth_filter.get().strip()
        sql = ("SELECT c.cloth_id, COALESCE(cn.name,''), COALESCE(jn.name,''), "
               "COALESCE(d.name,'') "
               "FROM owned_cloth c "
               "LEFT JOIN name_text jn ON jn.kind='dress' AND jn.id=c.cloth_id "
               "LEFT JOIN name_text cn ON cn.kind='dress_cn' AND cn.id=c.cloth_id "
               "LEFT JOIN name_text d ON d.kind='dress_desc' AND d.id=c.cloth_id ")
        if f:
            rows = self.q(sql + "WHERE c.cloth_id LIKE ? OR cn.name LIKE ? "
                                 "ORDER BY c.cloth_id", (f"%{f}%", f"%{f}%"))
        else:
            rows = self.q(sql + "ORDER BY c.cloth_id")
        for r in rows:
            t.insert("", "end", iid=str(r[0]), values=r)
        self.status(f"服装 {len(rows)} 件")

    def _add_cloth(self):
        s = self.var_cloth.get().strip()
        if not s:
            return
        try:
            cid = int(s)
        except ValueError:
            messagebox.showerror("格式错误", "必须是整数")
            return
        self.ex("INSERT OR IGNORE INTO owned_cloth(cloth_id) VALUES (?)", (cid,))
        self.refresh_cloth()
        self.status(f"已添加服装 {cid}")

    def _del_cloth(self):
        sel = self.tree_cloth.selection()
        if not sel:
            return
        for cid in sel:
            self.ex("DELETE FROM owned_cloth WHERE cloth_id=?", (int(cid),))
        self.refresh_cloth()
        self.status(f"删除 {len(sel)} 件")

    def _fill_cloth(self):
        try:
            mc = sqlite3.connect(f"file:{MDB}?mode=ro", uri=True)
            ids = [r[0] for r in mc.execute("SELECT id FROM dress_data").fetchall()]
            mc.close()
        except Exception as e:
            messagebox.showerror("读 master 失败", str(e))
            return
        for i in ids:
            self.ex("INSERT OR IGNORE INTO owned_cloth(cloth_id) VALUES (?)", (i,))
        self.refresh_cloth()
        self.status(f"从 master 补齐到 {len(ids)} 件")

    # ============ Tab: 道具 ============
    def _build_item_tab(self):
        cols = ("道具ID", "中文名", "日文名", "数量")
        self.tree_item = self._make_tree(
            self.tab_item, cols, [80, 200, 240, 120], editable=True,
            on_edit=self._edit_item)

        # 宝石（不属于 item_list，单独放）
        gem = ttk.Frame(self.tab_item)
        gem.pack(fill="x", padx=4, pady=(6, 2))
        self.var_gem = tk.StringVar(value="")
        ttk.Label(gem, textvariable=self.var_gem, font=("Microsoft YaHei UI", 10)).pack(side="left")
        ttk.Button(gem, text="宝石拉满", command=self._max_gem).pack(side="left", padx=10)

        bar = ttk.Frame(self.tab_item)
        bar.pack(fill="x", padx=4, pady=(0, 4))
        ttk.Label(bar, text="筛选道具 ID：").pack(side="left")
        self.var_item_filter = tk.StringVar()
        e = ttk.Entry(bar, textvariable=self.var_item_filter, width=14)
        e.pack(side="left", padx=4)
        e.bind("<Return>", lambda ev: self.refresh_item())
        ttk.Button(bar, text="刷新", command=self.refresh_item).pack(side="left", padx=2)
        ttk.Button(bar, text="金币/钥匙 拉满", command=self._max_coin_key).pack(side="left", padx=8)
        self.var_item_info = tk.StringVar(value="")
        ttk.Label(bar, textvariable=self.var_item_info).pack(side="left", padx=10)

    def refresh_item(self):
        t = self.tree_item
        t.delete(*t.get_children())
        if not self.con:
            return
        f = self.var_item_filter.get().strip()
        sql = ("SELECT i.item_id, COALESCE(cn.name,''), COALESCE(jp.name,''), i.number "
               "FROM owned_item i "
               "LEFT JOIN name_text jp ON jp.kind='item' AND jp.id=i.item_id "
               "LEFT JOIN name_text cn ON cn.kind='item_cn' AND cn.id=i.item_id ")
        if f:
            rows = self.q(sql + "WHERE i.item_id LIKE ? OR cn.name LIKE ? "
                                 "ORDER BY i.item_id", (f"%{f}%", f"%{f}%"))
        else:
            rows = self.q(sql + "ORDER BY i.item_id")
        for r in rows:
            t.insert("", "end", iid=str(r[0]), values=r)
        self.var_item_info.set(f"{len(rows)} 种道具")
        fcoin = int(self.q("SELECT value FROM user_state WHERE key='fcoin'")[0][0]) if self.q("SELECT value FROM user_state WHERE key='fcoin'") else 0
        coin = int(self.q("SELECT value FROM user_state WHERE key='coin'")[0][0]) if self.q("SELECT value FROM user_state WHERE key='coin'") else 0
        self.var_gem.set(f"宝石：免费 {fcoin:,}    付费 {coin:,}")

    def _edit_item(self, tree, row, col, new):
        if col != "数量":
            return
        try:
            val = int(new)
        except ValueError:
            messagebox.showerror("格式错误", "必须是整数")
            return
        try:
            self.ex("UPDATE owned_item SET number=? WHERE item_id=?", (val, int(row)))
            tree.set(row, "数量", val)
            iid = int(row)
            if iid == 59:
                self.ex("INSERT OR REPLACE INTO user_state(key,value) VALUES ('gold_item',?)",
                        (str(val),))
            elif iid == 190:
                self.ex("INSERT OR REPLACE INTO user_state(key,value) VALUES ('key_item',?)",
                        (str(val),))
            self.status(f"道具 {row} 数量 = {val:,}")
        except Exception as e:
            messagebox.showerror("保存失败", str(e))

    def _max_gem(self):
        for k in ("fcoin", "coin"):
            self.ex("INSERT OR REPLACE INTO user_state(key,value) VALUES (?,?)",
                    (k, str(COIN_MAX)))
        self.refresh_item()
        self.status(f"宝石 = {COIN_MAX:,}（免费+付费各一份）")

    def _max_coin_key(self):
        self.ex("INSERT OR REPLACE INTO owned_item(item_id,number) VALUES (59,?)",
                (COIN_MAX,))
        self.ex("INSERT OR REPLACE INTO owned_item(item_id,number) VALUES (190,?)",
                (KEY_MAX,))
        self.ex("INSERT OR REPLACE INTO user_state(key,value) VALUES ('gold_item',?)",
                (str(COIN_MAX),))
        self.ex("INSERT OR REPLACE INTO user_state(key,value) VALUES ('key_item',?)",
                (str(KEY_MAX),))
        self.ex("INSERT OR REPLACE INTO user_state(key,value) VALUES ('coin',?)",
                (str(COIN_MAX),))
        self.ex("INSERT OR REPLACE INTO user_state(key,value) VALUES ('fcoin',?)",
                (str(COIN_MAX),))
        self.refresh_item()
        self.refresh_item()
        self.status(f"金币/钥匙/宝石 = {COIN_MAX:,}")

    # ============ Tab: 事件 ============
    def _build_event_tab(self):
        cols = ("剧情ID", "角色ID", "解锁时间", "未读")
        self.tree_event = self._make_tree(self.tab_event, cols, [130, 100, 180, 80])

        bar = ttk.Frame(self.tab_event)
        bar.pack(fill="x", padx=4, pady=(0, 4))
        ttk.Label(bar, text="筛选角色 ID：").pack(side="left")
        self.var_ev_filter = tk.StringVar()
        e = ttk.Entry(bar, textvariable=self.var_ev_filter, width=12)
        e.pack(side="left", padx=4)
        e.bind("<Return>", lambda ev: self.refresh_event())
        ttk.Button(bar, text="刷新", command=self.refresh_event).pack(side="left", padx=2)
        ttk.Button(bar, text="全部设为已读", command=self._clear_new_flag).pack(side="left", padx=8)
        ttk.Button(bar, text="全部解锁", command=self._unlock_all_events).pack(side="left", padx=2)

    def refresh_event(self):
        t = self.tree_event
        t.delete(*t.get_children())
        f = self.var_ev_filter.get().strip()
        if f:
            rows = self.q("SELECT story_id, chara_id, unlocked_at, new_flag FROM unlocked_event "
                          "WHERE chara_id LIKE ? ORDER BY chara_id, story_id LIMIT 3000", (f"%{f}%",))
        else:
            rows = self.q("SELECT story_id, chara_id, unlocked_at, new_flag FROM unlocked_event "
                          "ORDER BY chara_id, story_id LIMIT 3000")
        for r in rows:
            t.insert("", "end", values=r)
        total = self.q("SELECT COUNT(*) FROM unlocked_event")[0][0]
        self.status(f"显示 {len(rows)} 条（共 {total:,} 条）")

    def _clear_new_flag(self):
        self.ex("UPDATE unlocked_event SET new_flag=0")
        self.refresh_event()
        self.status("全部设为已读")

    def _unlock_all_events(self):
        try:
            mc = sqlite3.connect(f"file:{MDB}?mode=ro", uri=True)
            rows = mc.execute("SELECT story_id, card_chara_id FROM single_mode_story_data "
                              "WHERE gallery_flag=1").fetchall()
            mc.close()
        except Exception as e:
            messagebox.showerror("读 master 失败", str(e))
            return
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        for sid, cid in rows:
            self.ex("INSERT OR IGNORE INTO unlocked_event(story_id, chara_id, unlocked_at, new_flag) "
                    "VALUES (?,?,?,0)", (sid, cid, ts))
        self.refresh_event()
        self.status(f"全解锁 {len(rows):,} 个事件")

    # ============ Tab: 卡池 ID ============
    def _build_pool_tab(self):
        cols = ("显示", "卡池ID", "中文名", "日文名", "类型", "卡数", "开始", "结束", "状态")
        self.tree_pool = self._make_tree(
            self.tab_pool, cols, [50, 80, 230, 250, 60, 60, 95, 95, 70])
        # 单击「显示」列切换勾选
        self.tree_pool.bind("<Button-1>", self._pool_click, add="+")

        bar = ttk.Frame(self.tab_pool)
        bar.pack(fill="x", padx=4, pady=(0, 4))
        self.var_pool_all = tk.BooleanVar(value=False)
        ttk.Checkbutton(bar, text="显示全部（含已过期）",
                        variable=self.var_pool_all,
                        command=self.refresh_pool).pack(side="left", padx=4)
        ttk.Button(bar, text="刷新", command=self.refresh_pool).pack(side="left", padx=2)
        self.var_pool_info = tk.StringVar(value="")
        ttk.Label(bar, textvariable=self.var_pool_info).pack(side="left", padx=12)

        # 底部：选中卡池的详情（原始 gacha_info_list 条目）
        ttk.Label(self.tab_pool, text="卡池详情（含 UP 卡 / 原始响应条目）：").pack(
            anchor="w", padx=8, pady=(6, 0))
        self.txt_pool = tk.Text(self.tab_pool, height=8, wrap="word")
        self.txt_pool.pack(fill="x", padx=8, pady=(0, 8))
        self.tree_pool.bind("<<TreeviewSelect>>", lambda ev: self._show_pool_detail())

    def refresh_pool(self):
        t = self.tree_pool
        t.delete(*t.get_children())
        if not self.con:
            return

        MDB = (r"C:/Program Files (x86)/Steam/steamapps/common/UmamusumePrettyDerby_Jpn/"
               r"UmamusumePrettyDerby_Jpn_Data/Persistent/master/master.mdb")
        try:
            mc = sqlite3.connect(f"file:{MDB}?mode=ro", uri=True)
            rows = mc.execute(
                "SELECT id, type, card_type, start_date, end_date FROM gacha_data "
                "ORDER BY id DESC").fetchall()
            pool_cnt = dict(mc.execute(
                "SELECT gacha_id, COUNT(*) FROM gacha_available GROUP BY gacha_id").fetchall())
            mc.close()
        except Exception as e:
            self.status(f"读 master 失败: {e}")
            return

        # 名称 + 勾选状态
        names_jp = dict(self.q("SELECT id, name FROM name_text WHERE kind='gacha'"))
        names_cn = dict(self.q("SELECT id, name FROM name_text WHERE kind='gacha_cn'"))
        enabled = dict(self.q("SELECT gacha_id, enabled FROM gacha_visible"))

        now = int(time.time())
        show_all = self.var_pool_all.get()
        shown = 0
        n_on = 0
        for gid, gtype, card_type, sd, ed in rows:
            on = enabled.get(gid, 0) == 1
            if on:
                n_on += 1
            if not show_all and not on:
                # 未勾选的只在「显示全部」时出现
                continue
            cnt = pool_cnt.get(gid, 0)
            if sd and ed:
                st_s = time.strftime("%Y-%m-%d", time.localtime(sd))
                st_e = time.strftime("%Y-%m-%d", time.localtime(ed))
                if now < (sd or 0):
                    state = "未开始"
                elif now > (ed or 0):
                    state = "已过期"
                else:
                    state = "有效"
            else:
                st_s = st_e = "—"
                state = "?"
            ct = {1: "角色", 2: "支援"}.get(card_type, str(card_type))
            t.insert("", "end", iid=str(gid),
                     values=("☑" if on else "☐", gid,
                             names_cn.get(gid, ""), names_jp.get(gid, ""),
                             ct, cnt, st_s, st_e, state))
            shown += 1

        self.var_pool_info.set(f"显示 {shown} 个（已勾选 {n_on} 个，共 {len(rows)} 个定义）")

    def _pool_click(self, event):
        """点击「显示」列切换勾选。"""
        if not self.con:
            return
        row = self.tree_pool.identify_row(event.y)
        col = self.tree_pool.identify_column(event.x)
        if not row or col != "#1":
            return
        gid = int(row)
        cur = self.con.execute(
            "SELECT enabled FROM gacha_visible WHERE gacha_id=?", (gid,)).fetchone()
        new_on = 0 if (cur and cur[0] == 1) else 1
        self.con.execute(
            "INSERT OR REPLACE INTO gacha_visible(gacha_id, enabled, sort) VALUES (?,?,?)",
            (gid, new_on, gid))
        self.con.commit()
        self.tree_pool.set(row, "显示", "☑" if new_on else "☐")
        n_on = self.q("SELECT COUNT(*) FROM gacha_visible WHERE enabled=1")[0][0]
        self.status(f"卡池 {gid} -> {'显示' if new_on else '隐藏'}（当前勾选 {n_on} 个）")

    def _show_pool_detail(self):
        sel = self.tree_pool.selection()
        if not sel or not self.con:
            return
        gid = int(sel[0])
        lines = []

        # 卡池名
        nm_jp = self.q("SELECT name FROM name_text WHERE kind='gacha' AND id=?", (gid,))
        nm_cn = self.q("SELECT name FROM name_text WHERE kind='gacha_cn' AND id=?", (gid,))
        note = self.q("SELECT name FROM name_text WHERE kind='gacha_note' AND id=?", (gid,))
        lines.append(f"卡池 {gid}")
        if nm_jp:
            lines.append(f"  名称:   {nm_jp[0][0]}")
        if nm_cn:
            lines.append(f"  中文:   {nm_cn[0][0]}")
        # 说明：日文 + 中文
        note_jp = self.q("SELECT name FROM name_text WHERE kind='gacha_note' AND id=?", (gid,))
        note_cn = self.q("SELECT name FROM name_text WHERE kind='gacha_note_cn' AND id=?", (gid,))
        if note_jp:
            lines.append(f"  说明:   {note_jp[0][0]}")
        if note_cn:
            lines.append(f"  中文说明: {note_cn[0][0]}")
        lines.append("")

        # UP 卡
        MDB = (r"C:/Program Files (x86)/Steam/steamapps/common/UmamusumePrettyDerby_Jpn/"
               r"UmamusumePrettyDerby_Jpn_Data/Persistent/master/master.mdb")
        try:
            mc = sqlite3.connect(f"file:{MDB}?mode=ro", uri=True)
            ups = mc.execute(
                "SELECT card_id, card_type, rarity, odds FROM gacha_available "
                "WHERE gacha_id=? AND is_pickup=1 ORDER BY rarity DESC, card_id",
                (gid,)).fetchall()
            total = mc.execute(
                "SELECT COUNT(*) FROM gacha_available WHERE gacha_id=?", (gid,)).fetchone()[0]
            mc.close()
        except Exception as e:
            lines.append(f"读 master 失败: {e}")
            ups = []
            total = 0

        lines.append(f"UP 卡: {len(ups)} 张（池内共 {total} 张）")
        for cid, ct, rar, odds in ups:
            # 角色卡用 card_cn/card，支援卡用 support_cn/support
            kind_cn = "card_cn" if ct == 1 else "support_cn"
            kind_jp = "card" if ct == 1 else "support"
            r = self.q("SELECT name FROM name_text WHERE kind=? AND id=?", (kind_cn, cid))
            name = r[0][0] if r else ""
            if not name:
                r = self.q("SELECT name FROM name_text WHERE kind=? AND id=?", (kind_jp, cid))
                name = r[0][0] if r else f"card {cid}"
            type_s = "角色" if ct == 1 else "支援"
            # 中文名：卡名 > 角色名（新卡翻译常缺，但角色名有）
            cn_name = ""
            r_cn = self.q("SELECT name FROM name_text WHERE kind=? AND id=?", (kind_cn, cid))
            if r_cn and r_cn[0][0]:
                cn_name = r_cn[0][0]
            else:
                # 回退到角色中文名
                chara_id = cid // 100
                r_ch = self.q("SELECT name FROM name_text WHERE kind='chara_cn' AND id=?",
                              (chara_id,))
                if r_ch and r_ch[0][0]:
                    cn_name = r_ch[0][0]
            cn_part = f"  /  {cn_name}" if cn_name and cn_name != name else ""
            lines.append(f"  {rar}★ [{type_s}] {name}{cn_part}   odds={odds}")

        lines.append("")
        # 原始 gacha_info_list 条目（从数据库 response_cache 读）
        try:
            found = False
            r = self.q("SELECT data FROM response_cache WHERE path='gacha/index'")
            if r:
                obj = msgpack.unpackb(r[0][0], raw=False, strict_map_key=False,
                                      unicode_errors="replace")
                for gi in obj.get("data", {}).get("gacha_info_list") or []:
                    if gi.get("id") == gid:
                        lines.append("原始 gacha_info_list 条目:")
                        lines.append(json.dumps(gi, ensure_ascii=False, indent=2))
                        found = True
                        break
            if not found:
                lines.append("（该池不在原始 gacha/index 响应里，由勾选动态加入）")
        except Exception as e:
            lines.append(f"读取原始条目失败: {e}")

        self.txt_pool.delete("1.0", "end")
        self.txt_pool.insert("1.0", "\n".join(lines))

    # ============ Tab: 抽卡 ============
    def _build_gacha_tab(self):
        cols = ("序号", "卡池ID", "类型", "角色名", "服装名", "新获得", "抽卡时间")
        self.tree_gacha = self._make_tree(
            self.tab_gacha, cols, [60, 90, 70, 200, 200, 70, 160])

        bar = ttk.Frame(self.tab_gacha)
        bar.pack(fill="x", padx=4, pady=(0, 4))
        ttk.Button(bar, text="刷新", command=self.refresh_gacha).pack(side="left", padx=2)
        ttk.Button(bar, text="清空记录", command=self._clear_gacha).pack(side="left", padx=8)
        self.var_gacha_stats = tk.StringVar(value="")
        ttk.Label(bar, textvariable=self.var_gacha_stats).pack(side="left", padx=12)

    def refresh_gacha(self):
        t = self.tree_gacha
        t.delete(*t.get_children())
        sql = """
            SELECT g.id, g.gacha_id,
                   CASE WHEN g.card_type = 1 THEN '角色' ELSE '支援' END AS type_cn,
                   CASE WHEN g.card_type = 1
                        THEN COALESCE(cn.name, cj.name, '')
                        ELSE COALESCE(scn.name, sj.name, '') END AS who,
                   CASE WHEN g.card_type = 1
                        THEN COALESCE(dcn.name, dj.name, '')
                        ELSE '' END AS cloth,
                   g.new_flag, g.drawn_at
            FROM gacha_log g
            LEFT JOIN card_dress cd  ON cd.card_id = g.card_id AND g.card_type = 1
            LEFT JOIN name_text cn   ON cn.kind = 'chara_cn' AND cn.id = cd.chara_id
            LEFT JOIN name_text cj   ON cj.kind = 'chara'    AND cj.id = cd.chara_id
            LEFT JOIN name_text dcn  ON dcn.kind = 'dress_cn' AND dcn.id = cd.dress_id
            LEFT JOIN name_text dj   ON dj.kind = 'dress'     AND dj.id = cd.dress_id
            LEFT JOIN name_text scn  ON scn.kind = 'support_cn' AND scn.id = g.card_id
                                    AND g.card_type = 2
            LEFT JOIN name_text sj   ON sj.kind = 'support'     AND sj.id = g.card_id
                                    AND g.card_type = 2
            ORDER BY g.id DESC LIMIT 2000
        """
        rows = self.q(sql)
        for r in rows:
            t.insert("", "end", values=r)
        total = self.q("SELECT COUNT(*) FROM gacha_log")[0][0]
        self.var_gacha_stats.set(f"共 {total} 条记录（显示最近 {len(rows)}）")

    def _clear_gacha(self):
        if not messagebox.askyesno("确认", "清空所有抽卡记录？"):
            return
        self.ex("DELETE FROM gacha_log")
        self.refresh_gacha()
        self.status("抽卡记录已清空")

    # ============ Tab: 工具 ============
    def _build_tools_tab(self):
        f = ttk.LabelFrame(self.tab_tools, text="一键操作", padding=12)
        f.pack(fill="x", padx=12, pady=12)

        btns = [
            ("金币 / 宝石 / 金币道具 拉满", self._max_coin),
            ("钥匙 拉满", self._max_key),
            ("所有角色亲爱度 / 粉丝 拉满", lambda: (self._max_love(), self._max_fan())),
            ("所有卡天赋拉满", self._max_talent),
            ("服装从 master 全量补齐", self._fill_cloth),
            ("事件全解锁", self._unlock_all_events),
            ("清空抽卡记录", self._clear_gacha),
        ]
        for i, (txt, cmd) in enumerate(btns):
            ttk.Button(f, text=txt, width=34, command=cmd).grid(
                row=i // 2, column=i % 2, padx=6, pady=6, sticky="w")

        # 账号信息
        f0 = ttk.LabelFrame(self.tab_tools, text="账号信息", padding=10)
        f0.pack(fill="x", padx=12, pady=(12, 0))
        row = ttk.Frame(f0)
        row.pack(fill="x")
        ttk.Label(row, text="玩家 ID（viewer_id）：").pack(side="left")
        self.var_viewer = tk.StringVar()
        e_vid = ttk.Entry(row, textvariable=self.var_viewer, width=20)
        e_vid.pack(side="left", padx=6)
        ttk.Button(row, text="保存", command=self._save_viewer).pack(side="left", padx=4)

        row2 = ttk.Frame(f0)
        row2.pack(fill="x", pady=(6, 0))
        ttk.Label(row2, text="库版本（schema_version）：").pack(side="left")
        self.var_schema = tk.StringVar()
        ttk.Entry(row2, textvariable=self.var_schema, width=10, state="readonly").pack(side="left", padx=6)

        f2 = ttk.LabelFrame(self.tab_tools, text="信息", padding=12)
        f2.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.txt_info = tk.Text(f2, height=12, wrap="word")
        self.txt_info.pack(fill="both", expand=True)

        bar = ttk.Frame(f2)
        bar.pack(fill="x", pady=(6, 0))
        ttk.Button(bar, text="刷新统计", command=self.refresh_info).pack(side="left")
        ttk.Button(bar, text="压缩数据库", command=self._vacuum).pack(side="left", padx=8)

    def refresh_account(self):
        """刷新账号信息（工具页顶部）。"""
        if not self.con:
            return
        v = self.q("SELECT value FROM user_state WHERE key='viewer_id'")
        s_ = self.q("SELECT value FROM user_state WHERE key='schema_version'")
        self.var_viewer.set(v[0][0] if v else "")
        self.var_schema.set(s_[0][0] if s_ else "")

    def _save_viewer(self):
        v = self.var_viewer.get().strip()
        if not v:
            return
        self.ex("INSERT OR REPLACE INTO user_state(key,value) VALUES ('viewer_id',?)", (v,))
        self.status(f"玩家 ID = {v}")

    def refresh_info(self):
        if not self.con:
            return
        lines = [f"数据库: {self.db_path}", f"大小: {self.db_path.stat().st_size:,} B", ""]
        tables = [r[0] for r in self.q(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        for t in tables:
            try:
                n = self.q(f"SELECT COUNT(*) FROM {t}")[0][0]
                lines.append(f"  {t:20s} {n:>8,} 行")
            except Exception:
                pass
        lines.append("")
        lines.append("=== user_state ===")
        for k, v in self.q("SELECT key, value FROM user_state ORDER BY key"):
            lines.append(f"  {k:16s} = {v}")

        self.txt_info.delete("1.0", "end")
        self.txt_info.insert("1.0", "\n".join(lines))

    def _vacuum(self):
        try:
            self.con.execute("VACUUM")
            self.con.commit()
            self.refresh_info()
            self.status("数据库压缩完成")
        except Exception as e:
            messagebox.showerror("压缩失败", str(e))

    # ============ Tab: 接口缓存 ============
    def _build_cache_tab(self):
        cols = ("接口路径", "declared", "大小", "缓存时间")
        self.tree_cache = self._make_tree(
            self.tab_cache, cols, [320, 100, 100, 170])

        bar = ttk.Frame(self.tab_cache)
        bar.pack(fill="x", padx=4, pady=(0, 4))
        ttk.Label(bar, text="筛选：").pack(side="left")
        self.var_cache_filter = tk.StringVar()
        e = ttk.Entry(bar, textvariable=self.var_cache_filter, width=24)
        e.pack(side="left", padx=4)
        e.bind("<Return>", lambda ev: self.refresh_cache())
        ttk.Button(bar, text="刷新", command=self.refresh_cache).pack(side="left", padx=2)
        self.var_cache_info = tk.StringVar(value="")
        ttk.Label(bar, textvariable=self.var_cache_info).pack(side="left", padx=12)

        # 下方 JSON 预览
        lf = ttk.LabelFrame(self.tab_cache, text="响应内容（JSON）", padding=4)
        lf.pack(fill="both", expand=True, padx=4, pady=(0, 4))
        self.txt_cache = tk.Text(lf, height=14, wrap="none")
        vsb = ttk.Scrollbar(lf, orient="vertical", command=self.txt_cache.yview)
        hsb = ttk.Scrollbar(lf, orient="horizontal", command=self.txt_cache.xview)
        self.txt_cache.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        self.txt_cache.pack(side="left", fill="both", expand=True)

        self.tree_cache.bind("<<TreeviewSelect>>", lambda ev: self._show_cache())

    def refresh_cache(self):
        t = self.tree_cache
        t.delete(*t.get_children())
        if not self.con:
            return
        f = self.var_cache_filter.get().strip()
        if f:
            rows = self.q("SELECT path, declared, LENGTH(data), cached_at "
                          "FROM response_cache WHERE path LIKE ? ORDER BY path", (f"%{f}%",))
        else:
            rows = self.q("SELECT path, declared, LENGTH(data), cached_at "
                          "FROM response_cache ORDER BY path")
        for r in rows:
            t.insert("", "end", iid=r[0], values=(r[0], r[1], f"{r[2]:,}", r[3] or ""))
        total_decl = self.q("SELECT COUNT(*) FROM response_cache")[0][0]
        self.var_cache_info.set(f"显示 {len(rows)} / 共 {total_decl} 个接口")

    def _show_cache(self):
        sel = self.tree_cache.selection()
        if not sel or not self.con:
            return
        path = sel[0]
        r = self.q("SELECT declared, data FROM response_cache WHERE path=?", (path,))
        if not r:
            return
        decl, blob = r[0]
        self.txt_cache.delete("1.0", "end")
        try:
            obj = msgpack.unpackb(blob, raw=False, strict_map_key=False,
                                  unicode_errors="replace")
            txt = json.dumps(obj, ensure_ascii=False, indent=2)
            self.txt_cache.insert("1.0", f"# {path}  declared={decl}\n\n" + txt)
        except Exception as e:
            self.txt_cache.insert("1.0", f"# {path}\n解析失败: {e}\n原始前 64 字节:\n{blob[:64].hex()}")

    # ============ Tab: 服务器 ============
    # ============ Tab: 角色编组 ============
    def _layout_sources(self):
        """加载角色/服装下拉数据源：[(id, "id 名称"), ...]"""
        chara = self.q(
            "SELECT c.chara_id, COALESCE(n.name,'') FROM owned_chara c "
            "LEFT JOIN name_text n ON n.kind='chara_cn' AND n.id=c.chara_id "
            "ORDER BY c.chara_id")

        # 服装列表：master.mdb 的 dress_data 全量（525 件），
        # 不能只用 owned_cloth —— 那样通用服装和新剧本服装没拥有就看不见。
        MDB = (r"C:/Program Files (x86)/Steam/steamapps/common/UmamusumePrettyderby_Jpn/"
               r"UmamusumePrettyderby_Jpn_Data/Persistent/master/master.mdb")
        dress_ids = []
        jp_names = {}
        try:
            mc = sqlite3.connect(f"file:{MDB}?mode=ro", uri=True)
            dress_ids = [int(r[0]) for r in mc.execute(
                "SELECT id FROM dress_data ORDER BY id")]
            # 日文原文名：text_data 的 category=14（index 是 SQL 保留字，要加方括号）
            try:
                jp_names = {int(r[0]): (r[1] or "") for r in mc.execute(
                    "SELECT [index], text FROM text_data WHERE category = 14")}
            except Exception:
                jp_names = {}
            # 角色名（含 NPC）：category=6
            try:
                jp_chara = {int(r[0]): (r[1] or "") for r in mc.execute(
                    "SELECT [index], text FROM text_data WHERE category = 6")}
            except Exception:
                jp_chara = {}
            mc.close()
        except Exception:
            dress_ids = []

        owned_cloth = {int(r[0]) for r in self.q("SELECT cloth_id FROM owned_cloth")}
        # 本地中文名表（可能不全）
        local_names = {int(r[0]): (r[1] or "") for r in self.q(
            "SELECT id, name FROM name_text WHERE kind='dress_cn'")}
        cn_chara = {int(r[0]): (r[1] or "") for r in self.q(
            "SELECT id, name FROM name_text WHERE kind='chara_cn'")}

        def chara_label(cid: int) -> str:
            """角色显示名：中文 > 日文 > 纯编号"""
            cn = (cn_chara.get(cid) or "").strip()
            if cn:
                return f"{cid} {cn}"
            jp = (jp_chara.get(cid) or "").strip()
            if jp:
                return f"{cid} {jp}"
            return str(cid)

        def cloth_label(did: int) -> str:
            """中文优先，没有就用日文原文，都没有只显示 id"""
            cn = (local_names.get(did) or "").strip()
            if cn:
                return f"{did} {cn}"
            jp = (jp_names.get(did) or "").strip()
            if jp:
                return f"{did} {jp}"
            return str(did)

        all_ids = sorted(set(dress_ids) | owned_cloth)
        self._cloth_items = [(did, cloth_label(did)) for did in all_ids]
        self._owned_cloth = owned_cloth
        self._chara_items = [(int(r[0]), f"{r[0]} {r[1]}".strip()) for r in chara]
        self._chara_map = {d: i for i, d in self._chara_items}
        self._cloth_map = {d: i for i, d in self._cloth_items}

        # 按角色分组的服装（含分类）：{chara_id: [(dress_id, 显示名, kind)]}
        # master.mdb 的 dress_data 才有 chara_id / costume_type / general_purpose
        self._cloth_by_chara = {}
        try:
            mc = sqlite3.connect(f"file:{MDB}?mode=ro", uri=True)
            meta_rows = mc.execute(
                "SELECT id, chara_id, costume_type, general_purpose, use_race, disp_order "
                "FROM dress_data").fetchall()
            mc.close()
        except Exception:
            meta_rows = []
        # dress_id -> (chara_id, costume_type, general_purpose, use_race, disp_order)
        meta = {int(r[0]): (int(r[1]), int(r[2]), int(r[3]), int(r[4]), int(r[5]))
                for r in meta_rows}

        owned = self._owned_cloth

        # ---- Live 专用：全量角色 + NPC ----
        # 注意：NPC（2001~2008 的 20xx，9001~9052 的 90xx）在 chara_data 里
        # start_date = 2524575600（2049-12-31，未实装标记），不能用 start_date 过滤掉。
        owned_chara = {cid for cid, _ in self._chara_items}
        try:
            mc = sqlite3.connect(f"file:{MDB}?mode=ro", uri=True)
            allc = mc.execute(
                "SELECT id, chara_category FROM chara_data "
                "WHERE start_date < 1795000000 "
                "   OR (id BETWEEN 2001 AND 2008) "
                "   OR (id BETWEEN 9001 AND 9100) "
                "ORDER BY id").fetchall()
            mc.close()
        except Exception:
            allc = []
        ch_name = {i: d for d, i in getattr(self, "_chara_map", {}).items()}
        live_items = []
        npc_items = []
        for row in allc:
            cid = int(row[0])
            label = chara_label(cid)          # "9001 骏川手纲" 这种
            is_npc = (2001 <= cid <= 2008) or (9001 <= cid <= 9100)
            if is_npc:
                npc_items.append((cid, label))
            else:
                tag = "" if cid in owned_chara else "（未育成）"
                live_items.append((cid, f"{label}{tag}"))
        self._live_chara_items = live_items
        self._live_chara_map = {d: i for i, d in live_items}
        # NPC 用自己的 chara_id（9001 对应 dress 900101），这样能选到服装
        self._npc_items = npc_items
        self._npc_map = {d: i for i, d in npc_items}
        self._live_all_items = live_items + npc_items

        for did, disp in self._cloth_items:
            ch, ct, gp, race, order = meta.get(did, (0, 0, 0, 0, 0))
            # 决胜服判定（实测 master.mdb 的规律）：
            #   chara_id > 0 且 use_race=1 且 disp_order ∈ {151, 152, 153}
            #   151=第1套 152=第2套 153=第3套（个别角色有第4套）
            # 不能用 costume_type==1 —— 那只标记第 1 套，第 2/3 套是 ct=0。
            # chara_id=0 的（校服/运动服）即使 use_race=1 也不是决胜服。
            if ch > 0 and race == 1 and 151 <= order <= 159:
                kind = "decisive"
                seq = order - 150
            elif gp == 1 or did < 100000:
                kind = "general"
                seq = 0
            else:
                kind = "private"
                seq = 0
            self._cloth_by_chara.setdefault(ch, []).append((did, disp, kind, seq))
            # chara_id=0 的（校服/运动服/泳装等通用服装）挂到每一个可选角色，
            # 包括 Live 里的未育成角色和 NPC（2001~2008 / 9001~9052）。
            if ch == 0:
                all_chara_ids = set(self._chara_map)
                all_chara_ids.update(d for d, _ in getattr(self, "_live_chara_items", []))
                all_chara_ids.update(d for d, _ in getattr(self, "_npc_items", []))
                for cid in all_chara_ids:
                    self._cloth_by_chara.setdefault(cid, []).append((did, disp, kind, seq))

        # 每个角色的决胜服按序号排序（第 1 套在前）
        for cid, lst in self._cloth_by_chara.items():
            lst.sort(key=lambda x: (0 if x[2] == "decisive" else 1, x[3], x[0]))

    def _build_layout_tab(self):
        # 此处数据库可能还没连接，先用空列表；refresh_layout 里再灌真实数据
        self._chara_items = []
        self._cloth_items = []
        self._chara_map = {}
        self._cloth_map = {}

        # ---- 大厅 ----
        top = ttk.LabelFrame(self.tab_layout, text="大厅编组", padding=6)
        top.pack(fill="x", padx=6, pady=(6, 4))
        head = ("位置", "角色", "服装")
        widths = [5, 32, 32]
        for i, (h, w) in enumerate(zip(head, widths)):
            ttk.Label(top, text=h, width=w).grid(row=0, column=i, padx=3, sticky="w")
        self.home_widgets = {}
        for pos in range(1, 5):
            ttk.Label(top, text=str(pos), width=5).grid(row=pos, column=0, padx=3, pady=2)
            cc = SearchCombo(top, self._chara_items, width=32)
            cc.grid(row=pos, column=1, padx=3, pady=2, sticky="w")
            dc = SearchCombo(top, self._cloth_items, width=32)
            dc.grid(row=pos, column=2, padx=3, pady=2, sticky="w")
            cc.cb.bind("<<ComboboxSelected>>",
                       lambda e, p=pos: self._sync_home_cloth(p), add="+")
            self.home_widgets[pos] = (cc, dc)
        # 一键：4 行各填本角色决胜服
        ttk.Button(top, text="各填决胜服",
                   command=self._apply_fill_decisive_home).grid(
            row=5, column=1, sticky="w", padx=3, pady=(4, 0))

        # ---- Live 编组 ----
        box = ttk.LabelFrame(self.tab_layout, text="Live 编组", padding=6)
        box.pack(fill="both", expand=True, padx=6, pady=(0, 4))

        bar = ttk.Frame(box)
        bar.pack(fill="x", pady=(0, 4))
        ttk.Label(bar, text="组号").pack(side="left")
        self.var_live_slot = tk.StringVar(value="1")
        ttk.Combobox(bar, textvariable=self.var_live_slot,
                     values=[str(i) for i in range(1, 11)],
                     width=4, state="readonly").pack(side="left", padx=4)
        ttk.Button(bar, text="载入该组",
                   command=self._load_live_slot).pack(side="left", padx=2)
        self.var_live_name = tk.StringVar()
        ttk.Label(bar, text="名称").pack(side="left", padx=(12, 2))
        ttk.Entry(bar, textvariable=self.var_live_name, width=14).pack(side="left")
        ttk.Button(bar, text="保存整组",
                   command=self._save_live_slot).pack(side="left", padx=8)
        # ---- 右侧：整体填充 ----
        fill = ttk.Frame(bar)
        fill.pack(side="right")

        ttk.Label(fill, text="整组角色").pack(side="left", padx=(0, 2))
        self.var_fill_chara = tk.StringVar()
        self.cb_fill_chara = ttk.Combobox(fill, textvariable=self.var_fill_chara,
                                          width=20, state="readonly")
        self.cb_fill_chara.pack(side="left", padx=2)

        ttk.Label(fill, text="整体服装").pack(side="left", padx=(8, 2))
        self.var_fill_dress = tk.StringVar()
        self.cb_fill_dress = ttk.Combobox(fill, textvariable=self.var_fill_dress,
                                          width=7, state="readonly",
                                          values=["不修改", "通用", "决胜服", "私服"])
        self.cb_fill_dress.set("不修改")
        self.cb_fill_dress.pack(side="left", padx=2)

        self.btn_fill = ttk.Button(fill, text="填充", command=self._apply_fill)
        self.btn_fill.pack(side="left", padx=6)

        self.var_fill_dress.trace_add("write", lambda *a: self._toggle_general_dress())

        self.var_live_hint = tk.StringVar(value="")
        ttk.Label(bar, textvariable=self.var_live_hint,
                  foreground="#888").pack(side="left", padx=10)

        # 「整体服装」选「通用」或「决胜服」时才弹出的额外一行（平时隐藏）
        self.row_general = ttk.Frame(box)

        # 子框架 A：通用服装（18 位穿同一件）
        self.row_gen_pick = ttk.Frame(self.row_general)
        ttk.Label(self.row_gen_pick, text="通用服装").pack(side="left", padx=(0, 4))
        self.var_fill_general = tk.StringVar()
        self.cb_fill_general = ttk.Combobox(self.row_gen_pick,
                                            textvariable=self.var_fill_general,
                                            width=40, state="readonly")
        self.cb_fill_general.pack(side="left", padx=2)
        ttk.Label(self.row_gen_pick,
                  text="（选一件后点「填充」，18 位全部穿这件）",
                  foreground="#888").pack(side="left", padx=8)

        # 子框架 B：决胜服套数（配合「填决胜服」按钮）
        self.row_seq_pick = ttk.Frame(self.row_general)
        ttk.Label(self.row_seq_pick, text="填第几套").pack(side="left", padx=(0, 4))
        self.var_fill_seq = tk.StringVar(value="1")
        self.cb_fill_seq = ttk.Combobox(self.row_seq_pick,
                                        textvariable=self.var_fill_seq,
                                        width=3, state="readonly",
                                        values=["1", "2", "3", "4"])
        self.cb_fill_seq.pack(side="left", padx=2)
        ttk.Label(self.row_seq_pick,
                  text="（点「填决胜服」时每行按自己角色填这一套）",
                  foreground="#888").pack(side="left", padx=8)

        self._fill_general_visible = False
        self._fill_row_mode = None   # "general" / "decisive" / None

        # 滚动区
        canvas = tk.Canvas(box, highlightthickness=0)
        sb = ttk.Scrollbar(box, orient="vertical", command=canvas.yview)
        self.live_inner = ttk.Frame(canvas)
        self.live_inner.bind("<Configure>",
                             lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.live_inner, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self._live_canvas_wrap = (canvas, sb)

        for i, (h, w) in enumerate((("位置", 6), ("角色", 34), ("服装", 34))):
            ttk.Label(self.live_inner, text=h, width=w).grid(row=0, column=i, padx=3, sticky="w")

        self.live_widgets = {}
        for pos in range(1, 19):
            ttk.Label(self.live_inner, text=str(pos), width=5).grid(row=pos, column=0, padx=3, pady=1)
            cc = SearchCombo(self.live_inner, getattr(self, "_live_all_items", self._chara_items), width=32)
            cc.grid(row=pos, column=1, padx=3, pady=1, sticky="w")
            dc = SearchCombo(self.live_inner, self._cloth_items, width=32)
            dc.grid(row=pos, column=2, padx=3, pady=1, sticky="w")
            cc.cb.bind("<<ComboboxSelected>>",
                       lambda e, p=pos: self._sync_cloth_of(p), add="+")
            self.live_widgets[pos] = (cc, dc)

        foot = ttk.Frame(self.tab_layout)
        foot.pack(fill="x", padx=6, pady=(0, 6))
        ttk.Button(foot, text="保存大厅",
                   command=self._save_home_layout).pack(side="left", padx=2)
        ttk.Button(foot, text="重新载入",
                   command=self.refresh_layout).pack(side="left", padx=2)

    # ---- 大厅读写 ----
    def _save_home_layout(self):
        n = 0
        for pos, (cc, dc) in self.home_widgets.items():
            cid = cc.get_id()
            if not cid:
                continue
            self.ex("INSERT OR REPLACE INTO chara_layout(kind, slot, position, chara_id, dress_id, color_id) "
                    "VALUES ('home', 1, ?, ?, ?, 0)", (pos, cid, dc.get_id()))
            n += 1
        self.status(f"大厅编组已保存 {n} 个位置")

    # ---- Live 读写 ----
    def _load_live_slot(self):
        try:
            slot = int(self.var_live_slot.get())
        except ValueError:
            return
        rows = self.q("SELECT position, chara_id, dress_id, mob_id FROM chara_layout "
                      "WHERE kind='live' AND slot=? ORDER BY position", (slot,))
        by_pos = {r[0]: (r[1], r[2], r[3]) for r in rows}
        for pos, (cc, dc) in self.live_widgets.items():
            cid, did, mob = by_pos.get(pos, (0, 0, 0))
            if mob:
                cc.cb.set(f"NPC {mob}")
            else:
                cc.set_id(cid)
            dc.set_items(self._cloth_items_for(cid) or self._cloth_items)
            dc.set_id(did)
        # 预设名
        import json as _j
        name = f"编组{slot}"
        r = self.q("SELECT value FROM meta WHERE key='live_preset_names'")
        if r and r[0][0]:
            try:
                name = _j.loads(r[0][0]).get(str(slot), name)
            except Exception:
                pass
        self.var_live_name.set(name)
        self.var_live_hint.set(f"已载入 组{slot}（{len(rows)} 人）")

    def _save_live_slot(self):
        try:
            slot = int(self.var_live_slot.get())
        except ValueError:
            return
        n = 0
        self.ex("DELETE FROM chara_layout WHERE kind='live' AND slot=?", (slot,))
        for pos, (cc, dc) in self.live_widgets.items():
            txt = cc.cb.get().strip()
            cid = cc.get_id()
            mob = 0
            if txt.startswith("NPC "):
                try:
                    mob = int(txt.split()[1])
                except (IndexError, ValueError):
                    mob = 0
                cid = 0
            if not cid and not mob:
                continue
            self.ex("INSERT OR REPLACE INTO chara_layout(kind, slot, position, chara_id, dress_id, mob_id) "
                    "VALUES ('live', ?, ?, ?, ?, ?)", (slot, pos, cid, dc.get_id(), mob))
            n += 1
        # 名称
        import json as _j
        names = {}
        r = self.q("SELECT value FROM meta WHERE key='live_preset_names'")
        if r and r[0][0]:
            try:
                names = _j.loads(r[0][0])
            except Exception:
                names = {}
        names[str(slot)] = self.var_live_name.get().strip() or f"编组{slot}"
        self.ex("INSERT OR REPLACE INTO meta(key,value) VALUES ('live_preset_names',?)",
                (_j.dumps(names, ensure_ascii=False),))
        self.status(f"Live 组{slot} 已保存 {n} 人")
        self.var_live_hint.set(f"已保存 组{slot}（{n} 人）")

    def _cloth_items_for(self, chara_id: int):
        """该角色可用的服装列表 [(id, 显示名), ...]

        决胜服按 disp_order 排好序，显示名加「第N套」后缀方便区分。
        """
        if not chara_id:
            return []
        lst = self._cloth_by_chara.get(chara_id, [])
        out = []
        for did, disp, kind, seq in lst:
            if kind == "decisive" and seq > 0:
                out.append((did, f"{disp} 第{seq}套"))
            else:
                out.append((did, disp))
        return out

    def _sync_cloth_of(self, pos: int):
        if pos not in self.live_widgets:
            return
        cc, dc = self.live_widgets[pos]
        cid = cc.get_id()
        items = self._cloth_items_for(cid)
        dc.set_items(items)
        # 默认选该角色第一件决胜服
        if items:
            dec = [x for x in self._cloth_by_chara.get(cid, []) if x[2] == "decisive"]
            pick = dec[0][0] if dec else items[0][0]
            dc.set_id(pick)

    def _sync_home_cloth(self, pos: int):
        if pos not in self.home_widgets:
            return
        cc, dc = self.home_widgets[pos]
        cid = cc.get_id()
        items = self._cloth_items_for(cid)
        dc.set_items(items)
        if items:
            dec = [x for x in self._cloth_by_chara.get(cid, []) if x[2] == "decisive"]
            pick = dec[0][0] if dec else items[0][0]
            dc.set_id(pick)

    # ---- 整体填充 ----
    def _refresh_fill_chara(self):
        # 用 Live 全量（含 NPC），ownned_chara 只是一部分
        src = (getattr(self, "_live_all_items", [])
               or getattr(self, "_chara_items", []))
        names = [d for _cid, d in src]
        if not names:
            names = [d for d in getattr(self, "_chara_map", {})]
        self.cb_fill_chara.configure(state="readonly")
        self.cb_fill_chara["values"] = ["🎲 随机填充"] + names
        if names and not self.var_fill_chara.get():
            self.cb_fill_chara.current(0)

    def _toggle_general_dress(self):
        """「整体服装」选「通用」或「决胜服」时才弹出额外那一行。

        通用 → 显示「通用服装」下拉（18 位穿同一件）
        决胜服 → 显示「填第几套」下拉（每行按自己角色填）
        其他 → 整行隐藏
        """
        if not hasattr(self, "cb_fill_general"):
            return
        if not hasattr(self, "row_seq_pick"):
            return   # row_general 还没构建完（初始化时 set() 会触发 trace）
        kind = self.var_fill_dress.get().strip()
        want = kind if kind in ("通用", "决胜服") else None

        if want is None:
            if self._fill_general_visible:
                self.row_general.pack_forget()
                self._fill_general_visible = False
                self._fill_row_mode = None
            return

        if not self._fill_general_visible:
            self.row_general.pack(fill="x", pady=(0, 4),
                                  before=self._live_canvas_wrap[0])
            self._fill_general_visible = True

        if want != self._fill_row_mode:
            if want == "通用":
                self.row_seq_pick.pack_forget()
                self.row_gen_pick.pack(fill="x")
                self._refresh_general_dress()
            else:
                self.row_gen_pick.pack_forget()
                self.row_seq_pick.pack(fill="x")
            self._fill_row_mode = want

    def _refresh_general_dress(self):
        """列出所有通用服装：6 位数以下（id < 100000）全部算通用。

        这些是特雷森学园制服、运动服、泳装等，任何角色都能穿。
        不用 general_purpose 判断 —— 那个字段只标了一部分。
        """
        items = []
        seen = set()
        for did, disp in getattr(self, "_cloth_items", []):
            if did < 100000 and did not in seen:
                seen.add(did)
                items.append((did, disp))
        items.sort(key=lambda x: x[0])
        self.cb_fill_general["values"] = [d for _i, d in items]
        self._general_map = {d: i for i, d in items}
        if items and not self.var_fill_general.get():
            self.cb_fill_general.current(0)

    def _apply_fill(self):
        import random as _rd
        want = self.var_fill_chara.get().strip()
        dress_kind_label = self.var_fill_dress.get().strip()

        # 保底：选「通用」但下拉还没显示时，先显示出来
        if dress_kind_label == "通用" and not self._fill_general_visible:
            self._toggle_general_dress()
            self.status("已展开「通用服装」下拉，请选一件再点填充")
            return
        if dress_kind_label == "通用" and not self.var_fill_general.get():
            self.status("请先在「通用服装」里选一件")
            return
        kind_map = {"通用": "general", "决胜服": "decisive", "私服": "private"}

        if not want:
            messagebox.showinfo("提示", "先选「整组角色」")
            return
        if want == "🎲 随机填充":
            chara_ids = [cid for cid, _ in self._chara_items]
        else:
            chara_ids = [self._chara_map.get(want, 0)]
            if not chara_ids[0]:
                head = want.split()[0]
                chara_ids = [int(head)] if head.isdigit() else []

        n = 0
        for pos, (cc, dc) in self.live_widgets.items():
            cid = _rd.choice(chara_ids) if want == "🎲 随机填充" else chara_ids[0]
            if not cid:
                continue
            cc.set_id(cid)
            # 先按角色刷新服装下拉
            items = self._cloth_items_for(cid)
            dc.set_items(items)
            # 再按整体服装规则挑
            if dress_kind_label == "不修改":
                continue
            want_kind = kind_map.get(dress_kind_label)
            if want_kind == "general":
                # 用额外下拉里选定的那件通用服装
                gid = getattr(self, "_general_map", {}).get(self.var_fill_general.get().strip(), 0)
                if gid:
                    dc.set_id(gid)
                    n += 1
                    continue
            if want_kind == "decisive":
                # 按「填第几套」选，没有该套退回第 1 套
                try:
                    want_seq = int(self.var_fill_seq.get() or "1")
                except ValueError:
                    want_seq = 1
                dec = sorted([x for x in self._cloth_by_chara.get(cid, [])
                              if x[2] == "decisive"], key=lambda x: x[3])
                if dec:
                    pick = next((x for x in dec if x[3] == want_seq), dec[0])
                    dc.set_id(pick[0])
                    n += 1
                    continue
                # 该角色没有决胜服，退回第一件可用
                if items:
                    dc.set_id(items[0][0])
                n += 1
                continue
            cand = [x for x in self._cloth_by_chara.get(cid, []) if x[2] == want_kind]
            if not cand:
                cand = self._cloth_by_chara.get(cid, [])
            if cand:
                dc.set_id(cand[0][0])
            n += 1
        self.var_live_hint.set(f"已填充 {n} 位（{want} / {dress_kind_label}）")

    def _apply_fill_decisive_home(self):
        """大厅 4 行按角色填指定套数的决胜服。"""
        try:
            want_seq = int(self.var_fill_seq.get() or "1")
        except ValueError:
            want_seq = 1

        n = 0
        fallback = 0
        for pos, (cc, dc) in self.home_widgets.items():
            cid = cc.get_id()
            if not cid:
                continue
            items = self._cloth_items_for(cid)
            dc.set_items(items)
            if not items:
                continue
            dec = [x for x in self._cloth_by_chara.get(cid, [])
                   if x[2] == "decisive"]
            dec.sort(key=lambda x: x[3])
            if not dec:
                dc.set_id(items[0][0])
                n += 1
                continue
            pick = next((x for x in dec if x[3] == want_seq), None)
            if pick is None:
                pick = dec[0]
                fallback += 1
            dc.set_id(pick[0])
            n += 1
        msg = f"大厅 {n} 位已填第{want_seq}套"
        if fallback:
            msg += f"（{fallback} 位无该套已退回第1套）"
        self.status(msg)

    def refresh_layout(self):
        self._layout_sources()
        # 只灌一次角色列表（服装按角色分组，下面逐个位置设置时再灌）
        for cc, _dc in self.home_widgets.values():
            cc.set_items(self._chara_items)
        # Live 用全量（含 20xx/90xx NPC），不能只给 owned_chara
        live_all = getattr(self, "_live_all_items", []) or self._chara_items
        for cc, _dc in self.live_widgets.values():
            cc.set_items(live_all)
        # 大厅
        rows = self.q("SELECT position, chara_id, dress_id, color_id FROM chara_layout "
                      "WHERE kind='home' ORDER BY position")
        by_pos = {r[0]: (r[1], r[2]) for r in rows}
        for pos, (cc, dc) in self.home_widgets.items():
            pid, did = by_pos.get(pos, (0, 0))
            cc.set_id(pid)
            dc.set_items(self._cloth_items_for(pid) or self._cloth_items)
            dc.set_id(did)
        # 刷新「整组角色」下拉
        self._refresh_fill_chara()
        # Live：载入当前组号
        self._load_live_slot()

    # ========================================================================
    # 育成马娘（trained_chara）管理
    # ========================================================================
    def _build_trained_tab(self):
        cols = ("数据库编号", "角色[服装]", "速度", "耐力", "力量", "毅力", "智力",
                "评分", "Rank", "粉丝", "稀有度")
        self.tree_trained = self._make_tree(
            self.tab_trained, cols, [90, 240, 55, 55, 55, 55, 55, 75, 55, 85, 55],
            editable=False)

        bar = ttk.Frame(self.tab_trained)
        bar.pack(fill="x", padx=4, pady=(0, 4))

        ttk.Label(bar, text="卡片ID：").pack(side="left")
        self.var_tr_card = tk.StringVar()
        ttk.Entry(bar, textvariable=self.var_tr_card, width=10).pack(side="left", padx=2)

        ttk.Button(bar, text="添加（随机）", command=self._add_trained_random).pack(side="left", padx=6)
        ttk.Button(bar, text="添加（指定卡）", command=self._add_trained_card).pack(side="left", padx=2)
        ttk.Button(bar, text="刷新", command=self.refresh_trained).pack(side="left", padx=6)
        ttk.Button(bar, text="删除选中", command=self._del_trained).pack(side="left", padx=2)

        self.lbl_trained = ttk.Label(self.tab_trained, text="")
        self.lbl_trained.pack(fill="x", padx=6, pady=(0, 4))

    def _trained_template(self):
        """读出 load/index 模板（含 trained_chara 列表）。"""
        import msgpack
        row = self.q("SELECT data FROM response_cache WHERE path='load/index'")
        if not row:
            return None
        return msgpack.unpackb(row[0][0], raw=False, strict_map_key=False)

    def _trained_save(self, obj):
        import msgpack
        plain = msgpack.packb(obj, use_bin_type=True)
        if not self.con:
            raise RuntimeError("数据库未打开")
        self.con.execute("UPDATE response_cache SET data=?, declared=? WHERE path='load/index'",
                         (plain, len(plain)))
        self.con.commit()
        return len(plain)

    def refresh_trained(self):
        t = self.tree_trained
        t.delete(*t.get_children())
        obj = self._trained_template()
        if not obj:
            self.lbl_trained.config(text="没有 load/index 模板")
            return
        arr = obj.get("data", {}).get("trained_chara", [])

        # Rank 段位名映射（rank 编号 → UG5 / LG12 这类名字）
        rank_label = None
        try:
            from rank_table import rank_label as _rl_fn
            rank_label = _rl_fn
        except Exception:
            pass

        # 卡片名查表：优先中文 [服装名]角色名，缺失回退日文
        name_cn = {}
        name_jp = {}
        try:
            for cid, nm in self.q("SELECT id, name FROM name_text WHERE kind='card_cn'"):
                name_cn[int(cid)] = nm
            for cid, nm in self.q("SELECT id, name FROM name_text WHERE kind='card'"):
                name_jp[int(cid)] = nm
        except Exception:
            pass

        for it in arr:
            if not isinstance(it, dict):
                continue
            cid = it.get("card_id", "")
            try:
                _c = int(cid)
                label = name_cn.get(_c) or name_jp.get(_c) or f"#{cid}"
            except Exception:
                label = f"#{cid}"
            # Rank：直接把 rank 字段（段位编号）转成名称，不做分数推算
            _rk = it.get("rank", 0)
            try:
                _rl = rank_label(int(_rk)) if _rk else "-"
            except Exception:
                _rl = str(_rk)

            t.insert("", "end", iid=str(it.get("trained_chara_id", "")), values=(
                it.get("trained_chara_id", ""),
                label,
                it.get("speed", ""),
                it.get("stamina", ""),
                it.get("power", ""),
                it.get("guts", ""),
                it.get("wiz", ""),
                it.get("rank_score", ""),
                _rl,
                it.get("fans", ""),
                it.get("rarity", ""),
            ))
        self.lbl_trained.config(text=f"共 {len(arr)} 条育成马娘（存在 load/index 模板里）")

    def _add_trained_random(self):
        self._add_trained(None)

    def _add_trained_card(self):
        cid = self.var_tr_card.get().strip()
        if not cid.isdigit():
            self.status("请先填卡片 ID")
            return
        self._add_trained(int(cid))

    def _add_trained(self, card_id):
        try:
            from trained_chara_gen import add_trained_chara
            # 直接用编辑器已打开的库
            db = getattr(self.con, "database", None) if self.con else None
            if not db:
                self.status("数据库未打开")
                return
            r = add_trained_chara(db, card_id=card_id)
            self.status(f"已添加 trained_chara_id={r['trained_chara_id']} "
                        f"card={r['card_id']} 评分={r['rank_score']} 共 {r['total']} 条")
            self.refresh_trained()
        except Exception as e:
            self.status(f"添加失败: {e}")

    def _del_trained(self):
        sel = self.tree_trained.selection()
        if not sel:
            self.status("请先选中一条")
            return
        import traceback
        try:
            tid = int(sel[0])
            obj = self._trained_template()
            if not obj:
                self.status("读取模板失败")
                return
            arr = obj.get("data", {}).get("trained_chara", [])
            new_arr = [x for x in arr if int(x.get("trained_chara_id", -1)) != tid]
            if len(new_arr) == len(arr):
                self.status(f"未找到 trained_chara_id={tid}")
                return
            obj["data"]["trained_chara"] = new_arr
            size = self._trained_save(obj)
            self.status(f"已删除编号 {tid}，剩 {len(new_arr)} 条，模板 {size} B")
            self.refresh_trained()
        except Exception as e:
            self.status(f"删除失败: {type(e).__name__}: {e}")
            traceback.print_exc()

    # ========================================================================
    # 服务器日志（独立页）
    # ========================================================================
    def _build_log_tab(self):
        top = ttk.Frame(self.tab_log)
        top.pack(fill="x", padx=6, pady=(6, 2))

        self.lbl_log_src = ttk.Label(top, text="", foreground="#888")
        self.lbl_log_src.pack(side="left")

        bar = ttk.Frame(self.tab_log)
        bar.pack(fill="x", padx=6, pady=(0, 4))
        ttk.Button(bar, text="刷新一次", command=self.refresh_log).pack(side="left")
        ttk.Button(bar, text="清空显示", command=lambda: self.txt_log.delete("1.0", "end")).pack(side="left", padx=4)
        ttk.Button(bar, text="清空文件", command=self._clear_log_file).pack(side="left", padx=4)

        self.var_log_auto = tk.BooleanVar(value=True)
        ttk.Checkbutton(bar, text="自动刷新（1 秒）", variable=self.var_log_auto).pack(side="left", padx=10)

        ttk.Label(bar, text="只显示匹配：").pack(side="left", padx=(10, 2))
        self.var_log_filter = tk.StringVar()
        e = ttk.Entry(bar, textvariable=self.var_log_filter, width=16)
        e.pack(side="left")
        e.bind("<Return>", lambda ev: self.refresh_log())

        lf = ttk.Frame(self.tab_log)
        lf.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        # SimSun：Windows 自带的等宽中文字体，中英文粗细一致
        # （Consolas 不含中文，会回退到比例字体导致粗细不齐）
        self.txt_log = tk.Text(lf, wrap="none", font=("SimSun", 10))
        vsb = ttk.Scrollbar(lf, orient="vertical", command=self.txt_log.yview)
        hsb = ttk.Scrollbar(lf, orient="horizontal", command=self.txt_log.xview)
        self.txt_log.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        self.txt_log.pack(side="left", fill="both", expand=True)

    def _clear_log_file(self):
        p = self._srv_log_path()
        try:
            if p.exists():
                p.write_text("", encoding="utf-8")
            self.refresh_log()
            self.status("日志文件已清空")
        except Exception as e:
            self.status(f"清空失败: {e}")

    def refresh_log(self, tail_lines: int = 800):
        p = self._srv_log_path()
        self.lbl_log_src.config(text=f"{p}")

        if not p.exists():
            self.txt_log.delete("1.0", "end")
            self.txt_log.insert("1.0", f"(日志文件不存在: {p})")
            return

        try:
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except Exception as e:
            self.txt_log.insert("end", f"\n读取失败: {e}")
            return

        flt = self.var_log_filter.get().strip()
        if flt:
            lines = [ln for ln in lines if flt in ln]

        lines = lines[-tail_lines:]
        txt = "".join(lines)

        # 只在内容变化时重绘，避免滚动位置乱跳
        cur = self.txt_log.get("1.0", "end-1c")
        if cur == txt:
            return
        at_bottom = self.txt_log.yview()[1] > 0.98
        self.txt_log.delete("1.0", "end")
        self.txt_log.insert("1.0", txt)
        if at_bottom:
            self.txt_log.see("end")
        self.lbl_log_src.config(text=f"{p}    ({len(lines)} 行)")

    def _log_tick(self):
        if getattr(self, "var_log_auto", None) and self.var_log_auto.get():
            try:
                self.refresh_log()
            except Exception:
                pass
        try:
            self.after(1000, self._log_tick)
        except Exception:
            pass

    def _build_server_tab(self):
        self._srv_proc = None
        self._srv_log_pos = 0

        # 顶部：状态提示（控制在主窗口顶栏）
        top = ttk.Frame(self.tab_server)
        top.pack(fill="x", padx=8, pady=(8, 4))
        ttk.Label(top, text="服务端启停请用窗口顶栏的「启动 / 停止 / 重启」按钮",
                  foreground="#888888").pack(side="left")

        # ---- 模式 ----
        mf = ttk.LabelFrame(self.tab_server, text="运行模式", padding=8)
        mf.pack(fill="x", padx=8, pady=(0, 6))
        rowm = ttk.Frame(mf)
        rowm.pack(fill="x")
        self.var_mode = tk.StringVar(value="未知")
        ttk.Label(rowm, textvariable=self.var_mode,
                  font=("Microsoft YaHei UI", 10, "bold")).pack(side="left", padx=(0, 12))
        ttk.Button(rowm, text="切到在线录制", command=lambda: self._set_mode("online")).pack(side="left", padx=4)
        ttk.Button(rowm, text="切到离线回放", command=lambda: self._set_mode("local")).pack(side="left", padx=4)

        # ---- 剧本生成器 ----
        # 权威在 meta.use_real_model：关（默认）= 基于模板 0034 改造；
        # 开 = 用解包公式从零生成（Header/帧区/结果块全自建，21 种距离通用）。
        rf = ttk.LabelFrame(self.tab_server, text="剧本生成器", padding=8)
        rf.pack(fill="x", padx=8, pady=(0, 6))
        rowr = ttk.Frame(rf)
        rowr.pack(fill="x")
        self.var_real_model = tk.BooleanVar(value=False)
        ttk.Checkbutton(rowr, text="使用真实解包模型（从零生成，不依赖模板）",
                        variable=self.var_real_model,
                        command=self._toggle_real_model).pack(side="left")
        self.var_real_hint = tk.StringVar(value="")
        ttk.Label(rowr, textvariable=self.var_real_hint,
                  foreground="#888888").pack(side="left", padx=12)
        ttk.Label(rf, text="开启后：速度按 v0~v4 与 a0~a3 分段计算，属性/适性/干劲/天气全部参与；"
                           "关闭则沿用模板剧本改造。",
                  foreground="#888888").pack(anchor="w", pady=(4, 0))

        # ---- 外部剧本文件（覆盖 race_start 的 race_scenario）----
        rowsc = ttk.Frame(rf)
        rowsc.pack(fill="x", pady=(8, 0))
        ttk.Label(rowsc, text="外部剧本：").pack(side="left")
        self.var_scenario = tk.StringVar(value="")
        ttk.Entry(rowsc, textvariable=self.var_scenario, width=52).pack(side="left", padx=4)
        ttk.Button(rowsc, text="选择…", command=self._pick_scenario).pack(side="left", padx=2)
        ttk.Button(rowsc, text="应用", command=self._apply_scenario).pack(side="left", padx=2)
        ttk.Button(rowsc, text="清除", command=self._clear_scenario).pack(side="left", padx=2)
        self.var_scenario_hint = tk.StringVar(value="")
        ttk.Label(rf, textvariable=self.var_scenario_hint,
                  foreground="#888888").pack(anchor="w", pady=(2, 0))
        self._load_scenario_state()

        self._load_real_model_state()

        # ---- 开关 ----
        sf = ttk.LabelFrame(self.tab_server, text="开关", padding=8)
        sf.pack(fill="x", padx=8, pady=(0, 6))
        self.var_sw = {}
        sw_defs = [
            ("offline", "离线回放（拦截 0x3180）", "umalib.json"),
            ("ctrdump", "请求明文落盘（抽卡必需）", "ctrdump.on"),
            ("urlpatch_off", "不改 URL（走真服务器）", "urlpatch.off"),
            ("mark", "标记本地数据", "mark.on"),
            ("ksdump", "密钥流落盘", "ksdump.on"),
        ]
        for i, (key, label, _src) in enumerate(sw_defs):
            v = tk.BooleanVar(value=False)
            self.var_sw[key] = v
            ttk.Checkbutton(sf, text=label, variable=v,
                            command=lambda k=key: self._toggle_switch(k)).grid(
                row=i // 3, column=i % 3, sticky="w", padx=8, pady=4)

        # ---- 游戏 + 重建 ----
        gf = ttk.LabelFrame(self.tab_server, text="游戏 / 数据", padding=8)
        gf.pack(fill="x", padx=8, pady=(0, 6))
        ttk.Button(gf, text="启动游戏", command=self._game_start).pack(side="left", padx=4)
        ttk.Button(gf, text="关闭游戏", command=self._game_stop).pack(side="left", padx=4)
        ttk.Separator(gf, orient="vertical").pack(side="left", fill="y", padx=10)
        ttk.Button(gf, text="从游戏资料库同步", command=self._rebuild_replay).pack(side="left", padx=4)
        self.var_game = tk.StringVar(value="")
        ttk.Label(gf, textvariable=self.var_game).pack(side="left", padx=12)

        # 接口清单
        mid = ttk.LabelFrame(self.tab_server, text="接口清单", padding=6)
        mid.pack(fill="x", padx=8, pady=(0, 6))
        self.var_srv_paths = tk.StringVar(value="")
        ttk.Label(mid, textvariable=self.var_srv_paths).pack(anchor="w")

        # ---- 数据库配置（config 表） ----
        cf = ttk.LabelFrame(self.tab_server, text="数据库配置（config 表）", padding=6)
        cf.pack(fill="x", padx=8, pady=(0, 6))
        self.tree_cfg = self._make_tree(cf, ("配置项", "值"), [240, 620])
        self.tree_cfg.configure(height=4)
        self.tree_cfg.pack(fill="x", expand=False)
        rowc = ttk.Frame(cf)
        rowc.pack(fill="x", pady=(4, 0))
        ttk.Button(rowc, text="刷新配置", command=self._reload_cfg).pack(side="left", padx=2)
        ttk.Label(rowc, text="开关状态 config.switch.*，锁定路径 config.locked_paths",
                  foreground="#888").pack(side="left", padx=10)

        # 日志已拆到独立的「服务器日志」页签，这里不再重复

        # 初始同步开关状态
        try:
            self._refresh_server_switches()
        except Exception:
            pass

        # 定时刷新
        self.root.after(1500, self._srv_tick)

    # ---- umalib.json 读写 ----
    def _read_umalib(self) -> dict:
        try:
            with open(UMALIB_JSON, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _write_umalib(self, **kw):
        d = self._read_umalib()
        d.update(kw)
        try:
            os.makedirs(os.path.dirname(UMALIB_JSON), exist_ok=True)
            with open(UMALIB_JSON, "w", encoding="utf-8") as f:
                json.dump(d, f, ensure_ascii=False, indent=2)
        except Exception as e:
            messagebox.showerror("写入失败", str(e))

    def _switch_file(self, name: str) -> Path:
        return self.db_path.parent / name

    def _read_switch(self, key: str) -> bool:
        """读开关当前状态。"""
        try:
            if key == "offline":
                return bool(self._read_umalib().get("offline"))
            fn = {"ctrdump": "ctrdump.on", "urlpatch_off": "urlpatch.off",
                  "mark": "mark.on", "ksdump": "ksdump.on"}.get(key)
            if not fn:
                return False
            return self._switch_file(fn).exists()
        except Exception:
            return False

    def _toggle_switch(self, key: str):
        """调服务器 /api/toggle，所有开关状态由服务器写 config 表。"""
        try:
            port = (self.var_srv_port.get() or "826").strip()
            url = f"http://127.0.0.1:{port}/api/toggle?name={key}"
            import urllib.request as _ur
            with _ur.urlopen(url, timeout=5) as r:
                r.read()
            self.status(f"已切换 {key}")
            self._refresh_server_switches()
        except Exception as e:
            messagebox.showerror("切换失败", f"调 {url} 出错：{e}")
            # 回滚勾选状态
            try:
                self.var_sw[key].set(not bool(self.var_sw[key].get()))
            except Exception:
                pass


    # ---------- 外部剧本 ----------

    def _scenario_meta_path(self) -> str:
        """meta.scenario_path 的当前值。"""
        try:
            r = self.q("SELECT value FROM meta WHERE key='scenario_path'")
            return (r[0] if r and r[0] else "") or ""
        except Exception:
            return ""

    def _set_scenario_meta(self, path: str):
        try:
            row = self.q("SELECT COUNT(*) FROM meta WHERE key='scenario_path'")
            n = row[0] if row else 0
            if n:
                self.ex("UPDATE meta SET value=? WHERE key='scenario_path'", (path,))
            else:
                self.ex("INSERT INTO meta(key,value) VALUES('scenario_path',?)", (path,))
        except Exception as e:
            self.status("写 scenario_path 失败: %s" % e)

    def _load_scenario_state(self):
        p = self._scenario_meta_path()
        self.var_scenario.set(p)
        if p:
            import os as _os
            if _os.path.isfile(p):
                self.var_scenario_hint.set("生效中：%d B（服务器启动时读一次）" % _os.path.getsize(p))
            else:
                self.var_scenario_hint.set("⚠ 文件不存在")
        else:
            self.var_scenario_hint.set("留空则用数据库模板剧本")

    def _pick_scenario(self):
        from tkinter import filedialog
        p = filedialog.askopenfilename(
            title="选择剧本文件",
            filetypes=[("剧本二进制", "*.bin"), ("全部文件", "*.*")],
        )
        if p:
            self.var_scenario.set(p)

    def _apply_scenario(self):
        p = (self.var_scenario.get() or "").strip()
        import os as _os
        if p and not _os.path.isfile(p):
            self.status("文件不存在: %s" % p)
            return
        self._set_scenario_meta(p)
        self._load_scenario_state()
        self.status("外部剧本已设为：%s（需重启服务器生效）" % (p or "<无>"))

    def _clear_scenario(self):
        self.var_scenario.set("")
        self._set_scenario_meta("")
        self._load_scenario_state()
        self.status("已清除外部剧本，回退数据库模板")

    def _toggle_real_model(self):
        """切换「使用真实解包模型」。权威在 meta.use_real_model。"""
        try:
            import sqlite3 as _sq
            want = "1" if self.var_real_model.get() else "0"
            con = _sq.connect(str(DEFAULT_DB), timeout=10)
            try:
                row = con.execute("SELECT COUNT(*) FROM meta WHERE key='use_real_model'").fetchone()
                if row and row[0]:
                    con.execute("UPDATE meta SET value=? WHERE key='use_real_model'", (want,))
                else:
                    con.execute("INSERT INTO meta(key,value) VALUES('use_real_model',?)", (want,))
                con.commit()
            finally:
                con.close()
            self._load_real_model_state()
            self.status("剧本生成器：" + ("真实解包模型（从零生成）" if want == "1" else "模板改造"))
        except Exception as e:
            messagebox.showerror("切换失败", str(e))

    def _load_real_model_state(self):
        """从 meta 读开关状态并更新 UI。"""
        try:
            import sqlite3 as _sq
            con = _sq.connect(str(DEFAULT_DB), timeout=10)
            try:
                r = con.execute("SELECT value FROM meta WHERE key='use_real_model'").fetchone()
            finally:
                con.close()
            on = bool(r and str(r[0]) == "1")
            self.var_real_model.set(on)
            self.var_real_hint.set("当前：从零生成" if on else "当前：模板改造（默认）")
        except Exception:
            self.var_real_hint.set("")

    def _set_mode(self, mode: str):
        """online = 录制（不拦截、不改URL、落盘）；local = 回放（拦截、URL 指本地）。

        权威在数据库 meta.mode —— 插件通过服务器 /api/switches 读取，改文件已废弃。
        """
        try:
            import sqlite3 as _sq
            dbpath = str(DEFAULT_DB)
            target = "online" if mode == "online" else "offline"
            con = _sq.connect(dbpath, timeout=10)
            try:
                con.execute("UPDATE meta SET value=? WHERE key='mode'", (target,))
                con.commit()
                row = con.execute("SELECT value FROM meta WHERE key='mode'").fetchone()
            finally:
                con.close()
            if not row or row[0] != target:
                raise RuntimeError(f"写入失败，当前值={row[0] if row else 'None'}")

            if mode == "online":
                self.status("已切到在线录制（走真服务器 + 请求落盘）")
            else:
                self.status("已切到离线回放（拦截 0x3180）")
            self._refresh_server_switches()
        except Exception as e:
            messagebox.showerror("切换失败", str(e))

    def _refresh_server_switches(self):
        """从服务器 /api/switches 读状态（后台线程，避免阻塞 UI）。"""
        if getattr(self, "_sw_busy", False):
            return
        self._sw_busy = True
        port = (self.var_srv_port.get() or "826").strip()

        def worker():
            sw = None
            try:
                import urllib.request as _ur
                import json as _j
                with _ur.urlopen(f"http://127.0.0.1:{port}/api/switches", timeout=2) as r:
                    sw = _j.loads(r.read().decode())
            except Exception:
                sw = None
            try:
                game = _proc_running("UmamusumePrettyderby_Jpn.exe")
            except Exception:
                game = False
            # 回主线程更新 UI
            self.root.after(0, lambda: self._apply_switches(sw, game))

        import threading
        threading.Thread(target=worker, daemon=True).start()

    def _apply_switches(self, sw, game):
        """主线程：把拉到的开关状态写进界面。"""
        self._sw_busy = False
        if sw is None:
            for var in self.var_sw.values():
                var.set(False)
            self.var_mode.set("服务器未运行")
        else:
            for key, var in self.var_sw.items():
                var.set(bool(sw.get(key)))
            self.var_mode.set("离线回放" if sw.get("offline") else "在线录制")
        try:
            self.var_game.set("运行中" if game else "未运行")
        except Exception:
            pass

    def _game_start(self):
        exe = os.path.join(GAME_DIR, "UmamusumePrettyDerby_Jpn.exe")
        if not os.path.exists(exe):
            messagebox.showerror("找不到", exe)
            return
        try:
            import subprocess
            subprocess.Popen([exe], cwd=GAME_DIR, close_fds=True)
            self.status("游戏启动中")
            self.root.after(2000, self._refresh_server_switches)
        except Exception as e:
            messagebox.showerror("启动失败", str(e))

    def _game_stop(self):
        try:
            import subprocess
            subprocess.run(["powershell", "-NoProfile", "-Command",
                            "Get-Process UmamusumePrettyDerby_Jpn -ErrorAction SilentlyContinue | "
                            "Stop-Process -Force"], capture_output=True, timeout=20,
                           creationflags=0x08000000)
            self.status("游戏已关闭")
            self.root.after(1000, self._refresh_server_switches)
        except Exception as e:
            messagebox.showerror("关闭失败", str(e))

    def _rebuild_replay(self):
        """从 master 增量同步到数据库（替代已废弃的 replay.bin 重建）。"""
        script = Path(__file__).parent / "db_sync_incremental.py"
        if not script.exists():
            messagebox.showerror("找不到", f"缺 {script}")
            return
        self.status("同步中…")
        try:
            import subprocess
            r = subprocess.run([sys.executable, str(script)],
                               capture_output=True, text=True, encoding="gbk", errors="replace", timeout=300)
            out = (r.stdout or "")[-800:]
            self.txt_log.insert("end", f"\n=== 同步结果 ===\n{out}\n")
            self.txt_log.see("end")
            self.status("同步完成")
            self.refresh_all()
        except Exception as e:
            messagebox.showerror("同步失败", str(e))

    def _srv_log_path(self) -> Path:
        return self.db_path.parent / "localsrv.log" if self.db_path else Path("localsrv.log")

    def _srv_is_running(self) -> bool:
        if self._srv_proc and self._srv_proc.poll() is None:
            return True
        # 也检查端口是否被别的进程占着
        try:
            import socket
            port = int(self.var_srv_port.get() or 826)
            s_ = socket.socket()
            s_.settimeout(0.3)
            r = s_.connect_ex(("127.0.0.1", port))
            s_.close()
            return r == 0
        except Exception:
            return False

    def _srv_start(self):
        if self._srv_is_running():
            self.status("服务器已在运行")
            return
        port = self.var_srv_port.get().strip() or "826"
        server_py = Path(__file__).parent / "local_server.py"
        if not server_py.exists():
            messagebox.showerror("找不到", f"缺 {server_py}")
            return
        try:
            import subprocess
            kwargs = {}
            if os.name == "nt":
                kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
            self._srv_proc = subprocess.Popen(
                [sys.executable, "-u", str(server_py), "--port", port,
                 "--data-dir", str(self.db_path.parent)],
                cwd=str(server_py.parent.parent),
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                **kwargs)
            self.status(f"服务器启动中（端口 {port}）")
            self.root.after(2500, self._srv_refresh_state)
        except Exception as e:
            messagebox.showerror("启动失败", str(e))

    def _srv_stop(self):
        # 先停自己启的
        if self._srv_proc and self._srv_proc.poll() is None:
            try:
                self._srv_proc.terminate()
                self._srv_proc.wait(timeout=5)
            except Exception:
                try:
                    self._srv_proc.kill()
                except Exception:
                    pass
            self._srv_proc = None
        # 再清理占端口的 local_server 进程
        try:
            import subprocess
            ps = ("Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
                  "Where-Object { $_.CommandLine -like '*local_server*' } | "
                  "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }")
            subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                           capture_output=True, timeout=15, creationflags=0x08000000)
        except Exception:
            pass
        self.status("服务器已停止")
        self.root.after(600, self._srv_refresh_state)

    def _srv_restart(self):
        self._srv_stop()
        self.root.after(900, self._srv_start)

    def _reload_cfg(self):
        """读 config 表。"""
        if not hasattr(self, "tree_cfg"):
            return
        t = self.tree_cfg
        t.delete(*t.get_children())
        try:
            rows = self.q("SELECT key, value FROM config ORDER BY key")
        except Exception:
            rows = []
        for k, v in rows:
            disp = (v or "")[:200].replace("\n", " ")
            t.insert("", "end", values=(k, disp))
        self.status(f"配置 {len(rows)} 条")

    def _srv_refresh_state(self):
        try:
            self._refresh_server_switches()
        except Exception:
            pass
        running = self._srv_is_running()
        port = self.var_srv_port.get().strip() or "826"
        self.var_srv_state.set(("● 运行中  " if running else "○ 已停止  ") + f"端口 {port}")

        # 接口清单（从数据库读）
        try:
            n_pd = self.q("SELECT COUNT(*) FROM path_declared")[0][0]
            n_rc = self.q("SELECT COUNT(*) FROM response_cache")[0][0]
            self.var_srv_paths.set(f"{n_pd} 个接口已登记，{n_rc} 条响应缓存（offline.db）")
        except Exception:
            self.var_srv_paths.set("数据库读取失败")

    def _on_server_tab(self) -> bool:
        """当前是否停在「服务器」页（不在就不用刷日志/查库）。"""
        try:
            cur = self.nb.select()
            return str(self.nb.nametowidget(cur)) == str(self.tab_server)
        except Exception:
            return False

    def _srv_tick(self):
        """定时刷新状态和日志（仅在服务器页时执行，避免无谓开销）。"""
        try:
            if not self._on_server_tab():
                self.root.after(2000, self._srv_tick)
                return
            self._srv_refresh_state()
            if self.var_log_auto.get():
                log = self._srv_log_path()
                if log.exists():
                    size = log.stat().st_size
                    if size < self._srv_log_pos:
                        self._srv_log_pos = 0
                        self.txt_log.delete("1.0", "end")
                    if size > self._srv_log_pos:
                        with open(log, "r", encoding="utf-8", errors="replace") as f:
                            f.seek(self._srv_log_pos)
                            chunk = f.read()
                            self._srv_log_pos = f.tell()
                        chunk = chunk.replace("\x00", "")
                        if chunk:
                            self.txt_log.insert("end", chunk)
                            self.txt_log.see("end")
        except Exception:
            pass
        self.root.after(2000, self._srv_tick)

    # ============ 刷新 ============
    def refresh_all(self):
        if not self.con:
            return
        errs = []
        for name in ("refresh_chara", "refresh_card", "refresh_cloth", "refresh_item",
                     "refresh_event", "refresh_pool", "refresh_gacha", "refresh_account",
                     "refresh_cache", "refresh_info", "refresh_layout",
                     "_reload_cfg"):
            try:
                getattr(self, name)()
            except Exception as e:
                errs.append(f"{name}: {type(e).__name__}: {e}")
        if errs:
            self.status("部分刷新失败: " + "; ".join(errs[:3]))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(DEFAULT_DB))
    a = ap.parse_args()

    root = tk.Tk()
    App(root, Path(a.db))
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
