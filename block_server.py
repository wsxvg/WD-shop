#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""屏蔽名单直连写入服务。

为什么需要它：GitHub Pages 是纯静态托管，页面没有任何可写接口，
也没法在页面里放 GitHub Token（JS 对所有访客公开 = 仓库写权限裸奔）。
所以真正能实现「点一下就同步」的，只有一个跑在本机、持有仓库读写权限的进程。

用法：
    python block_server.py            # 监听 127.0.0.1:8766
    python block_server.py --rebuild  # 每次写入后自动重建页面产物

然后照常浏览 GitHub Pages（图片正常），在页面上点「屏蔽」——
只要本服务在跑，名单会**立即写入 data/blocklist.json**，无需再导出/粘贴/提交。
写完只剩一步 `git push`。

安全边界：
- 只绑定 127.0.0.1，外部机器连不上
- 校验 Origin：只放行本机与 github.io，杜绝你随便逛的网站往里灌数据
- 只写 data/blocklist.json 一个文件，不接受任意路径
"""
import argparse
import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "data", "blocklist.json")
VALID_KEYS = {"version", "updated_at", "_readme", "shops", "name_rules"}


def origin_allowed(origin):
    """Origin 头存在时必须来自本机或 GitHub Pages，否则拒绝。

    注意要先把端口摘掉再比域名，否则 "127.0.0.1:8765" 匹配不上 "127.0.0.1"。
    """
    if not origin or origin == "null":
        return True
    host = origin.split("//")[-1].split("/")[0].lower()
    if "@" in host:            # 防 user@host 形式的绕过
        host = host.rsplit("@", 1)[1]
    host = host.rsplit(":", 1)[0] if host.count(":") == 1 else host
    host = host.strip("[]")
    if not host:
        return False
    if host in ("localhost", "127.0.0.1", "::1"):
        return True
    return host.endswith(".github.io") or host.endswith(".github.com")


def write_blocklist(payload):
    """校验并落盘。只接受 blocklist.json 的合法字段。"""
    if not isinstance(payload, dict):
        raise ValueError("body 必须是 JSON 对象")
    unknown = set(payload) - VALID_KEYS
    if unknown:
        raise ValueError("含未知字段: %s" % ", ".join(sorted(unknown)))
    shops = payload.get("shops")
    if shops is not None and not isinstance(shops, list):
        raise ValueError("shops 必须是数组")
    for s in shops or []:
        if not isinstance(s, dict) or s.get("shopId") in (None, ""):
            raise ValueError("shops 里每项都必须含 shopId")
    rules = payload.get("name_rules")
    if rules is not None and not isinstance(rules, list):
        raise ValueError("name_rules 必须是数组")
    payload.setdefault("version", 1)
    payload["updated_at"] = payload.get("updated_at") or __import__("datetime").datetime.now(
        __import__("datetime").timezone.utc).isoformat()
    tmp = TARGET + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    os.replace(tmp, TARGET)   # 原子替换，避免写到一半被读到


class Handler(BaseHTTPRequestHandler):
    rebuild = False

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "600")

    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self.path.split("?")[0] != "/api/status":
            return self._json(404, {"error": "not found"})
        self._json(200, {"ok": True, "service": "blocklist", "rebuild": self.rebuild})

    def do_POST(self):
        if self.path.split("?")[0] != "/api/blocklist":
            return self._json(404, {"error": "not found"})
        if not origin_allowed(self.headers.get("Origin")):
            return self._json(403, {"error": "origin not allowed"})
        try:
            n = int(self.headers.get("Content-Length", 0))
            if n <= 0 or n > 512 * 1024:
                return self._json(400, {"error": "body 大小不合法"})
            payload = json.loads(self.rfile.read(n).decode("utf-8"))
            write_blocklist(payload)
        except Exception as ex:
            return self._json(400, {"error": str(ex)})

        rebuilt = False
        if self.rebuild:
            try:
                subprocess.run([sys.executable, "build_page.py"], cwd=HERE,
                               timeout=180, capture_output=True)
                rebuilt = True
            except Exception as ex:
                return self._json(500, {"error": "已写入，但重建失败: %s" % ex})
        return self._json(200, {"ok": True, "rebuilt": rebuilt,
                                "count": len(payload.get("shops") or [])})

    def log_message(self, fmt, *args):
        sys.stdout.write("  [block_server] " + fmt % args + "\n")
        sys.stdout.flush()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8766)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--rebuild", action="store_true", help="每次写入后重建页面产物")
    a = ap.parse_args()
    Handler.rebuild = a.rebuild
    srv = ThreadingHTTPServer((a.host, a.port), Handler)
    print(f"屏蔽直连服务已启动: http://{a.host}:{a.port}/api/status")
    print(f"  写入目标 : {TARGET}")
    print(f"  写入后重建页面产物: {'是' if a.rebuild else '否'}")
    print("  现在照常打开网站点「屏蔽」即可；写完执行 git push 让别人也生效。")
    print("  Ctrl+C 停止。\n")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止。")


if __name__ == "__main__":
    main()