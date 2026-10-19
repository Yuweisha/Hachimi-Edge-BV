use crate::{
    core::Hachimi,
    il2cpp::{symbols::{get_class, get_method_addr}, types::*}
};

// ---- Cut-in FOV (runtime scale from main-menu slider) ----
pub static CUTIN_FOV_RT: std::sync::atomic::AtomicU32 = std::sync::atomic::AtomicU32::new(0x3F800000);
pub fn fov_rt() -> f32 { f32::from_bits(CUTIN_FOV_RT.load(std::sync::atomic::Ordering::Relaxed)) }
pub fn set_fov_rt(v: f32) { CUTIN_FOV_RT.store(v.to_bits(), std::sync::atomic::Ordering::Relaxed); }

// ---- Cut-in progress bar data source ----
pub static CUTIN_CTRL: std::sync::atomic::AtomicUsize = std::sync::atomic::AtomicUsize::new(0);
pub static CUTIN_TICK: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);
pub static CUTIN_TOTAL_BITS: std::sync::atomic::AtomicU32 = std::sync::atomic::AtomicU32::new(0);
pub static CUTIN_TOTAL_OWNER: std::sync::atomic::AtomicUsize = std::sync::atomic::AtomicUsize::new(0);

fn now_ms() -> u64 {
    std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).map(|d| d.as_millis() as u64).unwrap_or(0)
}

pub fn cutin_active() -> bool {
    let t = CUTIN_TICK.load(std::sync::atomic::Ordering::Relaxed);
    t > 0 && now_ms().saturating_sub(t) < 600
}

pub fn cutin_current_time() -> f32 {
    let p = CUTIN_CTRL.load(std::sync::atomic::Ordering::Relaxed);
    if p == 0 { return 0.0; }
    unsafe { *((p as *const u8).add(0x538) as *const f32) }
}

pub fn cutin_total_time() -> f32 {
    f32::from_bits(CUTIN_TOTAL_BITS.load(std::sync::atomic::Ordering::Relaxed))
}

pub static CUTIN_PAUSED: std::sync::atomic::AtomicBool = std::sync::atomic::AtomicBool::new(false);

pub fn cutin_is_paused() -> bool {
    CUTIN_PAUSED.load(std::sync::atomic::Ordering::Relaxed)
}

pub fn cutin_seek(target: f32) {
    unsafe {
        let p = CUTIN_CTRL.load(std::sync::atomic::Ordering::Relaxed);
        warn!("[cutin] seek t={:.3} ctrl={:#x}", target, p);
        if p == 0 { return; }
        let this = p as *mut Il2CppObject;
        let k = *(this as *const *mut Il2CppClass);
        if k.is_null() { return; }
        let mp = crate::il2cpp::api::il2cpp_class_get_method_from_name(k, c"Pause".as_ptr(), 1);
        let mplay = crate::il2cpp::api::il2cpp_class_get_method_from_name(k, c"set_IsPlaying".as_ptr(), 1);
        warn!("[cutin] pause: ctrl={:#x} Pause={} set_IsPlaying={}", p, !mp.is_null(), !mplay.is_null());
        if !mp.is_null() {
            let mut v = true;
            let args: [*mut std::ffi::c_void; 1] = [&mut v as *mut bool as *mut std::ffi::c_void];
            crate::il2cpp::api::il2cpp_runtime_invoke(mp, this as *mut std::ffi::c_void, args.as_ptr() as *mut *mut std::ffi::c_void, std::ptr::null_mut());
        }
        if !mplay.is_null() {
            let mut f = false;
            let args: [*mut std::ffi::c_void; 1] = [&mut f as *mut bool as *mut std::ffi::c_void];
            crate::il2cpp::api::il2cpp_runtime_invoke(mplay, this as *mut std::ffi::c_void, args.as_ptr() as *mut *mut std::ffi::c_void, std::ptr::null_mut());
        }
        let ms = crate::il2cpp::api::il2cpp_class_get_method_from_name(k, c"SetCurrentTime".as_ptr(), 1);
        warn!("[cutin] seek: Pause={} SetCurrentTime={}", !mp.is_null(), !ms.is_null());
        if !ms.is_null() {
            let mut t = target;
            let args: [*mut std::ffi::c_void; 1] = [&mut t as *mut f32 as *mut std::ffi::c_void];
            crate::il2cpp::api::il2cpp_runtime_invoke(ms, this as *mut std::ffi::c_void, args.as_ptr() as *mut *mut std::ffi::c_void, std::ptr::null_mut());
        }
        let me = crate::il2cpp::api::il2cpp_class_get_method_from_name(k, c"EffectSimulateToCurrentFrame".as_ptr(), 0);
        if !me.is_null() {
            crate::il2cpp::api::il2cpp_runtime_invoke(me, this as *mut std::ffi::c_void, std::ptr::null_mut(), std::ptr::null_mut());
        }
    }
}


pub fn cutin_play() {
    unsafe {
        let p = CUTIN_CTRL.load(std::sync::atomic::Ordering::Relaxed);
        if p == 0 { return; }
        let this = p as *mut Il2CppObject;
        let k = *(this as *const *mut Il2CppClass);
        if k.is_null() { return; }
        let mp = crate::il2cpp::api::il2cpp_class_get_method_from_name(k, c"Pause".as_ptr(), 1);
        let mplay = crate::il2cpp::api::il2cpp_class_get_method_from_name(k, c"set_IsPlaying".as_ptr(), 1);
        let mwait = crate::il2cpp::api::il2cpp_class_get_method_from_name(k, c"set_IsWaiting".as_ptr(), 1);
        warn!(
            "[cutin] play: ctrl={:#x} Pause={} set_IsPlaying={} set_IsWaiting={}",
            p, !mp.is_null(), !mplay.is_null(), !mwait.is_null()
        );
        if !mp.is_null() {
            let mut v = false;
            let args: [*mut std::ffi::c_void; 1] = [&mut v as *mut bool as *mut std::ffi::c_void];
            crate::il2cpp::api::il2cpp_runtime_invoke(mp, this as *mut std::ffi::c_void, args.as_ptr() as *mut *mut std::ffi::c_void, std::ptr::null_mut());
        }
        for m in [mplay, mwait] {
            if m.is_null() {
                continue;
            }
            let mut t = true;
            let args: [*mut std::ffi::c_void; 1] = [&mut t as *mut bool as *mut std::ffi::c_void];
            crate::il2cpp::api::il2cpp_runtime_invoke(m, this as *mut std::ffi::c_void, args.as_ptr() as *mut *mut std::ffi::c_void, std::ptr::null_mut());
        }
        CUTIN_PAUSED.store(false, std::sync::atomic::Ordering::Relaxed);
        warn!("[cutin] play");
    }
}

pub fn cutin_pause() {
    unsafe {
        let p = CUTIN_CTRL.load(std::sync::atomic::Ordering::Relaxed);
        if p == 0 { return; }
        let this = p as *mut Il2CppObject;
        let k = *(this as *const *mut Il2CppClass);
        if k.is_null() { return; }

        let mp = crate::il2cpp::api::il2cpp_class_get_method_from_name(k, c"Pause".as_ptr(), 1);
        if !mp.is_null() {
            let mut v = true;
            let args: [*mut std::ffi::c_void; 1] = [&mut v as *mut bool as *mut std::ffi::c_void];
            crate::il2cpp::api::il2cpp_runtime_invoke(mp, this as *mut std::ffi::c_void, args.as_ptr() as *mut *mut std::ffi::c_void, std::ptr::null_mut());
        }
        let mplay = crate::il2cpp::api::il2cpp_class_get_method_from_name(k, c"set_IsPlaying".as_ptr(), 1);
        if !mplay.is_null() {
            let mut f = false;
            let args: [*mut std::ffi::c_void; 1] = [&mut f as *mut bool as *mut std::ffi::c_void];
            crate::il2cpp::api::il2cpp_runtime_invoke(mplay, this as *mut std::ffi::c_void, args.as_ptr() as *mut *mut std::ffi::c_void, std::ptr::null_mut());
        }

        // Pause 只停主时钟，音效/动画脚本仍会跑。拖动时之所以能真冻住，是因为还做了
        // SetCurrentTime + EffectSimulateToCurrentFrame —— 这里补齐这两步。
        let cur = cutin_current_time();
        let ms = crate::il2cpp::api::il2cpp_class_get_method_from_name(k, c"SetCurrentTime".as_ptr(), 1);
        if !ms.is_null() && cur > 0.0 {
            let mut t = cur;
            let args: [*mut std::ffi::c_void; 1] = [&mut t as *mut f32 as *mut std::ffi::c_void];
            crate::il2cpp::api::il2cpp_runtime_invoke(ms, this as *mut std::ffi::c_void, args.as_ptr() as *mut *mut std::ffi::c_void, std::ptr::null_mut());
        }
        let me = crate::il2cpp::api::il2cpp_class_get_method_from_name(k, c"EffectSimulateToCurrentFrame".as_ptr(), 0);
        if !me.is_null() {
            crate::il2cpp::api::il2cpp_runtime_invoke(me, this as *mut std::ffi::c_void, std::ptr::null_mut(), std::ptr::null_mut());
        }

        CUTIN_PAUSED.store(true, std::sync::atomic::Ordering::Relaxed);
        warn!(
            "[cutin] pause at {:.3} (Pause={} set_IsPlaying={} SetCurrentTime={} Simulate={})",
            cur, !mp.is_null(), !mplay.is_null(), !ms.is_null(), !me.is_null()
        );
    }
}

pub fn cutin_resume() {
    unsafe {
        let p = CUTIN_CTRL.load(std::sync::atomic::Ordering::Relaxed);
        if p == 0 { return; }
        let this = p as *mut Il2CppObject;
        let k = *(this as *const *mut Il2CppClass);
        if k.is_null() { return; }
        let mp = crate::il2cpp::api::il2cpp_class_get_method_from_name(k, c"Pause".as_ptr(), 1);
        if !mp.is_null() {
            let mut v = false;
            let args: [*mut std::ffi::c_void; 1] = [&mut v as *mut bool as *mut std::ffi::c_void];
            crate::il2cpp::api::il2cpp_runtime_invoke(mp, this as *mut std::ffi::c_void, args.as_ptr() as *mut *mut std::ffi::c_void, std::ptr::null_mut());
        }
    }
}

unsafe fn read_object_field(obj: *mut Il2CppObject, name: &str) -> *mut Il2CppObject {
    if obj.is_null() { return std::ptr::null_mut(); }
    let klass = *(obj as *const *mut Il2CppClass);
    if klass.is_null() { return std::ptr::null_mut(); }
    let Ok(cn) = std::ffi::CString::new(name) else { return std::ptr::null_mut(); };
    let field = crate::il2cpp::api::il2cpp_class_get_field_from_name(klass, cn.as_ptr());
    if field.is_null() { return std::ptr::null_mut(); }
    let off = crate::il2cpp::api::il2cpp_field_get_offset(field);
    *((obj as *const u8).add(off) as *const *mut Il2CppObject)
}

unsafe fn read_il2cpp_string(s: *mut Il2CppString) -> String {
    if s.is_null() { return String::new(); }
    let p = s as usize;
    let len = *((p + 16) as *const i32);
    if len <= 0 || len > 400 { return String::new(); }
    let chars = std::slice::from_raw_parts((p + 20) as *const u16, len as usize);
    String::from_utf16_lossy(chars)
}

unsafe fn set_go_active(go: *mut Il2CppObject, active: bool) {
    if go.is_null() { return; }
    let klass = *(go as *const *mut Il2CppClass);
    if klass.is_null() { return; }
    let m = crate::il2cpp::api::il2cpp_class_get_method_from_name(klass, c"SetActive".as_ptr(), 1);
    if m.is_null() { return; }
    let mut v = active;
    let args: [*mut std::ffi::c_void; 1] = [&mut v as *mut bool as *mut std::ffi::c_void];
    crate::il2cpp::api::il2cpp_runtime_invoke(m, go as *mut std::ffi::c_void, args.as_ptr() as *mut *mut std::ffi::c_void, std::ptr::null_mut());
}

static TAG_OBJECTS: once_cell::sync::Lazy<std::sync::Mutex<Vec<usize>>> = once_cell::sync::Lazy::new(|| std::sync::Mutex::new(Vec::new()));

fn suppress_tag_objects() {
    let Ok(mut v) = TAG_OBJECTS.lock() else { return; };
    if v.is_empty() { return; }
    v.retain(|&p| {
        unsafe {
            let alive = crate::il2cpp::hook::UnityEngine_CoreModule::Object::IsNativeObjectAlive(p as *mut Il2CppObject);
            if alive {
                set_go_active(p as *mut Il2CppObject, false);
            }
            alive
        }
    });
}

fn is_tag_prefab(s: &str) -> bool {
    s.contains("gacha_icon_new") || s.contains("gacha_chara_name") || s.contains("gacha_chrname")
}

unsafe fn hide_cloned_tag(prefab: *mut Il2CppObject, cloned: *mut Il2CppObject) {
    if prefab.is_null() || cloned.is_null() { return; }
    let k = *(prefab as *const *mut Il2CppClass);
    if k.is_null() { return; }
    let mn = crate::il2cpp::api::il2cpp_class_get_method_from_name(k, c"get_name".as_ptr(), 0);
    if mn.is_null() { return; }
    let nr = crate::il2cpp::api::il2cpp_runtime_invoke(mn, prefab as *mut std::ffi::c_void, std::ptr::null_mut(), std::ptr::null_mut());
    if nr.is_null() { return; }
    let s = read_il2cpp_string(nr as *mut Il2CppString);
    if !is_tag_prefab(&s) { return; }
    set_go_active(cloned, false);
    if let Ok(mut v) = TAG_OBJECTS.lock() {
        if v.len() < 64 { v.push(cloned as usize); }
    }
}

type CloneSingleFn = extern "C" fn(prefab: *mut Il2CppObject, parent: *mut Il2CppObject, world: bool) -> *mut Il2CppObject;
extern "C" fn CloneSingle_hook(prefab: *mut Il2CppObject, parent: *mut Il2CppObject, world: bool) -> *mut Il2CppObject {
    let r = get_orig_fn!(CloneSingle_hook, CloneSingleFn)(prefab, parent, world);
    unsafe { hide_cloned_tag(prefab, r); }
    r
}

type CloneSingle1Fn = extern "C" fn(prefab: *mut Il2CppObject) -> *mut Il2CppObject;
extern "C" fn CloneSingle1_hook(prefab: *mut Il2CppObject) -> *mut Il2CppObject {
    let r = get_orig_fn!(CloneSingle1_hook, CloneSingle1Fn)(prefab);
    unsafe { hide_cloned_tag(prefab, r); }
    r
}

const BLOCKED_IDS: [i32; 8] = [61, 83, 126, 145, 173, 264, 281, 293];
static SHADOW_TRACK: once_cell::sync::Lazy<std::sync::Mutex<std::collections::HashMap<i32, (u64, u32)>>> =
    once_cell::sync::Lazy::new(|| std::sync::Mutex::new(std::collections::HashMap::new()));
static AUTO_BLOCK: once_cell::sync::Lazy<std::sync::Mutex<std::collections::HashSet<i32>>> =
    once_cell::sync::Lazy::new(|| std::sync::Mutex::new(std::collections::HashSet::new()));

fn shadow_file_path() -> Option<std::path::PathBuf> {
    let exe = std::env::current_exe().ok()?;
    Some(exe.parent()?.join("hachimi").join("cutin_shadow_frames.txt"))
}

pub fn load_shadow_frames() {
    if let Some(p) = shadow_file_path() {
        if let Ok(txt) = std::fs::read_to_string(&p) {
            let Ok(mut set) = AUTO_BLOCK.lock() else { return; };
            for line in txt.lines() {
                if let Ok(v) = line.trim().parse::<i32>() { set.insert(v); }
            }
            info!("[cutin] loaded {} shadow frames", set.len());
        }
    }
}

fn append_shadow_frame(id: i32) {
    if let Some(p) = shadow_file_path() {
        if let Some(dir) = p.parent() { let _ = std::fs::create_dir_all(dir); }
        if let Ok(mut f) = std::fs::OpenOptions::new().create(true).append(true).open(&p) {
            use std::io::Write;
            let _ = writeln!(f, "{}", id);
        }
    }
}

fn observe_shadow_frame(id: i32) {
    if id <= 0 { return; }
    let now = now_ms();
    let mut detect = false;
    if let Ok(mut m) = SHADOW_TRACK.lock() {
        let e = m.entry(id).or_insert((now, 0));
        if now.saturating_sub(e.0) <= 10000 {
            e.1 += 1;
            if e.1 == 10 { detect = true; e.1 = 11; }
        } else {
            *e = (now, 1);
        }
    }
    if detect {
        let fresh = { AUTO_BLOCK.lock().map(|mut s| s.insert(id)).unwrap_or(false) };
        if fresh {
            info!("[cutin] auto-block shadow frame {}", id);
            append_shadow_frame(id);
        }
    }
}

fn is_blocked_frame(id: i32) -> bool {
    if BLOCKED_IDS.contains(&id) { return true; }
    AUTO_BLOCK.lock().map(|s| s.contains(&id)).unwrap_or(false)
}

type FireEvent2Fn = extern "C" fn(this: *mut Il2CppObject, key: *mut Il2CppObject, b: bool) -> ();
extern "C" fn FireEvent2(this: *mut Il2CppObject, key: *mut Il2CppObject, b: bool) {
    unsafe {
        if !key.is_null() {
            let id = *((key as *const u8).add(0x10) as *const i32);
            observe_shadow_frame(id);
            if Hachimi::instance().config.load().cutin_block_ui_events && is_blocked_frame(id) {
                return;
            }
        }
    }
    get_orig_fn!(FireEvent2, FireEvent2Fn)(this, key, b)
}

type AlterLateUpdateFn = extern "C" fn(this: *mut Il2CppObject, pos: *mut std::ffi::c_void, rot: *mut std::ffi::c_void, sc: f32) -> ();
/// cutin 自由视角下我们独占的相机 transform（外部写入会被 Transform hook 拦掉）。
pub static CUTIN_CAM_TR: std::sync::atomic::AtomicUsize = std::sync::atomic::AtomicUsize::new(0);
/// 我们自己写相机时置位，避免被上一条规则挡住。
pub static CUTIN_SELF_WRITE: std::sync::atomic::AtomicBool = std::sync::atomic::AtomicBool::new(false);
static CUTIN_CAM_TRACE: std::sync::atomic::AtomicUsize = std::sync::atomic::AtomicUsize::new(0);
extern "C" fn CutInAlterLateUpdate(this: *mut Il2CppObject, pos: *mut std::ffi::c_void, rot: *mut std::ffi::c_void, sc: f32) {
    // 自由视角开启时压制游戏自带的相机计算：不调原函数，由我们独占写 transform。
    // 这样游戏不会在同一帧更晚的位置覆盖回去。
    let free_cam = Hachimi::instance().config.load().cutin_free_camera;
    if !free_cam {
        get_orig_fn!(CutInAlterLateUpdate, AlterLateUpdateFn)(this, pos, rot, sc);
        // 诊断：游戏自己算完 Camera 后，读它的 transform，看游戏是怎么摆相机的
        static GN: std::sync::atomic::AtomicUsize = std::sync::atomic::AtomicUsize::new(0);
        if GN.fetch_add(1, std::sync::atomic::Ordering::Relaxed) % 30 == 0 {
            unsafe {
                let cam = read_object_field(this, "_targetCamera");
                if !cam.is_null() {
                    use crate::il2cpp::hook::UnityEngine_CoreModule::{Component, Transform};
                    let tr = Component::get_transform(cam);
                    if !tr.is_null() {
                        let p2 = Transform::get_position(tr);
                        let mut q = Quaternion_t::default();
                        Transform::get_rotation_Injected(tr, &mut q);
                        warn!(
                            "[cutin-game] pos=({:.2},{:.2},{:.2}) rot=({:.2},{:.2},{:.2},{:.2}) sc={:.2}",
                            p2.x, p2.y, p2.z, q.x, q.y, q.z, q.w, sc
                        );
                    }
                }
            }
        }
    }
    else {
        #[cfg(target_os = "windows")]
        unsafe {
            {
                // cutin 场景没有 tick 调用点，这里手动驱动输入。
                // free_camera.enabled 没有单独 UI，勾了「特写自由视角」就视为开启。
                crate::windows::free_camera::force_enable_for_cutin();
                crate::windows::free_camera::tick();

                let cam = read_object_field(this, "_targetCamera");
                if !cam.is_null() {
                    let ctl = CUTIN_CTRL.load(std::sync::atomic::Ordering::Relaxed);
                    if ctl != 0 {
                        apply_cutin_head_camera(ctl as *mut Il2CppObject, cam);
                    }
                }
            }
        }
    }
    if CUTIN_CAM_TRACE.fetch_add(1, std::sync::atomic::Ordering::Relaxed) % 60 == 0 {
        unsafe {
            let cam = read_object_field(this, "_targetCamera");
            let fov = if cam.is_null() { -1.0 } else {
                let k = *(cam as *const *mut Il2CppClass);
                let g = crate::il2cpp::api::il2cpp_class_get_method_from_name(k, c"get_fieldOfView".as_ptr(), 0);
                if g.is_null() { -1.0 } else {
                    let r = crate::il2cpp::api::il2cpp_runtime_invoke(g, cam as *mut std::ffi::c_void, std::ptr::null_mut(), std::ptr::null_mut());
                    if r.is_null() { -1.0 } else { *((r as *const u8).add(16) as *const f32) }
                }
            };
            warn!("[cutin] cam={:#x} fov={:.2} scale={:.2}", cam as usize, fov, sc);
        }
    }
    unsafe {
        suppress_tag_objects();

        // 头部相机独立于 FOV 缩放：先做，避免被下面的 scale==1.0 早退跳过。
        // 注意 this 是 CutInTimelineMotionCamera，GetCharacterModelController 在
        // CutInTimelineController 上 —— 用 ctl_touch 存下的控制器指针。
        let cam_cfg = Hachimi::instance().config.load();
        if cam_cfg.cutin_first_person || cam_cfg.cutin_free_camera {
            let cam = read_object_field(this, "_targetCamera");
            let ctl = CUTIN_CTRL.load(std::sync::atomic::Ordering::Relaxed);
            if !cam.is_null() && ctl != 0 {
                #[cfg(target_os = "windows")]
                apply_cutin_head_camera(ctl as *mut Il2CppObject, cam);
            }
        }

        let scale_rt = fov_rt();
        let mut scale = if (scale_rt - 1.0).abs() > 0.001 { scale_rt } else { Hachimi::instance().config.load().cutin_fov_scale };
        // 配置读到 0（旧缓存/未初始化）时直接跳过，否则 FOV 会被乘成 0，画面全坏
        if scale <= 0.01 {
            scale = 1.0;
        }
        if (scale - 1.0).abs() < 0.001 { return; }
        let cam = read_object_field(this, "_targetCamera");
        if !cam.is_null() {
            let klass = *(cam as *const *mut Il2CppClass);
            let get_m = crate::il2cpp::api::il2cpp_class_get_method_from_name(klass, c"get_fieldOfView".as_ptr(), 0);
            let set_m = crate::il2cpp::api::il2cpp_class_get_method_from_name(klass, c"set_fieldOfView".as_ptr(), 1);
            if !get_m.is_null() && !set_m.is_null() {
                let r = crate::il2cpp::api::il2cpp_runtime_invoke(get_m, cam as *mut std::ffi::c_void, std::ptr::null_mut(), std::ptr::null_mut());
                if !r.is_null() {
                    let fov = *((r as *const u8).add(16) as *const f32);
                    let mut new_fov = fov * scale;
                    if new_fov > 160.0 { new_fov = 160.0; }
                    let args: [*mut std::ffi::c_void; 1] = [&mut new_fov as *mut f32 as *mut std::ffi::c_void];
                    crate::il2cpp::api::il2cpp_runtime_invoke(set_m, cam as *mut std::ffi::c_void, args.as_ptr() as *mut *mut std::ffi::c_void, std::ptr::null_mut());
                }
            }
        }
    }
}




/// 从给定 transform 向下找名字含 head 的子节点（最多 3 层），找不到就返回原节点。
#[cfg(target_os = "windows")]
unsafe fn find_head_node(root: *mut Il2CppObject, depth: i32) -> *mut Il2CppObject {
    use crate::il2cpp::hook::UnityEngine_CoreModule::Transform;
    if root.is_null() || depth > 3 {
        return root;
    }
    let count = Transform::get_childCount(root);
    for i in 0..count {
        let child = Transform::GetChild(root, i);
        if child.is_null() {
            continue;
        }
        // Transform 继承自 Component → 取 GameObject 名不方便，用 GetChild 的 transform 名
        let name = transform_name(child);
        if name.to_lowercase().contains("head") {
            return child;
        }
        let deeper = find_head_node(child, depth + 1);
        if deeper != child {
            return deeper;
        }
    }
    root
}

/// 在 GameObject 层级里找头部节点（名字含 head / M_Hair / M_Face）。
#[cfg(target_os = "windows")]
unsafe fn camera_world_position(tr: *mut Il2CppObject) -> Option<Vector3_t> {
    if tr.is_null() {
        return None;
    }
    Some(crate::il2cpp::hook::UnityEngine_CoreModule::Transform::get_position(tr))
}

#[cfg(target_os = "windows")]
unsafe fn camera_world_rotation(tr: *mut Il2CppObject) -> Option<Quaternion_t> {
    use crate::il2cpp::hook::UnityEngine_CoreModule::Transform;
    if tr.is_null() {
        return None;
    }
    let mut q = Quaternion_t::default();
    Transform::get_rotation_Injected(tr, &mut q);
    Some(q)
}

#[cfg(target_os = "windows")]
unsafe fn transform_name(tr: *mut Il2CppObject) -> String {
    use crate::il2cpp::ext::Il2CppStringExt;
    // UnityEngine.Object.get_name
    let klass = *(tr as *const *mut Il2CppClass);
    let m = crate::il2cpp::api::il2cpp_class_get_method_from_name(klass, c"get_name".as_ptr(), 0);
    if m.is_null() {
        return String::new();
    }
    let r = crate::il2cpp::api::il2cpp_runtime_invoke(m, tr as *mut std::ffi::c_void, std::ptr::null_mut(), std::ptr::null_mut());
    if r.is_null() {
        return String::new();
    }
    let s = r as *mut Il2CppString;
    (*s).as_utf16str().to_string()
}

/// TLG 式特写第一人称：取 chara 0 的 ModelController → headTransform，
/// 把 motion camera 的 targetTransform 摆到头部（+7cm），FOV 不碰。
#[cfg(target_os = "windows")]
unsafe fn apply_cutin_head_camera(ctl: *mut Il2CppObject, cam: *mut Il2CppObject) {
    use crate::il2cpp::hook::UnityEngine_CoreModule::{Component, Transform};
    static HEAD_TRACE: std::sync::atomic::AtomicUsize = std::sync::atomic::AtomicUsize::new(0);
    if HEAD_TRACE.fetch_add(1, std::sync::atomic::Ordering::Relaxed) % 30 == 0 {
        warn!("[cutin-head] enter ctl={:#x} cam={:#x}", ctl as usize, cam as usize);
    }

    let klass = *(ctl as *const *mut Il2CppClass);
    if klass.is_null() { return; }
    let klass_name = std::ffi::CStr::from_ptr((*klass).name).to_string_lossy().to_string();
    if HEAD_TRACE.load(std::sync::atomic::Ordering::Relaxed) <= 1 {
        warn!("[cutin-head] this class = {}", klass_name);
    }

    // CutInTimelineController.GetCharacterModelController(int, bool) -> ModelController
    let get_mc = crate::il2cpp::api::il2cpp_class_get_method_from_name(
        klass, c"GetCharacterModelController".as_ptr(), 2);
    if get_mc.is_null() {
        warn!("[cutin-head] GetCharacterModelController 未找到");
        return;
    }
    let mut index: i32 = 0;
    let mut check: bool = false;
    let args: [*mut std::ffi::c_void; 2] = [
        &mut index as *mut i32 as *mut std::ffi::c_void,
        &mut check as *mut bool as *mut std::ffi::c_void,
    ];
    let mc = crate::il2cpp::api::il2cpp_runtime_invoke(
        get_mc, ctl as *mut std::ffi::c_void, args.as_ptr() as *mut *mut std::ffi::c_void,
        std::ptr::null_mut());
    if mc.is_null() {
        warn!("[cutin-head] modelController 为空");
        return;
    }

    // ModelController.GetHeadTransform()
    let mc_klass = *(mc as *const *mut Il2CppClass);
    let get_head = crate::il2cpp::api::il2cpp_class_get_method_from_name(
        mc_klass, c"GetHeadTransform".as_ptr(), 0);
    if get_head.is_null() {
        warn!("[cutin-head] GetHeadTransform 未找到");
        return;
    }
    let head = crate::il2cpp::api::il2cpp_runtime_invoke(
        get_head, mc as *mut std::ffi::c_void, std::ptr::null_mut(), std::ptr::null_mut());
    if head.is_null() {
        warn!("[cutin-head] headTransform 为空");
        return;
    }

    // GetHeadTransform 有时返回角色根节点，往下找真正的 head
    let head = find_head_node(head, 0);
    warn!("[cutin-head] node = {}", transform_name(head));

    // 相机 transform 与头部位姿
    let cam_tr = Component::get_transform(cam);
    if cam_tr.is_null() { return; }

    let mut head_pos = Transform::get_position(head);
    let mut head_rot = Quaternion_t::default();
    Transform::get_rotation_Injected(head, &mut head_rot);

    let config = Hachimi::instance().config.load();
    if config.cutin_free_camera {
        #[cfg(target_os = "windows")]
        {
            use crate::windows::free_camera;
            // 首次进入：以游戏当前的相机位姿为起点（保持默认视角，不跳到头部）
            if let (Some(cur_pos), Some(cur_rot)) = (
                camera_world_position(cam_tr),
                camera_world_rotation(cam_tr),
            ) {
                free_camera::ensure_cutin_start(cur_pos, cur_rot);
            }
            CUTIN_SELF_WRITE.store(false, std::sync::atomic::Ordering::Release);
            CUTIN_CAM_TR.store(cam_tr as usize, std::sync::atomic::Ordering::Release);

            // 诊断：读回相机当前位置，和上一帧我们写入的值比较，差值即"别人改动量"
            {
                static LAST_WRITTEN: std::sync::Mutex<Option<(f32, f32, f32)>> =
                    std::sync::Mutex::new(None);
                let cur = Transform::get_position(cam_tr);
                if let Ok(mut g) = LAST_WRITTEN.lock() {
                    if let Some((lx, ly, lz)) = *g {
                        let dx = cur.x - lx;
                        let dy = cur.y - ly;
                        let dz = cur.z - lz;
                        if dx.abs() + dy.abs() + dz.abs() > 0.05 {
                            warn!(
                                "[cutin-drift] dx={:.3} dy={:.3} dz={:.3} (written {:.2},{:.2},{:.2} now {:.2},{:.2},{:.2})",
                                dx, dy, dz, lx, ly, lz, cur.x, cur.y, cur.z
                            );
                        }
                    }
                    *g = Some((cur.x, cur.y, cur.z));
                }
            }
            let pos = free_camera::camera_pos();
            let look_at = free_camera::camera_look_at();
            CUTIN_SELF_WRITE.store(true, std::sync::atomic::Ordering::Release);
            Transform::set_position(cam_tr, pos);
            CUTIN_SELF_WRITE.store(false, std::sync::atomic::Ordering::Release);
            // 自由相机是 look_at 模式（rotation 通常为 None），必须用 LookRotation 算朝向，
            // 否则方向会退回头部朝向 —— 表现为"视角固定、WASD 方向不对"。
            // 用 Unity 的 lookAt 设朝向（aeffac4d 的行为：俯仰正常）
            CUTIN_SELF_WRITE.store(true, std::sync::atomic::Ordering::Release);
            crate::il2cpp::hook::UnityEngine_CoreModule::Transform::look_at(cam_tr, look_at);
            CUTIN_SELF_WRITE.store(false, std::sync::atomic::Ordering::Release);
            return;
        }
    }

    head_pos.y += 0.07;
    warn!(
        "[cutin-head] head=({:.2},{:.2},{:.2})",
        head_pos.x, head_pos.y, head_pos.z
    );
    Transform::set_position(cam_tr, head_pos);
    let mut q = head_rot;
    Transform::set_rotation_Injected(cam_tr, &mut q);
}

unsafe fn ctl_touch(this: *mut Il2CppObject) {
    let p = this as usize;
    let prev = CUTIN_CTRL.load(std::sync::atomic::Ordering::Relaxed);
    if prev != p {
        warn!("[cutin] controller {:#x} -> {:#x}", prev, p);
    }
    CUTIN_CTRL.store(p, std::sync::atomic::Ordering::Relaxed);
    CUTIN_TICK.store(now_ms(), std::sync::atomic::Ordering::Relaxed);
    if CUTIN_TOTAL_OWNER.load(std::sync::atomic::Ordering::Relaxed) != p {
        let k = *(this as *const *mut Il2CppClass);
        if !k.is_null() {
            let m = crate::il2cpp::api::il2cpp_class_get_method_from_name(k, c"GetTotalTime".as_ptr(), 0);
            if !m.is_null() {
                CUTIN_TOTAL_OWNER.store(p, std::sync::atomic::Ordering::Relaxed);
                let r = crate::il2cpp::api::il2cpp_runtime_invoke(m, this as *mut std::ffi::c_void, std::ptr::null_mut(), std::ptr::null_mut());
                if !r.is_null() {
                    let total = *((r as *const u8).add(16) as *const f32);
                    CUTIN_TOTAL_BITS.store(total.to_bits(), std::sync::atomic::Ordering::Relaxed);
                }
            }
        }
    }
}

type CTLAlterLateFn = extern "C" fn(this: *mut Il2CppObject) -> bool;
extern "C" fn CTL_AlterLateUpdate(this: *mut Il2CppObject) -> bool {
    unsafe { ctl_touch(this); }
    #[cfg(target_os = "windows")]
    crate::windows::free_camera::begin_cutin_scene();
    get_orig_fn!(CTL_AlterLateUpdate, CTLAlterLateFn)(this)
}

type CTLAlterUpdateFn = extern "C" fn(this: *mut Il2CppObject) -> bool;
extern "C" fn CTL_AlterUpdate(this: *mut Il2CppObject) -> bool {
    unsafe { ctl_touch(this); }
    get_orig_fn!(CTL_AlterUpdate, CTLAlterUpdateFn)(this)
}

type CTLAlterFixedFn = extern "C" fn(this: *mut Il2CppObject, a: f32, b: f32) -> ();
extern "C" fn CTL_AlterFixedUpdate(this: *mut Il2CppObject, a: f32, b: f32) {
    unsafe { ctl_touch(this); }
    get_orig_fn!(CTL_AlterFixedUpdate, CTLAlterFixedFn)(this, a, b)
}

fn find_class_any(umamusume: *const Il2CppImage, name: &str) -> *mut Il2CppClass {
    unsafe {
        let Ok(cn) = std::ffi::CString::new(name) else { return std::ptr::null_mut(); };
        if let Ok(k) = get_class(umamusume, c"Gallop", cn.as_c_str()) { return k; }
        if let Ok(k) = get_class(umamusume, c"", cn.as_c_str()) { return k; }
        let count = crate::il2cpp::api::il2cpp_image_get_class_count(umamusume);
        for i in 0..count {
            let kk = crate::il2cpp::api::il2cpp_image_get_class(umamusume, i) as *mut Il2CppClass;
            if kk.is_null() { continue; }
            let n = std::ffi::CStr::from_ptr((*kk).name).to_string_lossy();
            if n == name { return kk; }
        }
        std::ptr::null_mut()
    }
}

fn cls_opt(umamusume: *const Il2CppImage, name: &str) -> Option<*mut Il2CppClass> {
    let k = find_class_any(umamusume, name);
    if k.is_null() { None } else { Some(k) }
}

// GallopUtil.GotoTitleOnError(string)
type GotoTitleOnErrorFn = extern "C" fn(text: *mut Il2CppString) -> ();
static GOTO_ERR_LOGGED: std::sync::atomic::AtomicBool = std::sync::atomic::AtomicBool::new(false);
extern "C" fn GotoTitleOnError_hook(text: *mut Il2CppString) {
    if Hachimi::instance().config.load().intercept_error_dialog {
        if !GOTO_ERR_LOGGED.swap(true, std::sync::atomic::Ordering::Relaxed) {
            let msg = unsafe { read_il2cpp_string(text) };
            warn!("[cutin] intercepted GotoTitleOnError: {}", msg);
        }
        return;
    }
    get_orig_fn!(GotoTitleOnError_hook, GotoTitleOnErrorFn)(text)
}


unsafe fn dump_ctl_methods(umamusume: *const Il2CppImage) {
    use std::ffi::CStr;
    if let Ok(k) = crate::il2cpp::symbols::get_class(umamusume, c"Gallop.CutIn.Cutt", c"CutInTimelineController") {
        let mut names: Vec<String> = Vec::new();
        let mut it: *mut std::ffi::c_void = std::ptr::null_mut();
        loop {
            let m = crate::il2cpp::api::il2cpp_class_get_methods(k as *mut _, &mut it);
            if m.is_null() { break; }
            let n = CStr::from_ptr((*m).name).to_string_lossy().to_string();
            let c = crate::il2cpp::api::il2cpp_method_get_param_count(m);
            names.push(format!("{}/{}", n, c));
        }
        warn!("[cutin-ctl] methods: {}", names.join(", "));
    }
}


/// 一次性诊断：找出哪个类有 GetCharacterModelController / GetHeadTransform
unsafe fn scan_cutin_model_ctrl(umamusume: *const Il2CppImage) {
    use std::ffi::CStr;
    let count = crate::il2cpp::api::il2cpp_image_get_class_count(umamusume);
    for i in 0..count {
        let klass = crate::il2cpp::api::il2cpp_image_get_class(umamusume, i);
        if klass.is_null() { continue; }
        let cname = CStr::from_ptr((*klass).name).to_string_lossy().to_string();
        if !cname.contains("CutIn") && !cname.contains("ModelController") && !cname.contains("Cutt") {
            continue;
        }
        let mut hits: Vec<String> = Vec::new();
        let mut it: *mut std::ffi::c_void = std::ptr::null_mut();
        loop {
            let m = crate::il2cpp::api::il2cpp_class_get_methods(klass as *mut _, &mut it);
            if m.is_null() { break; }
            let n = CStr::from_ptr((*m).name).to_string_lossy().to_string();
            if n.contains("GetCharacterModelController") || n.contains("GetHeadTransform") || n.contains("Character") {
                let c = crate::il2cpp::api::il2cpp_method_get_param_count(m);
                hits.push(format!("{}/{}", n, c));
            }
        }
        if !hits.is_empty() {
            warn!("[cutin-scan] {} -> {}", cname, hits.join(", "));
        }
    }
}

pub fn init(umamusume: *const Il2CppImage) {
    unsafe { scan_cutin_model_ctrl(umamusume); }
    if let Ok(k) = get_class(umamusume, c"Gallop.CutIn.Cutt", c"CutInTimelineMotionCamera") {
        let a = get_method_addr(k, c"AlterLateUpdate", 3);
        if a != 0 { new_hook!(a, CutInAlterLateUpdate); }
    }
    unsafe { dump_ctl_methods(umamusume); }
    if let Some(ctl) = cls_opt(umamusume, "CutInTimelineController") {
        let a = get_method_addr(ctl, c"AlterLateUpdate", 0);
        if a != 0 { new_hook!(a, CTL_AlterLateUpdate); }
        let a = get_method_addr(ctl, c"AlterUpdate", 0);
        if a != 0 { new_hook!(a, CTL_AlterUpdate); }
        let a = get_method_addr(ctl, c"AlterFixedUpdate", 2);
        if a != 0 { new_hook!(a, CTL_AlterFixedUpdate); }
    }
    if let Some(pubr) = cls_opt(umamusume, "CutInTimelineEventPublisher") {
        let a = get_method_addr(pubr, c"FireEvent", 2);
        if a != 0 { new_hook!(a, FireEvent2); }
    }
    if let Ok(ui_img) = crate::il2cpp::symbols::get_assembly_image(c"UnityEngine.CoreModule") {
        if let Ok(obj_cls) = crate::il2cpp::symbols::get_class(ui_img, c"UnityEngine", c"Object") {
            let a = get_method_addr(obj_cls, c"Internal_CloneSingleWithParent", 3);
            if a != 0 { new_hook!(a, CloneSingle_hook); }
            let a = get_method_addr(obj_cls, c"Internal_CloneSingle", 1);
            if a != 0 { new_hook!(a, CloneSingle1_hook); }
        }
    }
    if let Ok(k) = get_class(umamusume, c"Gallop", c"GallopUtil") {
        let a = get_method_addr(k, c"GotoTitleOnError", 1);
        if a != 0 { new_hook!(a, GotoTitleOnError_hook); }
    }
    load_shadow_frames();
}
