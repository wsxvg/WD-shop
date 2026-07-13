#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用 HAR 中捕获的鉴权上下文，分页拉取「我关注的微店」全部店铺，
并用公开接口 /decorate/shopDetail.tab.getItemList 补全每个店铺的【全量在售商品】
（关注流接口只返回每店前 9 件预览，此接口按 offset/limit 分页返回完整列表）。

输出 data/follow_shops.json（与 build_page.py 共用）。

用法:
  python crawl.py            # 自动从最新 HAR 提取 context 并爬取
  python crawl.py --har xxx.har --pagesize 50
"""
import json
import os
import sys
import glob
import time
import urllib.parse
import urllib.request
import gzip
import re
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_HAR = os.path.join(HERE, "thor.weidian.com_2026_07_13_18_46_45.har")
OUT = os.path.join(HERE, "data", "follow_shops.json")
STATUS = os.path.join(HERE, "data", "status.json")
CONTEXT_FILE = os.path.join(HERE, "data", "context.json")

# 当 token 来自独立的 context.json（而非 HAR）时使用的默认请求头
DEFAULT_HEADERS = {
    "x-origin": "https://thor.weidian.com",
    "referer": "https://thor.weidian.com/wdbuybuy/maimai.getFollowShops/2.0",
    "accept": "application/json, text/plain, */*",
}

WDBASE = "https://thor.weidian.com/wdbuybuy/"
DECOBASE = "https://thor.weidian.com/decorate/"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36 MicroMessenger/7.0.20.1781")


def find_latest_har(here):
    """自动选用目录里最新的 thor.weidian.com_*.har 作为鉴权来源。"""
    files = glob.glob(os.path.join(here, "thor.weidian.com_*.har"))
    if not files:
        return DEFAULT_HAR
    return max(files, key=os.path.getmtime)


def load_har_context(har_path):
    """从 HAR 中第一个 getFollowShops 请求提取鉴权 context 与请求头。"""
    with open(har_path, "r", encoding="utf-8") as f:
        har = json.load(f)
    for e in har["log"]["entries"]:
        url = e["request"]["url"]
        if "maimai.getFollowShops/2.0" in url and "HavingShelfItems" not in url:
            if e["request"].get("method") == "POST" and e["request"].get("postData"):
                qs = urllib.parse.parse_qs(e["request"]["postData"]["text"])
            else:
                qs = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
            context = json.loads(qs["context"][0])
            headers = {}
            for h in e["request"]["headers"]:
                n, v = h["name"].lower(), h["value"]
                if n in ("x-origin", "referer", "accept"):
                    headers[n] = v
            return context, headers
    raise RuntimeError("HAR 中未找到 getFollowShops 请求")


def load_context(har_path=None):
    """解析 token（即 HAR 中 getFollowShops 请求的 context 参数）。
    优先读取 data/context.json（由用户/AI 从抓包提取），回退到最新 HAR。
    返回 (context, headers, source)；context 为 None 表示当前无可用 token。"""
    if har_path is None and os.path.exists(CONTEXT_FILE):
        try:
            with open(CONTEXT_FILE, "r", encoding="utf-8") as f:
                ctx = json.load(f)
            if isinstance(ctx, dict):
                return ctx, dict(DEFAULT_HEADERS), "context.json"
        except Exception as ex:
            print("  [warn] 读取 data/context.json 失败:", ex)
        har_path = find_latest_har(HERE)
    if har_path and os.path.exists(har_path):
        try:
            ctx, headers = load_har_context(har_path)
            return ctx, headers, "har:" + os.path.basename(har_path)
        except Exception as ex:
            print("  [warn] 从 HAR 提取 context 失败:", ex)
    return None, None, None


def save_status(out_path, token_ok, source, shops, total_products):
    """写入 data/status.json，供页面展示 token 是否过期。"""
    status = {
        "token_expired": not token_ok,
        "token_source": source or "none",
        "follow_refreshed": token_ok,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "shops": len(shops),
        "products": total_products,
    }
    try:
        with open(STATUS, "w", encoding="utf-8") as f:
            json.dump(status, f, ensure_ascii=False, indent=2)
    except Exception as ex:
        print("  [warn] 写入 status.json 失败:", ex)


def _decode(resp):
    raw = resp.read()
    if resp.headers.get("Content-Encoding", "").lower() == "gzip":
        raw = gzip.decompress(raw)
    return json.loads(raw.decode("utf-8"))


def call_api(context, path, page_num, page_size, headers):
    """POST 接口（wdbuybuy 域，关注列表等）。"""
    param = {"pageNum": page_num, "pageSize": page_size}
    body = urllib.parse.urlencode(
        {"param": json.dumps(param, separators=(",", ":")),
         "context": json.dumps(context, separators=(",", ":"))}
    ).encode("utf-8")
    req = urllib.request.Request(WDBASE + path, data=body, method="POST")
    req.add_header("content-type", "application/x-www-form-urlencoded")
    req.add_header("user-agent", UA)
    req.add_header("xweb_xhr", "1")
    req.add_header("accept", "*/*")
    req.add_header("accept-encoding", "identity")
    for k, v in headers.items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return _decode(resp)


def call_api_get(context, path, param, headers):
    """GET 接口（decorate 域，店铺商品列表，公开无需登录）。"""
    data = {"param": json.dumps(param, separators=(",", ":"))}
    # 带 context（若提供了有效鉴权则带，否则仅 param 也能公开访问）
    if context is not None:
        data["context"] = json.dumps(context, separators=(",", ":"))
    url = DECOBASE + path + "?" + urllib.parse.urlencode(data)
    req = urllib.request.Request(url, method="GET")
    req.add_header("user-agent", UA)
    req.add_header("xweb_xhr", "1")
    req.add_header("referer",
                   "https://servicewechat.com/wx4d1258677af59f5c/196/page-frame.html")
    if headers:
        for k, v in headers.items():
            if k == "referer":
                continue
            req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return _decode(resp)


def crawl(path, context, headers, page_size, max_pages=200):
    out = []
    for p in range(1, max_pages + 1):
        d = call_api(context, path, p, page_size, headers)
        st = d.get("status", {})
        if st.get("code") != 0:
            print(f"  [{path}] page {p} 返回错误: {st}  -> 停止")
            break
        rows = d.get("result", {}).get("dataList", [])
        out.extend(rows)
        has_more = d.get("result", {}).get("hasMore", False)
        print(f"  [{path}] page {p}: +{len(rows)} 条 (累计 {len(out)}, hasMore={has_more})")
        if not has_more or not rows:
            break
    return out


def norm_item(it):
    """把 getItemList 返回的商品字段映射成页面需要的格式。
    保留更多字段以支持销量/库存/标签等展示。
    """
    price = it.get("price")
    try:
        price_fen = int(round(float(price) * 100))
    except (TypeError, ValueError):
        price_fen = 0
    oprice = it.get("originalPrice")
    oprice_fen = 0
    if oprice is not None:
        try:
            oprice_fen = int(round(float(oprice) * 100))
        except (TypeError, ValueError):
            pass
    add_time = it.get("addTime")
    add_str = ""
    if add_time:
        try:
            add_str = datetime.fromtimestamp(int(add_time) / 1000, tz=timezone.utc)\
                .strftime("%Y-%m-%d")
        except (TypeError, ValueError, OverflowError):
            add_str = ""
    sold_text = it.get("sold") or ""
    sold_num = 0
    if sold_text:
        m = re.search(r'(\d+)', sold_text)
        if m:
            sold_num = int(m.group(1))
    return {
        "itemId": it.get("itemId"),
        "itemName": it.get("itemName"),
        "image": it.get("itemImg") or it.get("image"),
        "price": price_fen,
        "addTime": add_str,
        "stock": it.get("stock") or 0,
        "soldText": sold_text,
        "soldNum": sold_num,
        "originalPrice": oprice_fen,
        "itemTag": it.get("itemTag") or [],
        "preSale": bool(it.get("preSale")),
        "hasSku": bool(it.get("hasSku")),
    }


def crawl_shop_items(context, headers, shop_id, limit=100, max_retry=1):
    """用 decorate.shopDetail.tab.getItemList 分页拉取某店铺全部在售商品。
    每页 limit 拉到最大(2000)，翻页最少→总请求最少→最不易被限频。
    不在函数内做退避重试（限频是全局性的，交给调用方的冷却逻辑统一处理），
    仅检测：业务错误码 / 结果非 dict / 首页静默空 → 判为限频返回空列表。
    该接口公开，context 可为 None。"""
    items = []
    offset = 0
    while True:
        param = {"shopId": str(shop_id), "tabId": 0, "sortOrder": "desc",
                 "offset": offset, "limit": limit, "from": "wdplus",
                 "showItemTag": True}
        try:
            d = call_api_get(context, "shopDetail.tab.getItemList/1.0", param, headers)
        except Exception as e:
            print(f"    shop {shop_id} 请求异常: {type(e).__name__}: {e}")
            return items
        st = d.get("status", {}).get("code")
        res = d.get("result")
        if st != 0 or not isinstance(res, dict):
            print(f"    shop {shop_id} 业务错误: code={st}")
            return items
        lst = res.get("itemList", [])
        if offset == 0 and len(lst) == 0 and not res.get("hasData", False):
            return items  # 首页静默空 → 限频，返回空让调用方冷却重试
        items.extend(lst)
        if len(lst) < limit or not res.get("hasData", False):
            break
        offset += limit
        time.sleep(1.0)  # 翻页间隔（降频）
    return items


def save_progress(shops, out):
    """把当前 shops（已含补全的 items）写出，实时保存防中断丢数据。"""
    merged = []
    for r in shops:
        rec = dict(r)
        if "items" not in rec:
            rec["items"] = []
        rec["hasShelfItems"] = bool(rec.get("onShelfItemNum", 0) > 0 or rec.get("items"))
        merged.append(rec)
    merged.sort(key=lambda x: x.get("followTime", 0), reverse=True)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)


def main():
    har_arg = sys.argv[sys.argv.index("--har") + 1] if "--har" in sys.argv else None
    page_size = 50
    if "--pagesize" in sys.argv:
        page_size = int(sys.argv[sys.argv.index("--pagesize") + 1])

    # 阶段1：解析 token（context）。无 token 也能跑，只是无法获取新关注店铺
    context, headers, source = load_context(har_arg)
    print("token 来源:", source or "无（将仅刷新已有店铺的商品）")
    if context is not None:
        print("uid:", context.get("uid"), "appid:", context.get("wxappid"))

    # 阶段2：尝试用 token 拉最新关注列表（可失败/过期）
    fresh = None
    if context is not None:
        try:
            s1 = crawl("maimai.getFollowShops/2.0", context, headers, page_size)
            s2 = crawl("maimai.getFollowShopsHavingShelfItems/2.0", context, headers, page_size)
            if len(s1) == 0:
                print("  [!] 关注列表返回 0 条，token 可能已失效")
            else:
                fresh = (s1, s2)
        except Exception as e:
            print("  [!] 取关注列表失败（token 可能已过期）:", e)

    token_ok = fresh is not None

    # 阶段3：决定店铺名单
    if token_ok:
        shops_all, with_items = fresh
        by_id = {r["shopId"]: r for r in shops_all if "shopId" in r}
        shelf_ids = set()
        for r in with_items:
            sid = r.get("shopId")
            if sid:
                shelf_ids.add(sid)
                if sid in by_id:
                    by_id[sid]["shopAddTime"] = r.get("addTime")
        shops = shops_all
        print(f"已用 token 刷新关注列表：{len(shops)} 个店铺")
    else:
        if os.path.exists(OUT):
            existing = json.load(open(OUT, encoding="utf-8"))
            by_id = {r["shopId"]: r for r in existing if "shopId" in r}
            shops = existing
            # 全量刷新所有店铺，空店 getItemList 公开接口也能正常返回 0 件
            shelf_ids = set(by_id.keys())
            print(f"  [!] Token 已过期/缺失，载入历史 {len(shops)} 个店铺，"
                  f"仅刷新商品（不获取新关注）")
        else:
            print("  [!] 无 token 且无历史数据，无法爬取。请更新 data/context.json 后重试。")
            return

    # 阶段4：商品补全（getItemList 公开接口，无需 token，可增量刷新）
    total = len(shelf_ids)
    print(f"刷新 {total} 个店铺的全量商品 (getItemList)…", flush=True)
    t0 = time.time()
    pending = list(shelf_ids)
    consecutive_empty = 0
    cooldowns = 0
    MAX_COOLDOWNS = 20
    done_count = 0
    while pending:
        sid = pending.pop(0)
        shop_name = str(by_id.get(sid, {}).get("name") or sid)[:18]
        raw = crawl_shop_items(context, headers, sid)
        if raw:
            by_id[sid]["items"] = [norm_item(it) for it in raw]
            by_id[sid]["hasShelfItems"] = True
            consecutive_empty = 0
            done_count += 1
            pct = done_count / total * 100 if total else 100
            bar_len = 20
            filled = int(bar_len * done_count / total) if total else bar_len
            bar = "#" * filled + "-" * (bar_len - filled)
            elapsed = time.time() - t0
            eta = elapsed / done_count * (total - done_count) if done_count else 0
            print(f"  [{bar}] {done_count}/{total} {pct:.1f}% | "
                  f"{shop_name} {len(raw)}件 | 剩{total-done_count}家 "
                  f"已用{elapsed:.0f}s 预计还需{eta:.0f}s", flush=True)
        else:
            consecutive_empty += 1
            pending.append(sid)  # 限频，放回队尾稍后重试
            print(f"  [限频重试] {shop_name} 暂无返回，放回队尾 "
                  f"(已完成 {done_count}/{total})", flush=True)
            if consecutive_empty >= 2:
                cooldowns += 1
                if cooldowns > MAX_COOLDOWNS:
                    print("  !! 限频超时，放弃剩余未填店铺，保存已得数据", flush=True)
                    pending = []
                    break
                print(f"  !! 检测到限频，全局冷却 300s "
                      f"({cooldowns}/{MAX_COOLDOWNS})…", flush=True)
                time.sleep(300)
                consecutive_empty = 0
        if done_count % 5 == 0 or not pending:
            save_progress(shops, OUT)
        time.sleep(2.5)
    # 其余无在售店铺 items 置空
    for sid in by_id:
        if "items" not in by_id[sid]:
            by_id[sid]["items"] = []
            by_id[sid]["hasShelfItems"] = False
    save_progress(shops, OUT)
    print(f"商品补全完成，用时 {time.time()-t0:.1f}s")

    n_items = sum(1 for r in shops if r.get("items"))
    total_products = sum(len(r.get("items", [])) for r in shops)
    save_status(OUT, token_ok, source, shops, total_products)
    print(f"\n完成: {len(shops)} 个店铺, 其中 {n_items} 个有在售商品, "
          f"共 {total_products} 件全量商品 -> {OUT}")
    print("  token 状态:", "有效（已刷新关注列表）" if token_ok
          else "已过期/缺失（仅刷新已有商品，未获取新关注店铺）")


if __name__ == "__main__":
    main()
