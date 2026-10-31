import io

p = 'src/il2cpp/hook/umamusume/UmaCapture.rs'
s = io.open(p, encoding='utf-8').read()

parser = '''
// ===== 最小 msgpack -> JSON 解析器（无外部依赖）=====
struct Mp<'a> {
    b: &'a [u8],
    i: usize,
}

impl<'a> Mp<'a> {
    fn new(b: &'a [u8]) -> Self { Mp { b, i: 0 } }

    fn u8(&mut self) -> Option<u8> {
        let v = *self.b.get(self.i)?;
        self.i += 1;
        Some(v)
    }

    fn take(&mut self, n: usize) -> Option<&'a [u8]> {
        if self.i + n > self.b.len() { return None; }
        let s = &self.b[self.i..self.i + n];
        self.i += n;
        Some(s)
    }

    fn be_uint(&mut self, n: usize) -> Option<u64> {
        let s = self.take(n)?;
        let mut v = 0u64;
        for &x in s { v = (v << 8) | x as u64; }
        Some(v)
    }

    fn be_int(&mut self, n: usize) -> Option<i64> {
        let v = self.be_uint(n)?;
        let bits = n * 8;
        if bits == 64 { Some(v as i64) }
        else {
            let sign = 1u64 << (bits - 1);
            if v & sign != 0 { Some((v as i64) - ((1i64) << bits)) } else { Some(v as i64) }
        }
    }

    fn json_str(&self, s: &[u8]) -> String {
        let mut o = String::with_capacity(s.len() + 2);
        o.push('"');
        for &c in s {
            match c {
                b'"' => o.push_str("\\\\\\""),
                b'\\\\' => o.push_str("\\\\\\\\"),
                b'\\n' => o.push_str("\\\\n"),
                b'\\r' => o.push_str("\\\\r"),
                b'\\t' => o.push_str("\\\\t"),
                0x08 => o.push_str("\\\\b"),
                0x0c => o.push_str("\\\\f"),
                0x00..=0x1f => o.push_str(&format!("\\\\u{:04x}", c)),
                _ => { o.push(c as char); }
            }
        }
        o.push('"');
        o
    }

    fn hex(&self, s: &[u8]) -> String {
        let mut o = String::with_capacity(s.len() * 2 + 2);
        o.push('"');
        for &c in s { o.push_str(&format!("{:02x}", c)); }
        o.push('"');
        o
    }

    fn value(&mut self, out: &mut String, depth: usize) -> Option<()> {
        if depth > 64 { return None; }
        let t = self.u8()?;
        match t {
            0x00..=0x7f => out.push_str(&format!("{}", t)),
            0xe0..=0xff => out.push_str(&format!("{}", t as i8)),
            0x80..=0x8f => self.map(out, (t & 0x0f) as usize, depth),
            0x90..=0x9f => self.array(out, (t & 0x0f) as usize, depth),
            0xa0..=0xbf => {
                let s = self.take((t & 0x1f) as usize)?;
                out.push_str(&self.json_str(s));
                Some(())
            }
            0xc0 => { out.push_str("null"); Some(()) }
            0xc2 => { out.push_str("false"); Some(()) }
            0xc3 => { out.push_str("true"); Some(()) }
            0xc4 => { let n = self.u8()? as usize; let s = self.take(n)?; out.push_str(&self.hex(s)); Some(()) }
            0xc5 => { let n = self.be_uint(2)? as usize; let s = self.take(n)?; out.push_str(&self.hex(s)); Some(()) }
            0xc6 => { let n = self.be_uint(4)? as usize; let s = self.take(n)?; out.push_str(&self.hex(s)); Some(()) }
            0xca => { let v = self.be_uint(4)? as u32; out.push_str(&format!("{}", f32::from_bits(v))); Some(()) }
            0xcb => { let v = self.be_uint(8)?; out.push_str(&format!("{}", f64::from_bits(v))); Some(()) }
            0xcc => { let v = self.u8()?; out.push_str(&format!("{}", v)); Some(()) }
            0xcd => { let v = self.be_uint(2)?; out.push_str(&format!("{}", v)); Some(()) }
            0xce => { let v = self.be_uint(4)?; out.push_str(&format!("{}", v)); Some(()) }
            0xcf => { let v = self.be_uint(8)?; out.push_str(&format!("{}", v)); Some(()) }
            0xd0 => { let v = self.be_int(1)?; out.push_str(&format!("{}", v)); Some(()) }
            0xd1 => { let v = self.be_int(2)?; out.push_str(&format!("{}", v)); Some(()) }
            0xd2 => { let v = self.be_int(4)?; out.push_str(&format!("{}", v)); Some(()) }
            0xd3 => { let v = self.be_int(8)?; out.push_str(&format!("{}", v)); Some(()) }
            0xd9 => { let n = self.u8()? as usize; let s = self.take(n)?; out.push_str(&self.json_str(s)); Some(()) }
            0xda => { let n = self.be_uint(2)? as usize; let s = self.take(n)?; out.push_str(&self.json_str(s)); Some(()) }
            0xdb => { let n = self.be_uint(4)? as usize; let s = self.take(n)?; out.push_str(&self.json_str(s)); Some(()) }
            0xdc => { let n = self.be_uint(2)? as usize; self.array(out, n, depth) }
            0xdd => { let n = self.be_uint(4)? as usize; self.array(out, n, depth) }
            0xde => { let n = self.be_uint(2)? as usize; self.map(out, n, depth) }
            0xdf => { let n = self.be_uint(4)? as usize; self.map(out, n, depth) }
            _ => None,
        }
    }

    fn array(&mut self, out: &mut String, n: usize, depth: usize) -> Option<()> {
        out.push('[');
        for i in 0..n {
            if i > 0 { out.push(','); }
            self.value(out, depth + 1)?;
        }
        out.push(']');
        Some(())
    }

    fn map(&mut self, out: &mut String, n: usize, depth: usize) -> Option<()> {
        out.push('{');
        for i in 0..n {
            if i > 0 { out.push(','); }
            let kt = self.u8()?;
            let key = match kt {
                0xa0..=0xbf => {
                    let s = self.take((kt & 0x1f) as usize)?;
                    self.json_str(s)
                }
                0xd9 => { let l = self.u8()? as usize; let s = self.take(l)?; self.json_str(s) }
                0xda => { let l = self.be_uint(2)? as usize; let s = self.take(l)?; self.json_str(s) }
                0xdb => { let l = self.be_uint(4)? as usize; let s = self.take(l)?; self.json_str(s) }
                _ => return None,
            };
            out.push_str(&key);
            out.push(':');
            self.value(out, depth + 1)?;
        }
        out.push('}');
        Some(())
    }
}

fn msgpack_to_json(data: &[u8]) -> Option<String> {
    let mut m = Mp::new(data);
    let mut out = String::with_capacity(data.len() * 2);
    m.value(&mut out, 0)?;
    Some(out)
}
'''

anchor = 'unsafe fn dump(tag: &str, seq: usize, data: *const u8, len: usize) {'
if 'fn msgpack_to_json' not in s:
    s = s.replace(anchor, parser + '\n' + anchor, 1)

old_dump = '''    let _ = std::fs::create_dir_all(&dir);
    let sl = std::slice::from_raw_parts(data, len);
    let _ = std::fs::write(format!("{}/{}_{}.bin", dir, format_args!("{:04}", seq), tag), sl);'''

new_dump = '''    let _ = std::fs::create_dir_all(&dir);
    let sl = std::slice::from_raw_parts(data, len);

    if tag == "resp_dst" {
        match msgpack_to_json(sl) {
            Some(j) => {
                let _ = std::fs::write(format!("{}/{:04}_resp.json", dir, seq), j.as_bytes());
                return;
            }
            None => warn!("[capture] {} seq={} msgpack 解析失败，落 bin", tag, seq),
        }
    }
    let _ = std::fs::write(format!("{}/{:04}_{}.bin", dir, seq, tag), sl);'''

assert old_dump in s, 'dump 块未找到'
s = s.replace(old_dump, new_dump, 1)

io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('已加 Rust 端 msgpack->JSON')
