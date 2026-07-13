// Deno Deploy 入口：服务静态文件（index.html / data/*.json 等）
// 在 https://console.deno.com 创建项目 → 连接本仓库 → 入口选这个文件即可
import { serveDir } from "jsr:@std/http/file-server";

Deno.serve((req) => serveDir(req, { fsRoot: "." }));
