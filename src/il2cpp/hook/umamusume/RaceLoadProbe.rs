// 比赛加载链路探针 —— 定位「卡比赛加载」卡在哪一步
//
// 思路：在 RaceSimulateData 的反序列化、帧数据解析、马管理器初始化、
//       视图创建等 10 个关键点各打一次日志，看客户端执行到哪一步就停了。
//
// 打开方式：环境变量 `HACHIMI_RACELOAD_PROBE=1`
// 日志前缀：`[raceload]`

use std::ffi::c_void;
use std::sync::atomic::{AtomicUsize, Ordering};

use crate::il2cpp::{
    symbols::{get_class, get_method_addr},
    types::*,
};

macro_rules! probe_fn {
    ($name:ident, $label:expr, $slot:ident) => {
        static $slot: AtomicUsize = AtomicUsize::new(0);
        let $name = || {
            let n = $slot.fetch_add(1, Ordering::Relaxed);
            if n == 0 {
                info!("[raceload] ★ {}", $label);
            } else if n < 3 {
                info!("[raceload]   {} (第 {} 次)", $label, n + 1);
            }
        };
    };
}

// ---------- 各函数原地址 ----------
static ORIG_DESER: AtomicUsize = AtomicUsize::new(0);
static ORIG_DESER_HDR: AtomicUsize = AtomicUsize::new(0);
static ORIG_IMPORT_B64: AtomicUsize = AtomicUsize::new(0);
static ORIG_FRAME_DESER: AtomicUsize = AtomicUsize::new(0);
static ORIG_HORSE_FRAME_DESER: AtomicUsize = AtomicUsize::new(0);
static ORIG_HORSE_NUM: AtomicUsize = AtomicUsize::new(0);
static ORIG_HR_INIT: AtomicUsize = AtomicUsize::new(0);
static ORIG_CREATE_HRINFO: AtomicUsize = AtomicUsize::new(0);
static ORIG_CHECK_FINISH: AtomicUsize = AtomicUsize::new(0);
static ORIG_FINALIZE_MODEL: AtomicUsize = AtomicUsize::new(0);
static ORIG_CREATE_RACEVIEW: AtomicUsize = AtomicUsize::new(0);
static ORIG_B64_TO_SIM: AtomicUsize = AtomicUsize::new(0);
static ORIG_IMPORTER_IMPORT: AtomicUsize = AtomicUsize::new(0);
static ORIG_IMPORT_DIRECT: AtomicUsize = AtomicUsize::new(0);
static ORIG_POST_PROC: AtomicUsize = AtomicUsize::new(0);
static ORIG_POST_IMPORT: AtomicUsize = AtomicUsize::new(0);

// ---------- 计数 ----------
static N_DESER: AtomicUsize = AtomicUsize::new(0);
static N_HDR: AtomicUsize = AtomicUsize::new(0);
static N_B64: AtomicUsize = AtomicUsize::new(0);
static N_FRAME: AtomicUsize = AtomicUsize::new(0);
static N_HFRAME: AtomicUsize = AtomicUsize::new(0);
static N_HNUM: AtomicUsize = AtomicUsize::new(0);
static N_HINIT: AtomicUsize = AtomicUsize::new(0);
static N_CHINFO: AtomicUsize = AtomicUsize::new(0);
static N_FINISH: AtomicUsize = AtomicUsize::new(0);
static N_FINALIZE: AtomicUsize = AtomicUsize::new(0);
static N_RACEVIEW: AtomicUsize = AtomicUsize::new(0);
static N_B64SIM: AtomicUsize = AtomicUsize::new(0);
static N_IMPIMP: AtomicUsize = AtomicUsize::new(0);
static N_IMPDIR: AtomicUsize = AtomicUsize::new(0);
static N_POSTPROC: AtomicUsize = AtomicUsize::new(0);
static N_POSTIMP: AtomicUsize = AtomicUsize::new(0);



// ---------- Hook 函数（只记日志，然后调原函数）----------

#[inline]
fn mark(slot: &AtomicUsize, label: &str) {
    let n = slot.fetch_add(1, Ordering::Relaxed);
    if n < 3 {
        if n == 0 {
            info!("[raceload] {}  ★首次", label);
        } else {
            info!("[raceload] {} (第 {} 次)", label, n + 1);
        }
    }
}

type FnGeneric1 = unsafe extern "C" fn(*mut Il2CppObject) -> *mut Il2CppObject;
type FnGeneric0 = unsafe extern "C" fn(*mut Il2CppObject) -> i32;
type FnVoid0 = unsafe extern "C" fn(*mut Il2CppObject);
type FnVoid1 = unsafe extern "C" fn(*mut Il2CppObject, *mut Il2CppObject);
type FnInt0 = unsafe extern "C" fn(*mut Il2CppObject) -> i32;

unsafe extern "C" fn h_deser(this: *mut c_void, a0: *mut c_void, a1: *mut c_void, a2: *mut c_void, a3: *mut c_void) -> isize {
    mark(&N_DESER, "N_DESER");
    type FnN = unsafe extern "C" fn(*mut c_void, *mut c_void, *mut c_void, *mut c_void, *mut c_void) -> isize;
    let f: FnN = std::mem::transmute(ORIG_DESER.load(Ordering::Relaxed));
    f(this, a0, a1, a2, a3)
}

unsafe extern "C" fn h_deser_hdr(this: *mut c_void, a0: *mut c_void, a1: *mut c_void, a2: *mut c_void, a3: *mut c_void) -> isize {
    mark(&N_HDR, "N_HDR");
    type FnN = unsafe extern "C" fn(*mut c_void, *mut c_void, *mut c_void, *mut c_void, *mut c_void) -> isize;
    let f: FnN = std::mem::transmute(ORIG_DESER_HDR.load(Ordering::Relaxed));
    f(this, a0, a1, a2, a3)
}

unsafe extern "C" fn h_import_b64(this: *mut Il2CppObject) -> *mut Il2CppObject {
    mark(&N_B64, "Reader.ImportBase64");
    let f: FnGeneric1 = std::mem::transmute(ORIG_IMPORT_B64.load(Ordering::Relaxed));
    f(this)
}

unsafe extern "C" fn h_frame_deser(this: *mut c_void, a0: *mut c_void, a1: *mut c_void, a2: *mut c_void, a3: *mut c_void) -> isize {
    mark(&N_FRAME, "N_FRAME");
    type FnN = unsafe extern "C" fn(*mut c_void, *mut c_void, *mut c_void, *mut c_void, *mut c_void) -> isize;
    let f: FnN = std::mem::transmute(ORIG_FRAME_DESER.load(Ordering::Relaxed));
    f(this, a0, a1, a2, a3)
}

unsafe extern "C" fn h_hframe_deser(this: *mut c_void, a0: *mut c_void, a1: *mut c_void, a2: *mut c_void, a3: *mut c_void) -> isize {
    mark(&N_HFRAME, "N_HFRAME");
    type FnN = unsafe extern "C" fn(*mut c_void, *mut c_void, *mut c_void, *mut c_void, *mut c_void) -> isize;
    let f: FnN = std::mem::transmute(ORIG_HORSE_FRAME_DESER.load(Ordering::Relaxed));
    f(this, a0, a1, a2, a3)
}

unsafe extern "C" fn h_horse_num(this: *mut Il2CppObject) -> i32 {
    let f: FnInt0 = std::mem::transmute(ORIG_HORSE_NUM.load(Ordering::Relaxed));
    let n = f(this);
    let c = N_HNUM.fetch_add(1, Ordering::Relaxed);
    if c < 3 {
        info!("[raceload] GetHorseDataNum = {}  ★首次", n);
    }
    n
}

unsafe extern "C" fn h_hr_init(this: *mut Il2CppObject, arg0: *mut c_void) -> isize {
    mark(&N_HINIT, "HorseManagerReplay.Init");
    // ★★ 反汇编 0x3D10480 的关键事实：r14 = rdx = arg0，不是 this！
    //   0x3D1048F  mov r14, rdx        ← arg0 = RaceSimulateData
    //   0x3D10492  mov rbx, rcx        ← this = RaceHorseManagerReplay
    //   0x3D104F5  mov edx, [r14+0xA0] ← RaceSimulateData + 0xA0 = 马数
    //   0x3D1057D  mov rdx, [r14+0xD0] ← RaceSimulateData + 0xD0 = 马数据数组
    //   0x3D10584  mov rsi, [rbx+0x10] ← this + 0x10 = 输出数组
    //   0x3D10525  mov [rbx+0x18], eax ← this + 0x18 = 马数
    //   0x3D1052A  mov [rbx+0x98], eax-1 ← this + 0x98 = 马数-1
    //
    // 上一版误把 this 当成 RaceSimulateData，读出来全是垃圾（马数=-656021632）。
    unsafe {
        if !arg0.is_null() {
            let p = arg0 as *const u8;
            let n_horse = *(p.add(0xA0) as *const i32);
            let arr = *(p.add(0xD0) as *const usize);
            let arr_len = if arr != 0 { *((arr + 0x18) as *const usize) } else { 0 };
            let f10 = *(p.add(0x10) as *const i32);
            let f2c = *(p.add(0x2C) as *const i32);
            info!("[raceload] Init arg0(RaceSimulateData): 马数={}  数组={:#x}  数组len={}  +0x10={}  +0x2C={}",
                  n_horse, arr, arr_len, f10, f2c);
        } else {
            warn!("[raceload] Init arg0 = NULL");
        }
        if !this.is_null() {
            let q = this as *const u8;
            let o10 = *(q.add(0x10) as *const usize);
            info!("[raceload] Init this(HorseManagerReplay): 输出数组(+0x10)={:#x}", o10);
        }
    }
    type FnN = unsafe extern "C" fn(*mut c_void, *mut c_void) -> isize;
    let f: FnN = std::mem::transmute(ORIG_HR_INIT.load(Ordering::Relaxed));
    let r = f(this as *mut c_void, arg0);
    unsafe {
        if !this.is_null() {
            let q = this as *const u8;
            let h10 = *(q.add(0x10) as *const usize);
            let h18 = *(q.add(0x18) as *const i32);
            let h98 = *(q.add(0x98) as *const i32);
            info!("[raceload] Init 之后: 输出数组={:#x}  +0x18={}  +0x98={}", h10, h18, h98);
        }
    }
    r
}

unsafe extern "C" fn h_create_hrinfo(this: *mut Il2CppObject, a0: *mut c_void,
                                       a1: *mut c_void, a2: *mut c_void) -> isize {
    mark(&N_CHINFO, "CreateHorseRaceInfo");
    type FnN = unsafe extern "C" fn(*mut c_void, *mut c_void, *mut c_void, *mut c_void) -> isize;
    let f: FnN = std::mem::transmute(ORIG_CREATE_HRINFO.load(Ordering::Relaxed));
    f(this as *mut c_void, a0, a1, a2)
}

unsafe extern "C" fn h_check_finish(this: *mut Il2CppObject, a0: *mut c_void) -> u8 {
    mark(&N_FINISH, "CheckFinishOrderValid");
    type FnN = unsafe extern "C" fn(*mut c_void, *mut c_void) -> u8;
    let f: FnN = std::mem::transmute(ORIG_CHECK_FINISH.load(Ordering::Relaxed));
    let r = f(this as *mut c_void, a0);
    let c = N_FINISH.load(Ordering::Relaxed);
    if c <= 3 {
        info!("[raceload] CheckFinishOrderValid 返回 {}", r);
    }
    r
}

unsafe extern "C" fn h_finalize(this: *mut Il2CppObject) {
    mark(&N_FINALIZE, "FinalizeInitModel");
    let f: FnVoid0 = std::mem::transmute(ORIG_FINALIZE_MODEL.load(Ordering::Relaxed));
    f(this)
}

unsafe extern "C" fn h_create_view(this: *mut Il2CppObject) {
    mark(&N_RACEVIEW, "CreateRaceView");
    let f: FnVoid0 = std::mem::transmute(ORIG_CREATE_RACEVIEW.load(Ordering::Relaxed));
    f(this)
}

// --- RaceSimulateReader / Importer 链 ---

unsafe extern "C" fn h_b64_to_sim(this: *mut Il2CppObject, a0: *mut c_void) -> isize {
    mark(&N_B64SIM, "ImporterBase64.Base64ToSimData");
    type FnN = unsafe extern "C" fn(*mut c_void, *mut c_void) -> isize;
    let f: FnN = std::mem::transmute(ORIG_B64_TO_SIM.load(Ordering::Relaxed));
    f(this as *mut c_void, a0)
}

unsafe extern "C" fn h_importer_import(this: *mut Il2CppObject) -> isize {
    mark(&N_IMPIMP, "ImporterBase64.Import");
    type FnN = unsafe extern "C" fn(*mut c_void) -> isize;
    let f: FnN = std::mem::transmute(ORIG_IMPORTER_IMPORT.load(Ordering::Relaxed));
    f(this as *mut c_void)
}

unsafe extern "C" fn h_import_direct(this: *mut Il2CppObject, a0: *mut c_void) -> isize {
    mark(&N_IMPDIR, "Reader.ImportDirect");
    type FnN = unsafe extern "C" fn(*mut c_void, *mut c_void) -> isize;
    let f: FnN = std::mem::transmute(ORIG_IMPORT_DIRECT.load(Ordering::Relaxed));
    f(this as *mut c_void, a0)
}

unsafe extern "C" fn h_post_proc(this: *mut Il2CppObject) -> isize {
    mark(&N_POSTPROC, "Reader._ImportPostProcess");
    type FnN = unsafe extern "C" fn(*mut c_void) -> isize;
    let f: FnN = std::mem::transmute(ORIG_POST_PROC.load(Ordering::Relaxed));
    f(this as *mut c_void)
}

// ---------- 安装 ----------

fn hook_one(
    hachimi: &std::sync::Arc<crate::core::Hachimi>,
    class: *mut Il2CppClass,
    method: &std::ffi::CStr,
    argc: i32,
    detour: usize,
    slot: &AtomicUsize,
    tag: &str,
) {
    let addr = get_method_addr(class, method, argc);
    if addr == 0 {
        warn!("[raceload] {} 地址为空", tag);
        return;
    }
    match hachimi.interceptor.hook(addr, detour) {
        Ok(t) => {
            slot.store(t, Ordering::SeqCst);
            info!("[raceload] hooked {} @ {:#x}", tag, addr);
        }
        Err(e) => error!("[raceload] hook {} 失败: {}", tag, e),
    }
}

pub fn init(umamusume: *const Il2CppImage) {
    // 默认开启（探针开销小：10 个方法，每个只打前 3 次日志）
    // 关闭方式：环境变量 HACHIMI_RACELOAD_PROBE=0
    if std::env::var("HACHIMI_RACELOAD_PROBE").ok().as_deref() == Some("0") {
        return;
    }
    info!("[raceload] === 比赛加载探针启动 ===");

    let hachimi = crate::core::Hachimi::instance();
    let mut n_ok = 0;

    // StandaloneSimulator.RaceSimulateData
    if let Ok(k) = get_class(umamusume, c"StandaloneSimulator", c"RaceSimulateData") {
        hook_one(&hachimi, k, c"Deserialize", 1, h_deser as usize, &ORIG_DESER, "RaceSimulateData.Deserialize");
        hook_one(&hachimi, k, c"DeserializeHeader", 1, h_deser_hdr as usize, &ORIG_DESER_HDR, "RaceSimulateData.DeserializeHeader");
        hook_one(&hachimi, k, c"GetHorseDataNum", 0, h_horse_num as usize, &ORIG_HORSE_NUM, "RaceSimulateData.GetHorseDataNum");
    } else {
        warn!("[raceload] RaceSimulateData 类未找到");
    }

    // Gallop.RaceSimulateReader
    if let Ok(k) = get_class(umamusume, c"Gallop", c"RaceSimulateReader") {
        hook_one(&hachimi, k, c"ImportBase64", 1, h_import_b64 as usize, &ORIG_IMPORT_B64, "Reader.ImportBase64");
        hook_one(&hachimi, k, c"ImportDirect", 1, h_import_direct as usize, &ORIG_IMPORT_DIRECT, "Reader.ImportDirect");
        hook_one(&hachimi, k, c"_ImportPostProcess", 0, h_post_proc as usize, &ORIG_POST_PROC, "Reader._ImportPostProcess");
        n_ok += 3;
    } else {
        warn!("[raceload] RaceSimulateReader 类未找到");
    }

    // Gallop.RaceSimulateImporterBase64 —— 真正解码 base64 的类
    if let Ok(k) = get_class(umamusume, c"Gallop", c"RaceSimulateImporterBase64") {
        hook_one(&hachimi, k, c"Base64ToSimData", 1, h_b64_to_sim as usize, &ORIG_B64_TO_SIM, "Importer.Base64ToSimData");
        hook_one(&hachimi, k, c"Import", 0, h_importer_import as usize, &ORIG_IMPORTER_IMPORT, "Importer.Import");
        n_ok += 2;
    } else {
        warn!("[raceload] RaceSimulateImporterBase64 类未找到");
    }

    // StandaloneSimulator.RaceSimulateFrameData
    if let Ok(k) = get_class(umamusume, c"StandaloneSimulator", c"RaceSimulateFrameData") {
        hook_one(&hachimi, k, c"Deserialize", 3, h_frame_deser as usize, &ORIG_FRAME_DESER, "FrameData.Deserialize");
    } else {
        warn!("[raceload] RaceSimulateFrameData 类未找到");
    }

    // StandaloneSimulator.RaceSimulateHorseFrameData
    if let Ok(k) = get_class(umamusume, c"StandaloneSimulator", c"RaceSimulateHorseFrameData") {
        hook_one(&hachimi, k, c"Deserialize", 2, h_hframe_deser as usize, &ORIG_HORSE_FRAME_DESER, "HorseFrameData.Deserialize");
    } else {
        warn!("[raceload] RaceSimulateHorseFrameData 类未找到");
    }

    // Gallop.RaceHorseManagerReplay
    if let Ok(k) = get_class(umamusume, c"Gallop", c"RaceHorseManagerReplay") {
        hook_one(&hachimi, k, c"Init", 1, h_hr_init as usize, &ORIG_HR_INIT, "RaceHorseManagerReplay.Init");
        hook_one(&hachimi, k, c"CreateHorseRaceInfo", 3, h_create_hrinfo as usize, &ORIG_CREATE_HRINFO, "CreateHorseRaceInfo");
        hook_one(&hachimi, k, c"CheckFinishOrderValid", 1, h_check_finish as usize, &ORIG_CHECK_FINISH, "CheckFinishOrderValid");
    } else {
        warn!("[raceload] RaceHorseManagerReplay 类未找到");
    }

    // Gallop.RaceManagerReplayBase
    if let Ok(k) = get_class(umamusume, c"Gallop", c"RaceManagerReplayBase") {
        hook_one(&hachimi, k, c"FinalizeInitModel", 0, h_finalize as usize, &ORIG_FINALIZE_MODEL, "FinalizeInitModel");
        hook_one(&hachimi, k, c"CreateRaceView", 0, h_create_view as usize, &ORIG_CREATE_RACEVIEW, "CreateRaceView");
    } else {
        warn!("[raceload] RaceManagerReplayBase 类未找到");
    }

    info!("[raceload] === 探针安装完成 ===");
}
