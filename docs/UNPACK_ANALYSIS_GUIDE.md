# 脱壳产物人工分析指南

本包提供的是从**运行中进程内存**重建的 PE 文件（非磁盘原文件）。磁盘上的
`GameAssembly.dll` 等模块被加壳，`.text` 只有转发桩；内存里的才是解密后的真实代码。

---

## 1. 文件清单

| 文件 | 大小 | 来源 | 状态 |
|---|---|---|---|
| `GameAssembly_unpacked.dll` | 182.1 MB | 内存 dump | 代码明文，metadata 仍加密 |
| `libnative_unpacked.dll` | 3.8 MB | 内存 dump | 明文，含 SQLCipher / LZ4 |
| `CySpringPlugin_unpacked.dll` | 942 KB | 内存 dump | `.text` 是跳转桩，真码在 `.fptable` |
| `lib_burst_generated_unpacked.dll` | 336 KB | 内存 dump | 明文 |
| `global-metadata_dump.dat` | 128 MB | 内存 dump | **无效**，抓到的是指针数组，非 metadata |

**重建方式**：按内存镜像写回，节表 `VirtualSize` 直接作为 `RawSize`，
因此 **文件偏移 == RVA**，不需要再做 RVA→FOA 换算。

---

## 2. PE 结构速查

```
SizeOfImage 处 → OptionalHeader
节表起点     → PE sig + 0x18 + SizeOfOptionalHeader
每个节 40 字节：Name(8) VirtualSize(4) VirtualAddress(4) RawSize(4) RawPtr(4) ...
```

`GameAssembly_unpacked.dll` 的节布局（关键）：

| 节 | VA | 大小 | 内容 |
|---|---|---|---|
| `.text` | `0x1000` | 4.5 MB | **壳的转发桩**（`e9 xx xx xx xx` / `cc` 填充） |
| `il2cpp` | `0x491000` | 98 MB | **真正的 C# 编译代码**（IL2CPP 生成） |
| `.rdata` | `0x62B0000` | 20 MB | 只读数据、导入表 |
| `.data` | `0x75F4000` | 54 MB | 静态字段初始化数据（含 S-box 模板） |
| `.pdata` | `0xAE42000` | 5 MB | 异常展开信息 |

> 判断"某段代码在哪"：RVA 落在 `0x491000 ~ 0x62B0000` 之间 = 游戏逻辑；
> 落在 `0x1000 ~ 0x491000` = 壳的桩，顺着 `jmp` 目标才到真码。

---

## 3. 怎么判断加的是壳

| 特征 | 观察方法 | 本例结果 |
|---|---|---|
| 节名异常 | 看节表 | `CySpringPlugin` 有 `.fptable` / `.00cfg` |
| `.text` 全是跳转桩 | 首字节 `cc cc cc cc ... e9` | `CySpringPlugin` 命中 |
| 熵值异常 | 计算字节分布熵，> 7.5 可疑 | 各模块均正常（代码未加密） |
| 导入表极小 | 数 `IMAGE_IMPORT_DESCRIPTOR` | 正常 |
| **metadata 缺失** | 搜 `0xFAB11BAF` | **磁盘 0 命中 → 已加密** |

**本例真正的“壳”不是代码加密，而是 metadata 加密**：
代码可以反汇编，但**没有类名、方法名可查**——所有字符串都在
`global-metadata.dat` 里，而这个文件在磁盘上不存在（`Metadata/` 目录为空）。

---

## 4. 各产物要点

### GameAssembly_unpacked.dll

- 代码**未加密**，可直接反汇编
- **AES-NI 指令 0 条**：`aesenc` / `aesdec` / `aeskeygenassist` / `pclmulqdq` 全部为 0
- 字符串池里有 `RijndaelManaged` / `CreateDecryptor` / `CryptoStream` / `TransformBlock`
  —— 这是 **.NET 库的类名**，不是游戏自己的加密实现
- `.data` 里有 AES S-box 的初始化模板（`63 7c 77 7b f2 6b 6f c5 ...`），
  但**代码没有任何 RIP 相对引用指向它**——因为它是 `static byte[]`，
  运行时从模板复制到 GC 堆，代码只访问「静态字段槽位」

**结论**：纯软件 AES 查表实现，静态无固定地址可追。

### libnative_unpacked.dll

导出符号直接暴露用途：

```
sqlite3_key / sqlite3mc_config_cipher   → SQLCipher（本地 master.mdb 加密）
LZ4_compress_default_ext                → LZ4 压缩（网络 body 压缩）
LZ4_decompress_safe_ext
```

**AES-GCM 指令集中在这里**（`aesenc` x9 / `aesdec` x5 / `aeskeygenassist` x34），
但那是 **SQLCipher 的**，与 HTTP body 加密无关。

### CySpringPlugin_unpacked.dll

- `.text` 尺寸 0，全是跳转桩
- 真实代码在 `.fptable` 节（196 KB）
- 物理模拟插件，与网络无关

### lib_burst_generated_unpacked.dll

- 完全明文，`push rbp; push r15; ...; sub rsp, 0x78` 标准序言
- Unity Burst 编译的 SIMD 代码

---

## 5. 静态分析命令速查

### 找字符串

```bash
strings -n 6 GameAssembly_unpacked.dll | grep -i aes
# 或直接字节搜索（更快）
python -c "d=open('GameAssembly_unpacked.dll','rb').read(); print(d.count(b'RijndaelManaged'))"
```

### 扫指令特征

```python
import capstone
c = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
# AES-NI
for ins in c.disasm(data, 0):
    if ins.mnemonic in ("aesenc","aesdec","aeskeygenassist"):
        ...
```

### 反汇编某个 RVA

文件偏移 == RVA，直接切片：

```python
for ins in md.disasm(data[rva : rva+0x200], rva):
    print("%#x  %-8s %s" % (ins.address, ins.mnemonic, ins.op_str))
```

### 找函数入口

从已知内部地址往回扫，找 `sub rsp, N` + `push` 序言，或往前找 `ret` / `int3` 填充。

---

## 6. metadata 是否加密的判定

`global-metadata.dat` 的第 4 字节起是版本号，**前 4 字节固定为 `0xFAB11BAF`**（小端 `AF 1B B1 FA`）。

```python
import struct
data = open("global-metadata.dat","rb").read()
print(hex(struct.unpack_from("<I", data, 0)[0]))   # 应该是 0xfab11baf
```

本例结果：

| 位置 | `0xFAB11BAF` | 结论 |
|---|---|---|
| 磁盘 `Metadata/global-metadata.dat` | 文件不存在（目录为空） | 未随包分发 |
| 磁盘 `GameAssembly.dll` | **0 命中** | 已加密 |
| 内存 `GameAssembly` 镜像 | **0 命中** | 已加密 / 头被剥离 |
| 内存全进程扫描 | 2 处，均在 exe 代码段（`cmp` 立即数） | 假阳性 |

**但运行时能用类名**（`il2cpp_class_get_name` 正常返回），说明解密后的字符串确实在内存里：

```
Cryptographer   0x3381aac8   0x339a1b88   0x8a84e2c0
CryptAES        0x3327e068   0x8a73fc00
AES256Crypt     0x33323a98   0x8a766d00
```

据此可从字符串区地址反推 metadata 基址（`base = string_addr - stringOffset`）。

---

## 7. 本次实战结论

1. **代码没加密，metadata 加密** —— 这是本作壳的核心，不是传统 VM 壳
2. **加密实现在 il2cpp 段（C# 手写）**，不在 .NET 库
   - 证据：`RijndaelManaged` / `CryptAES` / `AES256Crypt` 的 hook **全部零触发**
   - 若是 .NET 库调用，这些 hook 必然命中
3. **网络 body 结构**（从 base64 前后对齐验证）：

   ```
   base64(binary)  →  [u32 密文长度][密文]
   请求示例：0x3bc = 956，总长 960
   响应示例：0x20e = 526（明文长度），密文 393
   ```

   压缩比 526/393 ≈ 1.34，符合 LZ4 特征（`libnative` 里有 `LZ4_*_ext`）
4. **不是 AES-CBC**：密文长度 956 和 393 都不是 16 的倍数，也不是 32 的倍数
   → 应为流式模式（CTR/CFB/OFB）或自定义
5. **key 长度线索**：反汇编中出现 `mov ecx, 0x20`（32）后紧跟数组分配
   → AES-256 量级的密钥

---

## 8. 分析工具

| 用途 | 工具 |
|---|---|
| 反汇编 | `capstone`（Python）、`objdump`、IDA/Ghidra |
| 内存 dump | `tools/dump_pending_modules.py`（轮询模块加载后重建 PE） |
| 定位 metadata | `tools/find_metadata.py`（扫 `0xFAB11BAF` + 类名锚点） |
| 进程内存读取 | `kernel32!ReadProcessMemory` + `VirtualQueryEx` |

> 读内存一定要先用 `VirtualQueryEx` 校验 `State == MEM_COMMIT`
> 且 `Protect` 不含 `PAGE_NOACCESS` / `PAGE_GUARD`，否则读未提交页会抛异常。
