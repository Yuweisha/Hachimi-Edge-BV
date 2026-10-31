# 离线服务器操作手册

## 两种模式

| 模式 | 用途 | 服务器 | 开关 |
|---|---|---|---|
| **在线抓包** | 录新数据（数据是真的） | `--proxy` 转发 | `intercept.on` 删除、`mark.on` 删除 |
| **本地回放** | 离线跑（数据来自录像） | 无参数 | `intercept.on` 存在 |

`urlpatch.off` 存在 = URL 不重写（走真实服务器），一般不要创建。

## 切换命令

### 切在线（录数据）
```bash
bash /c/Users/Schwarz/goto_online.sh
```
然后在游戏里把要用的功能点一遍，每点一次服务器记一条「路径 → 长度」。

### 切回放（离线）
```bash
bash /c/Users/Schwarz/local_on.sh
```
需要先确保 `path_declared.json` 和 `replay.bin` 是最新的。

## 数据流

```
游戏 → URL 重写到 127.0.0.1:8080
     → 服务器按路径查 path_declared，返回 36+declared 字节假体
       （前 4 字节 = declared，CTR 流密码长度不变）
     → 游戏调 0x3180 解密
     → 插件拦截，按 declared 查 replay.bin，返回录制明文
     → 解密与哈希校验完全跳过
```

## 关键文件

| 路径 | 说明 |
|---|---|
| `uma_replay/replay.bin` | 录制的明文库（`RPLY` + count + [src,decl,len,data]...） |
| `uma_replay/path_declared.json` | 路径 → 明文长度（服务器查这张表） |
| `uma_replay/intercept.on` | 拦截开关（存在=开） |
| `uma_replay/mark.on` | 数值替换开关（存在=开） |
| `hachimi/http/<时间戳>/` | 每次会话的抓包（json + msgpack） |
| `tools/rebuild_replay_decl.py` | 从抓包重建 replay.bin |
| `tools/local_server.py` | 本地服务器（`--proxy` 转发 / 无参数回放） |

## 三条硬约束

1. **数据必须同会话配套**：`start_session` 的 sid 和 `load/index` 必须是同一轮抓的，混用旧数据会「会话不匹配」或直接崩。
2. **sid 有时效**：录完尽快用，隔几小时可能过期，需要重新录。
3. **数值可改，但编码要合法**：msgpack 整数按值大小选编码，uint16 → uint32 会 +2 字节。客户端缓冲区够（`dstCap` ≈ 2×declared），但递归重写器必须稳健，否则 panic 直接崩游戏。

## 已知限制

- **只能重复上次结果**：抽卡、比赛、训练等需要服务器实时计算的，预制回复只能复现录像里的结果。
- **未录制接口**：默认返回哨兵 4116 → 插件给空响应 `{response_code:1,data:{}}`，能避免网络错误弹窗，但界面会空白或数据异常。
- **回放模式下点新功能必失败**：需要先切在线录一遍。

## 插件开关速查

| 文件 | 存在时 |
|---|---|
| `uma_replay/intercept.on` | 拦截 0x3180，返回录制明文 |
| `uma_replay/mark.on` | 金币/萝卜替换成 100000000 |
| `uma_replay/ksdump.on` | 密钥流落盘（调试用，会拖慢启动） |
| `urlpatch.off` | 关闭 URL 重写（走真实服务器） |

## diff 定位「改了没生效」的字段

**不要猜字段名，直接做两次快照对比。**

```bash
# 1. 在线模式启动，保存阅读前快照
mkdir -p "$GD/hachimi/snapshots/BEFORE"
cp "$GD/hachimi/http/<最新会话>/"*.msgpack "$GD/hachimi/snapshots/BEFORE"/

# 2. 在游戏里做一次目标操作（读一集剧情 / 开一个界面）

# 3. 重启游戏（抓新会话），保存 AFTER
mkdir -p "$GD/hachimi/snapshots/AFTER"
cp "$GD/hachimi/http/<新会话>/"*.msgpack "$GD/hachimi/snapshots/AFTER"/

# 4. 运行对比
python tools/diff_loadindex.py
```

**关键**：快照目录必须放在 `hachimi/snapshots/`，**不要放在 `hachimi/http/` 里**，否则会被 `ls -td http/*/ | head -1` 当成最新会话。

**判读**：排除必然增长的字段（`fcoin`、`rank_score`、`update_time`、`servertime`），剩下的那个才是目标。

实测读一集剧情，全量 diff 只有三处变化：

```
extra_story_data_list.story_event[446].state  0 -> 1     ← 目标
coin_info.fcoin                               11140 -> 11170
user_info.rank_score / update_time            自然增长
```

## 已实测的字段语义

| 字段（`load_index.data.` 下） | 作用 | 改法 |
|---|---|---|
| `extra_story_data_list.story_event[]` | **活动剧情解锁**（`episode_id` 1-460） | 从 `master.mdb` 的 `story_event_story_data.id` 补全全部 460 条，`state` 全 1 |
| `released_episode_data_array` | **只控制 NEW 标记**，不影响解锁数 | ⚠️ 不要当解锁开关用 |
| `main_story_data_list[]` | 主线故事（`episode_id` + `state`） | `state` 全 1 |
| `character_story_data_list[]` | 角色故事（`episode_id` + `state`） | `state` 全 1 |
| `coin_info.fcoin` | 宝石 | 值 <65536 时是 uint16 编码 |
| `item_list[].number`（`item_id`=13） | 金币 | 按 `item_id` 匹配，别按值替换 |

**最大的坑**：`released_episode_data_array` 名字最像「已解锁列表」，实际只点亮 NEW 标记。往里加 460 个 `900xxxxx` 的 story_id，界面上只会多出 NEW，解锁数一点不变。

## 活动剧情的两套 ID

| 表示 | 形态 | 用在哪 |
|---|---|---|
| `story_event_story_data.id` | 1-460 | **`extra_story_data_list.story_event[].episode_id`** |
| `story_event_story_data.story_id_1` | 90001001 这类 | 故事资源 ID，不用于进度记录 |
| `story_event_story_data.episode_index_id` | 1-10（每活动内） | 活动内序号 |

客户端**只认第一个**。这也是为什么搜 `90001001` 在原始 `load_index` 里一个都找不到。

