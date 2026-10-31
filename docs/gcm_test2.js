const crypto = require('crypto');
const fs = require('fs');
const KEYSTR = "s%5VNQ(H$&Bqb6#3+78h29!Ft4wSg)ex";
const nonce = fs.readFileSync('gcm_nonce.bin');
const ct = fs.readFileSync('gcm_ct.bin');
const tag = fs.readFileSync('gcm_tag.bin');

const cands = {
  'KEYSTR': Buffer.from(KEYSTR, 'utf8'),
  'sha256(KEYSTR)': crypto.createHash('sha256').update(KEYSTR).digest(),
  'md5(KEYSTR)x2': Buffer.concat([crypto.createHash('md5').update(KEYSTR).digest(), crypto.createHash('md5').update(KEYSTR).digest()]),
  'md5(KEYSTR)': crypto.createHash('md5').update(KEYSTR).digest(),
  'sha256(md5(KEYSTR))': crypto.createHash('sha256').update(crypto.createHash('md5').update(KEYSTR).digest()).digest(),
  'md5(KEYSTR).hex+KEYSTR': Buffer.from(crypto.createHash('md5').update(KEYSTR).digest('hex') + KEYSTR).subarray(0, 32),
};
for (const [name, key] of Object.entries(cands)) {
  if (key.length !== 32) { console.log(`${name.padEnd(24)} 长度 ${key.length} 跳过`); continue; }
  for (const alg of ['aes-256-gcm', 'aes-256-ctr']) {
    try {
      if (alg === 'aes-256-gcm') {
        const d = crypto.createDecipheriv(alg, key, nonce);
        d.setAuthTag(tag);
        const out = Buffer.concat([d.update(ct), d.final()]);
        console.log(`✅ ${name} + ${alg} 成功 len=${out.length}`);
        console.log('   hex:', out.subarray(0,32).toString('hex'));
        fs.writeFileSync('gcm_plain.bin', out);
      }
    } catch (e) {}
  }
  console.log(`${name.padEnd(24)} 失败`);
}
