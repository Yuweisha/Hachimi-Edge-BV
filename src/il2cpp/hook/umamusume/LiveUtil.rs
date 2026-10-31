use crate::{
    core::Hachimi,
    il2cpp::{symbols::get_method_addr, types::*}
};

type GetSingCharaIdListFn = extern "C" fn(songId: i32, songPartNumber: i32, allCharaIdArray: *mut Il2CppArray, vocalCharaIdArray: *mut Il2CppArray, shuffledCharaDataList: *mut Il2CppObject) -> *mut Il2CppObject;
extern "C" fn GetSingCharaIdList(songId: i32, songPartNumber: i32, allCharaIdArray: *mut Il2CppArray, vocalCharaIdArray: *mut Il2CppArray, shuffledCharaDataList: *mut Il2CppObject) -> *mut Il2CppObject {
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

    get_orig_fn!(GetSingCharaIdList, GetSingCharaIdListFn)(songId, songPartNumber, allCharaIdArray, vocalCharaIdArray, shuffledCharaDataList)
}

pub fn init(umamusume: *const Il2CppImage) {
    get_class_or_return!(umamusume, "Gallop", LiveUtil);

    let GetSingCharaIdList_addr = get_method_addr(LiveUtil, c"GetSingCharaIdList", 5);
    new_hook!(GetSingCharaIdList_addr, GetSingCharaIdList);
}

