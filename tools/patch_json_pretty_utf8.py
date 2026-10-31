import io

p = 'src/il2cpp/hook/umamusume/UmaCapture.rs'
s = io.open(p, encoding='utf-8').read()

# 1) json_str 改成整段 UTF-8 处理（保留转义），不再逐字节 as char
old_fn_start = s.index('    fn json_str(&self, s: &[u8]) -> String {')
old_fn_end = s.index('    fn hex(&self, s: &[u8]) -> String {')
new_fn = '''    fn json_str(&self, s: &[u8]) -> String {
        // 整段按 UTF-8 解码，非法序列替换掉，避免逐字节 as char 打乱多字节字符
        let text = String::from_utf8_lossy(s);
        let mut o = String::with_capacity(text.len() + 2);
        o.push('"');
        for ch in text.chars() {
            match ch {
                '"' => o.push_str("\\\\\\""),
                '\\\\' => o.push_str("\\\\\\\\"),
                '\\n' => o.push_str("\\\\n"),
                '\\r' => o.push_str("\\\\r"),
                '\\t' => o.push_str("\\\\t"),
                '\\u{8}' => o.push_str("\\\\b"),
                '\\u{c}' => o.push_str("\\\\f"),
                c if (c as u32) < 0x20 => o.push_str(&format!("\\\\u{:04x}", c as u32)),
                c => o.push(c),
            }
        }
        o.push('"');
        o
    }

'''
s = s[:old_fn_start] + new_fn + s[old_fn_end:]

# 2) 输出带缩进的 JSON
indent_fn = '''
/// 给紧凑 JSON 加缩进（只处理字符串外的括号/逗号）
fn pretty_json(src: &str) -> String {
    let mut out = String::with_capacity(src.len() + src.len() / 3);
    let mut depth = 0usize;
    let mut in_str = false;
    let mut esc = false;

    for ch in src.chars() {
        if in_str {
            out.push(ch);
            if esc {
                esc = false;
            } else if ch == '\\\\' {
                esc = true;
            } else if ch == '"' {
                in_str = false;
            }
            continue;
        }
        match ch {
            '"' => { in_str = true; out.push(ch); }
            '{' | '[' => {
                out.push(ch);
                depth += 1;
                out.push('\\n');
                for _ in 0..depth { out.push_str("  "); }
            }
            '}' | ']' => {
                depth = depth.saturating_sub(1);
                out.push('\\n');
                for _ in 0..depth { out.push_str("  "); }
                out.push(ch);
            }
            ',' => {
                out.push(ch);
                out.push('\\n');
                for _ in 0..depth { out.push_str("  "); }
            }
            ':' => { out.push_str(": "); }
            _ => out.push(ch),
        }
    }
    out
}
'''
if 'fn pretty_json' not in s:
    s = s.replace('fn msgpack_to_json(data: &[u8]) -> Option<String> {',
                  indent_fn + '\nfn msgpack_to_json(data: &[u8]) -> Option<String> {', 1)

# 3) 写盘时用 pretty
old_write = '                let _ = std::fs::write(&name, j.as_bytes());'
new_write = '                let pretty = pretty_json(&j);\n                let _ = std::fs::write(&name, pretty.as_bytes());'
if old_write in s:
    s = s.replace(old_write, new_write, 1)
    print('  已加缩进输出')

io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('改动完成')
