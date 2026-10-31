import io

# 1) UmaCapture.rs：改签名 + 加反射探测
p = 'src/il2cpp/hook/umamusume/UmaCapture.rs'
s = io.open(p, encoding='utf-8').read()

s = s.replace(
    'pub fn init() -> usize {\n    use windows::{core::w, Win32::System::LibraryLoader::GetModuleHandleW};',
    'pub fn init(umamusume: *const crate::il2cpp::types::Il2CppImage) -> usize {\n    use windows::{core::w, Win32::System::LibraryLoader::GetModuleHandleW};',
    1,
)

old_tail = '    info!("[capture] 安装完成 {}/3", n);\n    n\n}'
new_tail = '''    // 反射拿 HttpManager 的方法地址，避免硬编码 RVA 挂错函数
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
            }
            Err(e) => warn!("[capture] Gallop.HttpManager 未找到: {:?}", e),
        }
    }

    info!("[capture] 安装完成 {}/3", n);
    n
}'''
assert old_tail in s, '未找到 init 尾部'
s = s.replace(old_tail, new_tail, 1)
io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('UmaCapture.rs: 签名 + 反射探测 已改')

# 2) mod.rs：传 image
p2 = 'src/il2cpp/hook/umamusume/mod.rs'
m = io.open(p2, encoding='utf-8').read()
if 'UmaCapture::init()' in m:
    m = m.replace('UmaCapture::init();', 'UmaCapture::init(image);', 1)
    io.open(p2, 'w', encoding='utf-8', newline='\n').write(m)
    print('mod.rs: 已传 image')
else:
    print('mod.rs: 未找到调用点')

# 3) 确认
s2 = io.open(p, encoding='utf-8').read()
print('init 签名:', 'pub fn init(umamusume' in s2)
print('反射块:', 'get_method_addr_cached' in s2)
