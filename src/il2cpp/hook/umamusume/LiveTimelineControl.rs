use std::sync::atomic::{AtomicUsize, Ordering};

use crate::{
    core::Hachimi,
    windows::free_camera::{self, CameraScene},
    il2cpp::{
        symbols::{get_class, get_field_from_name, get_method_addr},
        types::*,
    },
};

use super::{Director, LiveTimelineWorkSheet, LiveTimelineKeyPostFilmDataList};

static LIVE_TIMELINE_CONTROL: AtomicUsize = AtomicUsize::new(0);
static SET_CHARACTOR_LOCATOR_ORIG: AtomicUsize = AtomicUsize::new(0);
static INIT_CHARA_MOTION_SEQUENCE_ORIG: AtomicUsize = AtomicUsize::new(0);
static DIRECTOR_GET_PLAY_SONG_ID: AtomicUsize = AtomicUsize::new(0);
static LIVE_LOCATORS_FIELD: AtomicUsize = AtomicUsize::new(0);
static LIVE_MOTION_SEQUENCES_FIELD: AtomicUsize = AtomicUsize::new(0);
static DIRECTOR_CHARACTER_LIST_FIELD: AtomicUsize = AtomicUsize::new(0);
static CHARACTER_DATA_INDEX_FIELD: AtomicUsize = AtomicUsize::new(0);
static CHARACTER_VISIBLE_FIELD: AtomicUsize = AtomicUsize::new(0);
static LIVE_SLOT_TRACE_COUNT: AtomicUsize = AtomicUsize::new(0);


#[repr(C)]
#[derive(Default)]
#[allow(dead_code)]
pub struct Vector4_t {
    pub x: f32,
    pub y: f32,
    pub z: f32,
    pub w: f32,
}

#[repr(C)]
#[allow(dead_code)]
pub struct PostFilmUpdateInfo {
    pub filmMode: i32,
    pub colorType: i32,
    pub filmPower: f32,
    pub filmOffsetParam: Vector2_t,
    pub filmOptionParam: Vector4_t,
    pub color0: Color_t,
    pub color1: Color_t,
    pub color2: Color_t,
    pub color3: Color_t,
    pub depthPower: f32,
    pub DepthClip: f32,
    pub layerMode: i32,
    pub colorBlend: i32,
    pub inverseVignette: bool,
    pub colorBlendFactor: f32,
    pub movieResId: i32,
    pub movieFrameOffset: i32,
    pub movieTime: f32,
    pub movieReverse: bool,
    pub RollAngle: f32,
    pub FilmScale: Vector2_t,
}

impl Default for PostFilmUpdateInfo {
    fn default() -> Self {
        Self {
            filmMode: 0,
            colorType: 0,
            filmPower: 0.0,
            filmOffsetParam: Default::default(),
            filmOptionParam: Default::default(),
            color0: Color_t {
                r: 0.0,
                g: 0.0,
                b: 0.0,
                a: 0.0,
            },
            color1: Color_t {
                r: 0.0,
                g: 0.0,
                b: 0.0,
                a: 0.0,
            },
            color2: Color_t {
                r: 0.0,
                g: 0.0,
                b: 0.0,
                a: 0.0,
            },
            color3: Color_t {
                r: 0.0,
                g: 0.0,
                b: 0.0,
                a: 0.0,
            },
            depthPower: 0.0,
            DepthClip: 0.0,
            layerMode: 0,
            colorBlend: 0,
            inverseVignette: false,
            colorBlendFactor: 0.0,
            movieResId: 0,
            movieFrameOffset: 0,
            movieTime: 0.0,
            movieReverse: false,
            RollAngle: 0.0,
            FilmScale: Default::default(),
        }
    }
}

#[repr(C)]
#[allow(dead_code)]
struct PostEffectUpdateInfo_DOF {
    pub IsEnableDOF: bool,
    pub forcalSize: f32,
    pub blurSpread: f32,
    pub forcalPosition: Vector3_t,
    pub dofQuality: i32,
    pub dofBlurType: i32,
    pub dofForegroundSize: f32,
    pub dofFocalPoint: f32,
    pub dofSoomthness: f32,
    pub isUseFocalPoint: bool,
    pub BallBlurCurveFactor: f32,
    pub BallBlurBrightnessThreshhold: f32,
    pub BallBlurBrightnessIntensity: f32,
    pub BallBlurSpread: f32,
    pub IsPointBallBlur: bool,
}

fn clear_live_screen_effects(sheet: *mut Il2CppObject) {
    if sheet.is_null() || !free_camera::should_remove_live_screen_effects() {
        return;
    }    

    let post_film_keys = LiveTimelineWorkSheet::get_postFilmKeys(sheet);
    if !post_film_keys.is_null() {
        LiveTimelineKeyPostFilmDataList::Clear(post_film_keys);
    }

    let post_film2_keys = LiveTimelineWorkSheet::get_postFilm2Keys(sheet);
    if !post_film2_keys.is_null() {
        LiveTimelineKeyPostFilmDataList::Clear(post_film2_keys);
    }

    let post_film3_keys = LiveTimelineWorkSheet::get_postFilm3Keys(sheet);
    if !post_film3_keys.is_null() {
        LiveTimelineKeyPostFilmDataList::Clear(post_film3_keys);
    }
}

pub fn set_current(this: *mut Il2CppObject) {
    if !this.is_null() {
        LIVE_TIMELINE_CONTROL.store(this as usize, Ordering::Relaxed);
    }
}

fn clear_current() {
    LIVE_TIMELINE_CONTROL.store(0, Ordering::Relaxed);
}

fn should_remove_live_camera_effects() -> bool {
    free_camera::set_live_active();
    free_camera::should_remove_camera_effects()
}

fn should_override_live_camera() -> bool {
    free_camera::set_live_active();
    free_camera::is_scene_enabled(CameraScene::Live)
}

fn apply_current_live_character_options() {
    let director = Director::instance();
    if !director.is_null() {
        Director::apply_live_character_options(director);
    }
}

type NoArgsFn = extern "C" fn(this: *mut Il2CppObject);

type LiveVoidFrameFn = extern "C" fn(this: *mut Il2CppObject, sheet: *mut Il2CppObject, current_frame: i32);
type LiveBoolFrameFn = extern "C" fn(this: *mut Il2CppObject, sheet: *mut Il2CppObject, current_frame: i32) -> bool;
type LiveVoidFrameTimeFn = extern "C" fn(
    this: *mut Il2CppObject,
    sheet: *mut Il2CppObject,
    current_frame: i32,
    current_time: f32,
);

type AlterUpdate_CameraPosFn = extern "C" fn(
    this: *mut Il2CppObject,
    sheet: *mut Il2CppObject,
    current_frame: i32,
    current_time: f32,
    sheet_index: i32,
    is_use_camera_motion: bool,
);
extern "C" fn AlterUpdate_CameraPos(
    this: *mut Il2CppObject,
    sheet: *mut Il2CppObject,
    current_frame: i32,
    current_time: f32,
    sheet_index: i32,
    mut is_use_camera_motion: bool,
) {
    free_camera::set_live_active();
    clear_live_screen_effects(sheet);
    let free_camera_active = free_camera::is_scene_enabled(CameraScene::Live);
    let frame = if free_camera_active {
        is_use_camera_motion = false;
        0
    } else {
        current_frame
    };
    get_orig_fn!(AlterUpdate_CameraPos, AlterUpdate_CameraPosFn)(
        this,
        sheet,
        frame,
        current_time,
        sheet_index,
        is_use_camera_motion,
    );
}

type AlterUpdate_CameraLookAtFn = extern "C" fn(
    this: *mut Il2CppObject,
    sheet: *mut Il2CppObject,
    current_frame: i32,
    current_time: f32,
    out_look_at: *mut Vector3_t,
);
extern "C" fn AlterUpdate_CameraLookAt(
    this: *mut Il2CppObject,
    sheet: *mut Il2CppObject,
    current_frame: i32,
    current_time: f32,
    out_look_at: *mut Vector3_t,
) {
    free_camera::set_live_active();
    clear_live_screen_effects(sheet);
    get_orig_fn!(AlterUpdate_CameraLookAt, AlterUpdate_CameraLookAtFn)(
        this,
        sheet,
        current_frame,
        current_time,
        out_look_at,
    );

    set_current(this);
    if free_camera::is_scene_enabled(CameraScene::Live) && !out_look_at.is_null() {
        unsafe {
            *out_look_at = free_camera::camera_look_at();
        }
    }
}

extern "C" fn LiveTimelineControl_AlterLateUpdate(this: *mut Il2CppObject) {
    free_camera::set_live_active();
    free_camera::tick();
    get_orig_fn!(LiveTimelineControl_AlterLateUpdate, NoArgsFn)(this);
    apply_current_live_character_options();
    let director = Director::instance();
    if !director.is_null() {
        Director::enforce_live_free_camera_output(director);
    }
}

extern "C" fn LiveTimelineControl_OnDestroy(this: *mut Il2CppObject) {
    Director::restore_live_disabled_heads(0, true);
    clear_current();
    free_camera::end_scene(CameraScene::Live);
    get_orig_fn!(LiveTimelineControl_OnDestroy, NoArgsFn)(this);
}

extern "C" fn AlterUpdate_RadialBlur(
    this: *mut Il2CppObject,
    sheet: *mut Il2CppObject,
    current_frame: i32,
) {
    if !should_remove_live_camera_effects() {
        get_orig_fn!(AlterUpdate_RadialBlur, LiveVoidFrameFn)(this, sheet, current_frame);
    }
}

type SetupPostFilmUpdateDataInfoFn = extern "C" fn(
    this: *mut Il2CppObject,
    updateInfo: *mut PostFilmUpdateInfo,
    curData: *mut Il2CppObject,
    nextData: *mut Il2CppObject,
    currentFrame: i32,
);
extern "C" fn SetupPostFilmUpdateDataInfo(
    this: *mut Il2CppObject,
    updateInfo: *mut PostFilmUpdateInfo,
    curData: *mut Il2CppObject,
    nextData: *mut Il2CppObject,
    currentFrame: i32,
) {
    get_orig_fn!(SetupPostFilmUpdateDataInfo, SetupPostFilmUpdateDataInfoFn)(
        this, updateInfo, curData, nextData, currentFrame,
    );

    if should_remove_live_camera_effects() {
        unsafe { *updateInfo = PostFilmUpdateInfo::default(); }
    }
}

type SetupDOFUpdateInfoFn = extern "C" fn(
    this: *mut Il2CppObject,
    update_info: *mut PostEffectUpdateInfo_DOF,
    cur_data: *mut Il2CppObject,
    next_data: *mut Il2CppObject,
    current_frame: i32,
    camera_look_at: Vector3_t,
);
extern "C" fn SetupDOFUpdateInfo(
    this: *mut Il2CppObject,
    update_info: *mut PostEffectUpdateInfo_DOF,
    cur_data: *mut Il2CppObject,
    next_data: *mut Il2CppObject,
    current_frame: i32,
    camera_look_at: Vector3_t,
) {
    get_orig_fn!(SetupDOFUpdateInfo, SetupDOFUpdateInfoFn)(
        this,
        update_info,
        cur_data,
        next_data,
        current_frame,
        camera_look_at,
    );

    if should_remove_live_camera_effects() {
        unsafe {
            (*update_info).IsEnableDOF = false;
            (*update_info).isUseFocalPoint = false;
            (*update_info).IsPointBallBlur = false;
        }
    }
}

type SetupRadialBlurInfoFn = extern "C" fn(
    this: *mut Il2CppObject,
    update_info: *mut Il2CppObject,
    cur_data: *mut Il2CppObject,
    next_data: *mut Il2CppObject,
    current_frame: i32,
);
extern "C" fn SetupRadialBlurInfo(
    this: *mut Il2CppObject,
    update_info: *mut Il2CppObject,
    cur_data: *mut Il2CppObject,
    next_data: *mut Il2CppObject,
    current_frame: i32,
) {
    if should_remove_live_camera_effects() {
        return;
    }
    get_orig_fn!(SetupRadialBlurInfo, SetupRadialBlurInfoFn)(
        this,
        update_info,
        cur_data,
        next_data,
        current_frame,
    );
}

macro_rules! live_skip_void_frame {
    ($hook:ident, $type:ty) => {
        extern "C" fn $hook(this: *mut Il2CppObject, sheet: *mut Il2CppObject, current_frame: i32) {
            if should_remove_live_camera_effects() {
                return;
            }
            get_orig_fn!($hook, $type)(this, sheet, current_frame);
        }
    };
}

macro_rules! live_secondary_camera_void_frame {
    ($hook:ident, $type:ty) => {
        extern "C" fn $hook(this: *mut Il2CppObject, sheet: *mut Il2CppObject, current_frame: i32) {
            let _guard = free_camera::begin_live_secondary_camera_update();
            get_orig_fn!($hook, $type)(this, sheet, current_frame);
        }
    };
}

macro_rules! live_main_camera_void_frame {
    ($hook:ident, $type:ty) => {
        extern "C" fn $hook(this: *mut Il2CppObject, sheet: *mut Il2CppObject, current_frame: i32) {
            if should_override_live_camera() {
                return;
            }
            get_orig_fn!($hook, $type)(this, sheet, current_frame);
        }
    };
}

macro_rules! live_secondary_camera_void_frame_time {
    ($hook:ident, $type:ty) => {
        extern "C" fn $hook(
            this: *mut Il2CppObject,
            sheet: *mut Il2CppObject,
            current_frame: i32,
            current_time: f32,
        ) {
            let _guard = free_camera::begin_live_secondary_camera_update();
            get_orig_fn!($hook, $type)(this, sheet, current_frame, current_time);
        }
    };
}

live_secondary_camera_void_frame_time!(AlterUpdate_MultiCameraPosition, LiveVoidFrameTimeFn);
live_secondary_camera_void_frame_time!(AlterUpdate_MultiCameraLookAt, LiveVoidFrameTimeFn);
live_secondary_camera_void_frame!(AlterUpdate_MultiCameraRadialBlur, LiveVoidFrameFn);
live_secondary_camera_void_frame_time!(AlterUpdate_EyeCameraPosition, LiveVoidFrameTimeFn);
live_secondary_camera_void_frame_time!(AlterUpdate_MonitorCameraPosition, LiveVoidFrameTimeFn);
live_skip_void_frame!(AlterUpdate_PostEffect_BloomDiffusion, LiveVoidFrameFn);
live_skip_void_frame!(AlterUpdate_TiltShift, LiveVoidFrameFn);
live_main_camera_void_frame!(AlterUpdate_CameraLayer, LiveVoidFrameFn);
live_main_camera_void_frame!(AlterUpdate_CameraSwitcher, LiveVoidFrameFn);
live_main_camera_void_frame!(AlterUpdate_CameraMotion, LiveVoidFrameFn);
live_main_camera_void_frame!(AlterUpdate_HandShakeCamera, LiveVoidFrameFn);
live_secondary_camera_void_frame_time!(AlterUpdate_MonitorCameraLookAt, LiveVoidFrameTimeFn);
live_secondary_camera_void_frame_time!(AlterUpdate_EyeCameraLookAt, LiveVoidFrameTimeFn);

extern "C" fn AlterLateUpdate_CameraMotion(
    this: *mut Il2CppObject,
    sheet: *mut Il2CppObject,
    current_frame: i32,
) -> bool {
    if should_override_live_camera() {
        return false;
    }
    get_orig_fn!(AlterLateUpdate_CameraMotion, LiveBoolFrameFn)(this, sheet, current_frame)
}

extern "C" fn AlterUpdate_CameraFov(
    this: *mut Il2CppObject,
    sheet: *mut Il2CppObject,
    current_frame: i32,
) {
    let trainer_live_landscape = Director::is_trainer_live() && Hachimi::instance().config.load().trainer_live_landscape;

    if should_override_live_camera() || trainer_live_landscape {
        return;
    }

    get_orig_fn!(AlterUpdate_CameraFov, LiveVoidFrameFn)(this, sheet, current_frame);
}

extern "C" fn AlterUpdate_CameraRoll(
    this: *mut Il2CppObject,
    sheet: *mut Il2CppObject,
    current_frame: i32,
) {
    if should_override_live_camera() {
        return;
    }
    get_orig_fn!(AlterUpdate_CameraRoll, LiveVoidFrameFn)(this, sheet, current_frame);
}

type LiveFormationOffsetFn = extern "C" fn(
    this: *mut Il2CppObject,
    sheet: *mut Il2CppObject,
    current_frame: i32,
    character_object_list: *mut Il2CppObject,
    change_visibility: bool,
);
extern "C" fn AlterUpdate_FormationOffset(
    this: *mut Il2CppObject,
    sheet: *mut Il2CppObject,
    current_frame: i32,
    character_object_list: *mut Il2CppObject,
    mut change_visibility: bool,
) {
    free_camera::set_live_active();
    let disable_teleport = free_camera::should_disable_live_character_teleport();
    let frame = if disable_teleport { 0 } else { current_frame };
    if disable_teleport || free_camera::should_force_live_characters_visible() {
        change_visibility = false;
    }

    // Keep the formation-offset timeline at its initial pose when free camera
    // ignores the authored camera motion. This removes camera-directed teleports
    // without forcing character transform nodes to a shared local position.
    get_orig_fn!(AlterUpdate_FormationOffset, LiveFormationOffsetFn)(
        this,
        sheet,
        frame,
        character_object_list,
        change_visibility,
    );

    Director::apply_live_character_options_to_list(character_object_list);
    apply_current_live_character_options();
}

fn current_play_song_id() -> i32 {
    let director = Director::instance();
    if director.is_null() {
        return -1;
    }
    let song_addr = DIRECTOR_GET_PLAY_SONG_ID.load(Ordering::Acquire);
    if song_addr == 0 {
        return -2;
    }
    let get_song: extern "C" fn(*mut Il2CppObject) -> i32 =
        unsafe { std::mem::transmute(song_addr) };
    get_song(director)
}

fn trace_is_beyond_1193() -> bool {
    current_play_song_id() == 1193
}

type SetCharactorLocatorFn = extern "C" fn(
    this: *mut Il2CppObject,
    index: i32,
    locator: *mut Il2CppObject,
);

extern "C" fn SetCharactorLocator(
    this: *mut Il2CppObject,
    index: i32,
    locator: *mut Il2CppObject,
) {
    let orig: SetCharactorLocatorFn = unsafe {
        std::mem::transmute(SET_CHARACTOR_LOCATOR_ORIG.load(Ordering::Acquire))
    };
    if index == 10 {
        let n = LIVE_SLOT_TRACE_COUNT.fetch_add(1, Ordering::Relaxed);
        if n < 80 {
            let song = current_play_song_id();
            info!(
                "[live-slot-trace] SetCharactorLocator index=10 song={} locator_null={}",
                song,
                locator.is_null()
            );
        }
    }
    orig(this, index, locator);
}

type InitCharaMotionSequenceFn = extern "C" fn(
    this: *mut Il2CppObject,
    index: i32,
);

extern "C" fn InitCharaMotionSequence(this: *mut Il2CppObject, index: i32) {
    let orig: InitCharaMotionSequenceFn = unsafe {
        std::mem::transmute(INIT_CHARA_MOTION_SEQUENCE_ORIG.load(Ordering::Acquire))
    };
    orig(this, index);

    if index != 10 || !trace_is_beyond_1193() {
        return;
    }
    let locator_field = LIVE_LOCATORS_FIELD.load(Ordering::Acquire) as *mut FieldInfo;
    let sequence_field = LIVE_MOTION_SEQUENCES_FIELD.load(Ordering::Acquire) as *mut FieldInfo;
    if locator_field.is_null() || sequence_field.is_null() {
        warn!("[live-slot-trace] index=10 field lookup failed");
        return;
    }
    let locators: *mut Il2CppArray = unsafe { crate::il2cpp::symbols::get_field_value(this, locator_field) };
    let sequences: *mut Il2CppArray = unsafe { crate::il2cpp::symbols::get_field_value(this, sequence_field) };
    let locator = if locators.is_null() {
        std::ptr::null_mut()
    } else {
        unsafe { *((locators.add(1) as *mut *mut Il2CppObject).add(index as usize)) }
    };
    let sequence = if sequences.is_null() {
        std::ptr::null_mut()
    } else {
        unsafe { *((sequences.add(1) as *mut *mut Il2CppObject).add(index as usize)) }
    };
    let director_list_field = DIRECTOR_CHARACTER_LIST_FIELD.load(Ordering::Acquire) as *mut FieldInfo;
    let char_data_index_field = CHARACTER_DATA_INDEX_FIELD.load(Ordering::Acquire) as *mut FieldInfo;
    let char_visible_field = CHARACTER_VISIBLE_FIELD.load(Ordering::Acquire) as *mut FieldInfo;
    let director = Director::instance();
    let list: *mut Il2CppObject = crate::il2cpp::symbols::get_field_value(director, director_list_field);
    let list_access = crate::il2cpp::symbols::IList::<*mut Il2CppObject>::new(list);
    let count = list_access.as_ref().map(|x| x.count().clamp(0, 20) as usize).unwrap_or(0);
    let n = LIVE_SLOT_TRACE_COUNT.fetch_add(1, Ordering::Relaxed);
    if n < 40 {
        info!(
            "[live-slot-trace] InitCharaMotionSequence index=10 song=1193 locator_null={} sequence_null={} character_count={}",
            locator.is_null(), sequence.is_null(), count
        );
        if let Some(chars) = list_access.as_ref() {
            for i in 0..chars.count().clamp(0, 20) {
                let character = chars.get(i).unwrap_or(std::ptr::null_mut());
                if character.is_null() { continue; }
                let data_index = crate::il2cpp::symbols::get_field_value::<i32>(character, char_data_index_field);
                let visible = crate::il2cpp::symbols::get_field_value::<bool>(character, char_visible_field);
                info!("[live-slot-trace] character-list[{}] data_index={} visible={}", i, data_index, visible);
            }
        }
    }
}

fn hook_live_slot_trace(umamusume: *const Il2CppImage) {
    let Ok(class) = get_class(umamusume, c"Gallop.Live.Cutt", c"LiveTimelineControl") else {
        return;
    };
    let h = Hachimi::instance();
    for (name, argc, hook, target, tag) in [
        (
            c"SetCharactorLocator",
            2,
            SetCharactorLocator as *const () as usize,
            &SET_CHARACTOR_LOCATOR_ORIG,
            "SetCharactorLocator",
        ),
        (
            c"InitCharaMotionSequence",
            1,
            InitCharaMotionSequence as *const () as usize,
            &INIT_CHARA_MOTION_SEQUENCE_ORIG,
            "InitCharaMotionSequence",
        ),
    ] {
        let addr = get_method_addr(class, name, argc);
        if addr == 0 {
            warn!("[live-slot-trace] {} address missing", tag);
            continue;
        }
        match h.interceptor.hook(addr, hook) {
            Ok(trampoline) => {
                target.store(trampoline, Ordering::Release);
                info!("[live-slot-trace] hooked {}", tag);
            }
            Err(error) => error!("[live-slot-trace] hook {} failed: {}", tag, error),
        }
    }
}

pub fn init(umamusume: *const Il2CppImage) {
    hook_live_slot_trace(umamusume);
    let Ok(director_class) = get_class(umamusume, c"Gallop.Live", c"Director") else {
        warn!("[live-slot-trace] Director class missing");
        return;
    };
    let song_id_addr = get_method_addr(director_class, c"GetPlaySongId", 0);
    if song_id_addr != 0 {
        DIRECTOR_GET_PLAY_SONG_ID.store(song_id_addr, Ordering::Release);
    } else {
        warn!("[live-slot-trace] Director.GetPlaySongId address missing");
    }

    DIRECTOR_CHARACTER_LIST_FIELD.store(
        get_field_from_name(director_class, c"_characterObjectList") as usize,
        Ordering::Release,
    );
    let Ok(character_class) = get_class(umamusume, c"Gallop.Live", c"CharacterObject") else {
        warn!("[live-slot-trace] CharacterObject class missing");
        return;
    };
    CHARACTER_DATA_INDEX_FIELD.store(
        get_field_from_name(character_class, c"_characterDataIndex") as usize,
        Ordering::Release,
    );
    CHARACTER_VISIBLE_FIELD.store(
        get_field_from_name(character_class, c"_bVisible") as usize,
        Ordering::Release,
    );
    let Ok(control_class) = get_class(umamusume, c"Gallop.Live.Cutt", c"LiveTimelineControl") else {
        warn!("[live-slot-trace] LiveTimelineControl class missing");
        return;
    };
    LIVE_LOCATORS_FIELD.store(
        get_field_from_name(control_class, c"_liveCharactorLocators") as usize,
        Ordering::Release,
    );
    LIVE_MOTION_SEQUENCES_FIELD.store(
        get_field_from_name(control_class, c"_motionSequenceArray") as usize,
        Ordering::Release,
    );

    get_class_or_return!(umamusume, "Gallop.Live.Cutt", LiveTimelineControl);

    let AlterUpdate_CameraPos_addr = get_method_addr(LiveTimelineControl, c"AlterUpdate_CameraPos", 5);
    new_hook!(AlterUpdate_CameraPos_addr, AlterUpdate_CameraPos);

    let AlterUpdate_CameraLookAt_addr = get_method_addr(LiveTimelineControl, c"AlterUpdate_CameraLookAt", 4);
    new_hook!(AlterUpdate_CameraLookAt_addr, AlterUpdate_CameraLookAt);

    let LiveTimelineControl_AlterLateUpdate_addr = get_method_addr(LiveTimelineControl, c"AlterLateUpdate", 0);
    new_hook!(LiveTimelineControl_AlterLateUpdate_addr, LiveTimelineControl_AlterLateUpdate);

    let LiveTimelineControl_OnDestroy_addr = get_method_addr(LiveTimelineControl, c"OnDestroy", 0);
    new_hook!(LiveTimelineControl_OnDestroy_addr, LiveTimelineControl_OnDestroy);

    let AlterUpdate_RadialBlur_addr = get_method_addr(LiveTimelineControl, c"AlterUpdate_RadialBlur", 2);
    new_hook!(AlterUpdate_RadialBlur_addr, AlterUpdate_RadialBlur);

    let SetupPostFilmUpdateDataInfo_addr = get_method_addr(LiveTimelineControl, c"SetupPostFilmUpdateDataInfo", 4);
    new_hook!(SetupPostFilmUpdateDataInfo_addr, SetupPostFilmUpdateDataInfo);

    let SetupDOFUpdateInfo_addr = get_method_addr(LiveTimelineControl, c"SetupDOFUpdateInfo", 5);
    new_hook!(SetupDOFUpdateInfo_addr, SetupDOFUpdateInfo);

    let SetupRadialBlurInfo_addr = get_method_addr(LiveTimelineControl, c"SetupRadialBlurInfo", 4);
    new_hook!(SetupRadialBlurInfo_addr, SetupRadialBlurInfo);

    let AlterUpdate_MultiCameraRadialBlur_addr = get_method_addr(
        LiveTimelineControl,
        c"AlterUpdate_MultiCameraRadialBlur",
        2,
    );
    new_hook!(AlterUpdate_MultiCameraRadialBlur_addr, AlterUpdate_MultiCameraRadialBlur);

    let AlterUpdate_EyeCameraPosition_addr = get_method_addr(LiveTimelineControl, c"AlterUpdate_EyeCameraPosition", 3);
    new_hook!(AlterUpdate_EyeCameraPosition_addr, AlterUpdate_EyeCameraPosition);

    let AlterUpdate_MonitorCameraPosition_addr = get_method_addr(LiveTimelineControl, c"AlterUpdate_MonitorCameraPosition", 3);
    new_hook!(AlterUpdate_MonitorCameraPosition_addr, AlterUpdate_MonitorCameraPosition);

    let AlterUpdate_PostEffect_BloomDiffusion_addr = get_method_addr(
        LiveTimelineControl,
        c"AlterUpdate_PostEffect_BloomDiffusion",
        2,
    );
    new_hook!(AlterUpdate_PostEffect_BloomDiffusion_addr, AlterUpdate_PostEffect_BloomDiffusion);

    let AlterUpdate_TiltShift_addr = get_method_addr(LiveTimelineControl, c"AlterUpdate_TiltShift", 2);
    new_hook!(AlterUpdate_TiltShift_addr, AlterUpdate_TiltShift);

    let AlterUpdate_CameraLayer_addr = get_method_addr(LiveTimelineControl, c"AlterUpdate_CameraLayer", 2);
    new_hook!(AlterUpdate_CameraLayer_addr, AlterUpdate_CameraLayer);

    let AlterUpdate_CameraFov_addr = get_method_addr(LiveTimelineControl, c"AlterUpdate_CameraFov", 2);
    new_hook!(AlterUpdate_CameraFov_addr, AlterUpdate_CameraFov);

    let AlterUpdate_CameraRoll_addr = get_method_addr(LiveTimelineControl, c"AlterUpdate_CameraRoll", 2);
    new_hook!(AlterUpdate_CameraRoll_addr, AlterUpdate_CameraRoll);

    let AlterUpdate_CameraMotion_addr = get_method_addr(LiveTimelineControl, c"AlterUpdate_CameraMotion", 2);
    new_hook!(AlterUpdate_CameraMotion_addr, AlterUpdate_CameraMotion);

    let AlterLateUpdate_CameraMotion_addr = get_method_addr(LiveTimelineControl, c"AlterLateUpdate_CameraMotion", 2);
    new_hook!(AlterLateUpdate_CameraMotion_addr, AlterLateUpdate_CameraMotion);

    let AlterUpdate_HandShakeCamera_addr = get_method_addr(LiveTimelineControl, c"AlterUpdate_HandShakeCamera", 2);
    new_hook!(AlterUpdate_HandShakeCamera_addr, AlterUpdate_HandShakeCamera);

    let AlterUpdate_CameraSwitcher_addr = get_method_addr(LiveTimelineControl, c"AlterUpdate_CameraSwitcher", 2);
    new_hook!(AlterUpdate_CameraSwitcher_addr, AlterUpdate_CameraSwitcher);

    let AlterUpdate_MonitorCameraLookAt_addr = get_method_addr(LiveTimelineControl, c"AlterUpdate_MonitorCameraLookAt", 3);
    new_hook!(AlterUpdate_MonitorCameraLookAt_addr, AlterUpdate_MonitorCameraLookAt);

    let AlterUpdate_EyeCameraLookAt_addr = get_method_addr(LiveTimelineControl, c"AlterUpdate_EyeCameraLookAt", 3);
    new_hook!(AlterUpdate_EyeCameraLookAt_addr, AlterUpdate_EyeCameraLookAt);

    let AlterUpdate_MultiCameraPosition_addr = get_method_addr(LiveTimelineControl, c"AlterUpdate_MultiCameraPosition", 3);
    new_hook!(AlterUpdate_MultiCameraPosition_addr, AlterUpdate_MultiCameraPosition);

    let AlterUpdate_MultiCameraLookAt_addr = get_method_addr(LiveTimelineControl, c"AlterUpdate_MultiCameraLookAt", 3);
    new_hook!(AlterUpdate_MultiCameraLookAt_addr, AlterUpdate_MultiCameraLookAt);

    let AlterUpdate_FormationOffset_addr = get_method_addr(LiveTimelineControl, c"AlterUpdate_FormationOffset", 4);
    new_hook!(AlterUpdate_FormationOffset_addr, AlterUpdate_FormationOffset);
}
