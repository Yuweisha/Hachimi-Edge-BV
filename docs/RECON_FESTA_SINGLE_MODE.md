# 模拟点击育成侦察报告（`single_mode_festa`）

> 数据来源：`hachimi/http/20261028_162128` 序号 030~435，一次完整的线上 Festa 育成（半托管，游戏自己模拟点击）。
> 只写抓包里直接读到的事实。推断标 `[推断]`，未知标 `[未知]`。身份字段一律不列值。

---

## 一、这是什么

Festa 育成：每一回合、每次训练、每个事件都要和服务器交互。客户端负责点，服务器负责算。

```
030  pre_single_mode/index
031  training_challenge/exam_select        ← 选考核
032  idle_single_mode/pre_start
033  single_mode_festa/start               ← exam_id=84，28,713 B
034  single_mode_festa/check_event
035  single_mode_festa/check_event
036  single_mode/auto_play_select_plan     ← 「自动模式」开关
037  single_mode_festa/exec_command        ← 第一次训练
...  （主循环，约 400 个请求）
435  single_mode_festa/finish              ← 结算
```

---

## 二、接口频次

| 接口 | 次数 | 作用 |
|---|---|---|
| `check_event` | **225** | 推进回合 / 查事件 |
| `exec_command` | **64** | 执行训练等指令 |
| `get_choice_reward` | **37** | 领取选项奖励 |
| `race_entry` / `race_start` / `race_end` / `race_out` | 各 **14** | 比赛四步 |
| `attach_advice` | 6 | 附建议 |
| `gain_skills` | 3 | 获得技能 |
| `auto_play_select_plan` | 1 | 选自动计划 |
| `save_skill_filter_set` / `factor_order_load` / `factor_select` | 各 2~3 | 收尾 |

**`check_event` 是 `exec_command` 的 3.5 倍**——说明大部分回合只是「推进」，不需要训练。

---

## 三、`033 start`（28,713 B）

**请求**：只有公共头 + `exam_id = 84`

**响应** `data` 2 键：`festa_data_set` + `single_mode_start_common`

### 3.1 `festa_data_set`（9 键）

| 键 | 类型 | 每项字段 |
|---|---|---|
| `act_info_array` | list[5] | `act_gauge, act_training_state, act_type, advice_id, friend_outing_gain_act_level, level, need_act_gauge` |
| `advice_info_array` | list[0] | |
| `auto_setting_info` | dict{2} | `auto_call_preset_id` + `preset_array`(3 项：`advice_info_array, auto_setting_attach_advice_info_array, name, preset_id`) |
| `check_point_result_array` | list[0] | |
| `command_gain_act_gauge_array` | list[4] | `command_type, predict_gain_act_gauge_array` |
| `command_info_array` | list[5] | `command_id, command_type, is_upper_training_event_occurred, params_inc_dec_info_array, predict_gain_act_gauge_array` |
| `evaluation_info_array` | list[19] | `act_type, chara_id, target_id` |
| **`festa_info`** | dict{3} | `act_training_step=1` / `max_act_level=10` / `summer_camp_remain_turn_num=0` |
| `not_up_parameter_info` | dict{3} | |

### 3.2 `single_mode_start_common`（19 键）

| 键 | 类型 | 说明 |
|---|---|---|
| **`chara_info`** | dict{60} | 初始角色，`chara_grade=1`、`fans=1` |
| **`home_info`** | dict{13} | **主界面状态，每次 `exec_command` 都重发** |
| `auto_play_custom_plan_array` | list[2] | `plan_description, plan_id, plan_name, plan_setting_array` |
| `auto_play_selected_plan_id` | 150003 | 当前选中的自动计划 |
| `auto_play_default_plan_array` | list[0] | |
| `race_random_program_array` | list[6] | `program_id, turn` |
| **`reserved_race_info`** | dict{3} | `default_deck_num` / `needs_default_confirm` / `reserved_race_array`(9 项) |
| `add_trained_chara_array` | list[0] | |
| `effected_trainer_skill_id_array` | list[0] | |
| `mission_list` | list[0] | |
| `race_condition_array` | list[0] | |
| `is_umaplan` | false | |

### 3.3 `home_info`（13 键）— 客户端「点哪个训练」的唯一依据

```
available_continue_num      = 5
available_free_continue_num = 3
command_info_array          list[10]   ★ 每项：
    command_id                      指令 ID
    command_type                    类型
    failure_rate                    失败率
    is_enable                       是否可点
    level                           等级
    params_inc_dec_info_array       属性增减预告
    sub_command_partner_array       同行角色
    tips_event_partner_array        提示事件角色
continue_unlock_flag        = True
disable_command_id_array    list[0]
disable_command_info_array  list[0]
disable_race_turn_array     list[0]
free_continue_num           = 3
free_continue_time          = 1790322475
race_entry_restriction      = 1
shortened_race_state        = 4
special_home_id             = 0
```

**`[已确认]` 10 条指令，每条带 `failure_rate` 和属性增减预告。这是 UI 上「点哪个训练」的全部数据来源。**

---

## 四、`034 check_event`

**请求业务字段只有 `{"scenario_id": 0}`。**不带回合号，不带事件 ID。

**响应 `data` 13 键：**

```
chara_info                      角色状态
event_effected_factor_array     事件影响的因子
festa_data_set                  同 start
gain_parameter_info             属性增长
gain_partner_support_effect_array
home_info                       重发
not_down_parameter_info         防护
not_up_parameter_info           属性没涨的原因
race_condition_array
race_running_style
race_start_info                 ★ 出现比赛时才有内容
select_index_info_array
unchecked_event_array           ★ 待处理事件
```

**`unchecked_event_array` 里每条事件的 7 个字段：**

```
chara_id
event_contents_info
event_id
minigame_result
play_timing
story_id
succession_event_info
```

本次实测：`event_id=1001`、`chara_id=0`、`play_timing=1`

**`[已确认]` `check_event` 一次返回「当前状态 + 待处理事件」，客户端反复调用把它推进到下一回合。**

**`[未知]` 225 次调用里，哪些返回了事件、哪些只是空推进。** 需要逐条统计 `unchecked_event_array` 的长度。

---

## 五、`037 exec_command`

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
| `festa_data_set` | 9 键（同 start） |
| `gain_parameter_info` | `{effected_command_id_array, gain_partner_support_effect_array, is_view_training_bonus_turn_log}` |
| `gain_partner_support_effect_array` | list[0] |
| `home_info` | 13 键（重发） |
| `not_down_parameter_info` | 3 键 |
| `not_up_parameter_info` | **11 键** |
| `race_condition_array` | list[0] |
| `unchecked_event_array` | list[1] |

**`[已确认]` `command_id=101` 是一次训练，`result_state=2` 表示成功。**

**`[未知]` `command_id` 与训练项目的映射表**——需要统计 64 次请求的 `command_id` 分布才能反推。

### `not_up_parameter_info` 的 11 个键（属性没涨的原因）

```
chara_effect_id_array
command_lv_array
evaluation_chara_id_array
has_chara_effect_id_array
not_gain_chara_effect_array
skill_id_array
skill_lv_id_array
skill_tips_array
status_type_array
unsupported_evaluation_chara_id_array
unsupported_evaluation_support_card_id_array
```

---

## 六、比赛部分（14 场）

每场固定四步：

```
race_entry      进场
race_start      开赛（下发 race_scenario）
race_end        结束
race_out        退场
```

**实测 `race_start` 序号：**

```
84 / 137 / 180 / 195 / 240 / 262 / 314 / 330 / 364 / 380 / 392 / 403 / 411 / 421
```

**`[已确认]` `race_start` 的 `data.race_scenario` 与 `ultimate_race/race_start` 结构相同。**已用其中一份做样本（`samples/race_scenario_2000m_turf_18h.bin`）。

---

## 七、结束阶段

```
429~431  single_mode_festa/gain_skills ×3
432      single_mode_festa/save_skill_filter_set
433      single_mode_festa/factor_order_load
434      single_mode_festa/factor_select
435      single_mode_festa/finish          ← 30 键，与托管育成同构
```

`finish` 的 `single_mode_finish_common` 关键字段：

```
chara_info             60 字段，最终角色
trained_chara          list[92]     全部育成角色
trained_chara_id       610          本次新角色 ID
directory_card_array   list[15]
directory_card_num     131
directory_ranking      2
daily_reward_info      17 键
reward_item_info       17 键
love_point_info        5 键
training_challenge_result  9 键
```

---

## 八、角色变化（育成本次）

### 8.1 `load/index` 能看到什么

抓包里只有两次 `load/index`（序号 2 和 7），**都在育成之前**。育成结束后客户端**没有重新拉** `load/index`。

对比 002 与 007（相隔 35 秒，中间只做了 `gacha/exec`）：

| 键 | 002 | 007 |
|---|---|---|
| `home_story_data_array` | 1272 | 1273 |
| `talk_gallery_list` | 1272 | 1273 |
| `user_info` | 有差异 | 同左 |

**其余 139 个键完全相同。**

### 8.2 真正的角色变化在 `finish` 响应里

| 项 | 育成 A 后（序号 026） | 育成 B 后（序号 435） |
|---|---|---|
| `trained_chara` 数量 | **91** | **92** |
| `trained_chara_id` | **609** | **610** |
| `circle_point` | 14,135,348 | 14,713,019 |
| `directory_card_num` | 131 | 131 |
| `directory_ranking` | 0 | 2 |
| `scenario_record_array` | list[0] | list[3] |

**`[已确认]` 每完成一次育成，`trained_chara` 数组 +1，分配新的 `trained_chara_id`（609 → 610 连续递增）。**

**`[推断]` 育成 A 之前是 90 个**（91 - 1），因为抓到的是「完成后」的状态，无法直接看到育成前的数量。

### 8.3 `trained_chara` 每项的字段

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

**只有 8 个字段——这是角色列表里的摘要形态，不是完整属性。**完整属性要看 `finish` 顶层的 `chara_info`（60 字段）。

### 8.4 新角色何时进入 `load/index`

**`[未知]`。** 本次抓包在两次 `finish` 之后都没有重新拉 `load/index`，所以无法确认新角色是：
- 立刻出现在下一次 `load/index` 的 `trained_chara_array` 里
- 还是需要额外触发

**`[推断]`** 应该是下次启动或重新拉 `load/index` 时出现。

---

## 九、实现难点

| # | 问题 | 状态 |
|---|---|---|
| 1 | `command_id` → 训练项目的映射 | `[未知]` 统计 64 次请求可反推 |
| 2 | `failure_rate` 的计算 | `[未知]` 由 `home_info` 给出，算法不明 |
| 3 | `params_inc_dec_info_array`（属性增减预告）结构 | `[未知]` 未展开 |
| 4 | 事件触发条件 | `[未知]` 需统计 225 次 `unchecked_event_array` |
| 5 | `festa_data_set` 9 个子结构的语义 | `[未知]` 只知字段名 |
| 6 | `act_gauge` / `act_training_step` / `act_level` 机制 | `[未知]` |
| 7 | `auto_play_plan` 的 `plan_setting_array` | `[未知]` |
| 8 | `event_contents_info` 的结构 | `[未知]` |
| 9 | `get_choice_reward`（37 次）与事件选项的关系 | `[未知]` |
| 10 | `chara_info` 60 字段完整语义 | `[部分已知]` |
| 11 | `evaluation_info_array`（19 项）含义 | `[未知]` |
| 12 | `training_challenge_result`（考核结果） | `[未知]` |

---

## 十、`command_id` 实测对应（64 次执行的属性增量反推）

**先说一个重要事实：`exec_command` 的请求里没有 `command_id`。**

```json
{"chara_id": 0, "choice_number": 0, "current_turn": 1,
 "event_id": 1001, "exec_auto_play_plan_id": 150003}
```

`command_id` 只出现在**响应**的 `command_result` 里。**自动模式下训练由服务器选，客户端只负责执行。**

### 10.1 分布

| command_id | 次数 | 观察到的属性增量 |
|---|---|---|
| **5101** | 18 | speed +39~+120（主导） |
| **101** | 12 | speed +21~+65（主导） |
| **5105** | 8 | wiz +60~+102（主导） |
| **390** | 5 | speed +3~+17、power +1~+15（**sub_id=9052**） |
| **701** | 4 | wiz +10、speed +6~+13（小幅） |
| **5102** | 4 | stamina +51~+120（主导） |
| **102** | 3 | stamina +41~+43（主导） |
| **5104** | 3 | guts +77~+94（主导） |
| **105** | 2 | stamina +18~+19 |
| **103** | 2 | guts +15~+40 |
| **5103** | 2 | power +70~+118（主导） |
| **106** | 1 | wiz +32 |

`result_state` 全部为 **2**（成功），无失败。

### 10.2 确定的部分

**`5101~5105` 这一组能确定：**

| id | 训练项目 |
|---|---|
| `5101` | **速度**（18 次里 speed 都是最大增量） |
| `5102` | **耐力** |
| `5103` | **力量** |
| `5104` | **根性** |
| `5105` | **智力** |

**`101` 也是速度**，但增量明显小于 `5101`（+21~+65 vs +39~+120）——`[推断]` 是「同项目的基础版/低等级版」。

**`390` 是特殊指令**：唯一一个 `sub_id=9052` 的（其余全是 `sub_id=1`），增量为正但很小。`[推断]` 可能是「外出」或「休息+小恢复」。

**`701`**：wiz +10 为主，增量极小。`[推断]` 可能是「休息」或「心情提升」。

### 10.3 不确定的部分

**编号规则不是「后两位 = 训练类型」：**

```
103  → guts（不是 power）
105  → stamina（不是 wiz）
106  → wiz
101  → speed ✓ 符合
102  → stamina ✓ 符合
```

**`101~106` 这组的映射关系只确定了 101/102/106 三个，103 与 105 与「后两位规则」冲突。**

`[未知]` 需要更多样本（尤其是 104）才能定。

`[推断]` 可能 `1xx` 是「旧编号体系」，`51xx` 是「新体系」，两套编号不共用规则。

### 10.4 属性增长的整体曲线

64 次执行把角色从初始拉到最终：

```
起始(序号37)   speed 161  stamina 138  power 159  guts  99  wiz 154
最终(序号415)  speed 2223 stamina 1239 power 1597 guts 1163 wiz 1352
```

**speed 最先触顶（2223，序号 387 之后连续 4 次 +0）**，之后转向 stamina / power / guts。

`[已确认]` 属性有上限，触顶后 `not_up_parameter_info` 会有内容。

---

## 十一、下一步

**已完成：`command_id` 分布统计。**

**接下来两件事：**

1. **统计 225 次 `check_event` 里 `unchecked_event_array` 的长度分布**
   能看出多少回合有事件、多少只是空推进，从而定出事件触发频率。

2. **展开 `params_inc_dec_info_array` 的结构**
   这是 `home_info.command_info_array` 里的「属性增减预告」，拿到它就能算出「点某个训练会涨多少」，是 UI 的核心数据。
