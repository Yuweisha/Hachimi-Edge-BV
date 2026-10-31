# 育成（Single Mode）观察记录

> 来源：`hachimi/http/20261028_162128`，961 个文件（65 MB），包含两次完整的线上育成。
> 抓取方式：插件记录全部请求/响应明文（`req.json` / `res.json`），未做任何修改。
> 本文只记录**观察到的现象**，不含实现方案。所有结论标明证据来源。

---

## 一、两次育成是两种完全不同的模式

| | 育成 A | 育成 B |
|---|---|---|
| 接口前缀 | `idle_single_mode` | `single_mode_festa` |
| 用户描述 | 「自主训练，全托管，等时间即可」 | 「自动模式，半托管，游戏全程自己模拟点击」 |
| 育成期请求数 | **7 个** | **约 400 个** |
| 有训练过程吗 | **没有** | 有（`exec_command`） |
| 有比赛吗 | **没有** | 有（14 场） |
| 结束方式 | `finish`（直接结算） | `finish`（结算 + 因子选择） |

**这是两种独立的育成系统，不是同一套流程的两种操作方式。**

---

## 二、育成 A：`idle_single_mode`（放置式）

### 完整序列（序号 016~026）

```
016  pre_single_mode/index
017  pre_single_mode/get_succession_trained_chara
018  friend/index
019  idle_single_mode/pre_start        ← 检查是否有正在进行的放置育成
020  idle_single_mode/start            ← 开始（响应 13 KB）
021  idle_single_mode/end              ← 结束（响应 74.5 KB）
022  idle_single_mode/check_progress_log
023  skill_set/index
024  single_mode_festa/factor_order_load
025  single_mode_festa/factor_select
026  single_mode_festa/finish          ← 结算
```

### 请求/响应要点

**`019 pre_start`**
- 请求：只有公共头 + `is_get_friend_info=false`
- 响应 1,991 B，`data` 键：`last_idle_single_mode_start_info`、`reserved_race_info`
- 作用：查询上一个放置育成的记录，以及是否有预约的比赛

**`020 start`**
- 请求：只有公共头
- 响应 13,065 B，`data` 键：
  ```
  add_trained_chara_array      新增的育成角色
  mission_list                 任务
  progress_info                进度
  story_event_chara_bonus_list 剧情事件加成
  tp_info                      TP
  training_roadmap_selected_info  训练路线图（已选）
  user_item_array              道具
  ```

**`021 end`**
- 请求：只有公共头 + `scenario_id=0`
- 响应 **74,543 B**，`data` 键：`end_info`、`progress_log_info`、`training_roadmap_selected_info`
- **这是放置育成的核心**：`progress_log_info` 是这段时间自动跑出来的训练日志，`end_info` 是结算结果

**`022 check_progress_log`**
- 请求里有 `single_mode_start_request_common`（含 `current_money`、`current_succession_rank_point` 等）和 `start_info`（含 `continue_setting`）
- 响应仅 637 B，`data` 为空字典

### 观察

放置育成的**全部计算在服务器侧**。客户端只发 `start` / `end`，中间的 30 分钟（或更长的挂机时间）什么请求都不发。`end` 返回的 `progress_log_info`（74 KB）就是完整的过程记录。

**这意味着：要实现放置育成，服务器必须自己模拟整段训练过程并生成 progress_log。** 这不是回放能解决的问题。

---

## 三、育成 B：`single_mode_festa`（Festa 育成）

### 开始阶段（序号 030~036）

```
030  pre_single_mode/index
031  training_challenge/exam_select    ← 选择考核
032  idle_single_mode/pre_start
033  single_mode_festa/start           ← 开始，exam_id=84（响应 28.7 KB）
034  single_mode_festa/check_event
035  single_mode_festa/check_event
036  single_mode/auto_play_select_plan  ← 「自动模式」的开关在这里
```

**`033 start` 请求**：只有公共头 + `exam_id=84`
**`033 start` 响应** 28,713 B，`data` 键：`festa_data_set`、`single_mode_start_common`

### 主循环（序号 037~432）

接口频次：

| 接口 | 次数 | 推测作用 |
|---|---|---|
| `check_event` | **225** | 推进回合，查询当前事件 |
| `exec_command` | **64** | 执行训练/休息/外出等指令 |
| `get_choice_reward` | **37** | 领取选项奖励 |
| `attach_advice` | 6 | 附上建议 |
| `gain_skills` | 3 | 获取技能 |
| `auto_play_select_plan` | 1 | 自动模式选计划（只在开头出现） |

**`037 exec_command` 请求**：
```
single_mode_check_event_request_common = {
    'chara_id': 0, 'choice_number': 0, 'current_turn': 1, 'event_id': 100...
}
```
**响应** 21,552 B，`data` 键：
```
chara_info                      角色当前状态
command_result                  指令结果（练了什么、涨了多少）
festa_data_set                  Festa 数据
gain_parameter_info             属性增长
gain_partner_support_effect_array  支援卡效果
home_info                       主页信息
not_down_parameter_info / not_up_parameter_info  属性上限提示
race_condition_array            比赛条件
unchecked_event_array           待处理事件
```

### 比赛部分（14 场）

每场的固定四步：

```
single_mode_festa/race_entry      ← 进场（14 次）
single_mode_festa/race_start      ← 开赛，下发 race_scenario（14 次）
single_mode_festa/race_end        ← 结束
single_mode_festa/race_out        ← 退场
```

**这与 Ultimate Race 的比赛接口结构一致**（`race_entry` → `race_start` → `race_end`），但前缀是 `single_mode_festa`。

**已确认**：`421_single_mode_festa#race_start.res.json` 的 `data.race_scenario` 就是完整的比赛剧本，与 `ultimate_race/race_start` 的结构相同（我们已用这份数据做了样本，见 `UmaRaceGenerator/samples/`）。

### 结束阶段（序号 429~441）

```
429~431  single_mode_festa/gain_skills    ← 获得技能（3 次）
432      single_mode_festa/save_skill_filter_set
433      single_mode_festa/factor_order_load
434      single_mode_festa/factor_select
435      single_mode_festa/finish          ← 结算
436      trained_chara/change_nickname
437      friend/search
438      training_challenge/index
439      jobs/index
440      jukebox/draw_random_request
441      schedule_book/index
```

### 之后的内容（非育成）

```
442  schedule_book/start
443  team_stadium/index
444  team_stadium/opponent_list
445  team_stadium/decide_frame_order
446  team_stadium/start
447  team_stadium/replay_check
448  team_stadium/all_race_end
449  team_stadium/opponent_list
```

**这是 Team Stadium（团队竞技场），不属于育成。**

---

## 四、请求体的公共结构

所有育成请求都带同样的一组公共字段：

```
button_info / carrier / device / device_id / device_name
dmm_onetime_token / dmm_viewer_id / graphics_device_name
ip_address / keychain / locale / platform_os_version
steam_id / steam_session_auth_ticket / viewer_id
```

**只有 `pre_start` 这类无参数请求是「公共字段 + 少量业务字段」，`exec_command` 等才有真正的业务数据。**

**观察**：`steam_session_auth_ticket` 是 Steam 的会话票据（约 200 字节 hex），每台机器固定。这是**敏感数据**，本地服务器如果校验它，必须原样接受。

---

## 五、与 Ultimate Race 的关系

| | Ultimate Race | Single Mode Festa |
|---|---|---|
| 比赛接口 | `ultimate_race/race_entry` / `race_start` | `single_mode_festa/race_entry` / `race_start` |
| 剧本格式 | `race_scenario` | **相同**（已用样本验证结构一致） |
| 结果接口 | `replay_check` | `race_end` + `race_out` |
| 前置流程 | 直接进场 | 育成过程中触发 |

**关键发现：育成里的比赛和传奇赛用的是同一套剧本格式。** 这意味着我们已有的剧本生成器理论上可以直接用于育成中的比赛，但**还需要验证 `single_mode_festa/race_start` 的响应结构是否与 `ultimate_race/race_start` 完全一致**（目前只确认了 `race_scenario` 字段存在且格式相同）。

---

## 六、需要解决的问题（按优先级）

### 高优先级

1. **`idle_single_mode` 的 progress_log 怎么生成**
   放置育成的全部计算在服务端，`end` 返回 74 KB 的过程记录。格式**未解析**。

2. **`single_mode_festa` 的回合推进逻辑**
   225 次 `check_event` + 64 次 `exec_command` 构成完整流程。需要搞清楚：
   - `current_turn` 的范围（1~?）
   - 每个 turn 允许几次 `exec_command`
   - 事件触发条件（哪些 turn 会有 `check_event` 返回事件）

3. **训练指令的执行结果怎么算**
   `exec_command` 的返回里有 `gain_parameter_info`、`gain_partner_support_effect_array`——属性增长的具体公式**未知**。

### 中优先级

4. **Festa 的特殊机制**
   `festa_data_set` 在 `start`、每次 `exec_command`、`race_start` 里都出现。这个数据结构的作用**未解析**。

5. **`exam_id` 的作用**
   `start` 时传 `exam_id=84`，`training_challenge/exam_select` 在育成前调用。考核系统与育成的关系**未确认**。

6. **技能获取流程**
   3 次 `gain_skills` + `save_skill_filter_set`，技能是在育成过程中获得还是结束时统一选？**未确认**。

### 低优先级

7. **`factor_select` / `factor_order_load` 的因子系统**
   育成结束后的因子继承，与 Ultimate Race 的因子系统是否相同**未确认**。

8. **`training_roadmap_selected_info`**
   训练路线图，在 `start` 和 `end` 的响应里都出现。作用**未解析**。

---

## 七、下一步

按用户要求：**等比赛和加密两条线收尾后，立刻开始育成的实现。**

届时的工作顺序建议：

1. 先啃 `single_mode_festa`（半托管）——它的流程与 Ultimate Race 相近，且已有 400 个请求样本可对照
2. 再啃 `idle_single_mode`（放置）——需要自己实现整段训练模拟，工作量大得多
3. 两者的数据模型（`chara_info`、`festa_data_set`、`training_roadmap_selected_info`）需要先解析清楚

**目前这份记录只到「流程和接口层面」。「每个字段什么意思」还没有开始。**

---

## 附：本文的敏感数据处理

文中提到的请求体字段（`viewer_id`、`steam_id`、`steam_session_auth_ticket`、`device_id` 等）**只列字段名，不含实际值**。原始抓包文件保留在本地，不对外提供。
