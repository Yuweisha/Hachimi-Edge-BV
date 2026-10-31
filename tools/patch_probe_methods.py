import io

p = 'src/il2cpp/hook/umamusume/UmaCapture.rs'
s = io.open(p, encoding='utf-8').read()

# 把含字段遍历的整块替换成只探测方法地址
start = s.find('    // 用反射拿 HttpManager.Send，避免硬编码 RVA 挂错函数')
end = s.find('    info!("[capture] 安装完成 {}/3", n);', start)
assert start != -1 and end != -1

new_block = '''    // 用反射拿 HttpManager 的方法地址，避免硬编码 RVA 挂错函数
    unsafe {
        use crate::il2cpp::symbols::{get_class, get_method_addr_cached};

        match get_class(umamusume, c"Gallop", c"HttpManager") {
            Ok(klass) => {
                info!("[capture] 找到 Gallop.HttpManager");
                for argc in 1..=5 {
                    let addr = get_method_addr_cached(klass, c"Send", argc);
                    if addr != 0 {
                        info!("[capture] Send/{} @ {:#x}", argc, addr);
                    }
                }
                for name in [c"SendRequest", c"Request", c"SendInternal"] {
                    for argc in 1..=4 {
                        let addr = get_method_addr_cached(klass, name, argc);
                        if addr != 0 {
                            info!("[capture] {}/{} @ {:#x}", name.to_string_lossy(), argc, addr);
                        }
                    }
                }
            }
            Err(e) => warn!("[capture] Gallop.HttpManager 未找到: {:?}", e),
        }
    }

'''
s = s[:start] + new_block + s[end:]
io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('已改为只探测方法地址')
