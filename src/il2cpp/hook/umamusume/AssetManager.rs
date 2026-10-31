use std::sync::atomic::{AtomicBool, Ordering};

use crate::{
    core::Hachimi,
    il2cpp::{
        ext::{Il2CppObjectExt, Il2CppStringExt, StringExt},
        hook::umamusume::{CharacterBuildInfo, CharacterBuildInfo::UmaControllerType},
        symbols::{get_method_addr, get_assembly_image, get_class, invoke_object_method},
        types::*
    }
};

static mut CLASS: *mut Il2CppClass = 0 as _;
pub fn class() -> *mut Il2CppClass {
    unsafe { CLASS }
}

static mut GET_LOADER_ADDR: usize = 0;
impl_addr_wrapper_fn!(get_Loader, GET_LOADER_ADDR, *mut Il2CppObject,);

pub fn LoadAssetHandle(this: *mut Il2CppObject, path: *mut Il2CppString, flag: bool) -> *mut Il2CppObject {
    let mut params: [*mut std::ffi::c_void; 2] = [path as *mut _, &flag as *const _ as *mut _];
    invoke_object_method(this, c"LoadAssetHandle", 2, &mut params).unwrap_or(std::ptr::null_mut())
}

static mut GET_ASSETBUNDLE_ADDR: usize = 0;
impl_addr_wrapper_fn!(get_assetBundle, GET_ASSETBUNDLE_ADDR, *mut Il2CppObject, this: *mut Il2CppObject);

static LOADER_HOOK_INSTALLED: AtomicBool = AtomicBool::new(false);

fn install_load_asset_handle_hook(loader: *mut Il2CppObject) {
    if LOADER_HOOK_INSTALLED.load(Ordering::Acquire) || loader.is_null() {
        return;
    }

    unsafe {
        let loader_class = (*loader).klass();
        if loader_class.is_null() {
            return;
        }
        let class_name = std::ffi::CStr::from_ptr((*loader_class).name)
            .to_str()
            .unwrap_or("?");

        let addr = get_method_addr(loader_class, c"LoadAssetHandle", 2);
        if addr == 0 {
            warn!("[charres] LoadAssetHandle 不在 {} 上，稍后重试", class_name);
            return;
        }

        LOADER_HOOK_INSTALLED.store(true, Ordering::Release);
        debug!("[charres] LoadAssetHandle 已挂钩于 {}", class_name);
        new_hook!(addr, LoadAssetHandle_hook);
    }
}

type GetLoaderFn = extern "C" fn() -> *mut Il2CppObject;
extern "C" fn get_Loader_hook() -> *mut Il2CppObject {
    let loader = get_orig_fn!(get_Loader_hook, GetLoaderFn)();
    install_load_asset_handle_hook(loader);
    loader
}

type LoadAssetHandleFn = extern "C" fn(this: *mut Il2CppObject, path: *mut Il2CppString, flag: bool) -> *mut Il2CppObject;

/// 过场里的角色模型重映射。
///
/// 过场（EventTimeline / CutIn）**不能改角色 ID** —— Timeline 的轨道绑定和演出数据都是按
/// 角色预制好的，ID 对不上会让游戏卡死或模型整个消失。所以这里只把加载路径里的角色 ID
/// 换成目标角色的：模型、服装、贴图整套跟着换，游戏看到的数据层仍然是原角色。
fn remap_cutscene_char_asset(path: &str) -> Option<String> {
    let config = Hachimi::instance().config.load();
    let repl = &config.replace_global_char;
    if !repl.enable || !repl.replace_model_in_cutscene {
        return None;
    }

    // 只处理角色相关资源。
    let is_char_res = path.contains("3d/chara/")
        || path.contains("3d/motion/")
        || path.contains("chara/chr")
        || path.starts_with("chara/");
    if !is_char_res {
        return None;
    }

    // 图标 / 2D petit / 3D mini 一律不替换。
    // NPC 和未实装角色没有这三类资源，换过去会让资源加载挂住。
    if path.contains("chr_icon_") || path.contains("/petit/") || path.contains("/mini/") {
        return None;
    }

    // ★ 分部位：head 与 body 可以用不同的目标角色。
    //
    //   路径规律（实测）：
    //     3d/chara/body/bdy{id}_{sub}/...        身体
    //     3d/chara/head/chr{id}_{sub}/...        头部
    //     3d/chara/tail/tail{type}_{sub}/...     尾巴
    //     3d/motion/event/body/chara/chr{id}_00/ 动作
    //
    //   配置里 `head_char_id > 0` 时头部单独用它，否则跟随 `new_char_id`。
    //   这样就能做「A 的头 + B 的身体」。
    let is_head = path.contains("/head/");
    let is_motion = path.contains("3d/motion/");

    for entry in repl.data.iter() {
        let old = entry.orig_char_id;
        let body_target = entry.new_char_id;
        if old <= 0 || body_target <= 0 {
            continue;
        }

        // 头部目标：优先 head_char_id，没配就跟身体一致。
        let head_target = if entry.head_char_id > 0 {
            entry.head_char_id
        } else {
            body_target
        };

        // 选这个部位要用哪个目标 ID
        let target = if is_head { head_target } else { body_target };

        if target == old {
            continue;
        }

        // 路径里的角色 ID 有几种写法，按部位分别替换。
        //
        //   注意 `_{old}_` 这种形式（tex_tail0001_00_1003_diff）会同时命中
        //   body 和 head 的贴图，所以只在 body 分支里用，且放在最后。
        let pairs: Vec<(String, String)> = if is_head {
            vec![
                (format!("chr{old}_"), format!("chr{target}_")),
                (format!("chr{old}/"), format!("chr{target}/")),
                (format!("chr_{old}_"), format!("chr_{target}_")),
            ]
        } else if is_motion {
            // 动作路径按角色分包，跟身体走还是跟头走取决于配置。
            // 默认跟身体；`keep_original_motion` 时不换（由调用方保证不进来）。
            vec![
                (format!("chr{old}_"), format!("chr{target}_")),
                (format!("chr{old}/"), format!("chr{target}/")),
            ]
        } else {
            // body / tail / 贴图
            vec![
                (format!("bdy{old}_"), format!("bdy{target}_")),
                (format!("bdy{old}/"), format!("bdy{target}/")),
                (format!("chr{old}_"), format!("chr{target}_")),
                (format!("chr{old}/"), format!("chr{target}/")),
                (format!("tail{old}_"), format!("tail{target}_")),
                (format!("_{old}_"), format!("_{target}_")),
            ]
        };

        let mut out = path.to_string();
        let mut hit = false;
        for (oa, na) in &pairs {
            if out.contains(oa.as_str()) {
                out = out.replace(oa.as_str(), na.as_str());
                hit = true;
            }
        }

        if hit && out != path {
            warn!(
                "[charres] {} 替换 {} -> {}",
                if is_head { "head" } else if is_motion { "motion" } else { "body" },
                path,
                out
            );
            return Some(out);
        }
    }

    None
}

extern "C" fn LoadAssetHandle_hook(this: *mut Il2CppObject, path: *mut Il2CppString, flag: bool) -> *mut Il2CppObject {
    if !path.is_null() {
        let p = unsafe { (*path).as_utf16str() }.to_string();
        let low = p.to_lowercase();
        let logged = low.contains("3d/chara") || low.contains("bdy") || low.contains("chr");
        if logged {
            let ctrl = CharacterBuildInfo::CURRENT_CONTROLLER_TYPE.load(Ordering::Acquire);
            warn!("[charres] ctrl={:<9} {}", ctrl, p);
        }

        if let Some(remapped) = remap_cutscene_char_asset(&p) {
            // ★ 记录替换路径的加载耗时。
            //   游戏卡住时，最后一个「开始」没有对应的「完成」就是元凶。
            let t0 = std::time::Instant::now();
            warn!("[charres] >>> 开始加载 {}", remapped);
            let h = get_orig_fn!(LoadAssetHandle_hook, LoadAssetHandleFn)(
                this, remapped.to_il2cpp_string(), flag
            );
            warn!(
                "[charres] <<< 结束加载 {}  耗时 {:?}  返回={}",
                remapped,
                t0.elapsed(),
                if h.is_null() { "null" } else { "ok" }
            );
            return h;
        }

        if logged {
            let t0 = std::time::Instant::now();
            let h = get_orig_fn!(LoadAssetHandle_hook, LoadAssetHandleFn)(this, path, flag);
            let ms = t0.elapsed().as_millis();
            if ms >= 200 {
                warn!("[charres] (原路径) {} 耗时 {}ms", p, ms);
            }
            return h;
        }
    }

    get_orig_fn!(LoadAssetHandle_hook, LoadAssetHandleFn)(this, path, flag)
}

pub fn init(umamusume: *const Il2CppImage) {
    get_class_or_return!(umamusume, Gallop, AssetManager);

    unsafe {
        CLASS = AssetManager;
        GET_LOADER_ADDR = get_method_addr(AssetManager, c"get_Loader", 0);
    }

    if let Ok(cyan_image) = get_assembly_image(c"_Cyan.dll") {
        if let Ok(asset_handle_class) = get_class(cyan_image, c"Cyan.Loader", c"AssetHandle") {
            unsafe {
                GET_ASSETBUNDLE_ADDR = get_method_addr(asset_handle_class, c"get_assetBundle", 0);
            }
        } else {
            error!("Failed to find AssetHandle class in _Cyan.dll");
        }
    } else {
        error!("Failed to load _Cyan.dll assembly");
    }

    unsafe {
        new_hook!(GET_LOADER_ADDR, get_Loader_hook);
    }
}
