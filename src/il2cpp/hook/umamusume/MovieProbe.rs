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
    cutin_pause_state()
}

/// `CutInTimelineController` 的关键字段（偏移取自 il2cpp dump 注释）。
const CTL_CURRENT_TIME: usize = 0x538;
const CTL_CURRENT_FRAME: usize = 0x554;
const CTL_TARGET_FPS: usize = 0x48;
const CTL_IS_PAUSE: usize = 0x5d9;
const CTL_IS_AUTO_PLAY: usize = 0x5d8;
const CTL_IS_SUSPEND_AUTO: usize = 0x5e8;
const CTL_SPEED: usize = 0x5d4;
const CTL_REQUEST_TIME: usize = 0x69c;
const CTL_REQUEST_TIME_FLAG: usize = 0x6a0;

fn write_is_pause(this: *mut Il2CppObject, paused: bool) {
    unsafe {
        *((this as *mut u8).add(CTL_IS_PAUSE)) = if paused { 1 } else { 0 };
        *((this as *mut u8).add(CTL_SPEED) as *mut f32) = if paused { 0.0 } else { 1.0 };
    }
}

unsafe fn ctl_ptr() -> *mut Il2CppObject {
    CUTIN_CTRL.load(std::sync::atomic::Ordering::Relaxed) as *mut Il2CppObject
}

unsafe fn call_v0(this: *mut Il2CppObject, name: &std::ffi::CStr) -> bool {
    let k = *(this as *const *mut Il2CppClass);
    if k.is_null() { return false; }
    let m = crate::il2cpp::api::il2cpp_class_get_method_from_name(k, name.as_ptr(), 0);
    if m.is_null() { return false; }
    crate::il2cpp::api::il2cpp_runtime_invoke(m, this as *mut std::ffi::c_void, std::ptr::null_mut(), std::ptr::null_mut());
    true
}

unsafe fn call_b1_f1(this: *mut Il2CppObject, name: &std::ffi::CStr, b: bool, f: f32) -> bool {
    let k = *(this as *const *mut Il2CppClass);
    if k.is_null() { return false; }
    let m = crate::il2cpp::api::il2cpp_class_get_method_from_name(k, name.as_ptr(), 2);
    if m.is_null() { return false; }
    let mut b = b;
    let mut f = f;
    let args: [*mut std::ffi::c_void; 2] = [
        &mut b as *mut bool as *mut std::ffi::c_void,
        &mut f as *mut f32 as *mut std::ffi::c_void,
    ];
    crate::il2cpp::api::il2cpp_runtime_invoke(m, this as *mut std::ffi::c_void, args.as_ptr() as *mut *mut std::ffi::c_void, std::ptr::null_mut());
    true
}

unsafe fn call_b1(this: *mut Il2CppObject, name: &std::ffi::CStr, b: bool) -> bool {
    let k = *(this as *const *mut Il2CppClass);
    if k.is_null() { return false; }
    let m = crate::il2cpp::api::il2cpp_class_get_method_from_name(k, name.as_ptr(), 1);
    if m.is_null() { return false; }
    let mut b = b;
    let args: [*mut std::ffi::c_void; 1] = [&mut b as *mut bool as *mut std::ffi::c_void];
    crate::il2cpp::api::il2cpp_runtime_invoke(m, this as *mut std::ffi::c_void, args.as_ptr() as *mut *mut std::ffi::c_void, std::ptr::null_mut());
    true
}


/// 拖动进度条：写 `_currentTime` + `_requestTime` + `_requestTimeFlag`，再让特效对齐。
///
/// 同时把 `_currentFrame` 同步过去 —— `ResumeAutoUpdate` 会拿
/// `1 / _targetFps * _currentFrame` 反算 `_currentTime`，不同步的话一恢复就跳回拖动前的位置。
pub fn cutin_seek(target: f32) {
    unsafe {
        let this = ctl_ptr();
        if this.is_null() { return; }
        let fps = *((this as *const u8).add(CTL_TARGET_FPS) as *const i32);
        let frame = if fps > 0 { (target * fps as f32).round() as i32 } else { 0 };
        *((this as *mut u8).add(CTL_CURRENT_FRAME) as *mut i32) = frame;
        *((this as *mut u8).add(CTL_CURRENT_TIME) as *mut f32) = target;
        *((this as *mut u8).add(CTL_REQUEST_TIME) as *mut f32) = target;
        *((this as *mut u8).add(CTL_REQUEST_TIME_FLAG)) = 1;
        call_v0(this, c"EffectSimulateToCurrentFrame");
        info!(
            "[cutin] seek t={:.3} frame={} suspended={}",
            target,
            frame,
            *((this as *const u8).add(CTL_IS_PAUSE)) != 0
        );
    }
}

/// 继续播放。
///
/// 时间推进有两道独立门（源码 `ExternalFixedUpdate`）：
///   ① `_isPause` —— `Pause()` 置位、`Resume()` 清除；
///   ② `_isSuspendAutoPlay` —— `SuspendAutoUpdate()` 置位、`ResumeAutoUpdate()` 清除。
/// 只开一道照样不动，所以两个都要放开。
pub fn cutin_play() {
    unsafe {
        let this = ctl_ptr();
        if this.is_null() { return; }
        let keep = *((this as *const u8).add(CTL_CURRENT_TIME) as *const f32);
        // ResumeAutoUpdate 会用 `1/_targetFps * _currentFrame` 重算 _currentTime，
        // 帧号没同步过就会被拉回旧位置；先记下，重算后再校正。
        let ok = call_b1(this, c"ResumeAutoUpdate", false);
        write_is_pause(this, false);
        *((this as *mut u8).add(CTL_IS_AUTO_PLAY)) = 1;
        *((this as *mut u8).add(CTL_IS_SUSPEND_AUTO)) = 0;
        let now = *((this as *const u8).add(CTL_CURRENT_TIME) as *const f32);
        if !now.is_finite() || (now - keep).abs() > 0.05 {
            *((this as *mut u8).add(CTL_CURRENT_TIME) as *mut f32) = keep;
            *((this as *mut u8).add(CTL_REQUEST_TIME) as *mut f32) = keep;
            *((this as *mut u8).add(CTL_REQUEST_TIME_FLAG)) = 1;
        }
        CUTIN_PAUSED.store(false, std::sync::atomic::Ordering::Relaxed);
        info!("[cutin] play ResumeAutoUpdate={} keep={:.3} now={:.3}", ok, keep, now);
    }
}

/// 暂停：用游戏自己的 `SuspendAutoUpdate`。
///
/// 第一个参数是「是否一起暂停 CySpring（骨骼物理）」，照相功能传 false，
/// 这里保持一致；第二个参数 simulateEffectTime 传 -1 表示不额外模拟。
pub fn cutin_pause() {
    unsafe {
        let this = ctl_ptr();
        if this.is_null() { return; }
        let ok = call_b1_f1(this, c"SuspendAutoUpdate", false, -1.0);
        // 补一次特效对齐，否则暂停瞬间残留一帧未模拟的效果
        call_v0(this, c"EffectSimulateToCurrentFrame");
        CUTIN_PAUSED.store(true, std::sync::atomic::Ordering::Relaxed);
        info!("[cutin] pause SuspendAutoUpdate={}", ok);
    }
}

pub fn cutin_resume() {
    cutin_play();
}

/// 暂停状态：两道门任一关着都算暂停。
pub fn cutin_pause_state() -> bool {
    unsafe {
        let this = ctl_ptr();
        if this.is_null() {
            return CUTIN_PAUSED.load(std::sync::atomic::Ordering::Relaxed);
        }
        *((this as *const u8).add(CTL_IS_PAUSE)) != 0
            || *((this as *const u8).add(CTL_IS_SUSPEND_AUTO)) != 0
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

type AlterLateUpdateFn = extern "C" fn(this: *mut Il2CppObject, pos: *mut std::ffi::c_void, rot: *mut std::ffi::c_void, sc: f32) -> ();
/// cutin 自由视角下我们独占的相机 transform（外部写入会被 Transform hook 拦掉）。
pub static CUTIN_CAM_TR: std::sync::atomic::AtomicUsize = std::sync::atomic::AtomicUsize::new(0);
/// 我们自己写相机时置位，避免被上一条规则挡住。
pub static CUTIN_SELF_WRITE: std::sync::atomic::AtomicBool = std::sync::atomic::AtomicBool::new(false);
static CUTIN_CAM_TRACE: std::sync::atomic::AtomicUsize = std::sync::atomic::AtomicUsize::new(0);
extern "C" fn CutInAlterLateUpdate(this: *mut Il2CppObject, pos: *mut std::ffi::c_void, rot: *mut std::ffi::c_void, sc: f32) {
    // ★ 原函数必须照常调用。
    //
    //   过场相机的写入者不止这一个函数：`CutInTimelineController.AlterLateUpdate_MotionCamera`
    //   先把 `_motionCamera` 的插值参数写进 `_transformObject`（0xa0），再由这里落地；
    //   `AlterUpdate_CameraParam` 还会改 FOV/裁切。早先「自由视角时不调原函数」的做法会让
    //   前者算出的一整套相机状态没人消费，表现为镜头被游戏拽走/卡住不动。
    //   现在改成：先让游戏算，再在最后覆盖成自由相机的位置与朝向。
    get_orig_fn!(CutInAlterLateUpdate, AlterLateUpdateFn)(this, pos, rot, sc);
    let free_cam = Hachimi::instance().config.load().cutin_free_camera;
    if !free_cam {
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
    if free_cam {
        #[cfg(target_os = "windows")]
        {
            // cutin 场景没有 tick 调用点，这里手动驱动输入。
            // 自由相机由 `cutin_free_camera` 单独控制，不再改写 `windows.free_camera.enabled`
            // （旧实现在 Android 上写配置，导致「没开菜单也会自己开」）。
            crate::windows::free_camera::tick_cutin();
            // 覆盖动作统一放到 `CutInTimelineController.AlterLateUpdate` 之后做
            // （见 CTL_AlterLateUpdate）：那里的返回点是整帧过场相机写入的最后一站。
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

            // 停掉游戏自己的相机动画图（`CutInTimelineMotionCamera.StopAnimator` →
            // `_myAnimator.StopGraph()`）。不停的话 AnimateToUnity 每帧仍会写
            // transform，和我们抢所有权 —— 日志里 `[cutin-drift] dz=-16.6` 那种
            // 突变就是它，表现为镜头被拽回去/走弧线。
            {
                static STOPPED: std::sync::atomic::AtomicBool =
                    std::sync::atomic::AtomicBool::new(false);
                let motion_cam = read_object_field(ctl, "_motionCamera");
                if !motion_cam.is_null() && !STOPPED.swap(true, std::sync::atomic::Ordering::AcqRel) {
                    let k = *(motion_cam as *const *mut Il2CppClass);
                    if !k.is_null() {
                        let m = crate::il2cpp::api::il2cpp_class_get_method_from_name(
                            k, c"StopAnimator".as_ptr(), 0);
                        if !m.is_null() {
                            crate::il2cpp::api::il2cpp_runtime_invoke(
                                m, motion_cam as *mut std::ffi::c_void,
                                std::ptr::null_mut(), std::ptr::null_mut());
                            warn!("[cutin] StopAnimator 已调用（相机动画图停止）");
                        } else {
                            warn!("[cutin] StopAnimator 未找到");
                        }
                    }
                }
            }

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
    let ret = get_orig_fn!(CTL_AlterLateUpdate, CTLAlterLateFn)(this);

    // 这一帧的相机已由游戏写完（AlterLateUpdate_MotionCamera → CutInTimelineMotionCamera），
    // 在这里覆盖才是最后一步 —— 在 motion camera 的 AlterLateUpdate 里覆盖会被同帧更晚的写入拽回去。
    #[cfg(target_os = "windows")]
    if Hachimi::instance().config.load().cutin_free_camera {
        unsafe {
            // `_targetCamera` 在 CutInTimelineMotionCamera 上（+0x88），
            // controller 只持有 `_motionCamera`（+0xf8），要转一层。
            let motion_cam = read_object_field(this, "_motionCamera");
            if !motion_cam.is_null() {
                let cam = *((motion_cam as *const u8).add(0x88) as *const *mut Il2CppObject);
                if !cam.is_null() {
                    apply_cutin_head_camera(this, cam);
                }
            }
        }
    }

    ret
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

/// 打全量调用栈，定位 GotoTitleOnError 的调用者。
/// 用户要求：全量帧，不限层。
fn goto_err_stack() -> String {
    const MAX: usize = 62;
    #[link(name = "ntdll")]
    extern "system" {
        fn RtlCaptureStackBackTrace(
            skip: u32, count: u32,
            frames: *mut *mut std::ffi::c_void, hash: *mut u32,
        ) -> u16;
    }
    let mut frames = [std::ptr::null_mut(); MAX];
    let n = unsafe {
        RtlCaptureStackBackTrace(0, MAX as u32, frames.as_mut_ptr(), std::ptr::null_mut())
    } as usize;

    // GameAssembly 基址
    let base = unsafe {
        #[link(name = "kernel32")]
        extern "system" {
            fn GetModuleHandleW(name: *const u16) -> *mut std::ffi::c_void;
        }
        let w: Vec<u16> = "GameAssembly.dll\0".encode_utf16().collect();
        GetModuleHandleW(w.as_ptr()) as usize
    };

    let mut out = String::from("     调用栈（全量）:");
    for (i, f) in frames[..n].iter().enumerate() {
        let a = *f as usize;
        if a == 0 { continue; }
        if base != 0 && a >= base {
            out.push_str(&format!("\n      #{:<2} GameAssembly+0x{:X}", i, a - base));
        } else {
            out.push_str(&format!("\n      #{:<2} {:#x}", i, a));
        }
    }
    out
}

extern "C" fn GotoTitleOnError_hook(text: *mut Il2CppString) {
    let msg = unsafe { read_il2cpp_string(text) };
    if !GOTO_ERR_LOGGED.swap(true, std::sync::atomic::Ordering::Relaxed) {
        warn!("[cutin] GotoTitleOnError 被调用，text={:?}\n{}", msg, goto_err_stack());
    }
    if Hachimi::instance().config.load().intercept_error_dialog {
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
    if let Ok(k) = get_class(umamusume, c"Gallop", c"GallopUtil") {
        let a = get_method_addr(k, c"GotoTitleOnError", 1);
        if a != 0 { new_hook!(a, GotoTitleOnError_hook); }
    }
}
