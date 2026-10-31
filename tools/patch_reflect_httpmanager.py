import io

p = 'src/il2cpp/hook/umamusume/UmaCapture.rs'
s = io.open(p, encoding='utf-8').read()

# 1) init 改签名，接收 umamusume image
s = s.replace('pub fn init() -> usize {', 'pub fn init(umamusume: *const crate::il2cpp::types::Il2CppImage) -> usize {', 1)

# 2) 在 init 的 libnative hook 之后，加反射找 HttpManager
old_tail = '''    info!("[capture] 安装完成 {}/3", n);
    n
}'''
new_tail = '''    // 用反射拿 HttpManager.Send，避免硬编码 RVA 挂错函数
    unsafe {
        use crate::il2cpp::symbols::{get_class, get_method_addr_cached};
        use std::ffi::CStr;

        if let Ok(klass) = get_class(umamusume, c"Gallop", c"HttpManager") {
            // 打印字段，找 URL 存放位置
            let mut iter: *mut std::ffi::c_void = std::ptr::null_mut();
            let mut field_count = 0;
            loop {
                let f = crate::il2cpp::symbols::il2cpp_class_get_fields(klass, &mut iter);
                if f.is_null() { break; }
                let name = CStr::from_ptr((*f).name).to_string_lossy().to_string();
                info!("[capture] HttpManager 字段: {} offset={:#x}", name, (*f).offset);
                field_count += 1;
                if field_count > 40 { break; }
            }

            // 试 Send 的常见重载
            for argc in 1..=5 {
                let addr = get_method_addr_cached(klass, c"Send", argc);
                if addr != 0 {
                    info!("[capture] HttpManager.Send/{} @ {:#x}", argc, addr);
                }
            }
        } else {
            warn!("[capture] Gallop.HttpManager 未找到");
        }
    }

    info!("[capture] 安装完成 {}/3", n);
    n
}'''
assert old_tail in s
s = s.replace(old_tail, new_tail, 1)

io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('已改为反射查找 HttpManager')
