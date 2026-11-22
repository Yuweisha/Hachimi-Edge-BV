use std::sync::atomic::{AtomicBool, Ordering};

use crate::{
    core::{hachimi::GlobalCharReplaceConfig, Hachimi},
    il2cpp::symbols::Thread,
    il2cpp::{
        sql,
        symbols::{get_field_from_name, get_field_value, get_method_addr, set_field_value},
        types::*,
    },
};

#[repr(i32)]
#[derive(Clone, Copy, PartialEq, Eq)]
#[allow(dead_code)]
pub enum UmaControllerType {
    Default = 0x0,
    Race = 0x1,
    Training = 0x2,
    EventTimeline = 0x3,
    Live = 0x4,
    LiveTheater = 0x5,
    HomeStand = 0x6,
    HomeTalk = 0x7,
    HomeWalk = 0x8,
    CutIn = 0x9,
    TrainingTop = 0xa,
    SingleRace = 0xb,
    Simple = 0xc,
    Mini = 0xd,
    Paddock = 0xe,
    Champions = 0xf,
    Orig = 0x1919810,
}

fn is_replacable(controller_type: i32) -> bool {
    if controller_type == UmaControllerType::Orig as i32 {
        return false;
    }
    !matches!(controller_type, 0x0 | 0x7 | 0x8 | 0xd)
}

fn orig_allowed(allow_orig: bool, controller_type: i32) -> bool {
    allow_orig || controller_type != UmaControllerType::Orig as i32
}

pub fn find_replacement(char_replace: &GlobalCharReplaceConfig, chara_id: i32, mini: bool) -> Option<(i32, i32)> {
    char_replace.data.iter()
        .find(|e| e.orig_char_id == chara_id && (!mini || e.replace_mini))
        .map(|e| (e.new_char_id, e.new_cloth_id))
}

const MINI_FALLBACK_DRESS_ID: i32 = 2;

fn dress_belongs_to(dress_id: i32, chara_id: i32) -> bool {
    match sql::get_dress_chara_id(dress_id) {
        0 => true,
        owner => owner == chara_id
    }
}

fn align_dress_with_chara(dress_id: &mut i32, chara_id: i32) {
    if *dress_id < 100000 {
        return;
    }

    if dress_belongs_to(*dress_id, chara_id) {
        return;
    }
    let fallback = chara_id * 100 + 1;
    if sql::get_dress_info(fallback).is_some() {
        warn!(
            "dressId {} does not belong to chara {}! Replace to {}.",
            *dress_id, chara_id, fallback
        );
        *dress_id = fallback;
    } else {
        warn!(
            "dressId {} does not belong to chara {} and {} is missing!",
            *dress_id, chara_id, fallback
        );
    }
}

const SHARED_UNIVERSAL_DRESSES: &[i32] = &[3, 9];

fn is_universal_dress(dress_id: i32) -> bool {
    if sql::is_general_purpose_dress(dress_id) {
        return true;
    }
    SHARED_UNIVERSAL_DRESSES.contains(&dress_id)
}

pub fn auto_pick_dress(orig_dress_id: i32, target_chara_id: i32, preferred_dress_id: i32) -> i32 {
    let base = target_chara_id * 100;

    if orig_dress_id < 100000 {
        if is_universal_dress(orig_dress_id) {
            return orig_dress_id;
        }
        let fallback = base + 1;
        if sql::get_dress_info(fallback).is_some() {
            return fallback;
        }
        return orig_dress_id;
    }

    let want_head_sub = sql::get_head_id_from_dress_id(orig_dress_id);

    if want_head_sub == 0 && sql::get_dress_chara_id(preferred_dress_id) == target_chara_id {
        return preferred_dress_id;
    }

    if let Some(d) = (base..base + 100).find(|d| {
        sql::get_dress_chara_id(*d) == target_chara_id
            && sql::get_head_id_from_dress_id(*d) == want_head_sub
    }) {
        return d;
    }

    let fallback = base + 1;
    if sql::get_dress_info(fallback).is_some() {
        return fallback;
    }

    orig_dress_id
}

pub fn auto_pick_dress_for_track(
    orig_dress_id: i32,
    target_chara_id: i32,
    preferred_dress_id: i32,
) -> i32 {
    let base = target_chara_id * 100;
    if orig_dress_id < 100000 {
        if is_universal_dress(orig_dress_id) {
            return orig_dress_id;
        }
        let fallback = base + 1;
        if sql::get_dress_info(fallback).is_some() {
            return fallback;
        }
        return orig_dress_id;
    }

    let want_head_sub = sql::get_head_id_from_dress_id(orig_dress_id);
    if want_head_sub == 0 && sql::get_dress_chara_id(preferred_dress_id) == target_chara_id {
        return preferred_dress_id;
    }
    if let Some(d) = (base..base + 100).find(|d| {
        sql::get_dress_chara_id(*d) == target_chara_id
            && sql::get_head_id_from_dress_id(*d) == want_head_sub
    }) {
        return d;
    }
    let fallback = base + 1;
    if sql::get_dress_info(fallback).is_some() {
        return fallback;
    }
    orig_dress_id
}

static CHARA_PRELOAD_SCHEDULED: AtomicBool = AtomicBool::new(false);

fn chara_table_ready() -> bool {
    if sql::is_chara_data_ready() {
        return true;
    }

    if !CHARA_PRELOAD_SCHEDULED.swap(true, Ordering::AcqRel) {
        Thread::main_thread().schedule(|| {
            if !sql::preload_chara_data() {
                debug!("[replace] master.mdb 还没就绪，角色表稍后再加载");
            }
            CHARA_PRELOAD_SCHEDULED.store(false, Ordering::Release);
        });
    }

    false
}

static DRESS_PRELOAD_SCHEDULED: AtomicBool = AtomicBool::new(false);

fn dress_table_ready() -> bool {
    if sql::is_dress_info_ready() {
        return true;
    }

    if !DRESS_PRELOAD_SCHEDULED.swap(true, Ordering::AcqRel) {
        Thread::main_thread().schedule(|| {
            if !sql::preload_dress_info() {
                debug!("[replace] master.mdb 还没就绪，服装表稍后再加载");
            }
            DRESS_PRELOAD_SCHEDULED.store(false, Ordering::Release);
        });
    }

    false
}

/// 把目标角色的体型参数写进 CharacterBuildInfo。
///
/// 不同角色的 height/bust/skin/socks 不同，只换 chara_id 会让模型用原角色的比例。
fn sync_body_shape(this: *mut Il2CppObject, chara_id: i32) {
    let Some((height, bust, skin, socks, _scale, _shape)) = sql::get_chara_body_shape(chara_id) else {
        return;
    };
    unsafe {
        if !HEIGHT_TYPE_FIELD.is_null() {
            set_field_value(this, HEIGHT_TYPE_FIELD, &height);
        }
        if !BODY_SIZE_FIELD.is_null() {
            set_field_value(this, BODY_SIZE_FIELD, &height);   // bodySize 与 heightType 同源
        }
        if !BUST_TYPE_FIELD.is_null() {
            set_field_value(this, BUST_TYPE_FIELD, &bust);
        }
        if !SKIN_TYPE_FIELD.is_null() {
            set_field_value(this, SKIN_TYPE_FIELD, &skin);
        }
        if !SOCKS_TYPE_FIELD.is_null() {
            set_field_value(this, SOCKS_TYPE_FIELD, &socks);
        }
    }
}

fn replace_char_controller(
    chara_id: &mut i32, dress_id: &mut i32, head_id: &mut i32,
    controller_type: i32, allow_orig: bool
) -> bool {
    let hachimi = Hachimi::instance();
    let config = hachimi.config.load();
    let char_replace = &config.replace_global_char;

    if !char_replace.enable {
        return false;
    }

    if !dress_table_ready() {
        return false;
    }

    if !char_replace.replace_universal && !char_replace.auto_dress && *dress_id < 100000 {
        return false;
    }

    debug!(
        "[replace] 进入 ctrl={} chara={} dress={} head={}",
        controller_type, *chara_id, *dress_id, *head_id
    );

    if controller_type == UmaControllerType::Mini as i32 {
        if let Some((new_chara_id, new_dress_id)) = find_replacement(char_replace, *chara_id, true) {
            if sql::get_dress_have_mini(new_dress_id) {
                *chara_id = new_chara_id;
                *dress_id = new_dress_id;
                align_dress_with_chara(dress_id, new_chara_id);
                *head_id = sql::get_head_id_from_dress_id(*dress_id);
                return true;
            }
            warn!("dressId: {} does not have mini character!", new_dress_id);
            return false;
        }

        if !sql::get_dress_have_mini(*dress_id) {
            warn!("dressId: {} does not have mini character! Replace to {}.", *dress_id, MINI_FALLBACK_DRESS_ID);
            *dress_id = MINI_FALLBACK_DRESS_ID;
            return true;
        }
        return false;
    }

    if !is_replacable(controller_type) || !orig_allowed(allow_orig, controller_type) {
        return false;
    }

    if controller_type == UmaControllerType::EventTimeline as i32
        && crate::il2cpp::hook::umamusume::StoryTimelineData::SKIP_CUTSCENE_REPLACE.load(Ordering::Acquire)
    {
        return false;
    }

    if !char_replace.replace_in_cutscene
        && matches!(
            controller_type,
            x if x == UmaControllerType::EventTimeline as i32
                || x == UmaControllerType::CutIn as i32
        )
    {
        return false;
    }

    // 比赛场景（ctrl=1）默认不替换：
    //   实测替换后画面出现彩色横条/色块，而且会持续污染后续场景，直到重开游戏才恢复。
    //   需要换比赛里的角色时把 config 的 replace_in_race 设为 true。
    if !char_replace.replace_in_race
        && controller_type == UmaControllerType::Race as i32
    {
        return false;
    }

    if *chara_id == 9001 && controller_type == UmaControllerType::HomeStand as i32 {
        return false;
    }

    if let Some((new_chara_id, new_dress_id)) = find_replacement(char_replace, *chara_id, false) {
        // ★ mini 场景（ctrl=13）必须用「有 mini 模型」的服装。
        //   实测（hachimi.log）：dress 4/5/6 -> 904701，而 dress_data[904701].have_mini=0，
        //   mini 资源（3d/chara/mini/{mchr,mbdy,mtail}）加载不到 → 模型和图标全空白 → 软死。
        //   所以这里查目标服装的 have_mini，为 0 就跳过替换（保持原角色）。
        //   NPC（2000 段）和特殊角色（9000 段）在普通/Live 场景能正常替换，不能一刀切排除。
        if controller_type == UmaControllerType::Mini as i32
            && !sql::get_dress_have_mini(new_dress_id)
        {
            warn!(
                "[replace] mini 场景：目标服装 {}（角色 {}）没有 mini 模型，跳过替换",
                new_dress_id, new_chara_id
            );
            return false;
        }
        // 注：这里原来有个「dress_id < 1000 就当 mini 专用、非 mini 场景跳过」的判断，
        //     是错的。master.mdb 里 id < 1000 的 65 条 dress 全部 chara_id = 0，
        //     是通用服装（校服、Live 服等），不是 mini 专用。
        //     比如 dress_id=2 是通用校服（body_type=2 / use_live=1 / use_home=1），
        //     被这个判断挡掉后 _dressId 停留在 2，而资源层照样把 head 换成目标角色，
        //     骨架和资源对不上 → 剧情/Live 卡在装配阶段。
        if crate::il2cpp::hook::umamusume::SceneManager::is_race_scene_family()
            && (!chara_table_ready() || !sql::is_playable_chara(new_chara_id))
        {
            return false;
        }
        let orig = (*chara_id, *dress_id, *head_id);
        CURRENT_ORIG_DRESS.store(orig.1, Ordering::Release);
        *chara_id = new_chara_id;
        *dress_id = if char_replace.auto_dress {
            auto_pick_dress(orig.1, new_chara_id, new_dress_id)
        } else {
            new_dress_id
        };
        align_dress_with_chara(dress_id, new_chara_id);
        *head_id = sql::get_head_id_from_dress_id(*dress_id);
        debug!(
            "[replace] ctrl={} chara {}->{} dress {}->{} head {}->{}",
            controller_type, orig.0, *chara_id, orig.1, *dress_id, orig.2, *head_id
        );
        return true;
    }

    false
}

pub static CURRENT_CONTROLLER_TYPE: std::sync::atomic::AtomicI32 =
    std::sync::atomic::AtomicI32::new(-1);

/// 替换前的原 dress_id，供 `keep_original_motion` 使用
pub static CURRENT_ORIG_DRESS: std::sync::atomic::AtomicI32 = std::sync::atomic::AtomicI32::new(0);

static mut CHARA_ID_FIELD: *mut FieldInfo = 0 as _;
static mut CARD_ID_FIELD: *mut FieldInfo = 0 as _;
static mut DRESS_ID_FIELD: *mut FieldInfo = 0 as _;
static mut CONTROLLER_TYPE_FIELD: *mut FieldInfo = 0 as _;
static mut HEAD_MODEL_SUB_ID_FIELD: *mut FieldInfo = 0 as _;
static mut MOTION_DRESS_ID_FIELD: *mut FieldInfo = 0 as _;
static mut USE_DRESS_DATA_HEAD_FIELD: *mut FieldInfo = 0 as _;
static mut BODY_MODEL_SUB_ID_FIELD: *mut FieldInfo = 0 as _;
static mut MOTION_BODY_MODEL_SUB_ID_FIELD: *mut FieldInfo = 0 as _;
// 体型参数（不同角色的身高档/胸围/肤色/袜子类型不同，不同步会导致模型比例错乱）
static mut HEIGHT_TYPE_FIELD: *mut FieldInfo = 0 as _;
static mut BODY_SIZE_FIELD: *mut FieldInfo = 0 as _;
static mut BUST_TYPE_FIELD: *mut FieldInfo = 0 as _;
static mut SKIN_TYPE_FIELD: *mut FieldInfo = 0 as _;
static mut SOCKS_TYPE_FIELD: *mut FieldInfo = 0 as _;


type CharacterBuildInfoRebuildFn = extern "C" fn(this: *mut Il2CppObject);
extern "C" fn CharacterBuildInfo_Rebuild(this: *mut Il2CppObject) {
    unsafe {
        if !CHARA_ID_FIELD.is_null() {
            let mut chara_id: i32 = get_field_value(this, CHARA_ID_FIELD);
            let mut dress_id: i32 = get_field_value(this, DRESS_ID_FIELD);
            let controller_type: i32 = get_field_value(this, CONTROLLER_TYPE_FIELD);
            CURRENT_CONTROLLER_TYPE.store(controller_type, Ordering::Release);
            let mut head_model_sub_id: i32 = get_field_value(this, HEAD_MODEL_SUB_ID_FIELD);


            let replaced = replace_char_controller(&mut chara_id, &mut dress_id, &mut head_model_sub_id, controller_type, false);
            if replaced {
                set_field_value(this, CHARA_ID_FIELD, &chara_id);
                set_field_value(this, DRESS_ID_FIELD, &dress_id);
                set_field_value(this, HEAD_MODEL_SUB_ID_FIELD, &head_model_sub_id);
                // 游戏默认按 dress_data[dressId].head_sub_id 反推头部变体；dress 换掉之后
                // 那个值仍指向原服装的子类型（100230 -> 30），导致资源加载 chr{原角色}_30
                // 与替换后的骨架对不上。清 0 让游戏只用我们写好的 _headModelSubId。
                if !USE_DRESS_DATA_HEAD_FIELD.is_null() {
                    let no = 0i32;
                    set_field_value(this, USE_DRESS_DATA_HEAD_FIELD, &no);
                }

                // 动作 type 不做替换：剧情动作是按原角色制作的 clip，而 `chara_type` 是
                // 目标角色的动作族；两者一起换会出现「clip 是 A 的、rig/type 是 B 的」，
                // 表现为动作错位。动作要么整套跟原角色（现状），要么整套跟目标角色
                // （目标缺专属 clip 时只能回退，见 MotionReplace / StoryMotionPath）。
                // 体型参数同步：不同角色的 height/bust/skin/socks 不同，
                // 只换 chara_id 会让模型用原角色的比例，看起来「变了个样子」。
                sync_body_shape(this, chara_id);

                // 动作来源：默认跟随替换后的 dress（换成新角色动作）。
                // 打开 keep_original_motion 时保留原 dress —— 模型换新、动作沿用旧的。
                // 原 dress 值由 `replace_char_controller` 在改之前存进 CURRENT_ORIG_DRESS。
                let keep_motion = Hachimi::instance()
                    .config
                    .load()
                    .replace_global_char
                    .keep_original_motion;
                let motion_dress = if keep_motion {
                    CURRENT_ORIG_DRESS.load(Ordering::Acquire)
                } else {
                    dress_id
                };
                set_field_value(this, MOTION_DRESS_ID_FIELD, &motion_dress);
                let card_id = sql::get_first_card_id(chara_id);
                let card_id = if card_id > 0 { card_id } else { -1 };
                set_field_value(this, CARD_ID_FIELD, &card_id);
            }
        }
    }

    get_orig_fn!(CharacterBuildInfo_Rebuild, CharacterBuildInfoRebuildFn)(this);
}

type GetRaceDressIdFn = extern "C" fn(this: *mut Il2CppObject, is_apply_dress_change: bool) -> i32;
extern "C" fn GetRaceDressId(this: *mut Il2CppObject, _is_apply_dress_change: bool) -> i32 {
    let ret = get_orig_fn!(GetRaceDressId, GetRaceDressIdFn)(this, false);

    if ret > 100000 && ret <= 999999 {
        let chara_id = if ret / 10000 == 90 { ret % 10000 } else { ret / 100 };
        let mut new_chara_id = chara_id;
        let mut new_dress_id = ret;
        let mut new_head_id = 0;
        if replace_char_controller(&mut new_chara_id, &mut new_dress_id, &mut new_head_id, UmaControllerType::Orig as i32, true) {
            if dress_belongs_to(new_dress_id, chara_id) {
                return new_dress_id;
            }
            debug!(
                "[replace] GetRaceDressId: dress {} 不属于角色 {}，保留原值 {}",
                new_dress_id, chara_id, ret
            );
        }
    }

    ret
}

fn init_character_build_info(umamusume: *const Il2CppImage) {
    get_class_or_return!(umamusume, Gallop, CharacterBuildInfo);

    unsafe {
        CHARA_ID_FIELD = get_field_from_name(CharacterBuildInfo, c"_charaId");
        CARD_ID_FIELD = get_field_from_name(CharacterBuildInfo, c"_cardId");
        DRESS_ID_FIELD = get_field_from_name(CharacterBuildInfo, c"_dressId");
        CONTROLLER_TYPE_FIELD = get_field_from_name(CharacterBuildInfo, c"_controllerType");
        HEAD_MODEL_SUB_ID_FIELD = get_field_from_name(CharacterBuildInfo, c"_headModelSubId");
        MOTION_DRESS_ID_FIELD = get_field_from_name(CharacterBuildInfo, c"_motionDressId");
        USE_DRESS_DATA_HEAD_FIELD = get_field_from_name(CharacterBuildInfo, c"_isUseDressDataHeadModelSubId");
        BODY_MODEL_SUB_ID_FIELD = get_field_from_name(CharacterBuildInfo, c"_bodyModelSubId");
        MOTION_BODY_MODEL_SUB_ID_FIELD = get_field_from_name(CharacterBuildInfo, c"_motionBodyModelSubId");
        HEIGHT_TYPE_FIELD = get_field_from_name(CharacterBuildInfo, c"_heightType");
        BODY_SIZE_FIELD = get_field_from_name(CharacterBuildInfo, c"_bodySize");
        BUST_TYPE_FIELD = get_field_from_name(CharacterBuildInfo, c"_bustType");
        SKIN_TYPE_FIELD = get_field_from_name(CharacterBuildInfo, c"_skinType");
        SOCKS_TYPE_FIELD = get_field_from_name(CharacterBuildInfo, c"_socksType");
    }

    let CharacterBuildInfo_Rebuild_addr = get_method_addr(CharacterBuildInfo, c"Rebuild", 0);
    new_hook!(CharacterBuildInfo_Rebuild_addr, CharacterBuildInfo_Rebuild);

}

fn init_work_single_mode_chara_data(umamusume: *const Il2CppImage) {
    get_class_or_return!(umamusume, Gallop, WorkSingleModeCharaData);

    let GetRaceDressId_addr = get_method_addr(WorkSingleModeCharaData, c"GetRaceDressId", 1);
    new_hook!(GetRaceDressId_addr, GetRaceDressId);
}

pub fn init(umamusume: *const Il2CppImage) {
    init_character_build_info(umamusume);
    init_work_single_mode_chara_data(umamusume);
}
