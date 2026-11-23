use std::sync::atomic::{AtomicI32, AtomicUsize, Ordering};

use crate::{
    core::Hachimi,
    il2cpp::{
        symbols::{get_field_from_name, get_field_value, get_method_addr, set_field_value},
        types::*,
    },
};

static CREATE_SYSTEM_TEXT_BUILD_INFO_ADDR: AtomicUsize = AtomicUsize::new(0);
static CHARA_ID_FIELD: AtomicUsize = AtomicUsize::new(0);
static LOGGED_SYSTEM_TEXT_BORROWS: AtomicI32 = AtomicI32::new(0);

type CreateSystemTextMotionBuildInfoFn = extern "C" fn(
    build_info: *mut Il2CppObject,
    motion_chara_id: i32,
    method: *mut std::ffi::c_void,
) -> *mut Il2CppObject;

/// 给动作专用 BuildInfo 借用原角色 ID，舞台模型 BuildInfo 不变。
///
/// il2cpp 的 static 方法在 ARM64 上还带隐藏的 `MethodInfo*`（第三个寄存器），
/// 必须原样透传，否则安卓上调用 trampoline 时该参数是垃圾值，方法内部
/// 使用它就会崩（`GetBySystemTextId` 就是这样在加载 100% 时 SIGSEGV 的）。
extern "C" fn CreateSystemTextMotionBuildInfo(
    build_info: *mut Il2CppObject,
    motion_chara_id: i32,
    method: *mut std::ffi::c_void,
) -> *mut Il2CppObject {
    let orig: CreateSystemTextMotionBuildInfoFn = unsafe {
        std::mem::transmute(CREATE_SYSTEM_TEXT_BUILD_INFO_ADDR.load(Ordering::Acquire))
    };
    let result = orig(build_info, motion_chara_id, method);
    if result.is_null() {
        return result;
    }

    let chara_field = CHARA_ID_FIELD.load(Ordering::Acquire) as *mut FieldInfo;
    if chara_field.is_null() {
        return result;
    }
    let cfg = Hachimi::instance().config.load();
    let replace = &cfg.replace_global_char;
    if !replace.enable || !replace.replace_motion {
        return result;
    }

    let replaced_chara: i32 = unsafe { get_field_value(result, chara_field) };
    if replaced_chara != motion_chara_id {
        return result;
    }
    let Some(entry) = replace.data.iter().find(|entry| {
        entry.new_char_id == replaced_chara
            && entry.orig_char_id > 0
            && entry.orig_char_id != entry.new_char_id
    }) else {
        return result;
    };

    unsafe { set_field_value(result, chara_field, &entry.orig_char_id) };
    let n = LOGGED_SYSTEM_TEXT_BORROWS.fetch_add(1, Ordering::Relaxed);
    if n < 20 {
        info!(
            "[live-motion-borrow] system text build {} -> {} (model build unchanged)",
            replaced_chara, entry.orig_char_id
        );
    }
    result
}

fn init_system_text_motion_build_info(umamusume: *const Il2CppImage) {
    get_class_or_return!(umamusume, Gallop, CharacterBuildInfo);
    let chara_field = get_field_from_name(CharacterBuildInfo, c"_charaId");
    if chara_field.is_null() {
        return;
    }
    CHARA_ID_FIELD.store(chara_field as usize, Ordering::Release);

    get_class_or_return!(umamusume, Gallop, LiveUtil);
    let addr = get_method_addr(LiveUtil, c"CreateSystemTextMotionBuildInfo", 2);
    if addr == 0 {
        warn!("[live-motion-borrow] CreateSystemTextMotionBuildInfo 地址为空");
        return;
    }
    match Hachimi::instance().interceptor.hook(
        addr,
        CreateSystemTextMotionBuildInfo as *const () as usize,
    ) {
        Ok(trampoline) => {
            CREATE_SYSTEM_TEXT_BUILD_INFO_ADDR.store(trampoline, Ordering::Release);
            info!("[live-motion-borrow] hooked LiveUtil.CreateSystemTextMotionBuildInfo");
        }
        Err(error) => error!("[live-motion-borrow] hook 安装失败: {}", error),
    }
}

type GetSingCharaIdListFn = extern "C" fn(songId: i32, songPartNumber: i32, allCharaIdArray: *mut Il2CppArray, vocalCharaIdArray: *mut Il2CppArray, shuffledCharaDataList: *mut Il2CppObject, method: *mut std::ffi::c_void) -> *mut Il2CppObject;
extern "C" fn GetSingCharaIdList(songId: i32, songPartNumber: i32, allCharaIdArray: *mut Il2CppArray, vocalCharaIdArray: *mut Il2CppArray, shuffledCharaDataList: *mut Il2CppObject, method: *mut std::ffi::c_void) -> *mut Il2CppObject {
    if songId > 0 {
        info!("[live] song={} part={}", songId, songPartNumber);
    }

    let config = Hachimi::instance().config.load();
    let chara_vo_ids = config.live_vocals_swap_presets.get(&songId).unwrap_or(&config.live_vocals_swap);
    let replace = &config.replace_global_char;
    let force = replace.song_force_chara;

    if songId > 0 {
        unsafe {
            for array in [vocalCharaIdArray, allCharaIdArray] {
                if array.is_null() {
                    continue;
                }

                let len = (*array).max_length as usize;
                let data_ptr = array.add(1) as *mut i32;

                for i in 0..len {
                    let orig = if i < chara_vo_ids.len() { *data_ptr.add(i) } else { 0 };
                    let mut new_id = orig;

                    if i < chara_vo_ids.len() && chara_vo_ids[i] != 0 {
                        new_id = chara_vo_ids[i];
                    } else if force != 0 {
                        new_id = force;
                    } else if replace.enable && orig > 0 {
                        new_id = crate::core::voice_replace::effective_char_id(orig);
                    }

                    if new_id != orig {
                        *data_ptr.add(i) = new_id;
                    }
                }

                // 探针：打印该数组最终内容 + 重复检测
                if std::env::var("HACHIMI_SONG_PROBE").ok().as_deref() != Some("0") {
                    let tag = if std::ptr::eq(array, vocalCharaIdArray) { "vocal" } else { "all" };
                    let mut vals = Vec::with_capacity(len);
                    for i in 0..len {
                        vals.push(*data_ptr.add(i));
                    }
                    info!("[sing] song={} {} = {:?}", songId, tag, vals);
                    let mut seen = std::collections::HashMap::new();
                    let mut dup = 0;
                    for (i, v) in vals.iter().enumerate() {
                        if *v <= 0 {
                            continue;
                        }
                        if let Some(prev) = seen.insert(*v, i) {
                            dup += 1;
                            warn!("[sing]   ★ 槽位 {} 与 {} 同为角色 {}（第 {} 次重复）", prev, i, v, dup);
                        }
                    }
                    if dup > 0 {
                        warn!("[sing]   ★ 共 {} 个重复槽位 → 多声部同角色，极易无声", dup);
                    }
                }
            }
        }
    }

    get_orig_fn!(GetSingCharaIdList, GetSingCharaIdListFn)(songId, songPartNumber, allCharaIdArray, vocalCharaIdArray, shuffledCharaDataList, method)
}

pub fn init(umamusume: *const Il2CppImage) {
    init_system_text_motion_build_info(umamusume);
    get_class_or_return!(umamusume, "Gallop", LiveUtil);

    let GetSingCharaIdList_addr = get_method_addr(LiveUtil, c"GetSingCharaIdList", 5);
    new_hook!(GetSingCharaIdList_addr, GetSingCharaIdList);
}

