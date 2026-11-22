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
    cr.data
        .iter()
        .find(|e| e.new_char_id == chara_id && e.orig_char_id > 0)
        .map(|e| e.orig_char_id)
        .unwrap_or(chara_id)
}

type BasePathFn = extern "C" fn(
    chara_id: i32,
    sub_id: i32,
    anim_command: *mut Il2CppObject,
) -> *mut Il2CppString;

extern "C" fn GetEventCharaMotionBasePath(
    chara_id: i32,
    sub_id: i32,
    anim_command: *mut Il2CppObject,
) -> *mut Il2CppString {
    let use_id = map_to_orig(chara_id);
    let orig: BasePathFn = unsafe { std::mem::transmute(ORIG_BASE_PATH.load(Ordering::Relaxed)) };
    let ret = orig(use_id, sub_id, anim_command);

    if use_id != chara_id {
        let n = LOGGED.fetch_add(1, Ordering::Relaxed);
        if n < 10 {
            let path = if ret.is_null() {
                String::new()
            } else {
                unsafe { &*ret }.as_utf16str().to_string()
            };
            info!("[story-motion] chara {} -> {} : {}", chara_id, use_id, path);
        }
    }

    ret
}

type PersonalityFn = extern "C" fn(chara_id: i32) -> i32;

extern "C" fn GetRaceRunMotionPersonality(chara_id: i32) -> i32 {
    let use_id = map_to_orig(chara_id);
    let orig: PersonalityFn = unsafe { std::mem::transmute(ORIG_PERSONALITY.load(Ordering::Relaxed)) };
    orig(use_id)
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
