// 服装路径替换 —— Hook 模式（replace_model_in_cutscene）下套服装
//
// ClothBuildPathInfo 的四个路径函数（都是 -> String，全局各只有 1 个调用点，
// 集中在 0x337D6xx~0x337D8xx 的统一装配函数里，替换安全）：
//   GetCharacterHeadClothAssetFilePath(3)  @ 0x337BF00   头部服装
//   GetSpecialDressClothAssetPath(3)       @ 0x337D100   专属服装
//   GetCommonDressClothAssetFilePath(3)    @ 0x337C3B0   通用服装
//   GetTailClothAssetFilePath(2)           @ 0x337D2F0   尾巴服装
//
// 只替换路径里的 `chr{四位}` 段，其余原样。
// 开关：config.replace_global_char.replace_model_in_cutscene（false 时完全不动）

use std::sync::atomic::{AtomicUsize, Ordering};

use crate::{
    core::Hachimi,
    il2cpp::{
        ext::{Il2CppStringExt, StringExt},
        symbols::{get_class, get_method_addr},
        types::*,
    },
};

static ORIG_HEAD: AtomicUsize = AtomicUsize::new(0);
static ORIG_SPECIAL: AtomicUsize = AtomicUsize::new(0);
static ORIG_COMMON: AtomicUsize = AtomicUsize::new(0);
static ORIG_TAIL: AtomicUsize = AtomicUsize::new(0);
static N_HIT: AtomicUsize = AtomicUsize::new(0);

fn s(p: *mut Il2CppString) -> String {
    if p.is_null() {
        return String::new();
    }
    unsafe { &*p }.as_utf16str().to_string()
}

/// 把路径里的 `chr{四位}` 换成替换目标；不改就返回 None
fn rewrite_cloth_path(path: &str) -> Option<String> {
    if path.is_empty() {
        return None;
    }
    let cfg = Hachimi::instance().config.load();
    let cr = &cfg.replace_global_char;
    if !cr.enable || !cr.replace_model_in_cutscene {
        return None;
    }

    let bytes = path.as_bytes();
    let mut i = 0;
    while i + 4 <= bytes.len() {
        if &bytes[i..i + 3] == b"chr" {
            let start = i + 3;
            let mut end = start;
            while end < bytes.len() && bytes[end].is_ascii_digit() {
                end += 1;
            }
            if end - start == 4 {
                if let Ok(cid) = path[start..end].parse::<i32>() {
                    if let Some(entry) = cr
                        .data
                        .iter()
                        .find(|e| e.orig_char_id == cid && e.new_char_id > 0)
                    {
                        // ★ 必须替换路径里**所有** chr{orig}，不能只换第一个。
                        //
                        //   实测路径：3d/Chara/Head/chr1003_00/Clothes/pfb_chr1003_00_cloth03
                        //   里面出现两次 chr1003：目录名一次、文件名一次。
                        //   只换第一个会得到 chr1114_00/Clothes/pfb_chr1003_00_cloth03 ——
                        //   这个路径不存在，加载会挂住（表现为卡角色加载）。
                        let old_tag = format!("chr{:04}", cid);
                        let new_tag = format!("chr{:04}", entry.new_char_id);
                        let np = path.replace(&old_tag, &new_tag);
                        if np != path {
                            let n = N_HIT.fetch_add(1, Ordering::Relaxed);
                            if n < 20 {
                                info!("[cloth] {} → {}", path, np);
                            }
                            return Some(np);
                        }
                        return None;
                    }
                }
                break;
            }
            i = end;
        } else {
            i += 1;
        }
    }
    None
}

fn post(ret: *mut Il2CppString) -> *mut Il2CppString {
    match rewrite_cloth_path(&s(ret)) {
        Some(np) => np.to_il2cpp_string(),
        None => ret,
    }
}

// 3 参：this, a1(i32), a2(i32), a3(i32)
type ThreeFn = extern "C" fn(*mut Il2CppObject, i32, i32, i32) -> *mut Il2CppString;
extern "C" fn HeadCloth(this: *mut Il2CppObject, a1: i32, a2: i32, a3: i32) -> *mut Il2CppString {
    let orig: ThreeFn = unsafe { std::mem::transmute(ORIG_HEAD.load(Ordering::Relaxed)) };
    post(orig(this, a1, a2, a3))
}
extern "C" fn SpecialDress(this: *mut Il2CppObject, a1: i32, a2: i32, a3: i32) -> *mut Il2CppString {
    let orig: ThreeFn = unsafe { std::mem::transmute(ORIG_SPECIAL.load(Ordering::Relaxed)) };
    post(orig(this, a1, a2, a3))
}
extern "C" fn CommonDress(this: *mut Il2CppObject, a1: i32, a2: i32, a3: i32) -> *mut Il2CppString {
    let orig: ThreeFn = unsafe { std::mem::transmute(ORIG_COMMON.load(Ordering::Relaxed)) };
    post(orig(this, a1, a2, a3))
}

// 2 参：this, a1(i32), a2(i32)
type TwoFn = extern "C" fn(*mut Il2CppObject, i32, i32) -> *mut Il2CppString;
extern "C" fn TailCloth(this: *mut Il2CppObject, a1: i32, a2: i32) -> *mut Il2CppString {
    let orig: TwoFn = unsafe { std::mem::transmute(ORIG_TAIL.load(Ordering::Relaxed)) };
    post(orig(this, a1, a2))
}

// ===== 身体网格 =====
// GetBodyMeshPath(9) @ 0x3370FD0 —— 静态方法（ecx = arg1，不是 this）
// 反汇编确认：arg2 (edx) = charaId，arg3 (r8d) / arg4 (r9d)，其余走栈。
// 3 参版本 GetBodyMeshPath(3) 只是转发到它。
type BodyFn = extern "C" fn(
    i32, i32, i32, i32, usize, usize, usize, usize, usize,
) -> *mut Il2CppString;

static ORIG_BODY9: AtomicUsize = AtomicUsize::new(0);

extern "C" fn BodyMeshPath9(
    a1: i32, chara_id: i32, a3: i32, a4: i32,
    a5: usize, a6: usize, a7: usize, a8: usize, a9: usize,
) -> *mut Il2CppString {
    let orig: BodyFn = unsafe { std::mem::transmute(ORIG_BODY9.load(Ordering::Relaxed)) };

    // 只改 charaId，其他参数原样
    let use_id = {
        let cfg = Hachimi::instance().config.load();
        let cr = &cfg.replace_global_char;
        if cr.enable && cr.replace_model_in_cutscene {
            cr.data
                .iter()
                .find(|e| e.orig_char_id == chara_id && e.new_char_id > 0)
                .map(|e| e.new_char_id)
                .unwrap_or(chara_id)
        } else {
            chara_id
        }
    };

    let ret = orig(a1, use_id, a3, a4, a5, a6, a7, a8, a9);
    let path = s(ret);
    // 路径里如果还有 chr{原ID} 也一并换掉
    match if use_id != chara_id { rewrite_cloth_path(&path) } else { None } {
        Some(np) => np.to_il2cpp_string(),
        None => ret,
    }
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
        warn!("[cloth] {} 地址为空", tag);
        return;
    }
    match h.interceptor.hook(addr, detour) {
        Ok(t) => {
            slot.store(t, Ordering::SeqCst);
            info!("[cloth] hooked {} @ {:#x}", tag, addr);
        }
        Err(e) => error!("[cloth] hook {} 失败: {}", tag, e),
    }
}

pub fn init(umamusume: *const Il2CppImage) {
    let h = Hachimi::instance();
    let Ok(k) = get_class(umamusume, c"Gallop", c"ClothBuildPathInfo") else {
        warn!("[cloth] ClothBuildPathInfo 未找到");
        return;
    };

    hook_one(&h, k, c"GetCharacterHeadClothAssetFilePath", 3,
             HeadCloth as *const () as usize, &ORIG_HEAD, "HeadCloth");
    hook_one(&h, k, c"GetSpecialDressClothAssetPath", 3,
             SpecialDress as *const () as usize, &ORIG_SPECIAL, "SpecialDress");
    hook_one(&h, k, c"GetCommonDressClothAssetFilePath", 3,
             CommonDress as *const () as usize, &ORIG_COMMON, "CommonDress");
    hook_one(&h, k, c"GetTailClothAssetFilePath", 2,
             TailCloth as *const () as usize, &ORIG_TAIL, "TailCloth");

    // 身体网格属于 CharacterBuildPathInfo（不是 ClothBuildPathInfo）
    if let Ok(kb) = get_class(umamusume, c"Gallop", c"CharacterBuildPathInfo") {
        hook_one(&h, kb, c"GetBodyMeshPath", 9,
                 BodyMeshPath9 as *const () as usize, &ORIG_BODY9, "BodyMeshPath9");
    } else {
        warn!("[cloth] CharacterBuildPathInfo 未找到（身体网格 hook 跳过）");
    }
}
