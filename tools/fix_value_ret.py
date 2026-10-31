import io, re

p = 'src/il2cpp/hook/umamusume/UmaCapture.rs'
s = io.open(p, encoding='utf-8').read()

# 这些分支返回 ()，需要包成 Some(())
repl = [
    ('0x00..=0x7f => out.push_str(&format!("{}", t)),',
     '0x00..=0x7f => { out.push_str(&format!("{}", t)); Some(()) }'),
    ('0xe0..=0xff => out.push_str(&format!("{}", t as i8)),',
     '0xe0..=0xff => { out.push_str(&format!("{}", t as i8)); Some(()) }'),
    ('0xcc => { let v = self.u8()?; out.push_str(&format!("{}", v)); Some(()) }',
     '0xcc => { let v = self.u8()?; out.push_str(&format!("{}", v)); Some(()) }'),
]
for a, b in repl:
    if a in s:
        s = s.replace(a, b, 1)

io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('已修 value 分支返回类型')
