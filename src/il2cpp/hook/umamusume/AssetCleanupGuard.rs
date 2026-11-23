// 拦截资源自动清理 —— 防止游戏删掉已下载的语音 / 模型
//
// 游戏有个「数据管理」机制会定期清理下载的资源文件（语音、模型等），
// 清理后离线环境无法重新下载，导致语音丢失或资源加载失败。
//
// 拦截点（Cyan.LocalFile.DeleteFileHelper，实测方法表）：
//   DeleteAllFiles()                 @ 0x6262FE0   删所有
//   DeleteFilesByAnyGroupAsync(3)    @ 0x6263290   按组删
//   DeleteFilesAsync(2)              @ 0x62631E0   按名删
//
// 三个都是 void / IEnumerator 返回：
//   - DeleteAllFiles 直接返回，不删
//   - 两个 Async 版本返回 null（调用方会当作「没有要删的」，协程自然结束）
//
// 开关：config.block_asset_cleanup（默认 **false** = 只记录日志，不拦）
//       确认这些调用确实是自动清理后，再设成 true 才真正拦截

use std::ffi::c_void;
use std::sync::atomic::{AtomicUsize, Ordering};

use crate::{
    core::Hachimi,
    il2cpp::{
        symbols::{get_class, get_method_addr},
        types::*,
    },
};

static ORIG_DELETE_ALL: AtomicUsize = AtomicUsize::new(0);
static ORIG_DELETE_GROUP: AtomicUsize = AtomicUsize::new(0);
static ORIG_DELETE_FILES: AtomicUsize = AtomicUsize::new(0);
static N_BLOCKED: AtomicUsize = AtomicUsize::new(0);

/// 只记录不拦截（默认）。看日志确认触发时机后再决定要不要真的拦。
fn probe_only() -> bool {
    !Hachimi::instance().config.load().block_asset_cleanup
}

fn note(kind: &str) {
    let n = N_BLOCKED.fetch_add(1, Ordering::Relaxed);
    if n < 10 {
        warn!("[cleanup] 已拦截资源清理调用：{}", kind);
    }
}

// DeleteAllFiles(this)
type Void0 = extern "C" fn(*mut Il2CppObject);
extern "C" fn DeleteAllFiles(this: *mut Il2CppObject) {
    note("DeleteAllFiles");
    if !probe_only() {
        return; // block_asset_cleanup=true 时才真的拦
    }
    let orig: Void0 = unsafe { std::mem::transmute(ORIG_DELETE_ALL.load(Ordering::Relaxed)) };
    orig(this)
}

// DeleteFilesByAnyGroupAsync(this, a1, a2, a3) -> IEnumerator
type Ret3 = extern "C" fn(*mut Il2CppObject, *mut c_void, *mut c_void, *mut c_void) -> *mut Il2CppObject;
extern "C" fn DeleteFilesByAnyGroupAsync(
    this: *mut Il2CppObject, a1: *mut c_void, a2: *mut c_void, a3: *mut c_void,
) -> *mut Il2CppObject {
    note("DeleteFilesByAnyGroupAsync");
    if !probe_only() {
        return std::ptr::null_mut(); // null 协程 → 调用方跳过
    }
    let orig: Ret3 = unsafe { std::mem::transmute(ORIG_DELETE_GROUP.load(Ordering::Relaxed)) };
    orig(this, a1, a2, a3)
}

// DeleteFilesAsync(this, a1, a2) -> IEnumerator
type Ret2 = extern "C" fn(*mut Il2CppObject, *mut c_void, *mut c_void) -> *mut Il2CppObject;
extern "C" fn DeleteFilesAsync(
    this: *mut Il2CppObject, a1: *mut c_void, a2: *mut c_void,
) -> *mut Il2CppObject {
    note("DeleteFilesAsync");
    if !probe_only() {
        return std::ptr::null_mut();
    }
    let orig: Ret2 = unsafe { std::mem::transmute(ORIG_DELETE_FILES.load(Ordering::Relaxed)) };
    orig(this, a1, a2)
}

fn hook_one(
    h: &std::sync::Arc<Hachimi>,
    class: *mut Il2CppClass,
    name: &std::ffi::CStr,
    argc: i32,
    detour: usize,
    slot: &AtomicUsize,
    tag: &str,
) {
    let addr = get_method_addr(class, name, argc);
    if addr == 0 {
        warn!("[cleanup] {} 地址为空", tag);
        return;
    }
    match h.interceptor.hook(addr, detour) {
        Ok(t) => {
            slot.store(t, Ordering::SeqCst);
            info!("[cleanup] hooked {} @ {:#x}", tag, addr);
        }
        Err(e) => error!("[cleanup] hook {} 失败: {}", tag, e),
    }
}

pub fn init(umamusume: *const Il2CppImage) {
    let h = Hachimi::instance();
    let Ok(k) = get_class(umamusume, c"Cyan.LocalFile", c"DeleteFileHelper") else {
        warn!("[cleanup] DeleteFileHelper 未找到");
        return;
    };

    hook_one(&h, k, c"DeleteAllFiles", 0,
             DeleteAllFiles as *const () as usize, &ORIG_DELETE_ALL, "DeleteAllFiles");
    hook_one(&h, k, c"DeleteFilesByAnyGroupAsync", 3,
             DeleteFilesByAnyGroupAsync as *const () as usize, &ORIG_DELETE_GROUP, "DeleteFilesByAnyGroupAsync");
    hook_one(&h, k, c"DeleteFilesAsync", 2,
             DeleteFilesAsync as *const () as usize, &ORIG_DELETE_FILES, "DeleteFilesAsync");
}
