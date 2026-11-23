// 剧情 / 比赛的动作路径：替换角色后，原角色的专属动作在新角色上不存在，
// `EventTimelineModelController.LoadMotionClip` 拿到 null 会
// `GallopUtil.GotoTitleOnError(Localize.Text(1448))` —— 演出中途弹 Error0003 回标题。
//
// 这里把「动作资源归属」换回原角色：模型是替换后的，动作沿用原角色的 clip
// （与 keep_original_motion 的语义一致），路径一定存在。

use std::sync::atomic::{AtomicUsize, Ordering};

use crate::{
    core::Hachimi,
    il2cpp::{
        ext::Il2CppStringExt,
        symbols::{get_class, get_method_addr},
        types::*,
    },
};

static ORIG_BASE_PATH: AtomicUsize = AtomicUsize::new(0);
static ORIG_PERSONALITY: AtomicUsize = AtomicUsize::new(0);
static PERSONALITY_LOGGED: AtomicUsize = AtomicUsize::new(0);
static LOGGED: AtomicUsize = AtomicUsize::new(0);

/// 把一个「替换目标角色 ID」映射回原角色（未命中则原样返回）。
///
/// **不受 `keep_original_motion` 控制**。剧情/比赛里的动作分两种来源
/// （`StoryMotionInfo.GetMotionPathStoryTimeline` 按 `animCommand+0x20` 分支）：
///
/// | 分支 | 路径 | 带角色 ID |
/// |---|---|---|
/// | `num2 == 0 && num3 == -2` → `GetEventCharaMotionBasePath` | `3d/Motion/Event/Body/Chara/chr{id}_00/anm_eve_chr{id}_00_*` | **是** |
/// | `num2 == 1/2` → `ResourcePath.GetEventPlusMotionPath` | `3d/Motion/Event/Body/Type00/anm_eve_type00_*` | 否（共享） |
///
/// 共享分支谁都能播（实测 1001 的动作换到任何角色都正常）；
/// 角色专属分支是按原角色制作的 clip，目标角色没有 → 加载为 null →
/// 动作退化成静止/错位，剧情里还会走 `LoadMotionClip` 的
/// `GotoTitleOnError`。所以这里必须无条件映射回原角色。
///
/// 早先加了 `keep_original_motion` 前置条件，开关为 false 时直接放行，
/// 于是请求的是目标角色的专属 clip —— 这就是「1001 行、1003 不行」的原因。
fn map_to_orig(chara_id: i32) -> i32 {
    let cfg = Hachimi::instance().config.load();
    let cr = &cfg.replace_global_char;
    if !cr.enable {
        return chara_id;
    }

    // 总开关：复用「同时替换动作」（`replace_motion`）。
    //
    // 语义正好对应：那个开关原先只管 MotionReplace 的路径改写（swap motion），
    // 现在它同时控制「动作沿用原角色」这一族 hook。关掉 = 动作完全跟目标角色
    // （缺资源就播不出来），打开 = 动作借用原角色。
    if !cr.replace_motion {
        return chara_id;
    }

    // 实验模式：不按控制器类型设场景白名单；所有场景只要命中配置的角色映射，
    // 就将动作归属 ID 映射回原角色。由 replace_motion 总开关整体关闭/恢复。

    cr.data
        .iter()
        .find(|e| e.new_char_id == chara_id && e.orig_char_id > 0 && e.orig_char_id != chara_id)
        .map(|e| e.orig_char_id)
        .unwrap_or(chara_id)
}

type BasePathFn = extern "C" fn(
    chara_id: i32,
    sub_id: i32,
    anim_command: *mut Il2CppObject,
) -> *mut Il2CppString;

/// 诊断：动作来源标记（`animCommand+0x20`，0=角色专属/通用二选，1/2=共享 Type00，3=尾巴）。
unsafe fn anim_source(anim_command: *mut Il2CppObject) -> i32 {
    if anim_command.is_null() {
        return -1;
    }
    *((anim_command as *const u8).add(0x20) as *const i32)
}

/// 诊断：`animCommand+0x24`（-2 = 走 GetEventCharaMotionBasePath 角色专属分支）。
unsafe fn anim_flag(anim_command: *mut Il2CppObject) -> i32 {
    if anim_command.is_null() {
        return 0;
    }
    *((anim_command as *const u8).add(0x24) as *const i32)
}

extern "C" fn GetEventCharaMotionBasePath(
    chara_id: i32,
    sub_id: i32,
    anim_command: *mut Il2CppObject,
) -> *mut Il2CppString {
    let use_id = map_to_orig(chara_id);
    let orig: BasePathFn = unsafe { std::mem::transmute(ORIG_BASE_PATH.load(Ordering::Relaxed)) };
    let ret = orig(use_id, sub_id, anim_command);

    // 诊断：每次调用都记入参 + 返回路径（前 200 次，便于对齐「哪条动作被谁请求」）。
    // 映射与未映射都打，才能区分「没进这个分支」和「进了但没映射」。
    if use_id != chara_id {
        let n = LOGGED.fetch_add(1, Ordering::Relaxed);
        if n < 40 {
            let path = if ret.is_null() {
                "<null>".to_string()
            } else {
                unsafe { &*ret }.as_utf16str().to_string()
            };
            let (src, flag) = unsafe { (anim_source(anim_command), anim_flag(anim_command)) };
            info!(
                "[story-motion] base chara {} -> {} sub={} src={} flag={} : {}",
                chara_id, use_id, sub_id, src, flag, path
            );
        }
    }

    ret
}

type PersonalityFn = extern "C" fn(chara_id: i32) -> i32;

extern "C" fn GetRaceRunMotionPersonality(chara_id: i32) -> i32 {
    let use_id = map_to_orig(chara_id);
    let orig: PersonalityFn = unsafe { std::mem::transmute(ORIG_PERSONALITY.load(Ordering::Relaxed)) };
    let ret = orig(use_id);
    if use_id != chara_id {
        let n = PERSONALITY_LOGGED.fetch_add(1, Ordering::Relaxed);
        if n < 20 {
            info!("[story-motion] personality chara {} -> {} => {}", chara_id, use_id, ret);
        }
    }
    ret
}

static ORIG_EVENT_CHARA: AtomicUsize = AtomicUsize::new(0);
static EVENT_CHARA_LOGGED: AtomicUsize = AtomicUsize::new(0);

type EventCharaFn = extern "C" fn(
    chara_id: i32,
    motion_name: *mut Il2CppString,
    suffix: *mut Il2CppString,
    is_mirror: bool,
) -> *mut Il2CppString;

/// `ResourcePath.GetEventCharaMotionPath(charaId, motionName, suffix, isMirror)`。
///
/// 这是 **`SimpleModelController`**（剧情 `ctrl=12` 用的就是它）拼动作路径的地方，
/// 前面 hook 的三个函数都不覆盖它 —— 这就是「剧情里 2005 一次都没进 hook」的原因。
extern "C" fn GetEventCharaMotionPath(
    chara_id: i32,
    motion_name: *mut Il2CppString,
    suffix: *mut Il2CppString,
    is_mirror: bool,
) -> *mut Il2CppString {
    // 二分开关：HACHIMI_NO_EVENTCHARA=1 时完全绕过本 hook（不改参数、不打日志）。
    static DISABLED: std::sync::atomic::AtomicBool =
        std::sync::atomic::AtomicBool::new(false);
    static CHECKED: std::sync::atomic::AtomicBool = std::sync::atomic::AtomicBool::new(false);
    if !CHECKED.swap(true, Ordering::AcqRel) {
        let off = std::env::var("HACHIMI_NO_EVENTCHARA").ok().as_deref() == Some("1");
        DISABLED.store(off, Ordering::Release);
        if off {
            warn!("[story-motion] GetEventCharaMotionPath 已禁用（HACHIMI_NO_EVENTCHARA=1）");
        }
    }
    if DISABLED.load(Ordering::Acquire) {
        let orig: EventCharaFn = unsafe { std::mem::transmute(ORIG_EVENT_CHARA.load(Ordering::Relaxed)) };
        return orig(chara_id, motion_name, suffix, is_mirror);
    }

    let use_id = map_to_orig(chara_id);
    let orig: EventCharaFn = unsafe { std::mem::transmute(ORIG_EVENT_CHARA.load(Ordering::Relaxed)) };
    let ret = orig(use_id, motion_name, suffix, is_mirror);

    if use_id != chara_id {
        let n = EVENT_CHARA_LOGGED.fetch_add(1, Ordering::Relaxed);
        if n < 40 {
            let path = if ret.is_null() {
                "<null>".to_string()
            } else {
                unsafe { &*ret }.as_utf16str().to_string()
            };
            let name = if motion_name.is_null() {
                "<null>".to_string()
            } else {
                unsafe { &*motion_name }.as_utf16str().to_string()
            };
            info!(
                "[story-motion] event-chara chara {} -> {} name={} mirror={} : {}",
                chara_id, use_id, name, is_mirror, path
            );
        }
    }

    ret
}

static ORIG_OVERRIDE: AtomicUsize = AtomicUsize::new(0);
static OVERRIDE_LOGGED: AtomicUsize = AtomicUsize::new(0);

type OverridePathFn = extern "C" fn(
    chara_id: i32,
    sub_id: i32,
    motion_name: *mut Il2CppString,
) -> *mut Il2CppString;

/// `ResourcePath.GetCharaOverrideMotionPath(charaId, subId, motionName)`。
///
/// 剧情（ctrl=12 Simple）的 layerIndex 落在 12..17，`EventTimelineModelController.LoadMotion`
/// 对这一段走的是本函数，**不经过** `StoryMotionInfo`：
///
/// | layerIndex | 用哪个函数 |
/// |---|---|
/// | 1 | `StoryMotionInfo.GetMotionPathStoryTimeline` |
/// | >15 | `StoryMotionInfo.GetMotionPathStoryTimeline` |
/// | 16..17 | `ResourcePath.GetCharaOverrideMotionPath` |
/// | 12..15 | `ResourcePath.GetCharaOverrideMotionPath` |
/// | 其它 | `ResourcePath.GetOverrideMotionPath`（路径里没有角色 ID） |
///
/// 它同样把 charaId 拼进 `3d/Motion/Event/Body/Chara/chr{id}_00/...`，
/// 所以替换后目标角色缺这条 clip 就播不出来 —— 这就是「剧情动作不出来」的真因。
extern "C" fn GetCharaOverrideMotionPath(
    chara_id: i32,
    sub_id: i32,
    motion_name: *mut Il2CppString,
) -> *mut Il2CppString {
    let use_id = map_to_orig(chara_id);
    let orig: OverridePathFn = unsafe { std::mem::transmute(ORIG_OVERRIDE.load(Ordering::Relaxed)) };
    let ret = orig(use_id, sub_id, motion_name);

    if use_id != chara_id {
        let n = OVERRIDE_LOGGED.fetch_add(1, Ordering::Relaxed);
        if n < 40 {
            let path = if ret.is_null() {
                "<null>".to_string()
            } else {
                unsafe { &*ret }.as_utf16str().to_string()
            };
            let name = if motion_name.is_null() {
                "<null>".to_string()
            } else {
                unsafe { &*motion_name }.as_utf16str().to_string()
            };
            info!(
                "[story-motion] override chara {} -> {} sub={} name={} : {}",
                chara_id, use_id, sub_id, name, path
            );
        }
    }

    ret
}

fn hook_one(
    class: *mut Il2CppClass,
    name: &std::ffi::CStr,
    argc: i32,
    detour: usize,
    slot: &AtomicUsize,
    tag: &str,
) {
    let addr = get_method_addr(class, name, argc);
    if addr == 0 {
        warn!("[story-motion] {} 地址为空", tag);
        return;
    }
    let h = Hachimi::instance();
    match h.interceptor.hook(addr, detour) {
        Ok(t) => {
            slot.store(t, Ordering::SeqCst);
            info!("[story-motion] hooked {} @ {:#x}", tag, addr);
        }
        Err(e) => error!("[story-motion] hook {} 失败: {}", tag, e),
    }
}



pub fn init(umamusume: *const Il2CppImage) {

    if let Ok(k) = get_class(umamusume, c"Gallop", c"ResourcePath") {
        hook_one(
            k,
            c"GetEventCharaMotionPath",
            4,
            GetEventCharaMotionPath as *const () as usize,
            &ORIG_EVENT_CHARA,
            "ResourcePath.GetEventCharaMotionPath",
        );
        hook_one(
            k,
            c"GetCharaOverrideMotionPath",
            3,
            GetCharaOverrideMotionPath as *const () as usize,
            &ORIG_OVERRIDE,
            "ResourcePath.GetCharaOverrideMotionPath",
        );
    } else {
        warn!("[story-motion] ResourcePath 未找到");
    }

    if let Ok(k) = get_class(umamusume, c"Gallop", c"StoryMotionInfo") {
        hook_one(
            k,
            c"GetEventCharaMotionBasePath",
            3,
            GetEventCharaMotionBasePath as *const () as usize,
            &ORIG_BASE_PATH,
            "StoryMotionInfo.GetEventCharaMotionBasePath",
        );
    } else {
        warn!("[story-motion] StoryMotionInfo 未找到");
    }

    if let Ok(k) = get_class(umamusume, c"Gallop", c"ModelLoader") {
        // ★ 安卓不要 hook 这个函数。
        //
        //   il2cpp 里它是 8 字节的 tail-call thunk：
        //     0x9983528  mov w1,#1 ; b 0x9983474   GetRaceRunMotionPersonality
        //     0x9983530  mov w1,#4 ; b 0x9983474   GetRaceOverRunMotionPersonality
        //     0x9983538  mov w1,#0 ; b 0x9983474   GetRaceGateInMotionPersonality
        //   三者紧邻，每个只有 2 条指令。dobby 在 ARM64 上要写 16 字节跳转
        //   （ldr x16,#8; br x16; .quad），会把后面两个函数整个覆盖掉 ——
        //   MasterDataUtil.InitChara 调 GetRaceOverRunMotionPersonality 时
        //   执行到被覆盖的字节，memcpy 越界崩溃（fault addr 0x792ffffff0）。
        //   Windows 用 minhook 的 5 字节 jmp，不越界，所以只在安卓出问题。
        #[cfg(target_os = "windows")]
        hook_one(
            k,
            c"GetRaceRunMotionPersonality",
            1,
            GetRaceRunMotionPersonality as *const () as usize,
            &ORIG_PERSONALITY,
            "ModelLoader.GetRaceRunMotionPersonality",
        );
    }

}
