// 套动作 —— A 被替换成 B 时，A 的动作也用 B 的
//
// 动作资源路径实测格式（从 [charres] 日志抄的）：
//   3d/motion/event/body/chara/chr1011_00/anm
//                                ↑ chr{charaId}_{变体}
//
// 只替换路径里的 `chr{四位数}` 段，变体号原样保留 —— 变体对应动作档位
// （胜负服/私服等），跟角色无关，不能一起改。
//
// 开关：config.replace_global_char.replace_motion（默认 true）
//
// hook 点：
//   CharacterBuildPathInfo.GetCharacterHeadModelFilePath 附近不方便，
//   动作走 SwapMotionData：
//     OutgameSwapMotionData.GetOutgameSwapMotionPath(4)  @ 0x56A87D0  过场/主页
//     RaceSwapMotionData.GetBodySwapMotionPath(5)        @ 0x56AB530  比赛身体
//     RaceSwapMotionData.GetFacialSwapMotionPath(5)      @ 0x56AB660  比赛面部
//     RaceSwapMotionData.GetRunningMotionPath(4)         @ 0x56AA9B0  跑姿
//     RaceSwapMotionData.GetGateInMotionPath(4)          @ 0x56AA730  入闸
//
// 这些函数全局调用点很少（Outgame 2 个、Body/Facial 各 3 个），替换安全。

use std::sync::atomic::{AtomicUsize, Ordering};

use crate::{
    core::Hachimi,
    il2cpp::{
        ext::{Il2CppStringExt, StringExt},
        symbols::{get_class, get_method_addr},
        types::*,
    },
};

static ORIG_OUTGAME: AtomicUsize = AtomicUsize::new(0);
static ORIG_RUNNING: AtomicUsize = AtomicUsize::new(0);
static ORIG_GATEIN: AtomicUsize = AtomicUsize::new(0);
static N_HIT: AtomicUsize = AtomicUsize::new(0);
static N_MISS: AtomicUsize = AtomicUsize::new(0);

fn s(p: *mut Il2CppString) -> String {
    if p.is_null() {
        return String::new();
    }
    unsafe { &*p }.as_utf16str().to_string()
}

/// 已停用：动作改写统一由 `StoryMotionPath` 负责。
///
/// 本模块是「资源层替换」时代的产物 —— 那时 `_charaId` 不动、只改加载路径，
/// 所以要把 A 的动作路径改写成 B 的。现在数据层真换人（`_charaId` = B），
/// 路径天然就是 B 的，这里再改只会和 `StoryMotionPath` 方向相反、互相抵消：
///
/// | 机制 | 方向 | 语义 |
/// |---|---|---|
/// | `StoryMotionPath` | `chrB` → `chrA` | 动作沿用原角色（当前方案） |
/// | `MotionReplace` | `chrA` → `chrB` | 动作跟目标角色（旧方案） |
///
/// 两者同时开时结果取决于调用顺序，不可预期。所以这里直接返回 None，
/// hook 仍然装着（便于将来需要时复用），但不再改写任何路径。
fn rewrite_motion_path(_path: &str) -> Option<String> {
    None
}

fn post(ret: *mut Il2CppString) -> *mut Il2CppString {
    let path = s(ret);
    match rewrite_motion_path(&path) {
        Some(newp) => newp.to_il2cpp_string(),
        None => ret,
    }
}

// 签名统一：this, 若干参数 -> String
// Outgame: this, arg1(ptr), arg2(i32), arg3(i32), arg4(i32)
type OutgameFn = extern "C" fn(*mut Il2CppObject, *mut Il2CppObject, i32, i32, i32) -> *mut Il2CppString;
extern "C" fn GetOutgameSwapMotionPath(
    this: *mut Il2CppObject, a1: *mut Il2CppObject, a2: i32, a3: i32, a4: i32,
) -> *mut Il2CppString {
    let orig: OutgameFn = unsafe { std::mem::transmute(ORIG_OUTGAME.load(Ordering::Relaxed)) };
    post(orig(this, a1, a2, a3, a4))
}

// Running/GateIn: this, arg1, arg2, arg3 (4 参)
type FourFn = extern "C" fn(*mut Il2CppObject, *mut Il2CppObject, i32, i32) -> *mut Il2CppString;
extern "C" fn GetRunningMotionPath(
    this: *mut Il2CppObject, a1: *mut Il2CppObject, a2: i32, a3: i32,
) -> *mut Il2CppString {
    let orig: FourFn = unsafe { std::mem::transmute(ORIG_RUNNING.load(Ordering::Relaxed)) };
    post(orig(this, a1, a2, a3))
}

extern "C" fn GetGateInMotionPath(
    this: *mut Il2CppObject, a1: *mut Il2CppObject, a2: i32, a3: i32,
) -> *mut Il2CppString {
    let orig: FourFn = unsafe { std::mem::transmute(ORIG_GATEIN.load(Ordering::Relaxed)) };
    post(orig(this, a1, a2, a3))
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
        warn!("[motion] {} 地址为空", tag);
        return;
    }
    match h.interceptor.hook(addr, detour) {
        Ok(t) => {
            slot.store(t, Ordering::SeqCst);
            info!("[motion] hooked {} @ {:#x}", tag, addr);
        }
        Err(e) => error!("[motion] hook {} 失败: {}", tag, e),
    }
}

pub fn init(umamusume: *const Il2CppImage) {
    let h = Hachimi::instance();

    if let Ok(k) = get_class(umamusume, c"Gallop", c"OutgameSwapMotionData") {
        hook_one(&h, k, c"GetOutgameSwapMotionPath", 4,
                 GetOutgameSwapMotionPath as *const () as usize, &ORIG_OUTGAME, "Outgame.SwapMotionPath");
    }
    if let Ok(k) = get_class(umamusume, c"Gallop", c"RaceSwapMotionData") {
        hook_one(&h, k, c"GetRunningMotionPath", 4,
                 GetRunningMotionPath as *const () as usize, &ORIG_RUNNING, "Race.RunningMotionPath");
        hook_one(&h, k, c"GetGateInMotionPath", 4,
                 GetGateInMotionPath as *const () as usize, &ORIG_GATEIN, "Race.GateInMotionPath");
    }
    // ★ 四个方法分属两个类（typedump 实测）：
    //     Gallop.RaceSwapMotionData     GetRunningMotionPath(4) @ 0x56AA9B0
    //                                   GetGateInMotionPath(4)  @ 0x56AA730
    //     Gallop.SetCuttSwapMotionData  GetBodySwapMotionPath(5)   @ 0x56AB530
    //                                   GetFacialSwapMotionPath(5) @ 0x56AB660
    //   之前把 Body/Facial 也挂在 RaceSwapMotionData 上，get_method_addr 找不到 →
    //   地址为空 → 身体动作和面部表情完全没重定向，只剩跑姿和入闸生效。
    // ★ 不要 hook SetCuttSwapMotionData 的这两个方法（已撤）。
    //
    //   GetBodySwapMotionPath / GetFacialSwapMotionPath 是 5 参数方法，
    //   反汇编实测第 5 个参数从 [rsp+0x88] 读取：
    //     0x56AB59A  mov r9, qword ptr [rsp + 0x88]
    //     0x56AB5D0  call TryGetSwapMotion
    //
    //   用 MinHook 挂它时，trampoline 的栈布局和原函数预期不一致，
    //   第 5 参数读到垃圾值，TryGetSwapMotion 内部 call 0x1CF6330 直接崩。
    //   崩溃栈实测：
    //     +0x23F SetCuttSwapMotionData::TryGetSwapMotion     ← 崩在这
    //     +0xA5  SetCuttSwapMotionData::GetBodySwapMotionPath
    //     +0xAB  CutInSwapMotionPathFinder::TryGetBodySwapMotionPath
    //     +0x26E SetCutInCharaTypeMotionLoader::RegisterDownload
    //     ...（剧情场景切换协程 RegisterDownloadFromTimeline）
    //
    //   剧情场景切换（RegisterDownloadFromTimeline）会走这条链，
    //   所以一进剧情就崩。保留 hook 只会让游戏进不去剧情。
    //   动作保留靠 `keep_original_motion`（不动 _motionDressId）实现，不需要这里。
}
