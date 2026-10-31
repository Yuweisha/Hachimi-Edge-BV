import io

p = 'src/il2cpp/hook/umamusume/UmaCapture.rs'
s = io.open(p, encoding='utf-8').read()

probe = '''
// ===== URL 探针：HttpManager.Send(this, request_data) =====
type FnSend = unsafe extern "C" fn(this: *mut c_void, data: *mut c_void) -> i64;
static ORIG_SEND: AtomicUsize = AtomicUsize::new(0);
static HITS_SEND: AtomicUsize = AtomicUsize::new(0);

/// 读 Il2CppString（+0x10 起是 UTF-16LE，+0x10 前面是 length）
unsafe fn il2cpp_str(p: *const u8) -> Option<String> {
    if p.is_null() { return None; }
    let len = *(p.add(0x10) as *const i32);
    if len <= 0 || len > 4096 { return None; }
    let chars = std::slice::from_raw_parts(p.add(0x14) as *const u16, len as usize);
    Some(String::from_utf16_lossy(chars))
}

unsafe extern "C" fn hook_send(this: *mut c_void, data: *mut c_void) -> i64 {
    let n = HITS_SEND.fetch_add(1, Ordering::Relaxed);
    if n < 8 && !data.is_null() {
        let d = data as *const u8;
        info!("[url] #{} this={:p} data={:p}", n, this, data);
        // 扫前 0x180 字节里像指针的字段，试着当 Il2CppString 读
        for off in (0x10..0x180).step_by(8) {
            let v = *(d.add(off) as *const usize);
            if v == 0 { continue; }
            // 堆地址一般落在用户空间且 8 对齐
            if v < 0x10000 || v > 0x7fff_ffff_ffff { continue; }
            if let Some(txt) = il2cpp_str(v as *const u8) {
                if txt.len() >= 4 && txt.chars().all(|c| c.is_ascii_graphic() || c == ' ') {
                    info!("[url]   +{:#x} -> {}", off, txt);
                }
            }
        }
    }
    let o = ORIG_SEND.load(Ordering::Relaxed);
    if o == 0 { return 0; }
    let f: FnSend = std::mem::transmute(o);
    f(this, data)
}
'''

anchor = '/// 在 libnative 上装 hook。返回成功安装的个数。'
if 'hook_send' not in s:
    s = s.replace(anchor, probe + '\n' + anchor, 1)

# init 里挂 send
install = '''
    // GameAssembly 的 HttpManager.Send
    if let Ok(ga) = unsafe { GetModuleHandleW(w!("GameAssembly.dll")) } {
        let addr = ga.0 as usize + 0x86a640;
        match hachimi.interceptor.hook(addr, hook_send as *const () as usize) {
            Ok(t) => {
                ORIG_SEND.store(t as usize, Ordering::Relaxed);
                info!("[capture] hook Send OK tramp={:#x}", t);
                n += 1;
            }
            Err(e) => warn!("[capture] hook Send FAILED: {:?}", e),
        }
    }
'''
if 'hook Send OK' not in s:
    s = s.replace('    info!("[capture] 安装完成 {}/3", n);',
                  install + '\n    info!("[capture] 安装完成 {}/4", n);', 1)

io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('已加 Send 探针')
