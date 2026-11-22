// 抽卡演出横幅（星级 / 角色名 / 「新！」）不显示。
//
// 早期是「机器学习 + 事件拦截」，已整体移除（黑名单会跨会话累积、隐藏过的对象不会恢复）。
//
// 现在的拦截点来自源码（`umamusume.dll` 反编译）：
//
//   // GachaFlashCharaNamePlate
//   public static void PlayIn(object context, int pageIndex)
//   {
//       object obj11 = ((byte*)context + 0x50)[0];       // flash holder
//       object obj15 = obj11.GetFromName(obj14);         // 按星级挑名字 flash
//       GallopGameObjectExtensions.SetActiveWithCheck(obj15, true);   // ← 真正让它出现
//       obj15.Play(0x17e30a6e0, 0);
//   }
//
// 也就是说横幅是 **PlayIn 直接 SetActive(true) 播的**，跟 `Setup()` 没关系。
// `Setup()` 只负责注册 label 回调（PlayInLabel / PlayInPiece00Label /
// PlayInPiece01Label），那些回调才给名字贴图与碎片赋值 ——
// 早先误拦 `Setup` 的后果是「文本没人写 → 显示 [12345678901234] 占位符，
// 横幅照样出现」，也就是「没屏蔽，但被污染了」。所以 Setup 必须照常跑。
//
// 拦 `PlayIn` 才是从源头不让它显示；「新！」角标由实例方法 `PlayNewLabel`
// 挂 `pf_fl_gacha_icon_new00`（由 in_chara 等 label 回调触发），单独拦。

use std::sync::atomic::{AtomicUsize, Ordering};

use crate::{
    core::Hachimi,
    il2cpp::{
        symbols::{get_class, get_method_addr},
        types::*,
    },
};

static ORIG_NAME_PLAY_IN: AtomicUsize = AtomicUsize::new(0);
static ORIG_SUPPORT_PLAY_IN: AtomicUsize = AtomicUsize::new(0);
static ORIG_NEW_LABEL: AtomicUsize = AtomicUsize::new(0);
static N_SKIP: AtomicUsize = AtomicUsize::new(0);

type PlayInFn = extern "C" fn(context: *mut Il2CppObject, page_index: i32);
type PlayNewLabelFn = extern "C" fn(this: *mut Il2CppObject);

fn suppressed() -> bool {
    Hachimi::instance().config.load().cutin_block_ui_events
}

fn note(tag: &str) {
    let n = N_SKIP.fetch_add(1, Ordering::Relaxed);
    if n < 8 {
        info!("[banner] 跳过 {} #{}", tag, n + 1);
    }
}

extern "C" fn name_plate_play_in(context: *mut Il2CppObject, page_index: i32) {
    if suppressed() {
        note("GachaFlashCharaNamePlate.PlayIn");
        return;
    }
    let orig: PlayInFn = unsafe { std::mem::transmute(ORIG_NAME_PLAY_IN.load(Ordering::Relaxed)) };
    orig(context, page_index);
}

extern "C" fn support_play_in(context: *mut Il2CppObject, page_index: i32) {
    if suppressed() {
        note("GachaFlashSupportCard.PlayIn");
        return;
    }
    let orig: PlayInFn = unsafe { std::mem::transmute(ORIG_SUPPORT_PLAY_IN.load(Ordering::Relaxed)) };
    orig(context, page_index);
}

extern "C" fn play_new_label(this: *mut Il2CppObject) {
    if suppressed() {
        note("GachaFlashCharaNamePlate.PlayNewLabel");
        return;
    }
    let orig: PlayNewLabelFn = unsafe { std::mem::transmute(ORIG_NEW_LABEL.load(Ordering::Relaxed)) };
    orig(this);
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
        warn!("[banner] {} 地址为空", tag);
        return;
    }
    let h = Hachimi::instance();
    match h.interceptor.hook(addr, detour) {
        Ok(t) => {
            slot.store(t, Ordering::SeqCst);
            info!("[banner] hooked {} @ {:#x}", tag, addr);
        }
        Err(e) => error!("[banner] hook {} 失败: {}", tag, e),
    }
}

pub fn init(umamusume: *const Il2CppImage) {
    if let Ok(k) = get_class(umamusume, c"Gallop", c"GachaFlashCharaNamePlate") {
        hook_one(
            k,
            c"PlayIn",
            2,
            name_plate_play_in as *const () as usize,
            &ORIG_NAME_PLAY_IN,
            "GachaFlashCharaNamePlate.PlayIn",
        );
        hook_one(
            k,
            c"PlayNewLabel",
            0,
            play_new_label as *const () as usize,
            &ORIG_NEW_LABEL,
            "GachaFlashCharaNamePlate.PlayNewLabel",
        );
    } else {
        warn!("[banner] GachaFlashCharaNamePlate 未找到");
    }

    if let Ok(k) = get_class(umamusume, c"Gallop", c"GachaFlashSupportCard") {
        hook_one(
            k,
            c"PlayIn",
            2,
            support_play_in as *const () as usize,
            &ORIG_SUPPORT_PLAY_IN,
            "GachaFlashSupportCard.PlayIn",
        );
    } else {
        warn!("[banner] GachaFlashSupportCard 未找到");
    }
}
