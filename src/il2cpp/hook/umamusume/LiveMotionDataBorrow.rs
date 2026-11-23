// Live（演唱会）动作数据借用 —— 模型跟目标角色，动作/文本/表情跟原角色
//
// ## 为什么挂在这里
//
// Live 的动作**完全由 master 的 `character_system_text` 驱动**：
//
//   Director.RegisterSystemTextMotion(register, buildInfo, systemTextId)      // 预加载
//     → MasterCharacterSystemText.GetBySystemTextId(buildInfo._charaId, id)  // Director.cs:7728
//   LiveModelController.ChangeSystemTextAnimation                            // 播放
//     → MasterCharacterSystemText.GetBySystemTextId(charaId, id)             // LiveModelController.cs:2626 / 3068
//
// 拿到记录后再用它的 `motion_set` 查 `chara_motion_set` 得到 body_motion /
// body_motion_type / tail_motion。也就是说：**查不到记录 = 没有动作**，
// 而且预加载与播放走的是同一个入口。
//
// 实测数据（master.mdb）：`character_system_text` 里 1004 有 20000–20010 一整套，
// 1001 有，**2005 一条都没有**。所以原始 2005 在 Live 里同样没有动作 ——
// 这是角色自身缺数据，不是替换造成的。
//
// ## 方案
//
// 替换后的 BuildInfo 里 `_charaId` 是目标角色（例如 2005）。这里把查询用的
// charaId 映射回原角色（1004）：
//
//   | 用途 | 角色 | 由谁决定 |
//   |---|---|---|
//   | 模型（头/身/尾巴） | 目标角色 | BuildInfo 的 `_charaId`（本 hook 不改） |
//   | 动作数据（motion_set） | 原角色 | **本 hook** |
//   | 动作资源路径 | 原角色 | `LiveUtil::CreateSystemTextMotionBuildInfo` |
//
// 三者合起来就是「模型用目标角色，其余全用原角色」。资源不需要额外预加载：
// 路径指向原角色后，游戏的下载注册与加载流程会自己把原角色的 AB 拉进来。
//
// 开关：复用 `replace_motion`（语义 = 动作沿用原角色）。场景范围是全场景 ——
// 只有 `chara_id` 命中配置的场景才会映射；Q 版（Mini，ctrl=13）例外，
// 它用 `mchr/mbdy` 独立资源，借用普通角色的系统文本会错位。

use std::sync::atomic::{AtomicI32, AtomicUsize, Ordering};

use crate::{
    core::Hachimi,
    il2cpp::{
        hook::umamusume::CharacterBuildInfo::CURRENT_CONTROLLER_TYPE,
        symbols::{get_class, get_method_addr},
        types::*,
    },
};

const CTRL_MINI: i32 = 0xd;

/// 全场景生效：替换后动作数据一律跟随原角色，模型跟随目标角色。
///
/// 不需要按控制器类型白名单限制 —— 只有 `chara_id` 命中配置 `new_char_id`
/// 的查询才会被映射，而替换本身在 Default / HomeTalk / HomeWalk / Mini
/// 这几个场景里已经被 `CharacterBuildInfo::is_replacable` 挡掉了，
/// 天然不会命中。唯一保留的例外是 Q 版（Mini）：mini 用的是
/// `mchr/mbdy` 那套独立资源与动作，借用普通角色的系统文本会错位。
fn motion_borrow_allowed(ctrl: i32) -> bool {
    ctrl != CTRL_MINI
}

static ORIG_GET_BY_SYSTEM_TEXT_ID: AtomicUsize = AtomicUsize::new(0);
static LOGGED: AtomicI32 = AtomicI32::new(0);
static MISSES: AtomicI32 = AtomicI32::new(0);

/// 目标角色 → 原角色。未命中配置时返回 None（原样放行）。
fn motion_source_chara_id(chara_id: i32) -> Option<i32> {
    let cfg = Hachimi::instance().config.load();
    let cr = &cfg.replace_global_char;
    if !cr.enable || !cr.replace_motion {
        return None;
    }
    cr.data
        .iter()
        .find(|e| {
            e.new_char_id == chara_id && e.orig_char_id > 0 && e.orig_char_id != chara_id
        })
        .map(|e| e.orig_char_id)
}

/// `MasterCharacterSystemText.GetBySystemTextId(charaId, systemTextId)`
///
/// il2cpp 的静态方法在 ARM64 上会额外接收一个隐藏的 `MethodInfo*` 参数
/// （第三个寄存器 x2）。原实现只声明两个参数，在安卓上调用 trampoline 时
/// 该参数是垃圾值，方法内部的字典/字符串拷贝（memcpy）直接越界 ——
/// 表现为加载到 100% 时 SIGSEGV。这里把 `method` 显式透传，
/// Windows 上多传一个参数无影响。
type GetBySystemTextIdFn =
    extern "C" fn(chara_id: i32, system_text_id: i32, method: *mut std::ffi::c_void) -> *mut Il2CppObject;

extern "C" fn GetBySystemTextId(
    chara_id: i32,
    system_text_id: i32,
    method: *mut std::ffi::c_void,
) -> *mut Il2CppObject {
    let orig: GetBySystemTextIdFn = unsafe {
        std::mem::transmute(ORIG_GET_BY_SYSTEM_TEXT_ID.load(Ordering::Acquire))
    };

    let Some(orig_chara) = motion_source_chara_id(chara_id) else {
        return orig(chara_id, system_text_id, method);
    };

    let ctrl = CURRENT_CONTROLLER_TYPE.load(Ordering::Acquire);
    if !motion_borrow_allowed(ctrl) {
        return orig(chara_id, system_text_id, method);
    }

    let ret = orig(orig_chara, system_text_id, method);
    if ret.is_null() {
        let n = MISSES.fetch_add(1, Ordering::Relaxed);
        if n < 20 {
            warn!(
                "[live-motion-data] 原角色 {} 也没有 systemText={} 的记录（模型 {} 会没有这条动作）",
                orig_chara, system_text_id, chara_id
            );
        }
    } else {
        let n = LOGGED.fetch_add(1, Ordering::Relaxed);
        if n < 40 {
            info!(
                "[live-motion-data] master {} -> {} systemText={} ctrl={}",
                chara_id, orig_chara, system_text_id, ctrl
            );
        }
    }
    ret
}

pub fn init(umamusume: *const Il2CppImage) {
    let Ok(k) = get_class(umamusume, c"Gallop", c"MasterCharacterSystemText") else {
        warn!("[live-motion-data] MasterCharacterSystemText 未找到");
        return;
    };
    let addr = get_method_addr(k, c"GetBySystemTextId", 2);
    if addr == 0 {
        warn!("[live-motion-data] GetBySystemTextId 地址为空");
        return;
    }
    match Hachimi::instance()
        .interceptor
        .hook(addr, GetBySystemTextId as *const () as usize)
    {
        Ok(trampoline) => {
            ORIG_GET_BY_SYSTEM_TEXT_ID.store(trampoline, Ordering::Release);
            info!("[live-motion-data] hooked MasterCharacterSystemText.GetBySystemTextId @ {:#x}", addr);
        }
        Err(e) => error!("[live-motion-data] hook 安装失败: {}", e),
    }
}
