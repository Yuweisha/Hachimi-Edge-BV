# 托管育成侦察报告（`idle_single_mode`）

> 数据来源：`hachimi/http/20261028_162128` 序号 016~026，一次完整的线上放置育成。
> 只写抓包里直接读到的事实。推断标 `[推断]`，未知标 `[未知]`。身份字段一律不列值。

---

## 一、这是什么

放置式育成：开始后客户端**不再发任何请求**，等时间结束再一次性结算。

```
016  pre_single_mode/index
017  pre_single_mode/get_succession_trained_chara
018  friend/index
019  idle_single_mode/pre_start      ← 查是否有进行中的放置育成
020  idle_single_mode/start          ← 13,065 B
021  idle_single_mode/end            ← 74,543 B
022  idle_single_mode/check_progress_log
023  skill_set/index
024  single_mode_festa/factor_order_load
025  single_mode_festa/factor_select
026  single_mode_festa/finish        ← 结算
```

**7 个育成期请求。`start` 与 `end` 之间零请求。**

---

## 二、育成之前的三次「准备」请求

**`019 pre_start` 不是孤立的——它前面还有两个请求在准备「继承因子候选」。三者各管一件事：**

```
016  pre_single_mode/index                   育成入口信息
017  pre_single_mode/get_succession_trained_chara
                                             自己可继承的角色 + 好友摘要
018  friend/index                            好友可借来继承的角色
019  idle_single_mode/pre_start              上次全托的设置 + 预约比赛
```

### 2.1 `017 get_succession_trained_chara`

**请求**：`{"mission_id_array": [334017]}`

**响应 2,277,712 B**，`data` 两键：

```
succession_trained_chara_data: dict{2}
  succession_trained_chara_array: list[52]   自己的角色，每项：
      arrive_route_race_id / card_id / chara_grade / chara_seed
      create_time / factor_extend_array / factor_info_array / fans
  summary_user_info_array: list[16]          好友摘要
```

**`[已确认]` 这是「自己的角色里哪些可以用来继承因子」，可选 52 个。**

### 2.2 `018 friend/index`

**请求**：`{"is_get_succession_all": false, "saved_succession_trained_chara_array": []}`

**响应 1,337,579 B**，`data` 6 键：

| 键 | 类型 | 说明 |
|---|---|---|
| **`succession_info_array`** | list[46] | **好友可借来继承的角色**，每项 `{succession_chara_array, trained_chara_id, viewer_id}` |
| `friend_list` | list[17] | `{follow_time, follower_time, friend_viewer_id, state}` |
| `recommend_list` | list[30] | 推荐好友 |
| `user_info_summary_list` | list[46] | 好友摘要 |
| `follower_info_summary_list` | list[1] | |
| `follower_num` | 4 | |
| `last_friend_checked_time` | 2026-10-27 00:37:06 | |

**`[已确认]` `friend/index` 里的 `succession_info_array`（46 条）就是「好友那边能借来做因子继承的角色」。**

**这一点此前报告里写错了**——原以为它只是社交列表，实际是育成准备的一部分。

### 2.3 `019 pre_start`

**请求**：只有公共头 + `is_get_friend_info = false`

**响应** 1,991 B，`data` 2 键：

#### `last_idle_single_mode_start_info`（4 键）

| 键 | 值 | 说明 |
|---|---|---|
| `continue_setting` | dict{3} | `continue_flag` / `not_continue_flag_below_g2` / `not_continue_flag_unsuitable_race` |
| `priority_skill_array` | list[1] | `{priority, skill_id}` |
| `training_policy_ground_type` | 1 | 训练方针：场地类型 |
| `training_policy_param_rate_set_id` | 1 | 训练方针：参数比例集 |

#### `reserved_race_info`（3 键）

| 键 | 值 |
|---|---|
| `default_deck_num` | 0 |
| `needs_default_confirm` | 1 |
| `reserved_race_array` | list[8]，每项 `{deck_name, deck_num, race_array}` |

**`[已确认]` `pre_start` 返回的是「上次全托用的设置 + 已预约的 8 场比赛」，用于开始前的确认界面。**

**注意：`pre_start` 里没有角色，也没有继承因子。**角色与因子在 017/018 里，`pre_start` 只负责「继续设置 / 训练方针 / 预约比赛」这三样。

**`[未知]` 计时器不在 `pre_start`**——四个准备请求里都没有倒计时/截止时间字段（除 `tp_info.max_recovery_time` 是 TP 恢复时间，与育成无关）。

---

## 三、`020 start`（13,065 B）

`data` 8 键：

| 键 | 类型 | 本次值 |
|---|---|---|
| `add_trained_chara_array` | list | **0 条** |
| `mission_list` | list | 0 条 |
| **`progress_info`** | dict | **7 键（核心）** |
| `story_event_chara_bonus_list` | list | 0 条 |
| `story_event_mission_list` | list | 0 条 |
| `tp_info` | dict | `current_tp` / `max_tp` / `max_recovery_time` |
| `training_roadmap_selected_info` | null | |
| `user_item_array` | list | 0 条 |

### `progress_info` 的 7 个键

```
chara_info                        育成中的角色（60 字段）
dress_id                          服装 ID
effected_trainer_skill_id_array   生效的育成者技能
end_time                          结束时间戳    ★ 计时器终点
start_time                        开始时间戳    ★ 计时器起点
story_event_chara_bonus_list      剧情事件加成
story_event_mission_list          剧情事件任务
```

**`[已确认]` `start` 就把角色的 60 个字段建好了，并给出起止时间戳。客户端在 `end` 之前不会再有交互。**

### 全托计时器（实测）

```
start_time = 2026-10-28 17:38:38
end_time   = 2026-10-28 18:28:38
间隔        = 3000 秒 = 50.0 分钟 = 0.83 小时
```

**`[已确认]` 计时器由服务器在 `start` 时下发，本次为 50 分钟整。**

**`[未知]` 这个 50 分钟是否固定。** 只有一次样本，无法判断它是：
- 固定值（全托统一 50 分钟）
- 按角色/赛道/难度变化
- 按 `training_policy_param_rate_set_id` 之类的设置变化

**`[已确认]` 客户端在这 50 分钟内不发任何请求。**

**`[未知]` 客户端是否校验实际等待时长。** 抓包文件的 mtime 不可靠（`.res.json` 的写入时序与请求时间不对应，实测出现 `end.res` 比 `end` 晚 50 分钟这种明显异常），无法用它判断真实间隔。要确认这一点只能实机测试：发一对 `(start_time, end_time)` 间隔很小的值，看客户端是否拒绝 `end`。

**`[推断]` 服务器只要在下发 `start` 时给一对合理的 `(start_time, end_time)`，客户端就会按这个倒计时展示。**

---

## 四、`021 end`（74,543 B）— 全部产出

`data` 3 键：

```
end_info                        25 键
progress_log_info               10 键
training_roadmap_selected_info  null
```

### 4.1 `end_info`（25 键）

| 键 | 类型 | 内容 |
|---|---|---|
| **`chara_info`** | dict{60} | **育成完成的角色** |
| **`reward_summary_info`** | dict{17} | 奖励汇总 |
| `skill_filter_setting_array` | list[8] | 每项 `{set_type, set_value}` |
| `effected_factor_array` | list[0] | |
| `mission_list` | list[0] | |
| `race_scenario` | null | **放置育成无比赛剧本** |
| `race_start_info` | null | |
| `start_dress_info` | list[0] | |
| `unchecked_event_array` | list[0] | |
| `win_saddle_id_array` | list[0] | |
| `prev_chara_grade` | 0 | |
| `is_umaplan` | false | |

#### `reward_summary_info` 的 17 个键

```
add_fcoin                         金币
add_item_list          list[14]   每项 {item_id, number}
add_card_list          list[0]
add_chara_list         list[0]
add_cloth_list         list[0]
add_honor_list         list[0]
add_music_list         list[0]
add_piece_list         list[0]
add_present_num
add_story_id_array
add_support_card_list
add_support_card_limit_break_array
add_support_card_num_array
add_card_bonus_info
add_total_fan
force_update_honor_id
new_chara_profile_array
```

### 4.2 `progress_log_info`（10 键）— 核心

| 键 | 类型 | 内容 |
|---|---|---|
| **`event_gain_info`** | dict{23} | 属性总增长 |
| **`race_history_array`** | list[14] | **14 场比赛历史** |
| **`succession_factor_gain_array`** | list[3] | 3 个继承因子，每项 `{gain_factor_info_array, year}` |
| `succession_gain_info` | dict{23} | 继承加成（同结构） |
| `support_card_gain_info_array` | list[6] | 6 张支援卡，每项 `{gain_info, support_card_id}` |
| `chara_effect_log_array` | list[3] | 每项 `{chara_effect_id, gain_index, is_active}` |
| `continue_info` | dict{2} | `continue_item_before_num` / `continue_item_after_num` |
| `gain_skill_array` | list[0] | |
| `gain_skill_id_array` | list[0] | |
| `total_skill_point` | 7213 | |

#### `event_gain_info` 的 23 个键

```
speed / stamina / power / guts / wiz     每项 {sign, value}
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
speed        value = 1941    sign = 0
stamina      value = 1002    sign = 0
power        value =  759    sign = 0
guts         value =  389    sign = 0
wiz          value = 1057    sign = 0
skill_point  = 4023
total_skill_point = 7213
```

**`[已确认]` 要产出 14 场完整比赛的历史记录，即使客户端一次比赛请求都没发。**

### 4.3 结果角色（`chara_info` 的 60 字段）

本次育成结果：

```
card_id      = 111401        rarity       = 5
chara_grade  = 10            playing_state = 1
fans         = 570353        motivation   = 4
max_vital    = 104           route_id     = 121
race_running_style = 4

max_speed    = 2222          max_stamina  = 1870
max_power    = 1836          max_guts     = 1704
max_wiz      = 1842
default_max_speed/stamina/power/guts/wiz = 1200（全部）

proper_distance_short  = 4   proper_distance_mile   = 7
proper_distance_middle = 7   proper_distance_long   = 5
proper_ground_turf     = 7   proper_ground_dirt     = 5
proper_running_style_nige   = 1
proper_running_style_senko  = 6
proper_running_style_sashi  = 7
proper_running_style_oikomi = 7

chara_effect_id_array   list[2]
evaluation_info_array   list[19]
disable_skill_id_array  list[0]
nickname_id_array       list[0]
```

**另有约 25 个字段未在本文展开。**

---

## 五、托管育成的实现难点

| # | 问题 | 状态 |
|---|---|---|
| 1 | 14 场 `race_history_array` 怎么造 | `[未知]` 格式未解析，且没有对应剧本 |
| 2 | `event_gain_info` 的属性增长算法 | `[未知]` 只有结果值，无公式 |
| 3 | 3 个继承因子怎么选 | `[未知]` |
| 4 | 6 张支援卡成长怎么算 | `[未知]` |
| 5 | `start_time` / `end_time` 的时长规则 | `[未知]` |
| 6 | `training_roadmap_selected_info` 的作用 | `[未知]` 本次为 null |
| 7 | `evaluation_info_array`（19 项）的含义 | `[未知]` |
| 8 | 奖励怎么算（`add_fcoin` / `add_item_list`） | `[未知]` |

**核心难点：一次响应里要塞进「整段育成」的全部结果，包括 14 场比赛。任何一处结构性错误客户端都可能判非法，且不报错。**

---

## 六、与模拟点击育成的关系

两者**共用同一个结算接口** `single_mode_festa/finish`，但育成过程完全不共用。

| | 托管 | 模拟点击 |
|---|---|---|
| 请求数 | 7 | ~400 |
| 服务端要算什么 | 整段育成 | 每次指令的增量 |
| 比赛 | 无请求，但日志里有 14 场 | 14 次完整四步请求 |
| 事件系统 | 无 | 225 次 `check_event` |

**建议：先做模拟点击。** 托管需要凭空生成 74 KB 的完整过程记录，且 14 场比赛没有剧本可依；模拟点击有 400 个请求样本可逐条对照，错了只错一步。
