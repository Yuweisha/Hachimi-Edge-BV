// 主线程卡死看门狗。
//
// 卡死时主线程被阻塞，托管层和 Unity 都不会写日志（实测 Unity 侧 60 行启动日志后全空），
// 所以拿不到任何现场。这里用一个独立线程监测主线程心跳：
//
//   - `GameSystem.Update`（主线程每帧）刷新一个时间戳；
//   - 看门狗线程发现超过阈值没刷新，就挂起目标线程、读它的 RIP 与栈候选返回地址、写日志。
//
// 日志前缀 `[stall]`，地址按「模块 + RVA」输出，可直接对反编译函数。

use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::time::{Duration, Instant};

/// 主线程最后一次心跳的单调毫秒。
static LAST_BEAT: AtomicU64 = AtomicU64::new(0);
static HEARTBEATS: AtomicU64 = AtomicU64::new(0);
static STALLS: AtomicU64 = AtomicU64::new(0);
static MONITORING: AtomicBool = AtomicBool::new(false);

static START: once_cell::sync::Lazy<Instant> = once_cell::sync::Lazy::new(Instant::now);

fn now_ms() -> u64 {
    START.elapsed().as_millis() as u64
}

/// 主线程每帧调用。
pub fn beat() {
    LAST_BEAT.store(now_ms(), Ordering::Release);
    let n = HEARTBEATS.fetch_add(1, Ordering::Relaxed);
    if n == 0 {
        info!("[stall] 看门狗心跳已启动");
    }
}

#[cfg(target_os = "windows")]
mod win {
    use super::*;
    use std::ffi::c_void;

    #[repr(C)]
    pub struct Context {
        pub context_flags: u32,
        pub _pad: [u32; 6],
        pub rax: u64, pub rcx: u64, pub rdx: u64, pub rbx: u64,
        pub rsp: u64, pub rbp: u64, pub rsi: u64, pub rdi: u64,
        pub r8: u64, pub r9: u64, pub r10: u64, pub r11: u64,
        pub r12: u64, pub r13: u64, pub r14: u64, pub r15: u64,
        pub rip: u64,
    }

    #[repr(C)]
    pub struct ThreadEntry {
        pub dw_size: u32,
        pub cnt_usage: u32,
        pub thread_id: u32,
        pub owner_pid: u32,
        pub base_pri: i32,
        pub delta_pri: i32,
        pub flags: u32,
    }

    #[repr(C)]
    pub struct ModuleEntry {
        pub dw_size: u32,
        pub module_id: u32,
        pub pid: u32,
        pub glblcnt: u32,
        pub proccnt: u32,
        pub base: *mut c_void,
        pub size: u32,
        pub hmodule: *mut c_void,
        pub name: [u8; 256],
        pub path: [u8; 260],
    }

    const TH32CS_SNAPTHREAD: u32 = 0x4;
    const TH32CS_SNAPMODULE: u32 = 0x8;
    const THREAD_GET_CONTEXT: u32 = 0x0008;
    const THREAD_SUSPEND_RESUME: u32 = 0x0002;
    const THREAD_QUERY_INFORMATION: u32 = 0x0040;
    const CONTEXT_AMD64: u32 = 0x00100000;
    const CONTEXT_CONTROL: u32 = CONTEXT_AMD64 | 0x1;
    const CONTEXT_INTEGER: u32 = CONTEXT_AMD64 | 0x2;

    #[link(name = "kernel32")]
    extern "system" {
        fn GetCurrentProcessId() -> u32;
        fn GetCurrentProcess() -> *mut c_void;
        fn OpenThread(access: u32, inherit: i32, tid: u32) -> *mut c_void;
        fn CloseHandle(h: *mut c_void) -> i32;
        fn GetThreadContext(h: *mut c_void, ctx: *mut Context) -> i32;
        fn SuspendThread(h: *mut c_void) -> u32;
        fn ResumeThread(h: *mut c_void) -> u32;
        fn ReadProcessMemory(p: *mut c_void, addr: *const c_void, buf: *mut c_void, size: usize, read: *mut usize) -> i32;
        fn CreateToolhelp32Snapshot(flags: u32, pid: u32) -> *mut c_void;
        fn Thread32First(snap: *mut c_void, entry: *mut ThreadEntry) -> i32;
        fn Thread32Next(snap: *mut c_void, entry: *mut ThreadEntry) -> i32;
        fn Module32First(snap: *mut c_void, entry: *mut ModuleEntry) -> i32;
        fn Module32Next(snap: *mut c_void, entry: *mut ModuleEntry) -> i32;
        fn GetModuleHandleW(name: *const u16) -> *mut c_void;
    }

    fn module_base(name: &str) -> u64 {
        let mut w: Vec<u16> = name.encode_utf16().collect();
        w.push(0);
        unsafe { GetModuleHandleW(w.as_ptr()) as u64 }
    }

    fn modules(pid: u32) -> Vec<(u64, u64, String)> {
        let mut out = Vec::new();
        unsafe {
            let snap = CreateToolhelp32Snapshot(TH32CS_SNAPMODULE, pid);
            if snap as isize == -1 { return out; }
            let mut me: ModuleEntry = std::mem::zeroed();
            me.dw_size = std::mem::size_of::<ModuleEntry>() as u32;
            if Module32First(snap, &mut me) != 0 {
                loop {
                    let name = std::ffi::CStr::from_ptr(me.name.as_ptr() as *const i8)
                        .to_string_lossy().to_string();
                    out.push((me.base as u64, me.size as u64, name));
                    if Module32Next(snap, &mut me) == 0 { break; }
                }
            }
            CloseHandle(snap);
        }
        out
    }

    fn resolve(mods: &[(u64, u64, String)], addr: u64) -> String {
        for (base, size, name) in mods {
            if addr >= *base && addr < base + size {
                return format!("{}+0x{:X}", name, addr - base);
            }
        }
        format!("0x{:X}", addr)
    }

    unsafe fn read_mem(addr: u64, len: usize) -> Vec<u8> {
        let mut buf = vec![0u8; len];
        let mut got: usize = 0;
        if ReadProcessMemory(GetCurrentProcess(), addr as *const c_void,
                             buf.as_mut_ptr() as *mut c_void, len, &mut got) != 0 && got > 0 {
            buf.truncate(got);
            buf
        } else {
            Vec::new()
        }
    }

    /// 采样：固定缓冲区累积文本，全程不分配（避免挂起主线程时死锁）。
    pub fn sample_to_buffer() -> String {
        let pid = unsafe { GetCurrentProcessId() };
        let mods = modules(pid);
        let ga = module_base("GameAssembly.dll");
        let ga_size = 0x8000000u64;

        let mut tids: Vec<u32> = Vec::new();
        unsafe {
            let snap = CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0);
            if snap as isize != -1 {
                let mut te: ThreadEntry = std::mem::zeroed();
                te.dw_size = std::mem::size_of::<ThreadEntry>() as u32;
                if Thread32First(snap, &mut te) != 0 {
                    loop {
                        if te.owner_pid == pid { tids.push(te.thread_id); }
                        if Thread32Next(snap, &mut te) == 0 { break; }
                    }
                }
                CloseHandle(snap);
            }
        }

        // ★ 预分配 64KB：挂起主线程期间这个 String 绝不能扩容（扩容要拿堆锁，
        //   而主线程可能正持有它 → 看门狗自己死锁，实测只打出「无心跳」就没有下文）。
        let mut buf = String::with_capacity(65536);
        // 注：这里的 String 分配发生在「还没有挂起任何线程」之前，是安全的。
        use std::fmt::Write as _;
        let _ = write!(buf, "[stall] ===== 在主线程卡死时采样 {} 线程 =====\n", tids.len());
        let mut hits = 0;

        for tid in tids {
            unsafe {
                let ht = OpenThread(
                    THREAD_GET_CONTEXT | THREAD_SUSPEND_RESUME | THREAD_QUERY_INFORMATION,
                    0, tid,
                );
                if ht.is_null() { continue; }
                SuspendThread(ht);
                let mut ctx: Context = std::mem::zeroed();
                ctx.context_flags = CONTEXT_CONTROL | CONTEXT_INTEGER;
                if GetThreadContext(ht, &mut ctx) != 0 {
                    let in_ga = ga != 0 && ctx.rip >= ga && ctx.rip < ga + ga_size;
                    if in_ga && hits < 12 {
                        hits += 1;
                        let _ = write!(
                            buf,
                            "  tid={} rip={} rsp=0x{:X}\n      rax=0x{:X} rbx=0x{:X} rcx=0x{:X} rdx=0x{:X}",
                            tid, resolve(&mods, ctx.rip), ctx.rsp,
                            ctx.rax, ctx.rbx, ctx.rcx, ctx.rdx
                        );
                        // 沿栈扫「落在 GameAssembly 范围内」的指针，作为候选返回地址
                        let stack = read_mem(ctx.rsp, 0x400);
                        let mut n = 0;
                        for chunk in stack.chunks_exact(8) {
                            let v = u64::from_le_bytes(chunk.try_into().unwrap());
                            if v >= ga && v < ga + ga_size {
                                let _ = write!(buf, "\n      #{} {}", n, resolve(&mods, v));
                                n += 1;
                                if n >= 12 { break; }
                            }
                        }
                        buf.push('\n');
                    }
                }
                ResumeThread(ht);
                CloseHandle(ht);
            }
        }

        if hits == 0 {
            buf.push_str("  没有线程停在 GameAssembly 内（可能卡在 Unity 或等待锁）\n");
        }
        buf
    }
}

/// 启动看门狗线程。`timeout_secs` 内主线程无心跳即判定卡死并采样。
pub fn start(timeout_secs: u64) {
    if MONITORING.swap(true, Ordering::AcqRel) {
        return;
    }
    beat();
    std::thread::spawn(move || {
        let limit = timeout_secs * 1000;
        let mut reported_at = u64::MAX;
        loop {
            std::thread::sleep(Duration::from_millis(500));
            let last = LAST_BEAT.load(Ordering::Acquire);
            let now = now_ms();
            if now.saturating_sub(last) > limit {
                if reported_at != last {
                    reported_at = last;
                    let n = STALLS.fetch_add(1, Ordering::Relaxed);
                    // ★ 采样必须在「挂起线程 → 读上下文 → 恢复线程」全程不分配内存，
                    //   再在恢复之后写日志。否则：主线程被 SuspendThread 挂起时可能正持有
                    //   CRT/堆锁，而 error! 分配缓冲就要拿那把锁 → 看门狗自己死锁
                    //   （实测现象：只打出「8 秒无心跳」这一行，后面什么都没有）。
                    #[cfg(target_os = "windows")]
                    {
                        let report = win::sample_to_buffer();
                        error!(
                            "[stall] 主线程 {} 秒无心跳（第 {} 次，累计心跳 {}）\n{}",
                            (now - last) / 1000, n + 1,
                            HEARTBEATS.load(Ordering::Relaxed), report
                        );
                    }
                    #[cfg(not(target_os = "windows"))]
                    {
                        error!(
                            "[stall] 主线程 {} 秒无心跳（第 {} 次）",
                            (now - last) / 1000, n + 1
                        );
                    }
                }
            }
        }
    });
    info!("[stall] 看门狗已启动（阈值 {}s）", timeout_secs);
}

/// 由游戏初始化完成后调用（`GameSystem::init`）。
pub fn init(_image: *const crate::il2cpp::types::Il2CppImage) {
    start(8);
}
