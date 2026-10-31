// 资源路径探针 —— 定位「A 的头 + B 的身体」和「A 套 B 的动作」的可行点
//
// 目标方法（CharacterBuildPathInfo，静态）：
//   GetCharacterHeadModelFilePath(charaId: i32, headSubId: i32) -> String   @ 0x3375280
//   GetCharacterTailModelFilePath(charaId: i32, ...)             -> String   @ 0x3375310
//
// 反汇编依据（0x4817442 起的 CharacterBuildInfo.Rebuild 内部）：
//   mov rdi, [rbx + 0xC8]        ; _charaBuildPathInfo
//   mov edx, esi                 ; headModelSubId
//   mov [rbx + 0x20], esi        ; 写 _headModelSubId
//   mov ecx, r15d                ; charaId = r15d（= Rebuild 入参 ecx）
//   call GetCharacterHeadModelFilePath
//   mov [rdi + 0x18], rax        ; → _charaBuildPathInfo.headPrefabPath
//
// 结论：头部路径用的 charaId 来自 Rebuild 的入参，不是 _charaId 字段。
//      所以在字段上改角色不会影响头部路径 —— 必须在这里拦。
//
// 探针开关：HACHIMI_CBPATH_PROBE=0 关闭（默认开）

use std::sync::atomic::{AtomicUsize, Ordering};

use crate::il2cpp::{
    ext::Il2CppStringExt,
    symbols::{get_class, get_method_addr},
    types::*,
};

static ORIG_HEAD: AtomicUsize = AtomicUsize::new(0);
static ORIG_TAIL: AtomicUsize = AtomicUsize::new(0);
static N_HEAD: AtomicUsize = AtomicUsize::new(0);
static N_TAIL: AtomicUsize = AtomicUsize::new(0);

fn enabled() -> bool {
    std::env::var("HACHIMI_CBPATH_PROBE").ok().as_deref() != Some("0")
}

fn cue_str(p: *mut Il2CppString) -> String {
    if p.is_null() {
        return "<null>".to_string();
    }
    unsafe { &*p }.as_utf16str().to_string()
}

// (charaId, subId) -> String
type HeadFn = extern "C" fn(chara_id: i32, sub_id: i32) -> *mut Il2CppString;
type TailFn = extern "C" fn(chara_id: i32, arg: *mut Il2CppObject) -> *mut Il2CppString;

extern "C" fn GetCharacterHeadModelFilePath(chara_id: i32, sub_id: i32) -> *mut Il2CppString {
    let orig: HeadFn = unsafe { std::mem::transmute(ORIG_HEAD.load(Ordering::Relaxed)) };

    // ★ 纠正头部路径的 charaId：
    //   该函数的入参来自 CharacterBuildInfo.Rebuild 的 ecx（r15d），**不是 _charaId 字段**。
    //   所以替换时改字段只会换身体，头部仍按原角色加载 → 新身体 + 旧头 → 装配失败 → 过场软死。
    //   这里用 Rebuild 里记下的目标角色覆盖入参，让头/身体/尾巴统一。
    //   安全性：反汇编确认该函数全局只有 1 个调用点（0x4817454，Rebuild 内部），
    //          所以不会误伤其他流程。
    // 头部角色优先取 CURRENT_HEAD_CHARA（混搭配置），否则用身体的目标角色
    let head_override = super::super::umamusume::CharacterBuildInfo::CURRENT_HEAD_CHARA
        .load(Ordering::Relaxed);
    let body_target = super::super::umamusume::CharacterBuildInfo::CURRENT_TARGET_CHARA
        .load(Ordering::Relaxed);
    let target = if head_override > 0 { head_override } else { body_target };
    let use_id = if target > 0 && target != chara_id {
        target
    } else {
        chara_id
    };

    let ret = orig(use_id, sub_id);

    let n = N_HEAD.fetch_add(1, Ordering::Relaxed);
    if enabled() && n < 30 {
        if use_id != chara_id {
            info!(
                "[cbpath] head chara {} -> {} (纠正) sub={} -> {}",
                chara_id,
                use_id,
                sub_id,
                cue_str(ret)
            );
        } else {
            info!("[cbpath] head chara={} sub={} -> {}", chara_id, sub_id, cue_str(ret));
        }
    }
    ret
}

extern "C" fn GetCharacterTailModelFilePath(chara_id: i32, arg: *mut Il2CppObject) -> *mut Il2CppString {
    let orig: TailFn = unsafe { std::mem::transmute(ORIG_TAIL.load(Ordering::Relaxed)) };

    let target = super::super::umamusume::CharacterBuildInfo::CURRENT_TARGET_CHARA
        .load(Ordering::Relaxed);
    let use_id = if target > 0 && target != chara_id {
        target
    } else {
        chara_id
    };

    let ret = orig(use_id, arg);

    let n = N_TAIL.fetch_add(1, Ordering::Relaxed);
    if enabled() && n < 30 {
        if use_id != chara_id {
            info!("[cbpath] tail chara {} -> {} (纠正) -> {}", chara_id, use_id, cue_str(ret));
        } else {
            info!("[cbpath] tail chara={} -> {}", chara_id, cue_str(ret));
        }
    }
    ret
}

pub fn init(umamusume: *const Il2CppImage) {
    let Ok(k) = get_class(umamusume, c"Gallop", c"CharacterBuildPathInfo") else {
        warn!("[cbpath] CharacterBuildPathInfo 未找到");
        return;
    };

    let hachimi = crate::core::Hachimi::instance();

    let head = get_method_addr(k, c"GetCharacterHeadModelFilePath", 2);
    if head != 0 {
        match hachimi.interceptor.hook(head, GetCharacterHeadModelFilePath as *const () as usize) {
            Ok(t) => {
                ORIG_HEAD.store(t, Ordering::SeqCst);
                info!("[cbpath] hooked GetCharacterHeadModelFilePath @ {:#x}", head);
            }
            Err(e) => error!("[cbpath] hook head 失败: {}", e),
        }
    } else {
        warn!("[cbpath] GetCharacterHeadModelFilePath 地址为空");
    }

    let tail = get_method_addr(k, c"GetCharacterTailModelFilePath", 2);
    if tail != 0 {
        match hachimi.interceptor.hook(tail, GetCharacterTailModelFilePath as *const () as usize) {
            Ok(t) => {
                ORIG_TAIL.store(t, Ordering::SeqCst);
                info!("[cbpath] hooked GetCharacterTailModelFilePath @ {:#x}", tail);
            }
            Err(e) => error!("[cbpath] hook tail 失败: {}", e),
        }
    } else {
        warn!("[cbpath] GetCharacterTailModelFilePath 地址为空");
    }
}
