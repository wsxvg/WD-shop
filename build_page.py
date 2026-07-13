#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""根据 data/follow_shops.json 生成「我关注的微店」双视角单文件页面。
- 店铺视角：关注店铺卡片（可展开在售商品）
- 商品视角：跨商家摊平的商品总表，每件商品带「商家标签 + 价格」
数据内联进 index.html，双击即可打开。"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "follow_shops.json")


def load_data():
    with open(DATA, "r", encoding="utf-8") as f:
        return json.load(f)


HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>我关注的微店</title>
<style>
  :root{
    --bg:#f5f6f8; --card:#fff; --text:#1f2329; --sub:#8a9099;
    --line:#ebedf0; --brand:#ff5b4a; --brand-soft:#fff0ee; --chip:#eef0f3;
    --shadow:0 1px 3px rgba(0,0,0,.06),0 6px 18px rgba(0,0,0,.04);
  }
  *{box-sizing:border-box;}
  body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;
    background:var(--bg);color:var(--text);-webkit-font-smoothing:antialiased;}
  .wrap{max-width:1180px;margin:0 auto;padding:20px 16px 60px;}
  header h1{font-size:22px;margin:0 0 4px;display:flex;align-items:center;gap:8px;}
  header .stat{color:var(--sub);font-size:13px;margin-bottom:16px;}
  .tabs{display:flex;gap:8px;margin-bottom:14px;}
  .tab{padding:8px 16px;border-radius:10px;border:1px solid var(--line);background:var(--card);
    cursor:pointer;font-size:14px;font-weight:600;color:var(--sub);}
  .tab.active{background:var(--brand);color:#fff;border-color:var(--brand);}
  .toolbar{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px;
    box-shadow:var(--shadow);margin-bottom:18px;position:sticky;top:0;z-index:5;}
  .row{display:flex;gap:10px;flex-wrap:wrap;align-items:center;}
  .row + .row{margin-top:10px;}
  input[type=text],input[type=number],select{font-size:14px;padding:9px 12px;border:1px solid var(--line);
    border-radius:10px;background:#fafbfc;color:var(--text);outline:none;transition:border-color .15s;}
  input:focus,select:focus{border-color:var(--brand);background:#fff;}
  #search,#pSearch{flex:1;min-width:200px;}
  .toggle{display:inline-flex;align-items:center;gap:6px;font-size:13px;color:var(--sub);cursor:pointer;
    user-select:none;padding:8px 10px;border:1px solid var(--line);border-radius:10px;background:#fafbfc;}
  .toggle input{accent-color:var(--brand);}
  label.lbl{font-size:12px;color:var(--sub);}
  .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(248px,1fr));gap:14px;}
  .card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px;
    box-shadow:var(--shadow);display:flex;flex-direction:column;gap:10px;}
  .card.link{cursor:pointer;text-decoration:none;color:inherit;}
  .card.link:hover{transform:translateY(-2px);box-shadow:0 4px 10px rgba(0,0,0,.08),0 12px 28px rgba(0,0,0,.06);}
  .top{display:flex;gap:11px;align-items:center;}
  .avatar{width:48px;height:48px;border-radius:12px;object-fit:cover;background:var(--chip);flex:none;}
  .name{font-weight:600;font-size:15px;line-height:1.25;word-break:break-word;}
  .sid{font-size:11px;color:var(--sub);margin-top:2px;}
  .badge{display:inline-block;font-size:11px;padding:2px 7px;border-radius:999px;background:var(--brand-soft);color:var(--brand);font-weight:600;}
  .badges{display:flex;gap:6px;flex-wrap:wrap;}
  .metrics{display:grid;grid-template-columns:1fr 1fr;gap:6px 10px;font-size:12px;color:var(--sub);}
  .metrics b{color:var(--text);font-weight:600;font-size:13px;display:block;}
  .items{display:none;flex-direction:column;gap:8px;border-top:1px solid var(--line);padding-top:10px;}
  .items.open{display:flex;}
  .item{display:flex;gap:8px;align-items:center;text-decoration:none;color:inherit;}
  .item img{width:42px;height:42px;border-radius:8px;object-fit:cover;background:var(--chip);flex:none;}
  .item .it-name{font-size:12px;line-height:1.3;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;}
  .item .it-price{font-size:12px;color:var(--brand);font-weight:600;white-space:nowrap;}
  .toggle-items{font-size:12px;color:var(--brand);cursor:pointer;align-self:flex-start;font-weight:600;}
  /* 商品视角 */
  .pcard{background:var(--card);border:1px solid var(--line);border-radius:14px;overflow:hidden;
    box-shadow:var(--shadow);display:flex;flex-direction:column;text-decoration:none;color:inherit;}
  .pcard:hover{transform:translateY(-2px);box-shadow:0 4px 10px rgba(0,0,0,.08),0 12px 28px rgba(0,0,0,.06);}
  .pcard .pimg{width:100%;aspect-ratio:1/1;object-fit:cover;background:var(--chip);}
  .pcard .pbody{padding:10px 12px;display:flex;flex-direction:column;gap:8px;}
  .pcard .pname{font-size:13px;line-height:1.35;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;min-height:36px;}
  .pcard .pprice{color:var(--brand);font-weight:700;font-size:16px;}
  .pcard .pmerchant{display:inline-flex;align-items:center;gap:6px;font-size:12px;color:var(--sub);
    background:var(--chip);padding:4px 8px;border-radius:999px;align-self:flex-start;}
  .pcard .pmerchant img{width:18px;height:18px;border-radius:5px;object-fit:cover;}
  .empty{text-align:center;color:var(--sub);padding:60px 0;font-size:14px;}
  .banner{background:#fff4e5;border:1px solid #ffd8a8;color:#b54708;border-radius:12px;
    padding:10px 14px;font-size:13px;font-weight:600;margin-bottom:14px;display:flex;align-items:center;gap:8px;}
  .count{font-weight:600;color:var(--text);}
  .hide{display:none!important;}
  .sentinel{height:1px;}
  /* 商品卡片升级 */
  .pimg-wrap{position:relative;overflow:hidden;}
  .pbadge-discount{position:absolute;top:8px;left:0;background:var(--brand);color:#fff;
    font-size:11px;font-weight:700;padding:2px 8px;border-radius:0 8px 8px 0;}
  .pprice-row{display:flex;align-items:baseline;gap:6px;flex-wrap:wrap;}
  .pprice{color:var(--brand);font-weight:700;font-size:16px;}
  .pprice-original{font-size:12px;color:var(--sub);text-decoration:line-through;}
  .pmeta{font-size:11px;color:var(--sub);display:flex;gap:4px;flex-wrap:wrap;}
  .pmeta .dot{color:#d0d3d8;}
  .ptags{display:flex;gap:4px;flex-wrap:wrap;}
  .ptag{font-size:10px;padding:1px 6px;border-radius:4px;background:var(--brand-soft);color:var(--brand);font-weight:600;white-space:nowrap;}
  .pbtns{display:flex;gap:8px;flex-wrap:wrap;align-items:center;}
  .pbtn{font-size:12px;padding:5px 14px;border-radius:999px;border:1px solid var(--line);
    background:var(--card);cursor:pointer;color:var(--sub);user-select:none;transition:all .15s;white-space:nowrap;}
  .pbtn:hover{border-color:var(--brand);color:var(--brand);}
  .pbtn.active{background:var(--brand);color:#fff;border-color:var(--brand);font-weight:600;}
  .cate-btns{display:flex;gap:6px;flex-wrap:wrap;padding:4px 0;border-top:1px solid var(--line);margin-top:4px;}
  .cate-btn{font-size:12px;padding:4px 12px;border-radius:999px;border:1px solid var(--line);
    background:var(--card);cursor:pointer;color:var(--sub);user-select:none;transition:all .15s;white-space:nowrap;}
  .cate-btn:hover{border-color:var(--brand);color:var(--brand);}
  .cate-btn.active{background:var(--text);color:#fff;border-color:var(--text);font-weight:600;}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>⭐ 我关注的微店</h1>
    <div class="stat">数据来自微店抓包全量爬取 · 共 <span class="count" id="total">0</span> 个店铺 ·
      其中在售 <span class="count" id="withItems">0</span> 个 · 商品 <span class="count" id="totalItems">0</span> 件</div>
  </header>

  <div id="tokenWarn" class="banner hide">⚠️ Token 已过期，无法获取新关注店铺，请及时更新（已爬取的商品数据不受影响）</div>

  <div class="tabs">
    <div class="tab" data-view="shop">🏪 店铺视角</div>
    <div class="tab active" data-view="product">🛍 商品视角</div>
  </div>

  <!-- 店铺视角工具栏 -->
  <div class="toolbar hide" id="shopBar">
    <div class="row">
      <input type="text" id="search" placeholder="🔍 搜索店铺名 / 店铺ID…">
      <select id="sort">
        <option value="followTime">最近关注</option>
        <option value="followCount">粉丝最多</option>
        <option value="turningRate">转化最高</option>
        <option value="onShelfItemNum">在售最多</option>
        <option value="name">名称 A→Z</option>
      </select>
    </div>
    <div class="row">
      <label class="toggle"><input type="checkbox" id="fItems"> 只看有在售商品</label>
      <label class="lbl">粉丝≥</label>
      <input type="number" id="fMinFans" placeholder="0" min="0" style="width:100px">
      <label class="lbl">转化≥</label>
      <input type="number" id="fMinRate" placeholder="0" min="0" step="0.01" style="width:90px">
    </div>
  </div>

  <!-- 商品视角工具栏 -->
  <div class="toolbar" id="productBar">
    <div class="row">
      <input type="text" id="pSearch" placeholder="🔍 搜索商品名…">
      <select id="pMerchant"><option value="">全部商家</option></select>
      <select id="pSort">
        <option value="newest">最新上架</option>
        <option value="sold">销量最高</option>
        <option value="priceAsc">价格从低到高</option>
        <option value="priceDesc">价格从高到低</option>
      </select>
    </div>
    <div class="row">
      <label class="lbl">价格 ¥</label>
      <input type="number" id="pMin" placeholder="最低" min="0" style="width:100px">
      <label class="lbl">~ ¥</label>
      <input type="number" id="pMax" placeholder="最高" min="0" style="width:100px">
    </div>
    <div class="row" id="priceBtns" style="padding-top:4px">
      <span class="pbtn active" data-min="" data-max="">全部</span>
      <span class="pbtn" data-min="0" data-max="50">&lt; ¥50</span>
      <span class="pbtn" data-min="50" data-max="200">¥50-200</span>
      <span class="pbtn" data-min="200" data-max="500">¥200-500</span>
      <span class="pbtn" data-min="500" data-max="">&gt; ¥500</span>
    </div>
    <div class="cate-btns" id="cateBtns"></div>
  </div>

  <div class="grid" id="grid"></div>
  <div id="sentinel" class="sentinel"></div>
  <div class="empty hide" id="empty">没有符合条件的结果</div>
  <div class="stat" id="visStat" style="margin-top:14px"></div>
</div>

<script>
const TOKEN_EXPIRED = __TOKEN_EXPIRED__;
if (TOKEN_EXPIRED) {
  document.getElementById('tokenWarn').classList.remove('hide');
}
const SHOPS = __DATA__;
const PRODUCTS = [];
SHOPS.forEach(s=>{
  (s.items||[]).forEach(it=>{
    PRODUCTS.push({
      shopId:s.shopId, shopName:s.name, shopAvatar:s.headImage,
      itemId:it.itemId, itemName:it.itemName, image:it.image,
      price:it.price, priceYuan:(it.price||0)/100, addTime:it.addTime||'',
      stock:it.stock||0, soldText:it.soldText||'', soldNum:it.soldNum||0,
      originalPrice:it.originalPrice||0, itemTag:it.itemTag||[],
      preSale:it.preSale||false, hasSku:it.hasSku||false
    });
  });
});
// 品类快速筛选
const CATE_RULES = [
  { name: '短袖', kws: ['短袖','t恤','tee','体恤','短t'] },
  { name: '长袖', kws: ['长袖','长t'] },
  { name: '卫衣', kws: ['卫衣','hoodie','帽衫','连帽'] },
  { name: '外套', kws: ['外套','夹克','风衣','大衣','棉服','冲锋衣','牛仔外套'] },
  { name: '毛衣', kws: ['毛衣','针织','羊毛','开衫'] },
  { name: '短裤', kws: ['短裤','热裤','沙滩裤'] },
  { name: '长裤', kws: ['长裤','休闲裤','工装裤','牛仔裤','西裤','阔腿裤','拖地裤'] },
  { name: '裙子', kws: ['裙子','连衣裙','半身裙','蓬蓬裙','仙女裙','百褶裙','小黑裙'] },
  { name: '鞋子', kws: ['鞋','运动鞋','板鞋','帆布','拖鞋','凉鞋','靴子','德训鞋'] },
  { name: '配饰', kws: ['配饰','项链','手链','耳环','戒指','手表','腰带','墨镜','帽子','包包','背包','袜子','眼镜'] },
];
(()=>{
  const box = document.getElementById('cateBtns');
  const all = document.createElement('span');
  all.className = 'cate-btn active'; all.textContent = '全部'; all.dataset.cate = '';
  box.appendChild(all);
  CATE_RULES.forEach(c => {
    const b = document.createElement('span');
    b.className = 'cate-btn'; b.textContent = c.name; b.dataset.cate = c.name;
    box.appendChild(b);
  });
})();
function matchCategory(name, cate) {
  if (!cate) return true;
  const nl = name.toLowerCase();
  const rule = CATE_RULES.find(c => c.name === cate);
  return rule ? rule.kws.some(kw => nl.includes(kw)) : true;
}

const fmtNum = n => (n==null?0:n).toLocaleString('zh-CN');
const fmtRate = r => (r==null?0:(r*100).toFixed(2)) + '%';
const fmtPrice = p => '¥' + ((p==null?0:p)/100).toLocaleString('zh-CN',{maximumFractionDigits:((p/100)%1)?2:0});
const itemUrl = it => 'https://weidian.com/item.html?itemID=' + it.itemId;
const fmtDate = ts => ts? new Date(ts).toISOString().slice(0,10):'';

const grid=document.getElementById('grid');
const empty=document.getElementById('empty');
const visStat=document.getElementById('visStat');
document.getElementById('total').textContent=SHOPS.length;
document.getElementById('withItems').textContent=SHOPS.filter(d=>d.hasShelfItems).length;
document.getElementById('totalItems').textContent=PRODUCTS.length;

// 商品视角分批懒加载（避免一次性渲染上万张卡片卡死页面）
const sentinel = document.getElementById('sentinel');
const BATCH = 80;
let pAll = [], pShown = 0;
const io = new IntersectionObserver(es => {
  if (view === 'product' && es[0].isIntersecting && pShown < pAll.length) {
    renderProduct(false);
  }
}, { rootMargin: '400px' });
io.observe(sentinel);

// 商家下拉
const pMerchant=document.getElementById('pMerchant');
SHOPS.filter(s=>s.hasShelfItems).forEach(s=>{
  const o=document.createElement('option');o.value=s.shopId;o.textContent=s.name;pMerchant.appendChild(o);
});

let view='product';

function shopCard(d){
  const items=(d.items||[]).map(it=>`
    <a class="item" href="${itemUrl(it)}" target="_blank" rel="noopener">
      <img src="${it.image||''}" loading="lazy" onerror="this.style.visibility='hidden'">
      <div style="flex:1;min-width:0"><div class="it-name">${it.itemName||''}</div></div>
      <div class="it-price">${fmtPrice(it.price)}</div>
    </a>`).join('');
  const btn=(d.items&&d.items.length)?`<span class="toggle-items" data-toggle>展开在售商品 (${d.items.length})</span>`:'';
  return `<div class="card">
    <div class="top">
      <img class="avatar" src="${d.headImage||''}" loading="lazy" onerror="this.style.background='#eef0f3'">
      <div style="min-width:0;flex:1">
        <div class="name">${d.name||'(未命名)'}</div>
        <div class="sid">ID: ${d.shopId||''}</div>
      </div>
      ${d.focusFlag?'<span class="badge">特别关注</span>':''}
    </div>
    <div class="badges">
      ${d.hasShelfItems?'<span class="badge">有在售</span>':''}
      ${d.onShelfItemNum?`<span class="badge" style="background:#eef0f3;color:#5a6068">在售 ${d.onShelfItemNum}</span>`:''}
    </div>
    <div class="metrics">
      <div>粉丝<b>${fmtNum(d.followCount)}</b></div>
      <div>转化率<b>${fmtRate(d.turningRate)}</b></div>
      <div>关注时间<b>${fmtDate(d.followTime)}</b></div>
      <div>在售数<b>${fmtNum(d.onShelfItemNum)}</b></div>
    </div>
    ${btn}
    <div class="items">${items}</div>
  </div>`;
}

function productCard(p){
  const tags = (p.itemTag||[]).map(t => `<span class="ptag">${t.tagTitle||''}</span>`).join('');
  const hasOrig = p.originalPrice && p.originalPrice > p.price;
  const discount = hasOrig ? Math.round((1 - p.price/p.originalPrice) * 100) : 0;
  const meta = [p.soldText, p.stock ? `库存 ${p.stock}` : ''].filter(Boolean).join(' · ');
  return `<a class="pcard" href="${itemUrl(p)}" target="_blank" rel="noopener">
    <div class="pimg-wrap">
      <img class="pimg" src="${p.image||''}" loading="lazy" onerror="this.style.background='#eef0f3'">
      ${discount ? `<span class="pbadge-discount">-${discount}%</span>` : ''}
    </div>
    <div class="pbody">
      <div class="pname">${p.itemName||''}</div>
      <div class="pprice-row">
        <span class="pprice">${fmtPrice(p.price)}</span>
        ${hasOrig ? `<span class="pprice-original">${fmtPrice(p.originalPrice)}</span>` : ''}
      </div>
      ${meta ? `<div class="pmeta">${meta}</div>` : ''}
      ${tags ? `<div class="ptags">${tags}</div>` : ''}
      <span class="pmerchant"><img src="${p.shopAvatar||''}" onerror="this.style.display='none'">${p.shopName||''}</span>
    </div>
  </a>`;
}

function renderShop(){
  const kw=document.getElementById('search').value.trim().toLowerCase();
  const onlyItems=document.getElementById('fItems').checked;
  const minFans=parseFloat(document.getElementById('fMinFans').value)||0;
  const minRate=parseFloat(document.getElementById('fMinRate').value)||0;
  const sort=document.getElementById('sort').value;
  let list=SHOPS.filter(d=>{
    if(onlyItems&&!d.hasShelfItems)return false;
    if((d.followCount||0)<minFans)return false;
    if((d.turningRate||0)<minRate)return false;
    if(kw&&!((d.name||'')+' '+(d.shopId||'')).toLowerCase().includes(kw))return false;
    return true;
  });
  const sorters={
    followTime:(a,b)=>(b.followTime||0)-(a.followTime||0),
    followCount:(a,b)=>(b.followCount||0)-(a.followCount||0),
    turningRate:(a,b)=>(b.turningRate||0)-(a.turningRate||0),
    onShelfItemNum:(a,b)=>(b.onShelfItemNum||0)-(a.onShelfItemNum||0),
    name:(a,b)=>(a.name||'').localeCompare(b.name||'','zh'),
  };
  list.sort(sorters[sort]||sorters.followTime);
  grid.innerHTML=list.map(shopCard).join('');
  bindToggles();
  finish(list.length,SHOPS.length,'个店铺');
}

function renderProduct(reset){
  if(reset){
    const kw=document.getElementById('pSearch').value.trim().toLowerCase();
    const mid=document.getElementById('pMerchant').value;
    const min=parseFloat(document.getElementById('pMin').value)||0;
    const max=parseFloat(document.getElementById('pMax').value)||Infinity;
    const sort=document.getElementById('pSort').value;
    pAll=PRODUCTS.filter(p=>{
      if(mid&&String(p.shopId)!==mid)return false;
      if((p.priceYuan||0)<min)return false;
      if((p.priceYuan||0)>max)return false;
      if(kw&&!(p.itemName||'').toLowerCase().includes(kw))return false;
      return true;
    });
    const sorters={
      newest:(a,b)=>String(b.addTime).localeCompare(String(a.addTime)),
      sold:(a,b)=>(b.soldNum||0)-(a.soldNum||0),
      priceAsc:(a,b)=>(a.priceYuan||0)-(b.priceYuan||0),
      priceDesc:(a,b)=>(b.priceYuan||0)-(a.priceYuan||0),
    };
    pAll.sort(sorters[sort]||sorters.newest);
    pShown=0; grid.innerHTML='';
  }
  const batch=pAll.slice(pShown, pShown+BATCH);
  grid.insertAdjacentHTML('beforeend', batch.map(productCard).join(''));
  pShown+=batch.length;
  empty.classList.toggle('hide', pAll.length>0);
  visStat.textContent=`显示 ${Math.min(pShown,pAll.length)} / ${pAll.length} 件商品`;
  sentinel.classList.toggle('hide', pShown>=pAll.length || view!=='product');
}

function finish(n,total,unit){
  empty.classList.toggle('hide',n>0);
  visStat.textContent=`显示 ${n} / ${total} ${unit}`;
}

function bindToggles(){
  grid.querySelectorAll('[data-toggle]').forEach(btn=>{
    btn.addEventListener('click',()=>{
      const box=btn.nextElementSibling;
      box.classList.toggle('open');
      btn.textContent=box.classList.contains('open')?'收起在售商品':`展开在售商品 (${box.children.length})`;
    });
  });
}

function render(){ view==='shop'?renderShop():renderProduct(true); }

// tab 切换
document.querySelectorAll('.tab').forEach(t=>{
  t.addEventListener('click',()=>{
    view=t.dataset.view;
    document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));
    t.classList.add('active');
    document.getElementById('shopBar').classList.toggle('hide',view!=='shop');
    document.getElementById('productBar').classList.toggle('hide',view!=='product');
    sentinel.classList.toggle('hide', view!=='product');
    render();
  });
});

['search','sort','fItems','fMinFans','fMinRate'].forEach(id=>{
  document.getElementById(id).addEventListener('input',()=>view==='shop'&&render());
  document.getElementById(id).addEventListener('change',()=>view==='shop'&&render());
});
['pSearch','pMerchant','pSort','pMin','pMax'].forEach(id=>{
  document.getElementById(id).addEventListener('input',()=>view==='product'&&render());
  document.getElementById(id).addEventListener('change',()=>view==='product'&&render());
});
// 价格快捷按钮
document.querySelectorAll('#priceBtns .pbtn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('#priceBtns .pbtn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('pMin').value = btn.dataset.min;
    document.getElementById('pMax').value = btn.dataset.max;
    if (view === 'product') render();
  });
});
// 品类按钮事件
document.getElementById('cateBtns').addEventListener('click', e => {
  const btn = e.target.closest('.cate-btn');
  if (!btn) return;
  document.querySelectorAll('#cateBtns .cate-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  if (view === 'product') render();
});

render();
</script>
</body>
</html>
"""


def main():
    data = load_data()
    # 读取 token 状态，决定是否显示过期提示
    expired = False
    status_path = os.path.join(HERE, "data", "status.json")
    if os.path.exists(status_path):
        try:
            st = json.load(open(status_path, encoding="utf-8"))
            expired = bool(st.get("token_expired"))
        except Exception:
            pass
    out = (HTML
           .replace("__DATA__", json.dumps(data, ensure_ascii=False))
           .replace("__TOKEN_EXPIRED__", "true" if expired else "false"))
    out_path = os.path.join(HERE, "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(out)
    n_items = sum(1 for d in data if d.get("items"))
    total_products = sum(len(d.get("items", [])) for d in data)
    print("written:", out_path)
    print("shops:", len(data), "with items:", n_items, "products:", total_products)
    print("token 提示:", "已过期（页面将显示提示）" if expired else "正常")


if __name__ == "__main__":
    main()
