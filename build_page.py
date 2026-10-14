#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 data/follow_shops.json 拆成前端秒开所需的分层数据文件：

- data/shops_index.json      店铺元数据（~50KB，首屏秒开）
- data/shops_products_*.json 全量商品分块（每块 7000 件，后台排队加载）
- data/shops_products.json   全量商品单文件（兼容旧版，页面已不再优先读它）
- data/shops_data.json       旧完整格式（兼容兜底）
- data/status.json           token 状态 + 统计（供页面顶部提示）

同时应用【全局屏蔽名单】data/blocklist.json：命中的店铺不进入任何产物。
crawl.py 已在爬取源头过滤，这里再过滤一次是为了让「刚加进屏蔽名单、还没重跑
爬虫」的情况也能立刻从页面产物中消失。

注意：index.html 由人工维护，本脚本不生成 HTML。
"""
import glob
import json
import os
import time

from crawl import load_blocklist, block_reason

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "follow_shops.json")
STATUS = os.path.join(HERE, "data", "status.json")


def load_data():
    with open(DATA, "r", encoding="utf-8") as f:
        return json.load(f)


def drop_blocked(data):
    """剔除命中全局屏蔽名单的店铺，返回 (保留列表, 屏蔽数, 屏蔽商品数)。"""
    ids, rules = load_blocklist()
    if not ids and not rules:
        return data, 0, 0
    kept, blocked_items = [], 0
    for s in data:
        hit, _ = block_reason(s, ids, rules)
        if hit:
            blocked_items += len(s.get("items") or [])
        else:
            kept.append(s)
    return kept, len(data) - len(kept), blocked_items


def main():
    data = load_data()

    # 读 status.json：token 状态沿用 crawl 的写入，店铺/商品数稍后按本次数据重算，
    # 避免与实际数据不一致（此前曾出现 status 159/27687 而实际 165/18472）
    st = {}
    if os.path.exists(STATUS):
        try:
            st = json.load(open(STATUS, encoding="utf-8"))
            if not isinstance(st, dict):
                st = {}
        except Exception:
            st = {}
    expired = bool(st.get("token_expired"))

    # 屏蔽名单过滤（幂等：crawl.py 已过滤过的话这里不会有变化）
    before = len(data)
    data, blocked_shops, blocked_items = drop_blocked(data)
    if blocked_shops:
        print(f"  [block] 剔除屏蔽店铺 {blocked_shops} 个 / {blocked_items} 件商品 "
              f"（{before} -> {len(data)}）")

    # shops_index.json —— 店铺元数据（不含商品），页面首屏秒开
    idx = []
    for s in data:
        sc = dict(s)
        sc["itemCount"] = len(s.get("items") or [])  # 页面「查看全部 N 件商品」用
        sc["items"] = []  # 不嵌入商品，仅保留店铺信息
        idx.append(sc)
    idx_path = os.path.join(HERE, "data", "shops_index.json")
    with open(idx_path, "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False)

    # shops_products.json —— 扁平化全量商品，后台异步分块加载
    products = []
    for s in data:
        sid = s["shopId"]
        for it in s.get("items", []):
            products.append({
                "s": sid,
                "i": it.get("itemId"),
                "n": it.get("itemName"),
                "g": it.get("image"),
                "p": it.get("price"),
                "t": it.get("addTime", ""),
                "k": it.get("stock", 0),
                "d": it.get("soldText", ""),
                "u": it.get("soldNum", 0),
                "o": it.get("originalPrice", 0),
                "a": it.get("itemTag", []),
                "r": it.get("preSale", False),
                "h": it.get("hasSku", False),
                "f": it.get("freeShip", False),
                "m": it.get("status", 1),
                "c": it.get("itemComment", ""),
            })
    # 按 7000 件/块分段，首块秒出，其余后台排队
    CHUNK = 7000
    total_prods = len(products)
    n_chunks = (total_prods + CHUNK - 1) // CHUNK
    # 先清掉所有旧分块：分块数变少时（如 4 块 → 3 块）残留的旧文件会被页面
    # 的「fetch 到 404 为止」逻辑加载，混入上万件过期幽灵商品
    for old in glob.glob(os.path.join(HERE, "data", "shops_products_*.json")):
        os.remove(old)
        print(f"  [clean] 删除旧分块 {os.path.basename(old)}")
    for ci in range(n_chunks):
        chunk = products[ci * CHUNK: (ci + 1) * CHUNK]
        cp = os.path.join(HERE, f"data/shops_products_{ci}.json")
        with open(cp, "w", encoding="utf-8") as f:
            json.dump(chunk, f, ensure_ascii=False, separators=(",", ":"))
        print(f"  -> shops_products_{ci}.json: {os.path.getsize(cp)} bytes ({len(chunk)} 件)")

    # 保留完整文件兼容旧版
    prod_path = os.path.join(HERE, "data", "shops_products.json")
    with open(prod_path, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, separators=(",", ":"))

    # 保留旧 shops_data.json 兼容（页面加载新格式失败时的兜底）
    data_path = os.path.join(HERE, "data", "shops_data.json")
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

    # 回写 status.json：统计与本次产物保持一致
    st["shops"] = len(data)
    st["products"] = total_prods
    st["blocked_shops"] = blocked_shops
    # 告诉页面一共有几块，省掉「一直 fetch 到 404 为止」时产生的那次 404
    st["chunks"] = n_chunks
    st.setdefault("token_expired", False)
    st.setdefault("token_source", "none")
    st.setdefault("updated_at", "")
    st["build_time"] = int(time.time())
    with open(STATUS, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=2)

    n_items = sum(1 for d in data if d.get("items"))
    print(f"shops: {len(data)} with items: {n_items} products: {total_prods}"
          f" blocked: {blocked_shops}")
    print("token 提示:", "已过期（页面将显示提示）" if expired else "正常")


if __name__ == "__main__":
    main()