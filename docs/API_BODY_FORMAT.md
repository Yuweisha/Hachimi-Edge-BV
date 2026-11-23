# 赛马娘 API body 格式逆向报告

生成时间：2026-10-24
材料：`libnative_unpacked.dll`（内存 dump）、Ghidra 全量反编译 6503 个函数、
4 组真实样本（`C:/FiddlerDump/lz4pairs/`）

---

## 1. 结论速览

| 项 | 结论 |
|---|---|
| 加密 | **无**。PCG 生成器在游戏运行中零调用，`ctx+0x90` 解密回调为 NULL |
| 请求体 | **不压缩**（`LZ4_compress_default_ext` 零调用），msgpack 明文 |
| 响应体 | **压缩**，自定义熵编码，非 lz4/zstd/brotli 标准格式 |
| 未压缩响应 | **不被接受**（实测：游戏提示"无法从服务器读取数据"） |

---

## 2. body 结构

```
整体 = base64( [u32 LE 解压后长度][32 字节状态区][压缩数据] )
                 4 字节              32 字节             N 字节
```

要点：

- 长度字段是**解压后**的 msgpack 大小
- 32 字节状态区中，`[0:16]` 是 PCG 种子材料（`state = BE(...)`, `inc = BE(...)*2|1`），
  `[16:32]` 用途未完全确定
- 数据从偏移 **36**（0x24）开始
- 输入总长必须 ≥ 36，否则返回 -1

反编译依据（`LZ4_decompress_safe_ext`）：

```c
if (param_3 < 0x24) return -1;
declared = *(u32*)src;
inc   = (BE(src[12..20]) << 1) | 1;
state = BE(src[4..12]) * MULT + inc * (MULT + 1);
local_3d8 = src + 4;    // seed
local_3c0 = src + 9;    // int 指针，等价 src+36
```

---

## 3. PCG 密钥流算法（已完整还原）

`libnative+0x1070`，逐字节输出：

```c
for (i = 0; i < len; i++) {
    old = *state;
    *state = old * 0x5851F42D4C957F2D + inc;
    u32 x   = (u32)(old >> 45) ^ (u32)(old >> 27);
    u32 rot = (old >> 56) >> 3;                     // 等价 old >> 59
    out[i]  = (char)x << ((-rot) & 0x1f) | (byte)(x >> rot);
}
```

**注意**左移量是 `-rot & 0x1f`（即 32-rot），不是 `rot`。

Python 实现见 `tools/uma_pcg_decrypt.py`。

**但游戏实际不启用这条路径**——`ctx+0x90` 为空时直接走 `FUN_7ffa1b048740`（不解密）。

---

## 4. 解码器调用树

```
LZ4_decompress_safe_ext (0x3180)          外层：解析头、分配、错误处理
  ├─ 0x3ed20  主解码调度
  │   ├─ 0x3e5e0  块解码（含 pcVar2 解密回调、尺寸校验）
  │   ├─ 0x3e970  单块处理
  │   ├─ 0x3e440  收尾
  │   └─ bit 读取: 0x457a0 / 0x46600 / 0x46830 / 0x45fd0
  └─ 0x3e180  编码器（解压后重压校验）
      └─ 0x3f130  解压+重压组合入口
```

关键判定：

```c
pcVar2 = *(code **)(param_1 + 0x90);
if (pcVar2 == NULL) FUN_7ffa1b048740(...);   // 不解密（游戏走这里）
else                (*pcVar2)(lVar8);        // 走 PCG 解密
```

`0x75720` 是同步码搜索（250 次重试），`0x75620` 是密钥流写入 + 8 字节大端反转，
都只在校验分支里使用，不是主路径。

---

## 5. 压缩器不在导出表里

`LZ4_compress_default_ext`（`0x10f0`）入口约束：

```c
uVar27 = *(u32*)src + 4;
if (uVar27 < 0x78) return -1;
if (uVar27 == 0xaa) { local_580 = src + 0x1e; }   // 166+4=170
else if (uVar27 != 0x78) return -2;                // 116+4=120
local_574 = (srcSize - uVar27) + 0x58;             // 输出 = 输入 + 88
```

`*(u32*)src` 必须是 **116 或 166**，是两种硬编码模式，只处理固定尺寸块。
libnative 内部**没有任何函数调用这个导出**，游戏运行时也零调用。

**真正的通用编码器是 `0x3e180`（内部函数，不导出）**。

---

## 6. 已排除的可能性

| 假设 | 排除依据 |
|---|---|
| Gallop.CryptAES / AES256Crypt / Cryptographer | hook 全部零调用 |
| .NET RijndaelManaged 全链路 | CreateDecryptor/set_Key/TransformBlock 零调用 |
| KEYSTR 作为密钥 | 全组合爆破失败 |
| 标准 LZ4 | 官方 `lz4.block` 解不开 |
| 标准 zstd | `zstandard` 解不开（frame header 不匹配） |
| 标准 Brotli | `brotli` 解不开 |
| PCG 流解密后解压 | 解密结果仍高熵，各解压器均失败 |
| 未压缩响应 | Fiddler 替换实测被拒绝 |

---

## 7. 待完成

1. 翻译 `0x3ed20` 解码树 → Python，用 4 组样本验证
2. 翻译 `0x3e180` 编码树 → Python（离线生成响应的关键）
3. 确定 32 字节状态区后 16 字节的语义

工作量评估：两棵调用树约 6–8 个函数、上千行位运算代码。

---

## 8. 工具与环境

```
Ghidra 12.2      C:\ghidra\ghidra_12.2_PUBLIC
JDK 25           C:\jdk25\jdk-25.0.4.1+1
导出脚本         C:\Users\Schwarz\projects\ghidra-scripts\ExportDecompiled.java
全量反编译       docs/decompiled_dump.txt（17.4 MB，6503 函数）
样本              C:/FiddlerDump/lz4pairs/NNN_src.bin / NNN_dst.bin
插件源码         C:\Users\Schwarz\projects\uma-crypto-plugin
```

**重要**：磁盘上的 `libnative.dll` 是加壳的（`.text` rawsize 仅 0x1000），
必须用内存 dump 版 `libnative_unpacked.dll` 才能反编译出完整代码。
