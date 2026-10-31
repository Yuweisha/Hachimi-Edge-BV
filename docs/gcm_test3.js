const crypto = require('crypto');
const fs = require('fs');
const KEYSTR = "s%5VNQ(H$&Bqb6#3+78h29!Ft4wSg)ex";
const nonce = fs.readFileSync('gcm_nonce.bin');
const ct = fs.readFileSync('gcm_ct.bin');
const tag = fs.readFileSync('gcm_tag.bin');

const md5 = (s) => crypto.createHash('md5').update(s).digest();
const sha = (s) => crypto.createHash('sha256').update(s).digest();

const cands = {
  'KEYSTR[:16]': Buffer.from(KEYSTR).subarray(0, 16),
  'KEYSTR[-16:]': Buffer.from(KEYSTR).subarray(-16),
  'md5(KEYSTR)': md5(KEYSTR),
  'sha256(KEYSTR)[:16]': sha(KEYSTR).subarray(0, 16),
  'sha256(KEYSTR)[16:]': sha(KEYSTR).subarray(16),
  'md5(KEYSTR+KEYSTR)': md5(KEYSTR + KEYSTR),
};
for (const [name, key] of Object.entries(cands)) {
  for (const alg of ['aes-128-gcm', 'aes-192-gcm', 'aes-256-gcm']) {
    const need = { 'aes-128-gcm': 16, 'aes-192-gcm': 24, 'aes-256-gcm': 32 }[alg];
    if (key.length !== need) continue;
    try {
      const d = crypto.createDecipheriv(alg, key, nonce);
      d.setAuthTag(tag);
      const out = Buffer.concat([d.update(ct), d.final()]);
      console.log(`✅ ${name} + ${alg} len=${out.length}`);
      console.log('   hex:', out.subarray(0,32).toString('hex'));
      fs.writeFileSync('gcm_plain.bin', out);
    } catch (e) { /* 继续 */ }
  }
}
console.log('done');
