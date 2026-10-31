# UMA JP 离线/解密 本轮成果

## 一、已确证的协议结构

### HTTP 层

```
URL:   https://api.games.umamusume.jp/umamusume/<path>
       硬编码于 GameAssembly.dll .rdata RVA 0x7fcbb20
       （"https://" 在 0x7fcbb20，域名在 0x7fcbb28，共 40 字节）

Body:  base64 文本（不是二进制！）
       例：start_session 请求体 1280 字节，开头 "vAMA..."
       Content-Type: application/x-msgpack 是误导，实际是 base64 文本

Header:
  SID:        <会话 id>
  APP-VER:    2.32.0
  RES-VER:    10021120:TaKKekd21rzI
  ViewerID:   <用户 id>
  Device / Device-SubType / X-Unity-Version
  Accept-Encoding: deflate, gzip

UA: UnityPlayer/2022.3.62f2 (UnityWebRequest/1.0, libcurl/8.10.1-DEV)
```

### Body 二进制结构（base64 解码后）

```
请求: [u32 密文长度][32 字节密钥材料][密文]          头 36 字节
响应: [u32 明文长度][32 字节密钥材料][密文]          头 36 字节
```

### 解压/解密链路

```
0x3180  LZ4_decompress_safe_ext(src, dst, srcSize, dstCap)
  ├─ 0x15030  CTR 模式驱动（6 参数）
  │    ├─ ctx+0x18c  计数器（大端 +1）
  │    ├─ 0x14f60    生成 16 字节密钥流
  │    │    └─ 0x73b70  算法分发器（cat = type & 0xf000）
  │    └─ 0x44530 (MD5 block) 或 0x72990 (SHA block)
  │         选择器：ctx+0x1a1（0=MD5，2=SHA）
  └─ 0x173210  标准 LZ4 block 解压
```

**关键数值（实测）**：
- `cipher type = 0x00021210`，`cat = 0x1000`，块大小 16
- `ctx+0x1a1 = 2` → SHA 族
- `ctx+0xe0`（32 字节）每次会话不同 → 会话密钥材料
- `ctx+0x180`（16 字节）计数器块

### 解密实测结果

```
样本 00: 872 B    keystream 从 block#0    起 55 块    完整匹配
样本 01: 361 B    keystream 从 block#55   起 23 块    完整匹配
样本 02: 860 B    keystream 从 block#78   起 54 块    完整匹配
样本 03: 198419 B keystream 从 block#132  起 12402 块 完整匹配
```

**结论：CTR 密钥流在会话内连续排列，抓到即可解任意 body。**

## 二、离线服务器进展

### 已打通

1. **URL 重定向**：插件 patch `.rdata` 字符串
   ```
   https://api.games.umamusume.jp/umamusume  (40 B)
   → http://127.0.0.1:8080/umamusume/////////  (40 B，斜杠补齐)
   ```
   实测游戏请求成功到达本地，服务器返回 200。

2. **响应格式**：必须返回 **base64 文本**，不是解码后的二进制。
   返回二进制时客户端直接报「无法读取」；改成文本后 `0x3180` 被调用。

### 卡住

`start_session` 响应来自旧会话，`sid` / `servertime` 已失效。
客户端解出后判定不可用，后续不再发 `load/index`。

**闭环**：改 `sid` 需要解密 → 解密需要密钥流 → 密钥流需要游戏跑真实请求。

## 三、可行方案

| 方案 | 说明 | 状态 |
|---|---|---|
| **A. 半离线** | 首次 `start_session` 走真实服务器，之后切本地 | 未验证 |
| **B. 插件直接返回明文** | hook `0x3180` 返回录制明文（跳过解密） | 已验证命中，但要求请求先成功 |
| **C. 完整离线** | 需要能离线复算密钥流 | 未解（`ctx+0xe0` 来源不明） |

## 四、产物位置

```
C:/Users/Schwarz/uma_replay/       33 个接口（req.b64 / resp.b64 / .bin）
C:/Users/Schwarz/ksout/            13,625 个密钥流块（16 B/块）
C:/Users/Schwarz/ctrsamples/       4 组 (in/out/e0/b180/b60)
C:/Users/Schwarz/srvreq/           服务器收到的请求体
C:/FiddlerDump/                    212 个原始 dump（含 URL + REQB64/RSPB64）

C:/Users/Schwarz/projects/Hachimi-Edge/
  docs/decompiled.c                 GameAssembly 全量反编译（576 MB，289,304 函数）
  docs/decompiled_dump.txt          libnative 全量反编译（18 MB，6,230 函数）
  tools/local_server.py             本地服务器（base64 文本模式）
  tools/build_offline_db.py         从 FiddlerDump 生成录制库

C:/Users/Schwarz/projects/uma-curve-probe/
  src/lib.rs                        插件（URL patch + 各 hook 探针）
```

## 五、插件当前 hook 一览

| RVA | 函数 | 状态 |
|---|---|---|
| `0x3180` | LZ4_decompress_safe_ext | OK |
| `0x143210` | 标准 LZ4 block | OK |
| `0xab65a0` (GA) | HttpHelper.Send/13 | OK 但零触发 |
| `0x154f0` | 哈希校验（10 参数） | OK |
| `0x15030` | CTR 驱动（6 参数） | OK |
| `0x14f60` | 密钥流生成（6 参数） | OK |
| `0x2ecc80` | memcpy（IAT 跳板） | FAILED |

## 六、踩过的坑

1. **RVA 换算**：`Ghidra VA − 0x7ffa1b030000`，不是 `− 0x180000000`。
   曾把 `0x7ffa1b173210` 写成 `0x173210`（少减 0x30000）。
2. **hook 非函数起点会崩**：挂之前确认 `fo-3` 处是 `cc cc cc`。
3. **签名从反编译读，不要猜**：`0x14f60` 是 6 参数，用 4 个会崩。
4. **`methodPointers` 只覆盖 178,380 项**，方法表 350,216 项，高索引映射不到。
5. **URL 不在 metadata 字符串表**，在 `.rdata` 作为 C 字符串常量。
6. **响应必须是 base64 文本**。
