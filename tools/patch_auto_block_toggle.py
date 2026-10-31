"""给 Hachimi-Edge 加 cutin_auto_block_frames 开关：控制「自动学习屏蔽帧」是否启用。

- true（默认）：行为不变，10 秒内出现 10 次就自动加入屏蔽列表
- false：不再自动学习，只用 BLOCKED_IDS（硬编码的 8 个）
"""
import io

# ---------- 1. config 字段 ----------
P1 = "C:/Users/Schwarz/projects/Hachimi-Edge/src/core/hachimi.rs"
s = io.open(P1, encoding="utf-8").read()

anchor = '''    #[serde(default = "Config::default_cutin_block_ui_events")]
    pub cutin_block_ui_events: bool,'''
assert anchor in s, "cutin_block_ui_events 字段未匹配"

new_field = anchor + '''

    /// 是否自动学习「该屏蔽的帧」（10 秒内被触发 10 次就拉黑）。
    /// 关掉后只用内置 BLOCKED_IDS，避免抽卡横幅之类的高频 UI 被误伤。
    #[serde(default = "Config::default_cutin_auto_block_frames")]
    pub cutin_auto_block_frames: bool,'''
s = s.replace(anchor, new_field, 1)

anchor2 = '''    pub fn default_cutin_block_ui_events() -> bool { true }'''
assert anchor2 in s
s = s.replace(anchor2, anchor2 + '''

    pub fn default_cutin_auto_block_frames() -> bool { true }''', 1)

io.open(P1, "w", encoding="utf-8", newline="\n").write(s)
print("1. config 字段已加")

# ---------- 2. observe_shadow_frame 尊重开关 ----------
P2 = "C:/Users/Schwarz/projects/Hachimi-Edge/src/il2cpp/hook/umamusume/MovieProbe.rs"
s = io.open(P2, encoding="utf-8").read()

old = '''fn observe_shadow_frame(id: i32) {
    if id <= 0 { return; }'''
new = '''fn observe_shadow_frame(id: i32) {
    if id <= 0 { return; }
    // 自动学习开关：关掉后不再把高频帧拉黑（避免误伤抽卡横幅等 UI）
    if !Hachimi::instance().config.load().cutin_auto_block_frames {
        return;
    }'''
assert old in s, "observe_shadow_frame 未匹配"
s = s.replace(old, new, 1)
io.open(P2, "w", encoding="utf-8", newline="\n").write(s)
print("2. observe_shadow_frame 已加开关判断")

# ---------- 3. GUI 加勾选项 ----------
P3 = "C:/Users/Schwarz/projects/Hachimi-Edge/src/core/gui.rs"
s = io.open(P3, encoding="utf-8").read()

anchor3 = '''                ui.label(t!("config_editor.cutin_block_ui_events"));
                ui.checkbox(&mut config.cutin_block_ui_events, "");'''
assert anchor3 in s, "gui cutin_block_ui_events 未匹配"

new3 = anchor3 + '''

                ui.label(t!("config_editor.cutin_auto_block_frames"));
                ui.checkbox(&mut config.cutin_auto_block_frames, "");'''
s = s.replace(anchor3, new3, 1)
io.open(P3, "w", encoding="utf-8", newline="\n").write(s)
print("3. GUI 勾选项已加")
