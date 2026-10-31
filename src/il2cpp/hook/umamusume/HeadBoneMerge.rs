// 头部骨骼合并 —— 复刻 UmaViewer 的 MergeBone，让 A 的头能挂到 B 的身体上。
//
// 依据（Android 版运行时 dump 的 All.cs，Steam 版 RVA 已确认）：
//   ModelLoader.ReplaceHeadBone(SkinnedMeshRenderer smr, Transform targetBone, List<Mesh> meshes, bool flag)
//   ModelLoader.MergeHierarchy(Transform src, Transform dst)     RVA 0x58C5C30
//   ModelLoader.FindBoneInHierachy(Transform t, string name)     RVA 0x58BF8E0
//
// 反汇编确认：
//   MergeHierarchy(src, dst): src/dst 任一为 null 直接返回，否则遍历 src 子节点合并到 dst
//   FindBoneInHierachy(t, name): transform.Find(name) 的包装
//
// 本模块只做观察：记录游戏自己何时调 ReplaceHeadBone、传什么参数、从哪调。
// 拿到结果后再决定是 hook 拦截还是直接调用。

use std::ffi::c_void;
use std::sync::atomic::{AtomicU64, AtomicUsize, Ordering};

use crate::core::Hachimi;
use crate::il2cpp::symbols::get_method_addr;

static ORIG_REPLACE_HEAD_BONE: AtomicUsize = AtomicUsize::new(0);
static HITS: AtomicU64 = AtomicU64::new(0);

pub fn hits() -> u64 {
    HITS.load(Ordering::Relaxed)
}

/// ReplaceHeadBone 是 4 参数方法，全部走寄存器（rcx/rdx/r8/r9），
/// 不存在 5 参数那种栈偏移问题，可以安全 hook。
// ★ native 签名只有 3 个参数：rcx=this, rdx=参数, r9=bool。
//
//   反汇编 ReplaceHeadBone @ RVA 0x58C6BA0 全函数 262 条指令，寄存器使用：
//     0x58C6BB8  mov   r14, rcx      ; rcx = this
//     0x58C6BB5  mov   r12, rdx      ; rdx = 参数（SkinnedMeshRenderer）
//     0x58C6BB1  movzx r13d, r9b     ; r9 低字节 = bool
//     0x58C6C51  xor   r8d, r8d      ; r8 只是临时清零，不是输入参数
//   栈上的 [rsp+X] 全是 `mov [rsp+X], reg`（保存寄存器），不是读参数。
//
//   C# metadata 里是 4 个参数，所以 get_method_addr 要用 4 才能找到；
//   但 hook 的 detour 只需匹配 3 个 native 参数。
//
//   教训：之前按 5 个、4 个 native 参数 hook 都不对 —— 多传的会让 Rust
//   把 bool 放到栈上，而原函数从 r9 读，读到垃圾值导致卡死/地址为空。
type ReplaceHeadBoneFn = extern "C" fn(
    this: *mut c_void,
    smr: *mut c_void,
    flag: bool,
) -> *mut c_void;

extern "C" fn replace_head_bone_hook(
    this: *mut c_void,
    smr: *mut c_void,
    flag: bool,
) -> *mut c_void {
    let n = HITS.fetch_add(1, Ordering::Relaxed);
    if n < 20 {
        warn!(
            "[headbone] ReplaceHeadBone #{} this={:#x} smr={:#x} flag={}\n{}",
            n + 1,
            this as usize,
            smr as usize,
            flag,
            dump_stack()
        );
    }

    let orig: ReplaceHeadBoneFn =
        unsafe { std::mem::transmute(ORIG_REPLACE_HEAD_BONE.load(Ordering::Relaxed)) };
    orig(this, smr, flag)
}

#[link(name = "ntdll")]
extern "system" {
    fn RtlCaptureStackBackTrace(
        skip: u32,
        count: u32,
        frames: *mut *mut c_void,
        hash: *mut u32,
    ) -> u16;
}

#[link(name = "kernel32")]
extern "system" {
    fn GetModuleHandleW(name: *const u16) -> *mut c_void;
}

fn ga_base() -> usize {
    unsafe {
        let n: Vec<u16> = "GameAssembly.dll\0".encode_utf16().collect();
        GetModuleHandleW(n.as_ptr()) as usize
    }
}

fn dump_stack() -> String {
    const MAX: usize = 62;
    let mut frames = [std::ptr::null_mut(); MAX];
    let n = unsafe {
        RtlCaptureStackBackTrace(0, MAX as u32, frames.as_mut_ptr(), std::ptr::null_mut())
    } as usize;
    let base = ga_base();
    let mut out = String::from("    调用栈（全量）:");
    for (i, f) in frames[..n].iter().enumerate() {
        let a = *f as usize;
        if a == 0 {
            continue;
        }
        if base != 0 && a >= base {
            out.push_str(&format!("\n      #{:<2} GameAssembly+0x{:X}", i, a - base));
        } else {
            out.push_str(&format!("\n      #{:<2} {:#x}", i, a));
        }
    }
    out
}

pub fn init(image: *const crate::il2cpp::types::Il2CppImage) {
    let Ok(k) = crate::il2cpp::symbols::get_class(image, c"Gallop", c"ModelLoader") else {
        warn!("[headbone] Gallop.ModelLoader 未找到");
        return;
    };

    let addr = get_method_addr(k, c"ReplaceHeadBone", 4);
    if addr == 0 {
        warn!("[headbone] ReplaceHeadBone(4) 地址为空");
        return;
    }

    warn!("[headbone] ReplaceHeadBone @ {:#x}", addr);

    let h = Hachimi::instance();
    match h.interceptor.hook(addr, replace_head_bone_hook as *const () as usize) {
        Ok(t) => {
            ORIG_REPLACE_HEAD_BONE.store(t, Ordering::SeqCst);
            warn!("[headbone] hook 成功");
        }
        Err(e) => warn!("[headbone] hook 失败: {}", e),
    }
}
