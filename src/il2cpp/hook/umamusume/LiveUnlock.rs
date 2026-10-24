//! Live 曲目全解锁
//!
//! （形如 `[{music_id, acquisition_time}, ...]`），服务器没下发的曲目就不可播。
//!
//!
//!   +0x18 = max_length
//!   +0x20 = 首元素

use crate::il2cpp::{
    symbols::{get_class, get_method_addr},
    types::*,
};

type AddRangeMusicDataFn = extern "C" fn(this: *mut Il2CppObject, list: *mut Il2CppObject) -> i32;
static mut ORIG: usize = 0;

extern "C" fn AddRangeMusicData_hook(this: *mut Il2CppObject, list: *mut Il2CppObject) -> i32 {
    unsafe {
        let orig = ORIG;
        if orig == 0 {
            return 0;
        }
        let f: AddRangeMusicDataFn = std::mem::transmute(orig);

        let ret = f(this, list);

        if !crate::core::Hachimi::instance().config.load().unlock_all_live {
            return ret;
        }
        if list.is_null() {
            return ret;
        }

        let p = list as usize;
        let len = *((p + 0x18) as *const i32);
        if len <= 0 || len > 10000 {
            return ret;
        }
        let elem0 = *((p + 0x20) as *const usize);
        if elem0 == 0 {
            return ret;
        }
        let id_ptr = (elem0 + 0x10) as *mut i32;
        let old_id = *id_ptr;

        let mut existing: Vec<i32> = Vec::with_capacity(len as usize);
        for i in 0..len as usize {
            let e = *((p + 0x20 + i * 8) as *const usize);
            if e != 0 {
                existing.push(*((e + 0x10) as *const i32));
            }
        }

        let ids = crate::core::Hachimi::instance().live_data.load().live_ids.clone();
        let mut injected = 0usize;
        let mut dup = 0usize;
        for id in ids {
            if id == old_id {
                continue;
            }
            if existing.contains(&id) {
                dup += 1;
            }
            *id_ptr = id;
            f(this, list);
            injected += 1;
        }
        *id_ptr = old_id;

        info!(
            "[liveunlock] 原列表 {} 首 {:?} -> 注入 {} 首（其中与原有重复 {} 首）",
            existing.len(), existing, injected, dup
        );
        ret
    }
}

pub fn init(umamusume: *const Il2CppImage) {
    if !crate::core::Hachimi::instance().config.load().unlock_all_live {
        return;
    }

    let Ok(k) = get_class(umamusume, c"Gallop", c"WorkMusicData") else {
        warn!("[liveunlock] WorkMusicData 类未找到");
        return;
    };
    let addr = get_method_addr(k, c"AddRangeMusicData", 1);
    if addr == 0 {
        warn!("[liveunlock] AddRangeMusicData 地址为空");
        return;
    }
    let hachimi = crate::core::Hachimi::instance();
    match hachimi.interceptor.hook(addr, AddRangeMusicData_hook as *const () as usize) {
        Ok(trampoline) => {
            unsafe { ORIG = trampoline };
            info!("[liveunlock] hooked AddRangeMusicData @ {:#x}", addr);
        }
        Err(e) => error!("[liveunlock] hook 失败: {}", e),
    }
}
