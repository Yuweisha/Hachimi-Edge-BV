# 赛马娘 API 加解密要领

面向 `api.games.umamusume.jp` 的 `application/x-msgpack` 请求/响应，目标是能离线解开、改数据、再加密送回去（例如伪造 `live_theater/index` 解锁全 Live）。

以下结论全部来自实测，未经验证的推测都标了「待验证」。

---

## 1. 抓包样本

```
POST https://api.games.umamusume.jp/umamusume/live_theater/index
Content-Type: application/x-msgpack
APP-VER: 2.32.0
RES-VER: 10021120:TaKKekd21rzI
Device: 4 / Device-SubType: 1
```

| | base64 文本长度 | 二进制长度 | 前 4 字节 (LE u32) |
|---|---|---|---|
| 请求 | 1256 | 940 | `a8 03 00 00` = **936** |
| 响应 | 1424 | 1066 | `54 16 00 00` = **5716** |

Body 全都是 base64 文本，不是原始二进制。

---

## 2. 二进制结构（已验证长度自洽）

```
[u32 小端长度][16 字节 IV][密文]
```

| | 长度 | 拆解 |
|---|---|---|
| 请求 | 936 | 4 + 16 + **916** 密文 |
| 响应 | 1062 | 4 + 16 + **1042** 密文 |

两个密文长度都**不是 16 的倍数**（916 % 16 = 4，1042 % 16 = 2），所以：

- ❌ 不是 AES-CBC
- ❌ 不是 AES-ECB
- ✅ 只能是**流式**：CTR / CFB / OFB 之一

前 4 字节含义不同：

- **请求**：936 = 密文侧总长（4 字节头之后的所有数据）
- **响应**：5716 = **明文长度**（密文只有 1042 → 明文被压缩过，压缩比约 5.5:1，符合 msgpack 的 zlib 压缩特征）

> 实测用 zlib / raw-deflate / gzip 直接解响应体**全部失败**，说明是「先压缩再加密」，解压必须解密之后做。

---

## 3. 密钥（已从运行时读出）

客户端类 `Gallop.AES256Crypt` 有静态字段 `KEYSTR`：

```
KEYSTR = "s%5VNQ(H$&Bqb6#3+78h29!Ft4wSg)ex"    // 32 字符 = 256 bit
```

读取方式（Hachimi 探针 `LiveTheaterProbe`）：

```rust
let f = il2cpp_class_get_field_from_name(klass, c"KEYSTR".as_ptr());
let mut raw: *mut Il2CppObject = null_mut();
il2cpp_field_static_get_value(f, &mut raw as *mut _ as *mut c_void);
let s = &*(raw as *const Il2CppString);
info!("KEYSTR = {}", s.as_utf16str().to_string());
```

注意 `Cryptographer.cRandom` 是 `<null>`，不是密钥来源。

---

## 4. 客户端相关类（已 dump 确认）

| 类 | 关键成员 | 用途 |
|---|---|---|
| `Gallop.AES256Crypt` | `KEYSTR`(static), `Encrypt(2)`, `Decrypt(2)` | 主加解密，2 参数（数据 + IV？待验证） |
| `Gallop.CryptAES` | `Encrypt(1)`, `Decrypt(1)`, `EncryptRJ256(1)`, `DecryptRJ256(1)`, `KEY_SIZE`, `BLOCK_SIZE`, `CRYPT_LENGTH` | 底层 Rijndael 封装 |
| `Gallop.Cryptographer` | `GenerateIvString()`, `GenerateKeyString()`, `Encode(1)`, `Decode(1)`, `MakeMd5(1)` | IV / key 派生、md5 |

---

## 5. Live Theater 响应结构（已 dump）

`live_theater/index` 解析后的对象是 `Gallop.LiveTheaterInfo`：

| 字段 | 偏移 | 说明 |
|---|---|---|
| `<Id>` | 0x18 | music_id |
| `<SongName>` | 0x88 | 曲名 |
| `<IsPlayable>` | 0xb6 | **是否可播（解锁标记）** |
| `<IsNew>` | 0x15 | 新标记 |
| `<IsSkipStory>` | 0x14 | 跳过剧情 |
| `<SongCueSheetName>` | 0x20 | 音频 cue |
| `<JacketPath>` | 0x60 | 封面 |
| `<MoviePath>` | 0x38 | PV |
| `<CharaDressIdArray>` | 0x98 | 服装数组 |

本地 master 数据：`live_data` 表 **207 行**（全部曲目上限）。

客户端界面 `LiveTheaterMusicSelect.Initialize(1)` 接收列表，`LiveTheaterJacketList` 只是 UI。**换歌不再发请求**，说明列表在客户端内存里缓存，只有首次 `index` 决定可见范围。

---

## 6. 待验证：加密模式与 IV 生成

按优先级：

1. **AES-256-CTR**，IV = body[4:20]，counter 从 IV 起累加
2. **AES-256-CFB / OFB**，IV = body[4:20]
3. IV 由 `Cryptographer.GenerateIvString()` 生成（可能是随机 16 字节），`MakeMd5` 参与派生

**验证手段**（最可靠）：hook `AES256Crypt.Decrypt(2)` 和 `Encrypt(2)`，同时 dump 入参和出参，得到「密文 ↔ 明文」成对样本；拿 2~3 组样本就能唯一确定模式和 IV 布局。

---

## 7. 环境坑（本机实测）

- `python` 指向 3.14，`pip` 指向 3.11，两者 site-packages **不通用**。
- `pip install pycryptodome` 装到了 Hermes 自己的 venv（`AppData\Local\hermes\hermes-agent\venv`），`python -c "from Crypto..."` 仍然 `ModuleNotFoundError`。
- 解决办法：显式用装包的那个解释器，或建独立 venv：
  ```bash
  python -m venv C:/Users/Schwarz/projects/uma-api/.venv
  C:/Users/Schwarz/projects/uma-api/.venv/Scripts/pip install pycryptodome msgpack
  ```
- pip 直连 SSL 失败，需要镜像：`-i https://pypi.tuna.tsinghua.edu.cn/simple`

---

## 8. 伪造响应的完整流程（草案）

```
1. 抓一次真实的 live_theater/index 响应
2. 拆 [u32 len][IV 16][cipher]
3. AES-256-CTR 解密 → 得到 zlib 压缩的 msgpack
4. zlib 解压 → msgpack 明文（LiveTheaterIndexResponse）
5. 把 live 列表补全成 207 首（或把每首 IsPlayable 置 true）
6. msgpack 序列化 → zlib 压缩
7. AES-256-CTR 加密（新 IV，写回头部）
8. 重算 u32 长度头
9. Fiddler AutoResponder 替换响应
```

**风险点**：

- `live_theater/live_start` 可能独立校验权限，伪造 index 只解决「看得到」，未必「播得了」
- 服务端可能记录观看行为，异常数据有风控风险
- 若 IV 参与完整性校验（MAC），改数据会被拒

---

## 9. 当前进度

| 项 | 状态 |
|---|---|
| 二进制结构 | ✅ 已确认 |
| 密钥 | ✅ 已取得 |
| 加密模式 | ⏳ 未确认（CTR/CFB/OFB 三选一） |
| IV 生成 | ⏳ 未确认 |
| 明文结构 | ⏳ 未解出 |
| 伪造流程 | ⏳ 待模式确认后即可跑通 |

下一步只做一件事：**hook `AES256Crypt.Decrypt` 抓一对密文/明文**，模式立刻确定。
