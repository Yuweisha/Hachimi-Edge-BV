# 育成侦察报告：模拟点击 vs 托管

> 数据来源：`hachimi/http/20261028_162128`（961 个文件，65 MB），两次完整线上育成。
> 本文只写**从抓包里直接读到的事实**。凡属推断必标注 `[推断]`，无法确认的标 `[未知]`。
> 请求/响应里的身份字段（viewer_id / steam_id / device_id / sid 等）本文一律不列出值。

---

## 〇、两次育成的定位

| | 育成 A | 育成 B |
|---|---|---|
| 接口前缀 | `idle_single_mode` | `single_mode_festa` |
| 用户描述 | 自主训练，全托管，等时间即可 | 自动模式，半托管，游戏自己模拟点击 |
| 抓包序号范围 | 016 ~ 026 | 030 ~ 435 |
| 育成期请求数 | 7 | ~400 |
| 是否含训练 | 否 | 是（64 次 `exec_command`） |
| 是否含比赛 | 否 | 是（14 场） |
| 结算接口 | `single_mode_festa/finish` | `single_mode_festa/finish` |

**两者共用同一个结算接口 `finish`，但育成过程完全不共用。**

---

## 一、托管育成（`idle_single_mode`）

### 1.1 完整请求序列

```
016  pre_single_mode/index
017  pre_single_mode/get_succession_trained_chara
018  friend/index
019  idle_single_mode/pre_start          ← 检查是否有进行中的放置育成
020  idle_single_mode/start             ← 开始（响应 13,065 B）
021  idle_single_mode/end               ← 结束（响应 74,543 B）
022  idle_single_mode/check_progress_log
023  skill_set/index
024  single_mode_festa/factor_order_load
025  single_mode_festa/factor_select
026  single_mode_festa/finish           ← 结算
```

**从 `start` 到 `end` 之间没有任何请求。** 全部计算在服务器侧。

### 1.2 `019 pre_start`

- 请求业务字段：`is_get_friend_info = false`
- 响应 1,991 B，`data` 两键：
  ```
  last_idle_single_mode_start_info    上一次放置育成的开始信息
  reserved_race_info                  预约的比赛信息
  ```

### 1.3 `020 start`（响应 13,065 B）

`data` 8 键：

| 键 | 类型 | 说明 |
|---|---|---|
| `add_trained_chara_array` | list[0] | 本次为 0（角色还没生成） |
| `mission_list` | list[0] | |
| **`progress_info`** | dict{7} | **核心** |
| `story_event_chara_bonus_list` | list[0] | |
| `story_event_mission_list` | list[0] | |
| `tp_info` | dict{3} | `current_tp` / `max_tp` / `max_recovery_time` |
| `training_roadmap_selected_info` | null | |
| `user_item_array` | list[0] | |

**`progress_info` 的 7 个键：**

```
chara_info                          育成中的角色（60 字段）
dress_id                            服装
effected_trainer_skill_id_array     生效的育成者技能
end_time                            结束时间戳
start_time                          开始时间戳
story_event_chara_bonus_list        剧情事件加成
story_event_mission_list            剧情事件任务
```

**`[已确认]` `start` 返回的是「育成已开始」的状态，含起止时间戳。服务器必须在这里就把角色建出来。**

### 1.4 `021 end`（响应 74,543 B）— 放置育成的全部产出

`data` 3 键：

```
end_info                          25 键，结算结果
progress_log_info                 10 键，过程日志
training_roadmap_selected_info    null
```

#### `end_info` 结构

| 键 | 类型 | 内容 |
|---|---|---|
| **`chara_info`** | dict{60} | **育成完成的角色**（见 1.5） |
| `reward_summary_info` | dict{17} | 奖励汇总：`add_fcoin` / `add_item_list`(14 项) / `add_card_list` / `add_cloth_list` / `add_music_list` / `add_piece_list` / `add_story_id_array` / `add_total_fan` / `add_honor_list` / `new_chara_profile_array` 等 |
| `skill_filter_setting_array` | list[8] | 技能筛选设置，每项 `{set_type, set_value}` |
| `effected_factor_array` | list[0] | |
| `mission_list` | list[0] | |
| `race_scenario` | null | 放置育成无比赛剧本 |
| `race_start_info` | null | |
| `start_dress_info` | list[0] | |
| `unchecked_event_array` | list[0] | |
| `win_saddle_id_array` | list[0] | |
| `prev_chara_grade` | 0 | |
| `is_umaplan` | false | |

#### `progress_log_info` 结构 — **这是放置育成的核心**

| 键 | 类型 | 内容 |
|---|---|---|
| **`event_gain_info`** | dict{23} | 属性总增长（见下） |
| **`race_history_array`** | list[14] | **14 场比赛的历史**，每项 `{lose_tips_id, race_history, race_reward_info}` |
| **`succession_factor_gain_array`** | list[3] | 3 个继承因子，每项 `{gain_factor_info_array, year}` |
| `succession_gain_info` | dict{23} | 继承加成（与 event_gain_info 同结构） |
| `support_card_gain_info_array` | list[6] | 6 张支援卡的成长，每项 `{gain_info, support_card_id}` |
| `chara_effect_log_array` | list[3] | 角色效果日志，每项 `{chara_effect_id, gain_index, is_active}` |
| `continue_info` | dict{2} | `continue_item_before_num` / `continue_item_after_num` |
| `gain_skill_array` | list[0] | |
| `gain_skill_id_array` | list[0] | |
| `total_skill_point` | 7213 | 技能点总数 |

**`event_gain_info` 的 23 个键（属性增长的完整结构）：**

```
speed / stamina / power / guts / wiz    每项 {sign, value}
max_speed / max_stamina / max_power / max_guts / max_wiz
proper_distance_short / mile / middle / long
proper_ground_turf / dirt
proper_running_style_nige / senko / sashi / oikomi
skill_point
skill_tips_array[]        每项 {group_id, level, rarity}
skill_tips_log_array[]    每项 {gain_index, skill_tips}
```

**本次实测值：**

```
speed     value=1941    sign=0
stamina   value=1002    sign=0
power     value=759     sign=0
guts      value=389     sign=0
wiz       value=1057    sign=0
skill_point 4023  （event_gain_info 里）
total_skill_point 7213
```

**`[已确认]` 放置育成要产出 14 场完整比赛的历史记录，即使客户端一次比赛请求都没发。**

### 1.5 `chara_info` 的 60 个字段（育成结果角色）

`[已确认]` 从 `end_info.chara_info` 直接读出，本次育成结果是：

```
card_id      = 111401
rarity       = 5
chara_grade  = 10
fans         = 570353
speed        = (未在本文列出，见字段表)
stamina / power / guts / wiz
max_speed    = 2222
max_stamina  = 1870
max_power    = 1836
max_guts     = 1704
max_wiz      = 1842
motivation   = 4
max_vital    = 104
playing_state = 1
route_id     = 121
race_running_style = 4
proper_distance_short  = 4
proper_distance_mile   = 7
proper_distance_middle = 7
proper_distance_long   = 5
proper_ground_turf     = 7
proper_ground_dirt     = 5
proper_running_style_nige   = 1
proper_running_style_senko  = 6
proper_running_style_sashi  = 7
proper_running_style_oikomi = 7
default_max_speed / stamina / power / guts / wiz = 1200
chara_effect_id_array       list[2]
evaluation_info_array       list[19]
disable_skill_id_array      list[0]
nickname_id_array           list[0]
```

**其余字段未逐个展开（共 60 个，与 Festa 的 `chara_info` 同构）。**

---

## 二、模拟点击育成（`single_mode_festa`）

### 2.1 开始阶段

```
030  pre_single_mode/index
031  training_challenge/exam_select
032  idle_single_mode/pre_start
033  single_mode_festa/start            ← exam_id=84，响应 28,713 B
034  single_mode_festa/check_event
035  single_mode_festa/check_event
036  single_mode/auto_play_select_plan  ← 「自动模式」开关
037  single_mode_festa/exec_command
```

### 2.2 `033 start` 响应（28,713 B）

`data` 2 键：`festa_data_set` + `single_mode_start_common`

#### `festa_data_set`（9 键）

| 键 | 类型 | 说明 |
|---|---|---|
| `act_info_array` | list[5] | 每项 `{act_gauge, act_training_state, act_type, advice_id, friend_outing_gain_act_level, level, need_act_gauge}` |
| `advice_info_array` | list[0] | |
| `auto_setting_info` | dict{2} | `auto_call_preset_id` + `preset_array`(3 项，每项 `{advice_info_array, auto_setting_attach_advice_info_array, name, preset_id}`) |
| `check_point_result_array` | list[0] | |
| `command_gain_act_gauge_array` | list[4] | 每项 `{command_type, predict_gain_act_gauge_array}` |
| `command_info_array` | list[5] | 每项 `{command_id, command_type, is_upper_training_event_occurred, params_inc_dec_info_array, predict_gain_act_gauge_array}` |
| `evaluation_info_array` | list[19] | 每项 `{act_type, chara_id, target_id}` |
| **`festa_info`** | dict{3} | `act_training_step=1` / `max_act_level=10` / `summer_camp_remain_turn_num=0` |
| `not_up_parameter_info` | dict{3} | |

#### `single_mode_start_common`（19 键）

| 键 | 类型 | 说明 |
|---|---|---|
| **`chara_info`** | dict{60} | 初始角色，`chara_grade=1`、`fans=1` |
| **`home_info`** | dict{13} | **主界面状态（见下）** |
| `auto_play_custom_plan_array` | list[2] | 自定义计划，每项 `{plan_description, plan_id, plan_name, plan_setting_array}` |
| `auto_play_selected_plan_id` | 150003 | 当前选中的自动计划 |
| `auto_play_default_plan_array` | list[0] | |
| `race_random_program_array` | list[6] | 每项 `{program_id, turn}` |
| **`reserved_race_info`** | dict{3} | `default_deck_num` / `needs_default_confirm` / `reserved_race_array`(9 项) |
| `add_trained_chara_array` | list[0] | |
| `effected_trainer_skill_id_array` | list[0] | |
| `mission_list` | list[0] | |
| `race_condition_array` | list[0] | |
| `is_umaplan` | false | |

**`home_info` 的 13 键（每次 `exec_command` 都会重发）：**

```
available_continue_num     = 5
available_free_continue_num = 3
command_info_array         list[10]   每项 {command_id, command_type, failure_rate,
                                              is_enable, level, params_inc_dec_info_array,
                                              sub_command_partner_array, tips_event_partner_array}
continue_unlock_flag       = True
disable_command_id_array   list[0]
disable_command_info_array list[0]
disable_race_turn_array    list[0]
free_continue_num          = 3
free_continue_time         = 1790322475
race_entry_restriction     = 1
shortened_race_state       = 4
special_home_id            = 0
```

**`[已确认]` `home_info.command_info_array` 有 10 条指令，含 `failure_rate`（失败率）与 `params_inc_dec_info_array`（属性增减预告）。这是客户端「点哪个训练」的唯一依据。**

### 2.3 主循环

| 接口 | 次数 | 说明 |
|---|---|---|
| `check_event` | 225 | 推进回合 / 查事件 |
| `exec_command` | 64 | 执行训练等指令 |
| `get_choice_reward` | 37 | 领取选项奖励 |
| `attach_advice` | 6 | 附建议 |
| `gain_skills` | 3 | 获得技能 |

#### `034 check_event`

- **请求业务字段只有 `{"scenario_id": 0}`**
- 响应 `data` 13 键：
  ```
  chara_info / event_effected_factor_array / festa_data_set
  gain_parameter_info / gain_partner_support_effect_array / home_info
  not_down_parameter_info / not_up_parameter_info / race_condition_array
  race_running_style / race_start_info / select_index_info_array
  unchecked_event_array
  ```
- `unchecked_event_array` 本次 1 条，事件键：
  ```
  chara_id / event_contents_info / event_id / minigame_result
  play_timing / story_id / succession_event_info
  ```
  实测 `event_id=1001`、`chara_id=0`、`play_timing=1`

**`[已确认]` 一次 `check_event` 返回「当前状态 + 待处理事件」。客户端通过反复调用把它推进到下一回合。**

#### `037 exec_command`

**请求业务字段：**
```json
{"chara_id": 0, "choice_number": 0, "current_turn": 1,
 "event_id": 1001, "exec_auto_play_plan_id": 0}
```

**响应 `data` 12 键：**

| 键 | 内容 |
|---|---|
| `chara_info` | 更新后的角色（60 字段） |
| **`command_result`** | `{command_id=101, result_state=2, sub_id=1}` |
| `festa_data_set` | 同 start 结构，9 键 |
| `gain_parameter_info` | `{effected_command_id_array, gain_partner_support_effect_array, is_view_training_bonus_turn_log}` |
| `gain_partner_support_effect_array` | list[0] |
| `home_info` | 13 键（重发） |
| `not_down_parameter_info` | 3 键（护符/防护） |
| `not_up_parameter_info` | **11 键**（属性没涨的原因） |
| `race_condition_array` | list[0] |
| `unchecked_event_array` | list[1] |

**`[已确认]` `command_id=101` 对应一个训练指令，`result_state=2` 表示成功。**

**`[未知]` `command_id` 与具体训练项目（速度/耐力/力量…）的映射表。** 需要把 64 次 `exec_command` 的 `command_id` 全部统计后才能反推。

**`not_up_parameter_info` 的 11 个键（属性没涨时的原因清单）：**

```
chara_effect_id_array / command_lv_array / evaluation_chara_id_array
has_chara_effect_id_array / not_gain_chara_effect_array
skill_id_array / skill_lv_id_array / skill_tips_array
status_type_array / unsupported_evaluation_chara_id_array
unsupported_evaluation_support_card_id_array
```

### 2.4 比赛部分（14 场）

每场固定四步：

```
race_entry     进场
race_start     开赛（下发 race_scenario）
race_end       结束
race_out       退场
```

**`[已确认]` `race_start` 的 `data.race_scenario` 与 `ultimate_race/race_start` 结构相同**——已用其中一份做样本，见 `samples/`。

实测 `race_start` 序号：84 / 137 / 180 / 195 / 240 / 262 / 314 / 330 / 364 / 380 / 392 / 403 / 411 / 421（共 14 场）。

### 2.5 结束阶段

```
429~431  gain_skills ×3
432      save_skill_filter_set
433      factor_order_load
434      factor_select
435      finish
```

### 2.6 `435 finish` 响应（30 键）

与托管育成的 `finish` **完全同构**，关键字段：

```
chara_info           60 字段，最终角色
trained_chara        list[92]     全部育成角色（本次 92 个）
trained_chara_id     610          本次新角色的 ID
directory_card_array list[15]     图鉴
directory_card_num   131
directory_ranking    2
daily_reward_info    17 键（奖励）
reward_item_info     17 键
love_point_info      5 键
training_challenge_result  9 键
```

---

## 三、角色变化：育成前后

### 3.1 `load/index` 里能看到的

抓包里只有 **两次** `load/index`（序号 2 和 7），**都在育成开始之前**。育成结束后客户端没有重新拉 `load/index`。

**因此 `load/index` 无法直接反映育成前后的角色变化。**

对比 002 与 007（相隔 35 秒，中间只做了 `gacha/exec` 和 `jukebox`）：

| 键 | 002 | 007 |
|---|---|---|
| `home_story_data_array` | len 1272 | len 1273 |
| `talk_gallery_list` | len 1272 | len 1273 |
| `user_info` | 有差异（`best_team_evaluation` 等） | 同左 |

**其余 139 个键完全相同。**

### 3.2 真正的角色变化在 `finish` 响应里

| 项 | 育成 A 前 | 育成 A 后（026） | 育成 B 后（435） |
|---|---|---|---|
| `trained_chara` 数量 | 90（推得） | **91** | **92** |
| `trained_chara_id`（新角色） | — | **609** | **610** |
| `circle_point` | — | 14,135,348 | 14,713,019 |
| `directory_card_num` | — | 131 | 131 |
| `directory_ranking` | — | 0 | 2 |

**`[已确认]` 每完成一次育成，`trained_chara` 数组 +1，并分配一个新的 `trained_chara_id`。**

**`[推断]` 育成 A 之前是 90 个（91 - 1），因为抓到的是「完成后」的状态。**

### 3.3 `trained_chara` 每项的字段

```
arrive_route_race_id
card_id
chara_grade
chara_seed
create_time
factor_extend_array
factor_info_array
fans
```

**`[已确认]` 这是育成角色在「角色列表」里的摘要形态——只有 8 个字段，不是完整的 60 字段 `chara_info`。**

完整属性要看 `finish` 响应顶层的 `chara_info`。

### 3.4 新角色的登记位置

`[推断]` 育成完成后：
1. `finish` 返回新角色（`chara_info` 60 字段 + `trained_chara` 数组 +1）
2. 客户端的育成角色列表更新
3. 下次进游戏（或重新拉 `load/index`）时，`trained_chara_array` 里会多一条

**这一点无法从本次抓包证实**——因为育成结束后没有重新拉 `load/index`。

---

## 四、两种育成的对比

| 维度 | 托管（idle） | 模拟点击（festa） |
|---|---|---|
| 客户端参与度 | 只发 start / end | 每次训练、每个事件都要请求 |
| 服务端要算的内容 | 整段训练 + 14 场比赛 + 全部属性增长 | 每次指令的增量 |
| 响应体量 | start 13 KB，end 74 KB | 每次 exec_command 约 21 KB |
| 过程日志 | 一次性给全（`progress_log_info` 10 键） | 分散在每次响应里 |
| 事件系统 | 无（`unchecked_event_array` 为空） | 核心（225 次 `check_event`） |
| 比赛 | 无请求，但日志里有 14 场历史 | 14 次完整四步请求 |
| 结算接口 | 共用 `single_mode_festa/finish` | 同左 |

**关键结论：托管育成的工作量在「模拟整段育成」，模拟点击的工作量在「实现事件系统与指令结算」。两者都不轻松。**

---

## 五、实现时绕不开的问题

### 5.1 托管育成

| # | 问题 | 状态 |
|---|---|---|
| 1 | `progress_log_info` 的 14 场 `race_history_array` 怎么造 | `[未知]` 格式未解析 |
| 2 | 属性增长（`event_gain_info`）的算法 | `[未知]` 只有结果，无公式 |
| 3 | `succession_factor_gain_array`（3 个继承因子）怎么选 | `[未知]` |
| 4 | `support_card_gain_info_array`（6 张卡）怎么算 | `[未知]` |
| 5 | `training_roadmap_selected_info` 的作用 | `[未知]` 本次为 null |
| 6 | 起止时间戳与「挂机时长」的关系 | `[未知]` 只知道 start 时给了 end_time |

### 5.2 模拟点击育成

| # | 问题 | 状态 |
|---|---|---|
| 1 | `command_id` → 训练项目的映射表 | `[未知]` 需统计 64 次请求 |
| 2 | `failure_rate` 的计算 | `[未知]` 由 `home_info` 给出，但怎么算的不知道 |
| 3 | `params_inc_dec_info_array`（属性增减预告） | `[未知]` 结构未展开 |
| 4 | 事件触发条件（225 次 `check_event` 里哪些返回事件） | `[未知]` |
| 5 | `festa_data_set` 的 9 个子结构含义 | `[未知]` 只知字段名 |
| 6 | `act_gauge` / `act_training_step` / `act_level` 的机制 | `[未知]` |
| 7 | `auto_play_plan` 的 `plan_setting_array` 内容 | `[未知]` |
| 8 | `unchecked_event_array` 里 `event_contents_info` 的结构 | `[未知]` |
| 9 | `get_choice_reward`（37 次）与事件选项的关系 | `[未知]` |

### 5.3 两者共有

| # | 问题 | 状态 |
|---|---|---|
| 1 | `chara_info` 60 字段的完整语义 | `[部分已知]` 本次列出了约 35 个 |
| 2 | `evaluation_info_array`（19 项）的含义 | `[未知]` |
| 3 | `factor_info_array` / `factor_extend_array` 的因子系统 | `[未知]` |
| 4 | `training_challenge_result`（考核结果） | `[未知]` |
| 5 | `love_point_info` 的好感度计算 | `[未知]` |

---

## 六、下一步建议

**先做模拟点击（festa），不做托管。**

理由：

1. **有 400 个请求样本可逐条对照**，托管只有 7 个请求，信息密度低得多
2. **托管需要一次性生成 74 KB 的完整过程记录**，任何一处不对客户端都可能判非法；festa 是增量式的，错了只错一步
3. **托管的 14 场 `race_history_array` 没有对应的比赛剧本**，需要凭空造；festa 的 14 场有真实 `race_scenario`

**第一件事：统计 64 次 `exec_command` 的 `command_id` 分布，反推训练项目映射表。**

这个不需要新增抓包，现有数据就够。
