# 赛马娘（日服）HTTPS 请求与加密逻辑

> 基于 `UmamusumePrettyDerby_Jpn` v1.4.x 逆向与实测。证据分三类：
> **实测**（抓包/日志/内存读到的）、**反汇编**（静态读出的）、**推断**（未经实机确认）。

---

## 1. 网络层：URL 与证书

### 1.1 服务端地址硬编码在 `GameAssembly.dll`

```
文件: GameAssembly.dll
位置: .rdata 段, RVA 0x7fcbb20
长度: 40 字节（定长字符串常量，前后紧挨其它 URL 常量）
内容: "https://api.games.umamusume.jp/umamusume"
      ├─ [0:8]  "https://"                          8 字节
      └─ [8:40] "api.games.umamusume.jp/umamusume" 32 字节
```

**改这个字符串必须保持 40 字节**：

- 多了会覆盖后面的字符串常量（`api.games.umamusume.jp/u` 那段），导致别处崩溃
- 少了会残留旧串尾巴，拼出畸形 URL

**斜杠补齐的实现**（插件侧）：

```rust
std::ptr::write_bytes(target, b'/', 40);          // 先用 '/' 填满
std::ptr::copy_nonoverlapping(new_url.as_ptr(), target, new_url.len());
```

例：`http://127.0.0.1:826/umamusume`（31 字节）→ `http://127.0.0.1:826/umamusume/////////`（40 字节）。

服务器侧会规范化连续斜杠，所以多出的 `/` 无害，只是日志难看。

### 1.2 证书验证：Unity 用自己的 CA bundle，不读系统存储

```
Curl error 35: Cert verify failed. Certificate could not be verified
UnityTls error code: 7
```

**实测结论**：

- 浏览器、Python/OpenSSL 访问同一域名 **全部正常**（TLS 1.3 + 证书验证通过）
- 游戏 **拒绝** Let's Encrypt 证书（ISRG Root X1）
- `UnityPlayer.dll` 里有字符串 `unitytls_x509verify_explicit_ca`，说明走 **显式指定 CA**
- CA bundle 以 **二进制 DER 形式内嵌**在 `UnityPlayer.dll` 里（`cacert` 附近是 DigiCert 证书链），不是 PEM 文件

**所以：**

| 场景 | 可行性 |
|---|---|
| 本地 `http://127.0.0.1:port` | ✅ 正常工作 |
| 公网 `https://` + Let's Encrypt | ❌ 证书不被信任 |
| 公网 + 商业 CA（DigiCert 等，若 bundle 内包含） | ⚠️ 未验证，需签发能对上域名 |
| 改 `UnityPlayer.dll` 内 CA | ❌ 改变文件大小破坏 PE |
| hook `unitytls_x509verify_explicit_ca` | ⚠️ 未实现 |

**另外**：本机 `gethostbyname()` 能解析但 `getaddrinfo()` 失败时，游戏的 libcurl 也会 `Curl error 6: Could not resolve host`。临时用 hosts 可绕（但证书问题仍在）。

---

## 2. 协议加密层

### 2.1 响应体结构

```
HTTP body（文本） = Base64( 二进制 )
二进制 = [u32 declared][32B 密钥材料][密文]
```

| 字段 | 长度 | 说明 |
|---|---|---|
| `declared` | 4 | **解压后**的明文长度（小端 u32）。为 0 表示「不压缩」 |
| 密钥材料 | 32 | 每响应不同，参与 CTR 密钥派生 |
| 密文 | = declared | CTR 是流密码，**密文与明文等长** |

**所以 `srcSize = 36 + declared` 恒成立。**

**关键认知**：`declared` 是**明文长度**，不是 body 字节数。

日志 `proxy X -> declared=1229 (raw=930)` 里：

- `raw`（930）= base64 解码后的总字节 = 36 + 压缩后长度
- `declared`（1229）= 解压后的明文长度

两者不等是正常的，**不要当成响应被截断去查 chunked**。

### 2.2 解密链路（`libnative.dll`）

```
0x3180   解密主入口（读 [4B declared][32B key][密文]）
  ├→ 0x15030   CTR 驱动器（AES-CTR，按 declared 输出明文量）
  │    └→ 0x14f60  密钥流生成（16 字节/块）
  │         └→ 0x73b70  算法分发器（按 type 低 5 位 + 类别选算法）
  └→ 0x143210  LZ4 解压（declared > 0 时）
```

**`0x3180` 内部**：

```
ENTER srcSize=1260170 declared=1260134
  → dst+declared 处会被写 32 字节（SHA 校验值）
  → CTR 解密 src[36:] → LZ4 解压 → 写 dst
RET r=declared
```

**`declared == 0` 只表示「不压缩」**（跳过 LZ4），CTR 照常执行：

```
ENTER srcSize=256 declared=0
RET r=220  dst[0..3] = 83 ad "response_code"   ← msgpack 明文
```

**所以「`declared=0` 的接口不走 `0x3180`」是误判**——它们照走，只是跳压缩。

### 2.3 算法分发（`0x73b70` / `0x46produced` 系列）

`0x73b70` 是 EVP 式分发器，`0x474a0` 是它的包装（先 memset ctx 0x188 字节再调 `0x471a0`）。

`0x471a0` 按 `type & 0xffc07fff` 分类：

| 类别 | 分支 |
|---|---|
| `0x3c00200` | 主路径（`0x4b8a0` 查算法表 → `[rax+0x50]` 初始化） |
| `0x03800000` | 走 `0x46900`（抽卡请求加密走这条，实测 `cat=0x03800000 algo=0x09`） |
| 其它 | 按 cat 分发 |

`0x46900` 内部按 `algo | 0x02000000` 比较，接受 `0x03/0x04/0x05/0x08/0x09/0x0a/0x0b/0x0c/0x0d/0x10/0x11/0x12/0x13`，
不同 id 对应不同上下文长度（`0x40`/`0x48`/`0x68`/`0x88` 等）。

**⚠️ 不要 hook `0x474a0` / `0x46900`**：实测装上后**即使不被调用也会崩溃**（MinHook 改函数前导字节破坏原函数）。
判定法则：hook 零命中但抽卡时崩 → 撤 hook，不是调参数。

### 2.4 请求体结构（同构）

```
请求体 = [u32 declared][32B 密钥材料][密文]
```

**但是**：请求的加密路径与响应不同，`0x15030` 不一定覆盖。

实测抽卡请求（`gacha/exec`）：

- 加密后 base64 **1392 字符**（解码 1044 B，`declared=1040`）
- **单抽和十连长度完全相同** —— `draw_num` 从 1 变 10 都是 1 字节，无法靠长度区分

**抓请求明文的唯一可靠位置**：`0x15030` 的 `p2` 参数（加密方向的明文输入）。

**坑**：探针若写在 `if n < 6` 块里，抽卡请求常排在第 6 次之后 → **永远漏抓**。
现象是「有时能分辨、有时不能」，完全取决于当次抽卡排第几。落盘逻辑必须独立于次数限制。

---

## 3. 会话（sid）

### 3.1 三层表示

| 表示 | 形态 | 位置 | 生成 |
|---|---|---|---|
| raw token | **42 字符** | 响应 `data_headers.sid`；客户端 `Certification._sessionId` | 服务端签发 |
| 请求头 `SID` | 32 hex | 每个请求头 | `MD5(raw + "u1v72NHqkB")` |
| `sid16` | 16 B | 请求密文头部 | `Hex2bin(请求头 SID)`，参与 key/iv 派生 |

长度差 42 vs 32 是正常的——中间隔着一次带盐 MD5。

### 3.2 完全离线时不需要 hook sid

客户端只拿它拼请求头，本地服务器不校验。唯一必须守住的是**同轮配套**：

- `start_session` 的 sid 与 `load/index` 必须来自同一次录制
- 混用不同会话的数据 → 客户端检测到变更 → 「会话不匹配 / 已在其他设备登录」

**三条禁令（实测）**：

1. 不要随机化 sid —— 请求带旧 sid、响应给新 sid，客户端直接报「会话不匹配」，**比不改更糟**
2. 不要返回空 sid —— `UpdateSessionID` 无空值保护，会话被清空
3. 不要把请求头摘要回填进响应 —— 客户端会再散列一次

---

## 4. 客户端相关方法（metadata `methodIndex`）

| 方法 | index |
|---|---|
| `Gallop.Certification.get_SessionId` | 170380 |
| `Gallop.Certification.set_SessionId` | 170381 |
| `Gallop.HttpHelper.CommonProcessOnResponded` | 172677 |
| `Gallop.HttpHelper.UpdateSessionID` | 172678 |
| `Gallop.Cryptographer.MakeMd5` | 170412 |

`metadata v31` 结构：

- `sanity 0xFAB11BAF` + version 31
- `Il2CppTypeDefinition` stride `0x58`
- `Il2CppMethodDefinition` stride `0x24`，`parameterCount` 在 `+0x22`
- `methodPointers` 数组 RVA `0x069A3ED0`，178,380 项，需加运行时基址（每次启动不同）

---

## 5. 本地离线架构（当前实现）

```
游戏 → ① 插件改写 URL（.rdata 40 字节）→ http://127.0.0.1:826/umamusume
     → ② 本地服务器按路径查 path_declared → 回 [4B declared][32B 零][declared 字节零] 的 base64 假体
     → ③ 客户端调 0x3180 解密
     → ④ 插件拦截 0x3180，跳过解密，直接把 replay.bin 里的明文写进 dst
```

**关键点**：

- **服务器发的是假数据**（全零），长度正确即可；真明文由插件从 `replay.bin` 取
- **服务器按路径返回稳定的 `declared`**，插件按这个数查库才必中
- **`declared=0` 的接口**服务器要返回 `36 + 明文长度` 的假体（让客户端 `srcSize` 对上）
- 未录制接口返回哨兵 `4116`，插件给空响应 `{response_code:1, data:{}}`

**抽卡走「现场生成」**：

```
path_declared["gacha/exec"] = 8192（固定槽位，够装十连 ~2600 B）
服务器按 3%/18%/79% 抽卡 → 写 dynamic/8192.msgpack → 返回 8192 长度假体
插件：8192 在 replay.bin 查不到 → 回退读 dynamic/8192.msgpack
```

**`declared` 绝不能当序号用**——它是长度，假体必须 `36 + declared` 字节。

---

## 6. 实测数据速查

### 6.1 `libnative.dll` 关键 RVA

| 符号 | RVA | 作用 |
|---|---|---|
| `0x3180` | 解密主入口 | 读头 + CTR + LZ4 |
| `0x15030` | CTR 驱动器 | AES-CTR |
| `0x14f60` | 密钥流 | 16 字节/块 |
| `0x73b70` | 算法分发 | EVP 式 |
| `0x474a0` | 分发包装 | 先 memset ctx |
| `0x471a0` | 真正的分发 | 按 type 分类 |
| `0x46900` | `cat=0x03800000` 分支 | 抽卡加密走这条 |
| `0x143210` | LZ4 解压 | — |
| `0x60B9A0` | 算法注册表 | 项 24 B（`id` + 两个 fn 指针） |

### 6.2 头部偏移（`0x15030` 的 ctx）

| 偏移 | 含义 |
|---|---|
| `+0x18c` | 大端计数器 |
| `+0x1a0` | 方向：1=加密 / 0=解密 |
| `+0x1a1` | 算法选择：0=MD5 / 2=SHA |
| `+0x60` | 读取全 0（未使用） |
| `+0xe0` | 16 字节，每会话不同（疑似 IV/key 片段） |

### 6.3 实测样本长度

```
000 start_session    397 → 526
001 load/index    199065 → 1191205
002               260 → 224
003             14873 → 51385
004              1104 → 5757
006               943 → 6207
007             15767 → 119252
008               219 → 183
009               950 → 2723
010               869 → 1170
011               489 → 575
```

### 6.4 `declared=0` 接口（不压缩，仍走 `0x3180`）

```
note/trainer_note    明文 220 B
note/save_voice      明文 164 B
photo/library        明文 ?（未取到）
```

服务器侧用**负数**编码标记：`path_declared[path] = -明文长度`，
回放时返回 `[0u32][32B 零][明文长度字节零]`。

---

## 7. 关键教训清单

| 教训 | 细节 |
|---|---|
| `declared=0` ≠ 另一套加密 | 只是 `IsCompressed=false`，CTR 照走 |
| 探针次数限制会漏抓 | `if n < 6` 让抽卡请求永远漏掉 |
| hook 分发型函数会崩 | `0x474a0`/`0x46900` 即使零调用也崩（MinHook 改前导） |
| `patch_servertime` 自引用 UB | `out = Some(...); out.as_mut()` 在 `None` 分支里是未定义行为 |
| Unity 不认系统证书 | 内置 CA bundle，Let's Encrypt 被拒 |
| 40 字节 URL 不能改长度 | 前后都是定长字符串常量 |
| `servertime` 必须现场算 | `start_session` 与 `load/index` 差 7 小时就会弹「日期已改变」 |

---

## 8. 未解决

| 项 | 状态 |
|---|---|
| `note/trainer_note` 等 `declared=0` 接口的离线回放 | ✅ 已解决（负数编码 + `srcSize-36` 匹配） |
| 抽卡 `draw_num` 解析 | ⚠️ 依赖 `hook_ctr` 落盘，服务器与插件跨机时失效 |
| 公网 HTTPS | ❌ Unity CA 问题，已放弃 |
| `0x73b70` 密钥字段 | ❌ `ctx+0xe0` 每会话不同、`ctx+0x60` 全 0，未定位 |
| Android 迁移 | ⚠️ `libnative.so` 无壳可直接分析，但 RVA 需重新定位 |
