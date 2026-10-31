import io

p = 'src/il2cpp/hook/umamusume/UmaCapture.rs'
s = io.open(p, encoding='utf-8').read()

# 1) 导入 c_void
if 'use std::ffi::c_void;' not in s:
    s = s.replace('use log::{info, warn};', 'use log::{info, warn};\nuse std::ffi::c_void;', 1)

# 2) 全局 URL 槽（Send 里记下，3180 里消费）
if 'LAST_URL' not in s:
    slot = '''
// Send 与 3180 不在同一线程，用 Mutex 存最近一次 URL
static LAST_URL: std::sync::Mutex<Option<String>> = std::sync::Mutex::new(None);
static URL_SEQ: AtomicUsize = AtomicUsize::new(0);

fn set_url(u: String) {
    if let Ok(mut g) = LAST_URL.lock() {
        *g = Some(u);
    }
}

/// 取走当前 URL，并把路径整理成可做文件名的形式
fn take_url() -> String {
    let u = LAST_URL.lock().ok().and_then(|mut g| g.take());
    let raw = match u {
        Some(v) => v,
        None => return "unknown".to_string(),
    };
    // 去掉 host，只留路径；把 / ? = & 换成 _
    let path = if let Some(i) = raw.find("://") {
        let rest = &raw[i + 3..];
        match rest.find('/') {
            Some(j) => &rest[j..],
            None => rest,
        }
    } else {
        raw.as_str()
    };
    let cleaned: String = path
        .trim_matches('/')
        .chars()
        .map(|c| if c.is_ascii_alphanumeric() { c } else { '_' })
        .collect();
    let trimmed = cleaned.trim_matches('_').to_string();
    if trimmed.is_empty() { "unknown".into() } else { trimmed.chars().take(80).collect() }
}
'''
    s = s.replace('/// 在 libnative 上装 hook。返回成功安装的个数。', slot + '\n/// 在 libnative 上装 hook。返回成功安装的个数。', 1)

# 3) hook_send 里记录 URL（找到第一个像 URL 的字符串）
old = '            if let Some(txt) = il2cpp_str(v as *const u8) {\n                if txt.len() >= 4 && txt.chars().all(|c| c.is_ascii_graphic() || c == \' \') {\n                    info!("[url]   +{:#x} -> {}", off, txt);\n                }\n            }'
new = '''            if let Some(txt) = il2cpp_str(v as *const u8) {
                if txt.len() >= 4 && txt.chars().all(|c| c.is_ascii_graphic() || c == ' ') {
                    info!("[url]   +{:#x} -> {}", off, txt);
                    if txt.contains("://") || txt.starts_with('/') || txt.contains("/api/") {
                        set_url(txt.clone());
                    }
                }
            }'''
if old in s:
    s = s.replace(old, new, 1)
    print('  Send 里记录 URL')

# 4) resp JSON 命名带 URL
old_json = '''            Some(j) => {
                let _ = std::fs::write(format!("{}/{:04}_resp.json", dir, seq), j.as_bytes());
                return;
            }'''
new_json = '''            Some(j) => {
                let url = take_url();
                let name = format!("{}/{:04}_{}.json", dir, seq, url);
                let _ = std::fs::write(&name, j.as_bytes());
                info!("[capture] wrote {}", name);
                return;
            }'''
if old_json in s:
    s = s.replace(old_json, new_json, 1)
    print('  JSON 命名带 URL')

io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('改动完成')
