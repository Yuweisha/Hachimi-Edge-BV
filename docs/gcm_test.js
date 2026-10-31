const crypto = require('crypto');
const fs = require('fs');
const key = Buffer.from("s%5VNQ(H$&Bqb6#3+78h29!Ft4wSg)ex", 'utf8');
const nonce = fs.readFileSync('gcm_nonce.bin');
const ct = fs.readFileSync('gcm_ct.bin');
const tag = fs.readFileSync('gcm_tag.bin');
console.log('key', key.length, 'nonce', nonce.length, 'ct', ct.length, 'tag', tag.length);
try {
  const d = crypto.createDecipheriv('aes-256-gcm', key, nonce);
  d.setAuthTag(tag);
  const out = Buffer.concat([d.update(ct), d.final()]);
  console.log('SUCCESS len =', out.length);
  console.log('hex:', out.subarray(0, 48).toString('hex'));
  console.log('asc:', out.subarray(0, 48).toString('latin1').replace(/[^\x20-\x7e]/g, '.'));
  fs.writeFileSync('gcm_plain.bin', out);
} catch (e) { console.log('FAIL:', e.message); }
