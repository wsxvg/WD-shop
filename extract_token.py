#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从抓包 HAR 提取 getFollowShops 请求的 context（即登录 token），写入 data/context.json。
用法:
  python extract_token.py                 # 自动取目录里最新的 thor.weidian.com_*.har
  python extract_token.py 路径/xxx.har    # 指定 HAR 文件
写好的 data/context.json 会被 crawl.py 优先用作 token 来源。
"""
import json
import os
import sys
import glob
import urllib.parse as up

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "context.json")


def extract(har_path):
    """从 HAR 提取微店登录 token（即某个微店请求的 context 参数）。
    优先匹配 getFollowShops；若抓包里没有该请求（例如在抖音内打开微店），
    则回退到任意含 context 且带 token 的微店请求——token 是同一登录态，同样可用。"""
    with open(har_path, "r", encoding="utf-8") as f:
        d = json.load(f)
    entries = d["log"]["entries"]

    def parse_ctx(e):
        pd = e["request"].get("postData", {}).get("text", "")
        if pd:
            try:
                return json.loads(up.parse_qs(pd)["context"][0])
            except Exception:
                pass
        try:
            return json.loads(up.parse_qs(up.urlparse(e["request"]["url"]).query)["context"][0])
        except Exception:
            return None

    # 1) 优先 getFollowShops
    for e in entries:
        u = e["request"]["url"]
        if "maimai.getFollowShops/2.0" in u and "HavingShelfItems" not in u:
            c = parse_ctx(e)
            if c:
                return c
    # 2) 回退：任意 thor.weidian.com 且带 token 的请求
    for e in entries:
        if "thor.weidian.com" in e["request"]["url"]:
            c = parse_ctx(e)
            if c and c.get("token"):
                return c
    raise RuntimeError("HAR 中未找到任何微店登录 context")


def main():
    if len(sys.argv) > 1:
        har = sys.argv[1]
    else:
        files = sorted(glob.glob(os.path.join(HERE, "thor.weidian.com_*.har")),
                       key=os.path.getmtime)
        if not files:
            print("未找到 HAR 文件，请传入路径: python extract_token.py xxx.har")
            return
        har = files[-1]
    ctx = extract(har)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(ctx, f, ensure_ascii=False, indent=2)
    print("已写入 token ->", OUT)
    print("uid:", ctx.get("uid"), "appid:", ctx.get("wxappid"))


if __name__ == "__main__":
    main()
