// 套动作探针 —— 定位「A 用 B 的动作」的可行 hook 点
//
// 目标：Gallop.OutgameSwapMotionData.GetOutgameSwapMotionPath（非比赛场景：主页/过场）
//       Gallop.RaceSwapMotionData 下同名的几个方法（比赛场景）
//
// 反汇编确认的调用约定（调用点 0x34665A0）：
//   rcx = this（OutgameSwapMotionData 实例）
//   rdx = arg1（指针，来自 0x348FD00 的返回值）
//   r8d = arg2（int，从栈 [rsp+0x70] 取）
//   r9d = arg3（int，固定 0）
//   [rsp+0x20] = arg4（int，= r15d）
//   → String
//
// 游戏自带的 SwapData 结构（typedump.cs）：
//   SwapDataBase { DressId  +0x10 }
//   SwapData : SwapDataBase {
//       MotionName      +0x18  原动作名
//       SwapMotionName  +0x20  替换后的动作名
//       MotionType      +0x28
//       CharaId         +0x2C
//   }
//   OutgameSwapMotionData { SwapDataArray +0x20 }
//
// 也就是说游戏本身支持「角色+服装 → 换成另一套动作」，配置表是 ScriptableObject。
// 探针先把实际参数和返回值打出来，确认 arg2/arg4 谁是 charaId 谁是 dressId。
//
// 开关：HACHIMI_SWAPMOTION_PROBE=0 关闭（默认开）

use std::sync::atomic::{AtomicUsize, Ordering};

use crate::il2cpp::{
    ext::Il2CppStringExt,
    symbols::{get_class, get_method_addr},
    types::*,
};

static ORIG_OUTGAME: AtomicUsize = AtomicUsize::new(0);
static N_OUTGAME: AtomicUsize = AtomicUsize::new(0);

fn enabled() -> bool {
    std::env::var("HACHIMI_SWAPMOTION_PROBE").ok().as_deref() != Some("0")
}

fn s(p: *mut Il2CppString) -> String {
    if p.is_null() {
        return "<null>".into();
    }
    unsafe { &*p }.as_utf16str().to_string()
}

// this, arg1(ptr), arg2(i32), arg3(i32), arg4(i32) -> String
type OutgameFn = extern "C" fn(
    this: *mut Il2CppObject,
    a1: *mut Il2CppObject,
    a2: i32,
    a3: i32,
    a4: i32,
) -> *mut Il2CppString;

extern "C" fn GetOutgameSwapMotionPath(
    this: *mut Il2CppObject,
    a1: *mut Il2CppObject,
    a2: i32,
    a3: i32,
    a4: i32,
) -> *mut Il2CppString {
    let orig: OutgameFn = unsafe { std::mem::transmute(ORIG_OUTGAME.load(Ordering::Relaxed)) };
    let ret = orig(this, a1, a2, a3, a4);

    let n = N_OUTGAME.fetch_add(1, Ordering::Relaxed);
    if enabled() && n < 40 {
        // a1 的类型不确定，按 String 试读；读到乱码也无所谓，关键看 a2/a3/a4 和返回值
        let a1s = if a1.is_null() {
            "<null>".to_string()
        } else {
            s(a1 as *mut Il2CppString)
        };
        info!(
            "[swapmotion] outgame a1={:?}({}) a2={} a3={} a4={} -> {}",
            a1, a1s, a2, a3, a4, s(ret)
        );
    }
    ret
}

pub fn init(umamusume: *const Il2CppImage) {
    let hachimi = crate::core::Hachimi::instance();

    if let Ok(k) = get_class(umamusume, c"Gallop", c"OutgameSwapMotionData") {
        let addr = get_method_addr(k, c"GetOutgameSwapMotionPath", 4);
        if addr != 0 {
            match hachimi.interceptor.hook(addr, GetOutgameSwapMotionPath as *const () as usize) {
                Ok(t) => {
                    ORIG_OUTGAME.store(t, Ordering::SeqCst);
                    info!("[swapmotion] hooked GetOutgameSwapMotionPath @ {:#x}", addr);
                }
                Err(e) => error!("[swapmotion] hook 失败: {}", e),
            }
        } else {
            warn!("[swapmotion] GetOutgameSwapMotionPath 地址为空");
        }
    } else {
        warn!("[swapmotion] OutgameSwapMotionData 未找到");
    }
}
