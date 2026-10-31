import io

p = 'src/il2cpp/hook/umamusume/UmaCapture.rs'
s = io.open(p, encoding='utf-8').read()

# 1) 加一个「保留中间产物」开关，默认关
if 'DUMP_INTERMEDIATE' not in s:
    s = s.replace('pub static CAPTURE: AtomicBool = AtomicBool::new(true);',
                  'pub static CAPTURE: AtomicBool = AtomicBool::new(true);\n'
                  '/// 是否保留中间产物（密文 / LZ4 流 / 请求体）。默认关，只留 JSON\n'
                  'pub static DUMP_INTERMEDIATE: AtomicBool = AtomicBool::new(false);', 1)

# 2) dump 里非 resp_dst 的 tag，默认跳过
old = '''    let _ = std::fs::create_dir_all(&dir);
    let sl = std::slice::from_raw_parts(data, len);

    if tag == "resp_dst" {'''
new = '''    let _ = std::fs::create_dir_all(&dir);
    let sl = std::slice::from_raw_parts(data, len);

    // 只保留 JSON；中间产物需要显式开启
    if tag != "resp_dst" && !DUMP_INTERMEDIATE.load(Ordering::Relaxed) {
        return;
    }

    if tag == "resp_dst" {'''
assert old in s
s = s.replace(old, new, 1)

io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('已加 DUMP_INTERMEDIATE，默认只写 JSON')
