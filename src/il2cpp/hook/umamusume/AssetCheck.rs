// 资源存在性查询（Gallop.ResourceManager.IsExistAsset，静态 1 参）。
//
// 替换动作/模型时先问一句「目标角色有没有这条资源」：有就换成目标角色的，
// 没有就保留原角色的。这样既能让动作跟模型，又不会因为缺资源触发
// `LoadMotionClip` 的 null 分支（Error0003 回标题）。

use std::sync::atomic::{AtomicUsize, Ordering};

use crate::il2cpp::{
    ext::StringExt,
    symbols::{get_class, get_method_addr},
    types::*,
};

static ADDR: AtomicUsize = AtomicUsize::new(0);

type Fn1 = extern "C" fn(path: *mut Il2CppString) -> bool;

pub fn is_exist(path: &str) -> Option<bool> {
    let addr = ADDR.load(Ordering::Relaxed);
    if addr == 0 || path.is_empty() {
        return None;
    }
    let f: Fn1 = unsafe { std::mem::transmute(addr) };
    Some(f(path.to_il2cpp_string()))
}

pub fn init(umamusume: *const Il2CppImage) {
    let Ok(k) = get_class(umamusume, c"Gallop", c"ResourceManager") else {
        warn!("[exist] ResourceManager 未找到");
        return;
    };
    let addr = get_method_addr(k, c"IsExistAsset", 1);
    if addr == 0 {
        warn!("[exist] IsExistAsset 地址为空");
    } else {
        ADDR.store(addr, Ordering::SeqCst);
        info!("[exist] IsExistAsset @ {:#x}", addr);
    }
}
