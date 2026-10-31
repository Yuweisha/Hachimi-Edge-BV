import io

p = 'src/il2cpp/hook/umamusume/UmaCapture.rs'
s = io.open(p, encoding='utf-8').read()

# 在 take_url 之后加一个「按内容猜接口名」的函数
guess = '''
/// 没有 URL 时，按 msgpack 内容猜一个可读名字
fn guess_name(json: &str) -> String {
    // 只检查前 4KB，避免大响应全扫
    let head = if json.len() > 4096 { &json[..4096] } else { json };
    let hints: &[(&str, &str)] = &[
        ("\\"card_list\\"", "load_index"),
        ("\\"support_card_list\\"", "load_index"),
        ("\\"chara_list\\"", "load_index"),
        ("\\"trained_chara\\"", "load_index"),
        ("\\"resource_version\\"", "start_session"),
        ("\\"attest\\"", "start_session"),
        ("\\"music_list\\"", "live_music_list"),
        ("\\"live_permission_data\\"", "live_permission"),
        ("\\"user_info\\"", "user_info"),
        ("\\"mission_list\\"", "mission_list"),
        ("\\"present_list\\"", "present_list"),
        ("\\"gacha_info\\"", "gacha_info"),
        ("\\"home_info\\"", "home_info"),
        ("\\"team_data\\"", "team_data"),
        ("\\"race_result\\"", "race_result"),
        ("\\"single_mode\\"", "single_mode"),
        ("\\"story_event\\"", "story_event"),
        ("\\"shop\\"", "shop"),
        ("\\"notification\\"", "notification"),
    ];
    for (pat, name) in hints {
        if head.contains(pat) {
            return (*name).to_string();
        }
    }
    // 兜底：用 response_code + 大小
    format!("resp{}", json.len())
}
'''

anchor = '/// 在 libnative 上装 hook。返回成功安装的个数。'
if 'fn guess_name' not in s:
    s = s.replace(anchor, guess + '\n' + anchor, 1)

# JSON 写盘时，URL 为 unknown 就用猜测名
old = '''            Some(j) => {
                let url = take_url();
                let name = format!("{}/{:04}_{}.json", dir, seq, url);
                let _ = std::fs::write(&name, j.as_bytes());
                info!("[capture] wrote {}", name);
                return;
            }'''
new = '''            Some(j) => {
                let mut url = take_url();
                if url == "unknown" {
                    url = guess_name(&j);
                }
                let name = format!("{}/{:04}_{}.json", dir, seq, url);
                let _ = std::fs::write(&name, j.as_bytes());
                info!("[capture] wrote {}", name);
                return;
            }'''
if old in s:
    s = s.replace(old, new, 1)
    print('  已加内容推断命名')

io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('改动完成')
