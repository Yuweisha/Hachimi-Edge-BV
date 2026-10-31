// ModelLoader 探针：确认游戏原生的模型组装 API 是否能拿到地址。
//
// 依据：Android 版运行时 dump 的 All.cs 里有这些方法签名（方法体为空，签名真实）：
//   CompositeHead / CompositeFaceHair / CompositeTail / CompositeAttach
//   ReplaceHeadBone / MergeHierarchy / FindBoneInHierachy / ConnectModel
//   CreateModel / CreateModelInternal / CheckModelResourceExist
//
// 目的：拿到真实地址后，反汇编 CreateModel / CompositeHead 看组装流程，再决定 hook 点。

use std::ffi::c_void;

use crate::il2cpp::symbols::{get_class, get_method_addr};

const CANDIDATES: &[(&str, i32)] = &[
    ("CompositeHead", 5),
    ("CompositeHead", 6),
    ("CompositeFaceHair", 6),
    ("CompositeTail", 6),
    ("CompositeTail", 5),
    ("CompositeAttach", 4),
    ("ReplaceHeadBone", 4),
    ("MergeHierarchy", 2),
    ("FindBoneInHierachy", 2),
    ("ConnectModel", 3),
    ("RemoveMesh", 2),
    ("DuplicateMesh", 2),
    ("GetChildrenDic", 1),
    ("GetChildren", 1),
    ("RenumberMeshIndexes", 3),
    ("InvestigateMesh", 7),
    ("CreateModel", 1),
    ("CreateModelInternal", 1),
    ("CreateCustomModel", 1),
    ("BuildCustomModel", 6),
    ("CheckModelResourceExist", 1),
    ("CheckDressResourceExist", 1),
];

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

pub fn init(image: *const crate::il2cpp::types::Il2CppImage) {
    let Ok(k) = get_class(image, c"Gallop", c"ModelLoader") else {
        warn!("[modelloader] Gallop.ModelLoader 类未找到");
        return;
    };

    warn!("[modelloader] 开始探测 ModelLoader 的方法");
    let base = ga_base();

    let mut hit = 0;
    let mut miss = 0;

    for (name, params) in CANDIDATES {
        let Ok(cname) = std::ffi::CString::new(*name) else {
            continue;
        };
        let addr = get_method_addr(k, &cname, *params);
        if addr == 0 {
            miss += 1;
            debug!("[modelloader]   {} ({} 参) -> 未找到", name, params);
        } else {
            hit += 1;
            let rva = if base != 0 { addr.saturating_sub(base) } else { 0 };
            warn!(
                "[modelloader]   {} ({} 参) -> {:#x}  RVA 0x{:X}",
                name, params, addr, rva
            );
        }
    }

    warn!("[modelloader] 探测完成：命中 {} / 未找到 {}", hit, miss);
}
