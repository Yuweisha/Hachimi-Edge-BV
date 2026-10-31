import io

p = 'src/il2cpp/hook/umamusume/UmaCapture.rs'
s = io.open(p, encoding='utf-8').read()

# 1) 写盘改成后台线程，钩子里只做转字符串
old = '''            Some(j) => {
                let mut url = take_url();
                if url == "unknown" {
                    url = guess_name(&j);
                }
                let name = format!("{}/{:04}_{}.json", dir, seq, url);
                let pretty = pretty_json(&j);
                let _ = std::fs::write(&name, pretty.as_bytes());
                info!("[capture] wrote {}", name);
                return;
            }'''
new = '''            Some(j) => {
                let mut url = take_url();
                if url == "unknown" {
                    url = guess_name(&j);
                }
                let name = format!("{}/{:04}_{}.json", dir, seq, url);
                // 写盘丢到后台线程，避免阻塞游戏主线程导致 HTTP 超时
                std::thread::spawn(move || {
                    let _ = std::fs::write(&name, j.as_bytes());
                });
                return;
            }'''
if old in s:
    s = s.replace(old, new, 1)
    print('  JSON 写盘已改后台线程，去掉了 pretty')

io.open(p, 'w', encoding='utf-8', newline='\n').write(s)

# 检查 pretty_json 是否还有引用
s2 = io.open(p, encoding='utf-8').read()
print('pretty_json 调用:', s2.count('pretty_json(&'))
print('spawn 数量:', s2.count('thread::spawn'))
