# Token 更新说明 & 抓包解析提示词

## 一、什么是「token」
本项目爬取分两步：
1. **取关注店铺名单**（`getFollowShops` 系列接口，wdbuybuy 域）→ **需要登录态**，即 `context` 参数里的 token。
2. **取单店全量商品**（`getItemList`，decorate 域）→ **公开接口，不需要任何登录态/Cookie**，只要 `shopId` 即可。

所以：**即使 token 过期/缺失，也完全不影响爬取已关注店铺的商品**，只是无法发现"新关注的店铺"。

## 二、token 的格式
token 就是抓包里 `getFollowShops` 请求的 **`context` 参数反解后的整个 JSON 对象**（一个 dict），例如：

```json
{
  "token": "xxxx",
  "refreshToken": "xxxx",
  "uid": "123456",
  "wxappid": "wx4d1258677af59f5c",
  "wxtoken": "...",
  "deviceInfo": {},
  "env": {}
}
```

> 注意：不同时间/账号抓到的字段可能略有差异。**请把 `context` 反解后的「整个 JSON 对象」原样保存**，不要只取其中某个字段。字段数量和名称以实际抓包为准。
> 本项目约定把该 JSON 对象存到 **`data/context.json`**（一个纯 JSON 文件，内容就是上面的对象）。

## 三、如何更换 token（两种方式）

### 方式 A：本地有 HAR 文件（推荐）
1. 浏览器/微信打开「我关注的微店」页面，用开发者工具导出 HAR（或抓包保存为 `.har`）。
2. 放到项目目录，执行：
   ```powershell
   python extract_token.py xxx.har
   ```
   它会把 `context` 提取并写入 `data/context.json`。
3. 之后正常 `python crawl.py` 即可（会自动用最新的 context.json）。

### 方式 B：把抓包内容发给 AI 解析（见下方提示词）
把抓包得到的文本（HAR 文件内容，或某次 `getFollowShops` 请求的 URL/请求体）连同下方提示词一起发给 AI，让它输出 `context` 的 JSON，你再把该 JSON 存为 `data/context.json`。

## 四、发给 AI 的提示词（直接复制）

```
你是一个抓包解析助手。我会给你一段微店（weidian）的 HTTP 抓包内容（可能是完整 HAR 的 JSON，也可能是某次请求的 URL 或请求体文本）。
请从中找到接口路径包含 `maimai.getFollowShops/2.0` 且不包含 `HavingShelfItems` 的那一次请求。
该请求的 `context` 参数（位于 URL query 或 POST 表单体内，值为 URL 编码的 JSON 字符串）就是登录 token。
请：
1. 把 `context` 参数做 URL 解码 + JSON 解析；
2. 只输出解析后的「完整 JSON 对象」本身（不要任何解释、不要 markdown 代码块包裹、不要省略任何字段）；
3. 如果找到多个，只输出第一个。
输出示例（仅作格式参考，实际以抓包为准）：
{"token":"...","refreshToken":"...","uid":"...","wxappid":"...", ...}
```

## 五、token 过期后会怎样
- 页面顶部会出现橙色提示条：「⚠️ Token 已过期，无法获取新关注店铺，请及时更新（已爬取的商品数据不受影响）」。
- `crawl.py` 检测到 token 失效后，会自动跳过"取关注列表"，改为载入历史 `data/follow_shops.json`，只刷新已有店铺的商品（这一步不需要 token）。
- 你只需按上面的方式更新 `data/context.json`，下次 `crawl.py` 就会重新发现新关注的店铺。

## 六、安全提醒（上传 GitHub 前必读）
- **切勿**把 `.har` 文件、`data/context.json` 提交到 Git/GitHub（含登录 token，等同账号密码）。
- 项目已通过 `.gitignore` 忽略上述文件。只提交：`data/follow_shops.json`、`index.html`、`*.py`、`TOKEN_GUIDE.md` 等。
