"""最小离线服务器：按 URL 返回录制好的响应。

用法：
    python offline_server.py                 # 监听 127.0.0.1:8443（HTTPS，自签证书）
    python offline_server.py --port 8080
    python offline_server.py --http          # 明文 HTTP（配合 hosts + 代理改写）

工作原理：
    游戏请求 https://api.games.umamusume.jp/umamusume/<path>
    服务器查 C:/Users/Schwarz/uma_replay/<path>/resp.b64
    返回 {"response_code": 1, "data_headers": {...}, "data": <解出的 msgpack>}

注意：
    录制库里存的是**已加密**的响应体（base64）。客户端会自己解密，
    所以理论上可以原样返回。但响应头里的 sid/servertime 需要替换成当前会话的值，
    否则会出现「会话不匹配」。

    本脚本默认走「原样返回」模式，先用来看能不能进游戏。
"""
from __future__ import annotations

import argparse
import base64
import http.server
import json
import os
import ssl
import sys
import threading
import urllib.parse

DB_ROOT = r"C:/Users/Schwarz/uma_replay"
API_PREFIX = "/umamusume/"


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b""

        path = urllib.parse.urlparse(self.path).path
        if path.startswith(API_PREFIX):
            rel = path[len(API_PREFIX):]
        else:
            rel = path.lstrip("/")

        safe = rel.replace("/", "__")
        d = os.path.join(DB_ROOT, safe)
        resp_b64_path = os.path.join(d, "resp.b64")

        if not os.path.exists(resp_b64_path):
            self.log_message("MISS %s (rel=%s)", path, rel)
            payload = b"\x82\xadresponse_code\xcc\xda\xacdata_headers\x80"
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return

        with open(resp_b64_path, "r") as fp:
            b64 = fp.read().strip()

        try:
            payload = base64.b64decode(b64)
        except Exception as e:
            self.log_message("BAD base64 for %s: %s", rel, e)
            self.send_error(500)
            return

        self.log_message("HIT  %s -> %d bytes", rel, len(payload))
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        self.do_POST()


def make_selfsigned(cert_path: str, key_path: str):
    """用 cryptography 生成自签证书（避免依赖 openssl）。"""
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    import datetime

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "api.games.umamusume.jp"),
    ])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.utcnow() - datetime.timedelta(days=1))
        .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=3650))
        .add_extension(
            x509.SubjectAlternativeName([x509.DNSName("api.games.umamusume.jp")]),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )
    with open(key_path, "wb") as fp:
        fp.write(key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        ))
    with open(cert_path, "wb") as fp:
        fp.write(cert.public_bytes(serialization.Encoding.PEM))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8443)
    ap.add_argument("--http", action="store_true", help="明文 HTTP")
    args = ap.parse_args()

    if not os.path.isdir(DB_ROOT):
        print("录制库不存在: %s，先跑 build_offline_db.py" % DB_ROOT)
        return 1

    idx = os.path.join(DB_ROOT, "index.json")
    if os.path.exists(idx):
        data = json.load(open(idx, encoding="utf-8"))
        print("录制库: %d 个接口" % len(data.get("interfaces", [])))

    srv = http.server.ThreadingHTTPServer((args.host, args.port), Handler)

    if not args.http:
        cert = os.path.join(DB_ROOT, "_cert.pem")
        key = os.path.join(DB_ROOT, "_key.pem")
        if not (os.path.exists(cert) and os.path.exists(key)):
            print("生成自签证书 ...")
            make_selfsigned(cert, key)
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(cert, key)
        srv.socket = ctx.wrap_socket(srv.socket, server_side=True)

    scheme = "http" if args.http else "https"
    print("监听 %s://%s:%d" % (scheme, args.host, args.port))
    print("把 api.games.umamusume.jp 指到 %s，端口 %d" % (args.host, args.port))
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n停止")
    return 0


if __name__ == "__main__":
    sys.exit(main())
