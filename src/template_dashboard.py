"""Render the dashboard model into one self-contained HTML string.

The model carries only metadata, per-card per-category budgets, and a
normalized `transactions` array. Every panel is computed in the page from
that array, so the account checkboxes and the range toggle re-filter
everything consistently, and /api/refresh only has to return fresh data.

Charts use Chart.js from a CDN (needs internet the first load); if it can't
load, the numeric panels still render and only the graphs are skipped.
"""
import json

_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Spend Tracker</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
:root{
  --bg:#f4f3ef; --card:#ffffff; --card2:#faf9f5; --line:#e6e4dc;
  --tx:#1c1b16; --tx2:#63625a; --tx3:#9b9a90;
  --teal:#1a9467; --teal-bg:#e1f5ee; --teal-d:#0c6549;
  --coral:#d85a30; --coral-bg:#fbe8e0;
  --blue:#2f6fb0; --blue-bg:#e4eef8;
  --amber:#c98a1a; --amber-bg:#f9efd9;
  --purple:#6a5acd; --purple-bg:#ecebfa;
  --pink:#c2557a; --pink-bg:#f9e6ee;
}
@media (prefers-color-scheme:dark){:root{
  --bg:#141410; --card:#1f1f1b; --card2:#191915; --line:#2f2f29;
  --tx:#f0efe9; --tx2:#a3a29a; --tx3:#6f6e66;
  --teal:#4ec49a; --teal-bg:#0d3a2a; --teal-d:#7ad3b5;
  --coral:#e8896a; --coral-bg:#3a1a0e;
  --blue:#6fa8e0; --blue-bg:#13273d;
  --amber:#e0ad55; --amber-bg:#3a2c10;
  --purple:#9a8ce8; --purple-bg:#241f45;
  --pink:#dd8aac; --pink-bg:#3a1826;
}}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--tx);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;-webkit-font-smoothing:antialiased;font-size:14px;line-height:1.5}
.n{font-variant-numeric:tabular-nums;font-feature-settings:"tnum"}
.app{max-width:1200px;margin:0 auto;padding:22px 26px 70px}
.sec-title{font-size:12px;font-weight:700;letter-spacing:.6px;text-transform:uppercase;color:var(--tx3);margin:26px 2px 12px}
.topbar{display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap}
.brand{display:flex;align-items:center;gap:11px}
.logo{width:36px;height:36px;border-radius:10px;background:var(--teal);color:#fff;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:18px}
.brand h1{font-size:19px;font-weight:650;letter-spacing:-.3px}
.brand .sub{font-size:12px;color:var(--tx3)}
.controls{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.chip{display:inline-flex;align-items:center;gap:6px;border:0.5px solid var(--line);background:var(--card);border-radius:20px;padding:6px 12px;font-size:12.5px;font-weight:500;color:var(--tx2);cursor:pointer;user-select:none;transition:all .12s}
.chip.on{background:var(--teal-bg);border-color:var(--teal);color:var(--teal-d)}
.chip .box{width:13px;height:13px;border-radius:3px;border:1.5px solid currentColor;display:flex;align-items:center;justify-content:center;font-size:9px;font-weight:800}
.chip.on .box::after{content:'\2713'}
.seg{display:flex;background:var(--card);border:0.5px solid var(--line);border-radius:9px;overflow:hidden}
.seg button{border:none;background:transparent;color:var(--tx2);padding:7px 12px;font-size:12.5px;font-weight:500;cursor:pointer;font-family:inherit}
.seg button.on{background:var(--teal);color:#fff}
.run-btn{display:inline-flex;align-items:center;gap:6px;border:none;background:var(--teal);color:#fff;border-radius:9px;padding:8px 15px;font-size:12.5px;font-weight:600;cursor:pointer;font-family:inherit}
.run-btn:hover{background:var(--teal-d)} .run-btn:disabled{opacity:.7;cursor:default}
.run-btn .spin{display:inline-block;animation:spin .8s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.mini-btn{border:0.5px solid var(--line);background:var(--card);color:var(--tx2);border-radius:7px;padding:5px 11px;font-size:12px;font-weight:600;cursor:pointer;font-family:inherit}
.mini-btn:hover{border-color:var(--teal);color:var(--teal-d)}
.mini-btn.primary{background:var(--teal);border-color:var(--teal);color:#fff}
.datein{font-size:12px;padding:6px 8px;border:0.5px solid var(--line);border-radius:7px;background:var(--card);color:var(--tx);font-family:inherit}
.grid{display:grid;gap:14px}
.kpis{grid-template-columns:repeat(5,1fr)}
.c2{grid-template-columns:1.5fr 1fr} .c2e{grid-template-columns:1fr 1fr} .c3{grid-template-columns:repeat(3,1fr)}
@media(max-width:920px){.kpis{grid-template-columns:repeat(2,1fr)}.c2,.c2e,.c3{grid-template-columns:1fr}}
.card{background:var(--card);border:0.5px solid var(--line);border-radius:14px;padding:18px}
.card-h{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;gap:10px}
.card-h h3{font-size:14px;font-weight:600}
.card-h .meta{font-size:11.5px;color:var(--tx3);white-space:nowrap}
.label{font-size:10.5px;font-weight:600;letter-spacing:.4px;text-transform:uppercase;color:var(--tx3)}
.kpi .top{display:flex;align-items:center;justify-content:space-between;margin-bottom:9px}
.kpi .ic{width:28px;height:28px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:14px}
.kpi .val{font-size:24px;font-weight:700;letter-spacing:-.8px;line-height:1}
.kpi .cap{font-size:11.5px;color:var(--tx2);margin-top:6px}
.up{color:var(--coral);font-weight:600} .down{color:var(--teal);font-weight:600}
.bar{height:6px;background:var(--card2);border-radius:3px;overflow:hidden}
.bar>span{display:block;height:6px;border-radius:3px;background:var(--teal)}
.lrow{display:flex;align-items:center;gap:11px;padding:9px 0}
.lrow+.lrow{border-top:0.5px solid var(--line)}
.av{width:32px;height:32px;border-radius:8px;background:var(--card2);display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;color:var(--tx2);flex-shrink:0}
.lname{font-size:13px;font-weight:500} .lsub{font-size:11.5px;color:var(--tx3)}
.legend-dot{width:9px;height:9px;border-radius:3px;display:inline-block;flex-shrink:0}
.cal{display:grid;grid-template-columns:repeat(7,1fr);gap:5px}
.cdow{text-align:center;font-size:10px;color:var(--tx3);padding-bottom:2px}
.cell{aspect-ratio:1;border-radius:7px;background:var(--card2);display:flex;flex-direction:column;justify-content:space-between;padding:4px 5px}
.cell .cd{font-size:9px} .cell .ca{font-size:9.5px;font-weight:700;text-align:right}
.cell.future{opacity:.35}
.ins{display:flex;gap:11px;padding:11px 0} .ins+.ins{border-top:0.5px solid var(--line)}
.ins .ic{width:30px;height:30px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:15px;flex-shrink:0}
.ins .t{font-size:13px;font-weight:600} .ins .d{font-size:12px;color:var(--tx2);margin-top:1px}
table{width:100%;border-collapse:collapse}
th{text-align:left;font-size:10.5px;font-weight:600;letter-spacing:.4px;text-transform:uppercase;color:var(--tx3);padding:6px 8px;border-bottom:0.5px solid var(--line)}
td{padding:9px 8px;font-size:13px;border-bottom:0.5px solid var(--line)}
tr:last-child td{border-bottom:none}
.pill{display:inline-block;font-size:11px;font-weight:600;padding:2px 9px;border-radius:20px}
.tright{text-align:right}
.th-sort{cursor:pointer;user-select:none;white-space:nowrap} .th-sort:hover{color:var(--tx)}
.th-sort .arr{font-size:9px;color:var(--teal)}
.filter-row th{padding:6px 6px 10px;border-bottom:0.5px solid var(--line)}
.fin{width:100%;font-size:12px;padding:6px 8px;border:0.5px solid var(--line);border-radius:7px;background:var(--card2);color:var(--tx);font-family:inherit}
.fin:focus{outline:none;border-color:var(--teal)}
.pager{display:flex;align-items:center;justify-content:center;gap:5px;margin-top:16px;flex-wrap:wrap}
.pbtn{min-width:30px;height:30px;padding:0 8px;border:0.5px solid var(--line);background:var(--card);color:var(--tx2);border-radius:7px;font-size:12.5px;font-weight:500;cursor:pointer;font-family:inherit}
.pbtn:hover:not(:disabled){border-color:var(--teal);color:var(--teal-d)}
.pbtn.on{background:var(--teal);border-color:var(--teal);color:#fff} .pbtn:disabled{opacity:.4;cursor:default}
.pdots{color:var(--tx3);padding:0 2px}
.bud-in{width:66px;font-size:12px;padding:4px 7px;border:0.5px solid var(--teal);border-radius:6px;background:var(--card2);color:var(--tx);font-family:inherit;font-variant-numeric:tabular-nums}
.bud-in:focus{outline:none}
.chart-wrap{position:relative;height:210px} .donut-wrap{position:relative;height:180px}
.split{display:flex;height:12px;border-radius:6px;overflow:hidden;margin:14px 0 12px} .split>span{height:12px}
.empty{text-align:center;color:var(--tx3);font-size:13px;padding:22px 0}
.card-sub{margin:6px 0 4px;font-size:12px;font-weight:600;color:var(--tx2)}
</style>
</head>
<body>
<div class="app">
  <div class="topbar">
    <div class="brand">
      <div class="logo">$</div>
      <div><h1>Spend Tracker</h1><div class="sub" id="updlbl"></div></div>
    </div>
    <div class="controls">
      <span id="acctChips" style="display:flex;gap:6px;flex-wrap:wrap"></span>
      <div class="seg" id="rangeSeg">
        <button data-r="mtd">MTD</button>
        <button data-r="l30">Last 30</button>
        <button data-r="l90" class="on">Last 90</button>
        <button data-r="custom">Custom</button>
      </div>
      <span id="customRange" style="display:none;align-items:center;gap:6px">
        <input type="date" id="cStart" class="datein">
        <span style="color:var(--tx3)">\u2013</span>
        <input type="date" id="cEnd" class="datein">
      </span>
      <button class="run-btn" id="runBtn" onclick="runRefresh()"><span id="runIco">\u25B6</span> <span id="runTxt">Run</span></button>
    </div>
  </div>

  <div class="sec-title">At a glance</div>
  <div class="grid kpis" id="kpis"></div>

  <div class="sec-title">Trends</div>
  <div class="grid c2">
    <div class="card">
      <div class="card-h"><h3>Monthly spend</h3>
        <span style="display:flex;align-items:center;gap:6px"><span class="meta">break down by</span>
          <select id="dim" class="fin" style="width:auto;padding:5px 8px">
            <option value="cat">Category</option><option value="m">Merchant</option><option value="a">Account</option>
          </select></span>
      </div>
      <div class="chart-wrap"><canvas id="months"></canvas></div>
      <div id="monthlegend" style="display:flex;flex-wrap:wrap;gap:10px 14px;margin-top:12px"></div>
    </div>
    <div class="card">
      <div class="card-h"><h3>Pace this month</h3><span class="meta">cumulative vs last month</span></div>
      <div class="chart-wrap"><canvas id="pace"></canvas></div>
    </div>
  </div>

  <div class="sec-title">Where it goes</div>
  <div class="grid c2">
    <div class="card">
      <div class="card-h">
        <span style="display:flex;align-items:center;gap:8px">
          <button class="mini-btn" onclick="stepMonth(-1)" aria-label="Previous month">\u2039</button>
          <h3 id="calTitle">Daily spend</h3>
          <button class="mini-btn" onclick="stepMonth(1)" aria-label="Next month">\u203A</button>
        </span>
        <span class="meta">darker = more</span>
      </div>
      <div class="cal" id="caldow"></div>
      <div class="cal" id="calgrid" style="margin-top:5px"></div>
    </div>
    <div class="card">
      <div class="card-h"><h3>By category</h3><span class="meta" id="catMeta"></span></div>
      <div class="donut-wrap"><canvas id="donut"></canvas></div>
      <div id="catlegend" style="margin-top:14px"></div>
    </div>
  </div>

  <div class="sec-title">Budgets &amp; overspending</div>
  <div class="card">
    <div class="card-h"><h3>Category budgets</h3>
      <span style="display:flex;align-items:center;gap:8px"><span class="meta">this month \u00b7 spent \u00b7 projected \u00b7 target</span>
        <button class="mini-btn" id="budEdit" onclick="toggleBudEdit()">\u270E Edit</button></span>
    </div>
    <div id="budgets"></div>
    <div id="budActions" style="display:none;margin-top:16px;gap:8px;justify-content:flex-end">
      <button class="mini-btn" onclick="cancelBud()">Cancel</button>
      <button class="mini-btn primary" onclick="saveBud()">Save budgets</button>
    </div>
  </div>

  <div class="sec-title">Subscriptions &amp; recurring</div>
  <div class="grid c2e">
    <div class="card"><div class="card-h"><h3>Active subscriptions</h3><span class="meta" id="subMeta"></span></div><div id="subs"></div></div>
    <div class="card"><div class="card-h"><h3>Recurring watch</h3><span class="meta">flags</span></div><div id="subflags"></div></div>
  </div>

  <div class="sec-title">Cashflow &amp; big items</div>
  <div class="grid c2">
    <div class="card"><div class="card-h"><h3>Biggest purchases</h3><span class="meta" id="bigMeta"></span></div><div id="bigitems"></div></div>
    <div>
      <div class="card" style="margin-bottom:14px"><div class="card-h"><h3>By account</h3><span class="meta" id="acctMeta"></span></div><div id="acctsplit"></div></div>
      <div class="card"><div class="card-h"><h3>Travel vs everyday</h3><span class="meta" id="tvMeta"></span></div><div class="split" id="tvsplit"></div><div id="tvlabel" style="display:flex;justify-content:space-between;font-size:12px;color:var(--tx2)"></div></div>
    </div>
  </div>

  <div class="sec-title">Activity</div>
  <div class="card" style="margin-bottom:14px"><div class="card-h"><h3>Insights</h3><span class="meta">auto-detected</span></div><div id="insights"></div></div>
  <div class="card">
    <div class="card-h"><h3>All transactions</h3><span class="meta" id="txcount"></span></div>
    <table id="txtable">
      <thead>
        <tr>
          <th data-sort="raw" class="th-sort">Date <span class="arr"></span></th>
          <th data-sort="m" class="th-sort">Merchant <span class="arr"></span></th>
          <th data-sort="cat" class="th-sort">Category <span class="arr"></span></th>
          <th data-sort="a" class="th-sort">Acct <span class="arr"></span></th>
          <th data-sort="v" class="th-sort tright">Amount <span class="arr"></span></th>
        </tr>
        <tr class="filter-row">
          <th><input id="f-m" class="fin" type="text" placeholder="Search merchant\u2026" style="min-width:120px"></th>
          <th></th>
          <th><select id="f-cat" class="fin"><option value="">All categories</option></select></th>
          <th><select id="f-a" class="fin"><option value="">All</option></select></th>
          <th><select id="f-v" class="fin"><option value="">Any amount</option><option value="500">\u2265 $500</option><option value="100">\u2265 $100</option><option value="50">\u2265 $50</option><option value="20">\u2265 $20</option></select></th>
        </tr>
      </thead>
      <tbody id="txbody"></tbody>
    </table>
    <div id="txempty" class="empty" style="display:none">No transactions match your filters.</div>
    <div class="pager" id="txpager"></div>
  </div>
</div>

<script>
var MODEL = @@MODEL@@;
(function(){
var M=MODEL;
var TXN=(M.transactions||[]).slice();
var BUD=JSON.parse(JSON.stringify(M.budgets||{}));   // {card:{cat:cap}}
var T=M.today||{y:2026,m:1,d:1};
var MONTHS=['','Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
var MONTHS_L=['','January','February','March','April','May','June','July','August','September','October','November','December'];
var CAT_COLORS={'Travel':'--coral','Food and drink':'--teal','Merchandise':'--blue','Services':'--purple','Transportation':'--amber','Medical':'--pink','Entertainment':'--coral','Bank fees':'--tx3'};
var PALETTE=['--coral','--purple','--blue','--teal','--amber','--pink','--tx3'];
function catColor(c){return CAT_COLORS[c]||'--tx3';}
function cv(v){return getComputedStyle(document.documentElement).getPropertyValue(v).trim()||v;}
function pad(n){return String(n).padStart(2,'0');}
function money(n){return '$'+Math.round(n||0).toLocaleString();}
function money2(n){return '$'+(+(n||0)).toFixed(2);}
function ymd(dt){return dt.getFullYear()+'-'+pad(dt.getMonth()+1)+'-'+pad(dt.getDate());}
function addDays(dt,n){var d=new Date(dt);d.setDate(d.getDate()+n);return d;}
function todayDate(){return new Date(T.y,T.m-1,T.d);}
function fmtShort(raw){var p=raw.split('-');return MONTHS[+p[1]]+' '+(+p[2]);}

/* ---- account filter ---- */
var ALL_ACCTS=(function(){var s={},o=[];TXN.forEach(function(t){if(!s[t.a]){s[t.a]=1;o.push(t.a);}});return o;})();
var ACCTS={};ALL_ACCTS.forEach(function(a){ACCTS[a]=true;});
function acctOn(a){return !!ACCTS[a];}
function acctTxns(){return TXN.filter(function(t){return acctOn(t.a);});}

/* ---- range window ---- */
var rangeMode='l90', cStart=null, cEnd=null;
function windowBounds(){
  var end=todayDate(), start;
  if(rangeMode==='mtd'){start=new Date(T.y,T.m-1,1);}
  else if(rangeMode==='l30'){start=addDays(end,-29);}
  else if(rangeMode==='l90'){start=addDays(end,-89);}
  else{ // custom
    start = cStart ? new Date(cStart+'T00:00:00') : (M.minDate?new Date(M.minDate+'T00:00:00'):addDays(end,-89));
    end   = cEnd   ? new Date(cEnd+'T00:00:00')   : end;
  }
  var days=Math.round((end-start)/86400000)+1;
  return {s:ymd(start),e:ymd(end),days:days,startD:start,endD:end};
}
function windowLabel(){
  if(rangeMode==='mtd')return MONTHS_L[T.m]+' to date';
  if(rangeMode==='l30')return 'last 30 days';
  if(rangeMode==='l90')return 'last 90 days';
  var w=windowBounds();return fmtShort(w.s)+' \u2013 '+fmtShort(w.e);
}
function windowTxns(){var w=windowBounds();return acctTxns().filter(function(t){return t.raw>=w.s&&t.raw<=w.e;});}
function prevWindowTxns(){
  var w=windowBounds();
  var pe=addDays(w.startD,-1), ps=addDays(pe,-(w.days-1));
  var pes=ymd(pe),pss=ymd(ps);
  return acctTxns().filter(function(t){return t.raw>=pss&&t.raw<=pes;});
}

/* ---- month helpers (MTD-based panels) ---- */
function daysInMonth(y,m){return new Date(y,m,0).getDate();}
function monthTxns(y,m,accountFilter){
  var p=y+'-'+pad(m);
  return acctTxns().filter(function(t){return t.raw.indexOf(p)===0&&(!accountFilter||t.a===accountFilter);});
}
function sum(arr){return arr.reduce(function(a,b){return a+b.v;},0);}

/* ===================== KPIs ===================== */
function renderKPIs(){
  var win=windowTxns(), winTotal=sum(win);
  // MTD figures (budgets are monthly)
  var mtd=sum(monthTxns(T.y,T.m)), point=T.d, dim=daysInMonth(T.y,T.m);
  var pm=T.m-1,py=T.y;if(pm<1){pm=12;py--;}
  var prevMonthAll=monthTxns(py,pm);
  var prevToPoint=prevMonthAll.filter(function(t){return (+t.raw.split('-')[2])<=point;});
  var prevSum=sum(prevToPoint);
  var pace=prevSum>0?Math.round((mtd-prevSum)/prevSum*100):null;
  var projected=point>0?Math.round(mtd/point*dim):0;
  var activeDays=(function(){var s={};monthTxns(T.y,T.m).forEach(function(t){s[t.raw]=1;});return Object.keys(s).length;})();
  var dailyAvg=activeDays>0?Math.round(mtd/activeDays):0;
  var subs=detectSubs(), recurring=subs.reduce(function(a,b){return a+b.amt;},0);
  // budget totals for ACTIVE accounts
  var totalBudget=0;
  Object.keys(BUD).forEach(function(card){if(acctOn(card)){Object.keys(BUD[card]).forEach(function(c){totalBudget+=+BUD[card][c]||0;});}});
  var left=Math.max(0,totalBudget-mtd);
  var projOver=projected-totalBudget;
  var paceTag=pace===null?'':(pace<=0?'<span class="down">\u2193'+Math.abs(pace)+'%</span>':'<span class="up">\u2191'+Math.abs(pace)+'%</span>')+' vs last mo';
  var budCap=totalBudget>0?('of '+money(totalBudget)+' budget'):'no budget set';
  var projCap=totalBudget>0?(projOver>0?'<span class="up">'+money(projOver)+' over</span> budget':'<span class="down">under budget</span>'):'this month';
  var cards=[
    {l:'Spent \u00b7 '+windowLabel(),ic:'\uD83D\uDCB3',bg:'--teal-bg',c:'--teal-d',v:money(winTotal),cap:win.length+' transactions'},
    {l:'Left to spend',ic:'\uD83C\uDFAF',bg:'--teal-bg',c:'--teal-d',v:money(left),cap:budCap},
    {l:'Projected',ic:'\uD83D\uDCC8',bg:'--blue-bg',c:'--blue',v:money(projected),cap:projCap},
    {l:'This month',ic:'\uD83D\uDCC5',bg:'--amber-bg',c:'--amber',v:money(mtd),cap:paceTag||(activeDays+' active days')},
    {l:'Recurring / mo',ic:'\uD83D\uDD01',bg:'--purple-bg',c:'--purple',v:money(recurring),cap:subs.length+' subscriptions'}
  ];
  document.getElementById('kpis').innerHTML=cards.map(function(k){
    return '<div class="card kpi"><div class="top"><span class="label">'+k.l+'</span>'+
      '<span class="ic" style="background:var('+k.bg+');color:var('+k.c+')">'+k.ic+'</span></div>'+
      '<div class="val n">'+k.v+'</div><div class="cap">'+k.cap+'</div></div>';
  }).join('');
}

/* ===================== Subscriptions ===================== */
function detectSubs(){
  var byM={};
  acctTxns().forEach(function(t){if(t.v<=0)return;(byM[t.m]=byM[t.m]||[]).push({raw:t.raw,amt:t.v,cat:t.cat});});
  var subs=[];
  Object.keys(byM).forEach(function(name){
    var hits=byM[name].slice().sort(function(a,b){return a.raw<b.raw?-1:1;});
    if(hits.length<2)return;
    var amts=hits.map(function(h){return h.amt;});
    var avg=amts.reduce(function(a,b){return a+b;},0)/amts.length;
    var mx=Math.max.apply(null,amts),mn=Math.min.apply(null,amts);
    if(mn<=0||(mx-mn)/avg>0.22)return;
    var ok=true;
    for(var i=1;i<hits.length;i++){var g=(new Date(hits[i].raw)-new Date(hits[i-1].raw))/86400000;if(g<20){ok=false;break;}}
    if(!ok)return;
    subs.push({name:name,amt:avg,count:hits.length,cat:hits[0].cat,last:hits[hits.length-1].raw});
  });
  subs.sort(function(a,b){return b.amt-a.amt;});
  return subs;
}
function renderSubs(){
  var subs=detectSubs(), total=subs.reduce(function(a,b){return a+b.amt;},0);
  document.getElementById('subMeta').textContent=subs.length?money(total)+'/mo \u00b7 '+money(total*12)+'/yr':'none detected';
  var el=document.getElementById('subs');
  if(!subs.length){el.innerHTML='<div class="empty">No recurring charges detected yet.</div>';}
  else el.innerHTML=subs.map(function(s){
    var col=catColor(s.cat);
    return '<div class="lrow"><div class="av" style="background:var('+col+'-bg);color:var('+col+')">\uD83D\uDD01</div>'+
      '<div style="flex:1"><div class="lname">'+s.name+'</div><div class="lsub">'+s.count+' charges \u00b7 last '+fmtShort(s.last)+'</div></div>'+
      '<div style="text-align:right"><div class="n" style="font-size:13px;font-weight:600">'+money2(s.amt)+'</div><div class="lsub n">'+money(s.amt*12)+'/yr</div></div></div>';
  }).join('');
  // flags
  var flags=[];
  subs.forEach(function(s){
    var last=new Date(s.last), nextGuess=new Date(last);nextGuess.setMonth(nextGuess.getMonth()+1);
    var days=Math.round((nextGuess-todayDate())/86400000);
    if(days>=0&&days<=5)flags.push({ic:'\u26A0\uFE0F',c:'--coral',t:s.name+' renews in ~'+days+' day'+(days===1?'':'s'),d:money2(s.amt)+' recurring on '+s.name+'.'});
  });
  if(subs[0])flags.push({ic:'\uD83D\uDCA1',c:'--blue',t:'Largest subscription: '+subs[0].name,d:money2(subs[0].amt)+'/mo \u00b7 '+money(subs[0].amt*12)+'/yr.'});
  var fe=document.getElementById('subflags');
  fe.innerHTML=flags.length?flags.map(function(f){return '<div class="ins"><div class="ic" style="background:var('+f.c+'-bg);color:var('+f.c+')">'+f.ic+'</div><div><div class="t">'+f.t+'</div><div class="d">'+f.d+'</div></div></div>';}).join(''):'<div class="empty">Nothing needs attention.</div>';
}

/* ===================== Monthly stacked ===================== */
var monthsChart=null,paceChart=null,donutChart=null;
function monthKeys(){var s={};acctTxns().forEach(function(t){s[t.raw.slice(0,7)]=1;});return Object.keys(s).sort();}
function buildMonthly(dim){
  var keys=monthKeys();
  var byVal={};
  acctTxns().forEach(function(t){var v=t[dim],k=t.raw.slice(0,7);(byVal[v]=byVal[v]||{})[k]=(byVal[v][k]||0)+t.v;});
  var order=Object.keys(byVal).sort(function(a,b){
    var sa=0,sb=0;keys.forEach(function(k){sa+=byVal[a][k]||0;sb+=byVal[b][k]||0;});return sb-sa;});
  if(dim==='m'&&order.length>6){
    var top=order.slice(0,6),rest=order.slice(6),other={};
    rest.forEach(function(v){keys.forEach(function(k){other[k]=(other[k]||0)+(byVal[v][k]||0);});});
    order=top.concat(['Other']);byVal['Other']=other;
  }
  var series=order.map(function(v,i){
    var col=dim==='cat'?catColor(v):(dim==='a'?PALETTE[i%PALETTE.length]:PALETTE[i%PALETTE.length]);
    return {name:v,color:col,data:keys.map(function(k){return Math.round(byVal[v][k]||0);})};
  });
  return {labels:keys.map(function(k){return MONTHS[+k.slice(5,7)]+" '"+k.slice(2,4);}),series:series};
}
function renderMonthly(){
  if(typeof Chart==='undefined')return;
  var dim=document.getElementById('dim').value, d=buildMonthly(dim);
  var line=cv('--line');
  var ds=d.series.map(function(s){return {label:s.name,data:s.data,backgroundColor:cv(s.color),borderRadius:4,maxBarThickness:46,stack:'s'};});
  if(monthsChart)monthsChart.destroy();
  monthsChart=new Chart(document.getElementById('months'),{type:'bar',
    data:{labels:d.labels,datasets:ds},
    options:{responsive:true,maintainAspectRatio:false,
      plugins:{legend:{display:false},tooltip:{callbacks:{label:function(c){return ' '+c.dataset.label+': $'+c.raw.toLocaleString();}}}},
      scales:{x:{stacked:true,grid:{display:false}},y:{stacked:true,grid:{color:line},ticks:{callback:function(v){return '$'+(v>=1000?(v/1000)+'k':v);}}}}}});
  document.getElementById('monthlegend').innerHTML=d.series.map(function(s){
    return '<span style="display:flex;align-items:center;gap:6px;font-size:11.5px;color:var(--tx2)"><span class="legend-dot" style="background:'+cv(s.color)+'"></span>'+s.name+'</span>';}).join('');
}

/* ===================== Pace line ===================== */
function renderPace(){
  if(typeof Chart==='undefined')return;
  var dim=daysInMonth(T.y,T.m),point=T.d;
  var pm=T.m-1,py=T.y;if(pm<1){pm=12;py--;}
  function cum(y,m,upto){var arr=[],r=0,byd={};monthTxns(y,m).forEach(function(t){var d=+t.raw.split('-')[2];byd[d]=(byd[d]||0)+t.v;});for(var d=1;d<=upto;d++){r+=(byd[d]||0);arr.push(Math.round(r));}return arr;}
  var labels=[];for(var d=1;d<=point;d++)labels.push(d);
  var thisC=cum(T.y,T.m,point), lastC=cum(py,pm,point);
  var teal=cv('--teal'),tx3=cv('--tx3'),line=cv('--line');
  if(paceChart)paceChart.destroy();
  paceChart=new Chart(document.getElementById('pace'),{type:'line',
    data:{labels:labels,datasets:[
      {label:'This month',data:thisC,borderColor:teal,backgroundColor:cv('--teal-bg'),fill:true,tension:.3,borderWidth:2,pointRadius:0},
      {label:'Last month',data:lastC,borderColor:tx3,borderDash:[5,4],fill:false,tension:.3,borderWidth:1.5,pointRadius:0}
    ]},
    options:{responsive:true,maintainAspectRatio:false,
      plugins:{legend:{position:'bottom',labels:{boxWidth:14,boxHeight:2,font:{size:11}}}},
      scales:{y:{grid:{color:line},ticks:{callback:function(v){return '$'+v;}}},x:{grid:{display:false}}}}});
}

/* ===================== Categories + drift ===================== */
function renderCategories(){
  var win=windowTxns(), prev=prevWindowTxns();
  var cur={},pr={};
  win.forEach(function(t){cur[t.cat]=(cur[t.cat]||0)+t.v;});
  prev.forEach(function(t){pr[t.cat]=(pr[t.cat]||0)+t.v;});
  var cats=Object.keys(cur).map(function(c){
    var d=pr[c]>0?Math.round((cur[c]-pr[c])/pr[c]*100):null;
    return {name:c,v:cur[c],d:d};
  }).sort(function(a,b){return b.v-a.v;}).slice(0,7);
  var total=cats.reduce(function(a,b){return a+b.v;},0)||1;
  document.getElementById('catMeta').textContent=windowLabel()+' \u00b7 \u25B2\u25BC vs prior';
  document.getElementById('catlegend').innerHTML=cats.length?cats.map(function(c){
    var pct=Math.round(c.v/total*100),col=catColor(c.name);
    var drift=c.d===null?'<span style="width:44px"></span>':'<span style="font-size:11px;font-weight:600;width:44px;text-align:right;color:'+(c.d<=0?'var(--teal)':'var(--coral)')+'">'+(c.d<=0?'\u25BC':'\u25B2')+Math.abs(c.d)+'%</span>';
    return '<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px"><span class="legend-dot" style="background:'+cv(col)+'"></span>'+
      '<span style="font-size:12.5px;flex:1">'+c.name+'</span>'+drift+
      '<span class="n" style="font-size:12.5px;color:var(--tx2);width:58px;text-align:right">'+money(c.v)+'</span>'+
      '<span class="n" style="font-size:11px;color:var(--tx3);width:30px;text-align:right">'+pct+'%</span></div>';
  }).join(''):'<div class="empty">No spend in this range.</div>';
  if(typeof Chart==='undefined')return;
  if(donutChart)donutChart.destroy();
  if(!cats.length){return;}
  donutChart=new Chart(document.getElementById('donut'),{type:'doughnut',
    data:{labels:cats.map(function(c){return c.name;}),datasets:[{data:cats.map(function(c){return c.v;}),backgroundColor:cats.map(function(c){return cv(catColor(c.name));}),borderWidth:0}]},
    options:{responsive:true,maintainAspectRatio:false,cutout:'66%',plugins:{legend:{display:false},tooltip:{callbacks:{label:function(c){return ' '+c.label+': $'+c.raw.toLocaleString();}}}}}});
}

/* ===================== Calendar ===================== */
var VY=T.y,VM=T.m,HEAT=null;
function heatColors(){var teal=cv('--teal');return teal;}
function renderCalendar(){
  document.getElementById('calTitle').textContent='Daily spend \u00b7 '+MONTHS_L[VM]+' '+VY;
  var dim=daysInMonth(VY,VM),isCur=(VY===T.y&&VM===T.m),point=isCur?T.d:dim;
  var byd={};monthTxns(VY,VM).forEach(function(t){var d=+t.raw.split('-')[2];byd[d]=(byd[d]||0)+t.v;});
  var vals=[];for(var d=1;d<=point;d++)if(byd[d])vals.push(byd[d]);
  var mx=vals.length?Math.max.apply(null,vals):1, teal=cv('--teal'), card2=cv('--card2');
  document.getElementById('caldow').innerHTML='SMTWTFS'.split('').map(function(x){return '<div class="cdow">'+x+'</div>';}).join('');
  var fd=new Date(VY,VM-1,1).getDay(),cells='';
  for(var i=0;i<fd;i++)cells+='<div></div>';
  for(var d=1;d<=dim;d++){
    if(isCur&&d>T.d){cells+='<div class="cell future"><span class="cd" style="color:var(--tx3)">'+d+'</span></div>';continue;}
    var v=byd[d]||0,bg=card2,col='var(--tx3)',amt='';
    if(v){var r=Math.max(.16,Math.min(1,v/mx));bg='color-mix(in srgb, '+teal+' '+Math.round(r*100)+'%, '+card2+')';col=r>.4?'#fff':'var(--tx)';amt='$'+Math.round(v);}
    cells+='<div class="cell" style="background:'+bg+'"><span class="cd" style="color:'+col+';opacity:.7">'+d+'</span><span class="ca" style="color:'+col+'">'+amt+'</span></div>';
  }
  document.getElementById('calgrid').innerHTML=cells;
}
window.stepMonth=function(s){var m=VM+s,y=VY;if(m<1){m=12;y--;}if(m>12){m=1;y++;}VY=y;VM=m;renderCalendar();};

/* ===================== Budgets (per-card per-category) ===================== */
var budEditing=false;
function loadSavedBudgets(){try{var s=JSON.parse(localStorage.getItem('budgetOverrides')||'null');if(s)BUD=s;}catch(e){}}
function renderBudgets(){
  var el=document.getElementById('budgets');
  var cards=ALL_ACCTS.filter(function(a){return acctOn(a)&&BUD[a];});
  // also include budget cards even if no txns this month but account active
  Object.keys(BUD).forEach(function(a){if(acctOn(a)&&cards.indexOf(a)<0)cards.push(a);});
  if(!cards.length){el.innerHTML='<div class="empty">No budgets for the selected account(s). Add them in config/budgets.yaml.</div>';return;}
  var point=T.d,dim=daysInMonth(T.y,T.m);
  el.innerHTML=cards.map(function(card){
    var spentByCat={};monthTxns(T.y,T.m,card).forEach(function(t){spentByCat[t.cat]=(spentByCat[t.cat]||0)+t.v;});
    var caps=BUD[card]||{};
    var catNames=Object.keys(caps);
    var rows=catNames.map(function(cat,i){
      var cap=+caps[cat]||0, spent=spentByCat[cat]||0;
      var proj=point>0?Math.round(spent/point*dim):0;
      var pct=cap>0?Math.min(100,Math.round(spent/cap*100)):0;
      var projPct=cap>0?Math.min(100,Math.round(proj/cap*100)):0;
      var over=proj>cap&&cap>0, col=over?cv('--coral'):cv(catColor(cat));
      var capCell=budEditing
        ?'<span style="display:inline-flex;align-items:center;gap:3px"><span style="color:var(--tx2);font-size:12px">'+money(spent)+' / $</span><input class="bud-in n" type="number" min="0" step="25" value="'+cap+'" data-card="'+card+'" data-cat="'+cat+'" oninput="onCap(this)"></span>'
        :'<span class="n" style="font-size:12px;color:var(--tx2)">'+money(spent)+' / '+money(cap)+'</span>';
      return '<div style="margin-bottom:12px"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">'+
        '<span style="font-size:13px;font-weight:500">'+cat+'</span>'+capCell+'</div>'+
        '<div class="bar" style="height:8px;position:relative"><span style="width:'+pct+'%;height:8px;background:'+col+'"></span>'+
        (cap>0?'<span style="position:absolute;top:-2px;left:'+projPct+'%;width:2px;height:12px;background:var(--tx2);border-radius:1px" title="projected"></span>':'')+'</div>'+
        '<div style="font-size:11.5px;color:'+(over?'var(--coral)':'var(--tx3)')+';margin-top:5px">'+
        (cap<=0?'no target':(over?'\u26A0 projected '+money(proj)+' \u2014 '+money(proj-cap)+' over':money(Math.max(0,cap-spent))+' left \u00b7 on track'))+'</div></div>';
    }).join('');
    var cardTotalCap=catNames.reduce(function(a,c){return a+(+caps[c]||0);},0);
    var cardSpent=Object.keys(spentByCat).reduce(function(a,c){return a+spentByCat[c];},0);
    return '<div style="margin-bottom:8px"><div class="card-sub">'+card+' \u2014 '+money(cardSpent)+' of '+money(cardTotalCap)+'</div>'+
      '<div class="grid c3" style="gap:20px">'+rows+'</div></div>';
  }).join('<hr style="border:none;border-top:0.5px solid var(--line);margin:14px 0">');
}
window.onCap=function(inp){var card=inp.getAttribute('data-card'),cat=inp.getAttribute('data-cat');BUD[card]=BUD[card]||{};BUD[card][cat]=Math.max(0,parseInt(inp.value)||0);};
window.toggleBudEdit=function(){budEditing=true;document.getElementById('budEdit').style.display='none';document.getElementById('budActions').style.display='flex';renderBudgets();};
window.cancelBud=function(){loadSavedBudgets();budEditing=false;document.getElementById('budEdit').style.display='';document.getElementById('budActions').style.display='none';renderBudgets();renderKPIs();};
window.saveBud=function(){
  try{localStorage.setItem('budgetOverrides',JSON.stringify(BUD));}catch(e){}
  fetch('/api/budgets',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(BUD)}).catch(function(){});
  budEditing=false;document.getElementById('budEdit').style.display='';document.getElementById('budActions').style.display='none';
  renderBudgets();renderKPIs();
};

/* ===================== Cashflow ===================== */
function renderCashflow(){
  var win=windowTxns();
  document.getElementById('bigMeta').textContent=windowLabel();
  document.getElementById('acctMeta').textContent=windowLabel();
  document.getElementById('tvMeta').textContent=windowLabel();
  var big=win.slice().sort(function(a,b){return b.v-a.v;}).slice(0,6);
  document.getElementById('bigitems').innerHTML=big.length?big.map(function(b,i){var col=catColor(b.cat);
    return '<div class="lrow"><div class="av" style="background:var('+col+'-bg);color:var('+col+')">'+(i+1)+'</div>'+
      '<div style="flex:1"><div class="lname">'+b.m+'</div><div class="lsub">'+fmtShort(b.raw)+' \u00b7 '+b.cat+'</div></div>'+
      '<div class="n" style="font-size:14px;font-weight:700">'+money(b.v)+'</div></div>';}).join(''):'<div class="empty">No spend in this range.</div>';
  // account split
  var byA={};win.forEach(function(t){byA[t.a]=(byA[t.a]||0)+t.v;});
  var accs=Object.keys(byA).map(function(a){return [a,byA[a]];}).sort(function(a,b){return b[1]-a[1];});
  var atot=accs.reduce(function(a,b){return a+b[1];},0)||1;
  document.getElementById('acctsplit').innerHTML=accs.length?accs.map(function(a,i){var pct=Math.round(a[1]/atot*100),col=PALETTE[i%PALETTE.length];
    return '<div style="margin-bottom:12px"><div style="display:flex;justify-content:space-between;margin-bottom:6px">'+
      '<span style="font-size:12.5px"><span class="legend-dot" style="background:var('+col+');vertical-align:middle;margin-right:6px"></span>'+a[0]+'</span>'+
      '<span class="n" style="font-size:12.5px;color:var(--tx2)">'+money(a[1])+' \u00b7 '+pct+'%</span></div>'+
      '<div class="bar" style="height:7px"><span style="width:'+pct+'%;height:7px;background:var('+col+')"></span></div></div>';}).join(''):'<div class="empty">\u2014</div>';
  // travel vs everyday
  var travel=win.filter(function(t){return t.cat==='Travel';}).reduce(function(a,b){return a+b.v;},0);
  var everyday=sum(win)-travel, tot=travel+everyday;
  var tp=tot>0?Math.round(travel/tot*100):0, ep=100-tp;
  document.getElementById('tvsplit').innerHTML=tot>0?'<span style="width:'+tp+'%;background:var(--coral)"></span><span style="width:'+ep+'%;background:var(--teal)"></span>':'';
  document.getElementById('tvlabel').innerHTML=tot>0?'<span><span class="legend-dot" style="background:var(--coral);vertical-align:middle"></span> Travel <b class="n" style="color:var(--tx)">'+money(travel)+'</b> \u00b7 '+tp+'%</span><span>Everyday <b class="n" style="color:var(--tx)">'+money(everyday)+'</b> \u00b7 '+ep+'%</span>':'<span class="hint">No spend in this range.</span>';
}

/* ===================== Insights ===================== */
function renderInsights(){
  var win=windowTxns(),prev=prevWindowTxns();
  var ins=[];
  var byCat={};win.forEach(function(t){byCat[t.cat]=(byCat[t.cat]||0)+t.v;});
  var total=sum(win)||1;
  var topCat=Object.keys(byCat).sort(function(a,b){return byCat[b]-byCat[a];})[0];
  if(topCat)ins.push({ic:'\uD83D\uDCCA',c:'--coral',t:topCat+' is your top category',d:money(byCat[topCat])+' \u00b7 '+Math.round(byCat[topCat]/total*100)+'% of '+windowLabel()+'.'});
  var byM={};win.forEach(function(t){byM[t.m]=(byM[t.m]||0)+t.v;});
  var topM=Object.keys(byM).sort(function(a,b){return byM[b]-byM[a];})[0];
  if(topM)ins.push({ic:'\uD83C\uDFEA',c:'--blue',t:topM+' is your top merchant',d:money(byM[topM])+' over '+windowLabel()+'.'});
  var cur=sum(win),pr=sum(prev);
  if(pr>0){var d=Math.round((cur-pr)/pr*100);ins.push({ic:d<=0?'\u2705':'\u26A0\uFE0F',c:d<=0?'--teal':'--coral',t:(d<=0?'Down ':'Up ')+Math.abs(d)+'% vs prior period',d:money(cur)+' vs '+money(pr)+' the previous '+windowBounds().days+' days.'});}
  var subs=detectSubs();if(subs[0])ins.push({ic:'\uD83D\uDD01',c:'--purple',t:subs.length+' recurring charge'+(subs.length>1?'s':'')+' \u00b7 '+money(subs.reduce(function(a,b){return a+b.amt;},0))+'/mo',d:subs.slice(0,3).map(function(s){return s.name+' '+money2(s.amt);}).join(' \u00b7 ')+'.'});
  document.getElementById('insights').innerHTML=ins.length?ins.map(function(i){return '<div class="ins"><div class="ic" style="background:var('+i.c+'-bg);color:var('+i.c+')">'+i.ic+'</div><div><div class="t">'+i.t+'</div><div class="d">'+i.d+'</div></div></div>';}).join(''):'<div class="empty">Not enough data yet.</div>';
}

/* ===================== Transactions table ===================== */
var PER=12,sortKey='v',sortDir=-1,tpage=1;
function fillTableFilters(){
  var cats=[].concat.apply([],[]);var cs={};TXN.forEach(function(t){cs[t.cat]=1;});
  var fc=document.getElementById('f-cat');fc.innerHTML='<option value="">All categories</option>'+Object.keys(cs).sort().map(function(c){return '<option>'+c+'</option>';}).join('');
  var as={};TXN.forEach(function(t){as[t.a]=1;});
  var fa=document.getElementById('f-a');fa.innerHTML='<option value="">All</option>'+Object.keys(as).sort().map(function(a){return '<option>'+a+'</option>';}).join('');
}
function tableRows(){
  var w=windowBounds();
  var mq=document.getElementById('f-m').value.trim().toLowerCase();
  var cq=document.getElementById('f-cat').value, aq=document.getElementById('f-a').value;
  var vq=parseFloat(document.getElementById('f-v').value)||0;
  var rows=acctTxns().filter(function(t){return t.raw>=w.s&&t.raw<=w.e;})
    .filter(function(t){return (!mq||t.m.toLowerCase().indexOf(mq)>=0)&&(!cq||t.cat===cq)&&(!aq||t.a===aq)&&t.v>=vq;});
  rows.sort(function(a,b){var x=a[sortKey],y=b[sortKey];if(sortKey==='v')return (x-y)*sortDir;x=String(x).toLowerCase();y=String(y).toLowerCase();return x<y?-sortDir:x>y?sortDir:0;});
  return rows;
}
function renderTable(){
  var rows=tableRows(),total=rows.length,tot=sum(rows);
  document.getElementById('txcount').textContent=total+' txns \u00b7 '+money(tot)+' \u00b7 '+windowLabel();
  var pages=Math.max(1,Math.ceil(total/PER));if(tpage>pages)tpage=pages;
  var slice=rows.slice((tpage-1)*PER,(tpage-1)*PER+PER);
  var tb=document.getElementById('txbody');
  document.getElementById('txempty').style.display=total?'none':'block';
  tb.innerHTML=slice.map(function(t){var col=catColor(t.cat);
    return '<tr><td class="n" style="color:var(--tx2);white-space:nowrap">'+t.d+'</td>'+
      '<td style="font-weight:500">'+t.m+'</td>'+
      '<td><span class="pill" style="background:var('+col+'-bg);color:var('+col+')">'+t.cat+'</span></td>'+
      '<td style="color:var(--tx2)">'+t.a+'</td>'+
      '<td class="tright n" style="font-weight:600">'+money2(t.v)+'</td></tr>';}).join('');
  document.querySelectorAll('#txtable th.th-sort').forEach(function(th){var k=th.getAttribute('data-sort');th.querySelector('.arr').textContent=k===sortKey?(sortDir<0?'\u25BC':'\u25B2'):'';});
  renderPager(total,pages);
}
function renderPager(total,pages){
  var p=document.getElementById('txpager');
  if(pages<=1){p.innerHTML='';return;}
  var h='<button class="pbtn" '+(tpage===1?'disabled':'')+' onclick="goPage('+(tpage-1)+')">\u2039</button>';
  var win=[];for(var i=1;i<=pages;i++){if(i===1||i===pages||Math.abs(i-tpage)<=1)win.push(i);else if(win[win.length-1]!=='\u2026')win.push('\u2026');}
  win.forEach(function(i){h+=(i==='\u2026')?'<span class="pdots">\u2026</span>':'<button class="pbtn '+(i===tpage?'on':'')+'" onclick="goPage('+i+')">'+i+'</button>';});
  h+='<button class="pbtn" '+(tpage===pages?'disabled':'')+' onclick="goPage('+(tpage+1)+')">\u203A</button>';
  p.innerHTML=h;
}
window.goPage=function(p){tpage=p;renderTable();};

/* ===================== account chips + wiring ===================== */
function renderChips(){
  document.getElementById('acctChips').innerHTML=ALL_ACCTS.map(function(a){
    var lab=a.length>18?a.split(/\s+/).map(function(w){return w[0];}).join('').slice(0,4).toUpperCase():a;
    return '<span class="chip'+(acctOn(a)?' on':'')+'" onclick="toggleAcct(\''+a.replace(/'/g,"\\'")+'\')" title="'+a+'"><span class="box"></span>'+lab+'</span>';
  }).join('');
}
window.toggleAcct=function(a){ACCTS[a]=!ACCTS[a];renderChips();renderAll();};

function setRange(mode){
  rangeMode=mode;tpage=1;
  document.querySelectorAll('#rangeSeg button').forEach(function(b){b.className=b.getAttribute('data-r')===mode?'on':'';});
  document.getElementById('customRange').style.display=mode==='custom'?'inline-flex':'none';
  renderAll();
}
function renderAll(){renderKPIs();renderMonthly();renderPace();renderCategories();renderBudgets();renderSubs();renderCashflow();renderInsights();renderTable();}

/* refresh */
window.runRefresh=function(){
  var b=document.getElementById('runBtn'),ico=document.getElementById('runIco'),txt=document.getElementById('runTxt');
  if(b.disabled)return;b.disabled=true;ico.textContent='\u21BB';ico.className='spin';txt.textContent='Running\u2026';
  fetch('/api/refresh',{method:'POST'}).then(function(r){if(!r.ok)throw 0;return r.json();}).then(function(nm){
    M=nm;MODEL=nm;TXN=(M.transactions||[]).slice();BUD=JSON.parse(JSON.stringify(M.budgets||{}));loadSavedBudgets();T=M.today;
    ALL_ACCTS=(function(){var s={},o=[];TXN.forEach(function(t){if(!s[t.a]){s[t.a]=1;o.push(t.a);}});return o;})();
    ALL_ACCTS.forEach(function(a){if(!(a in ACCTS))ACCTS[a]=true;});
    VY=T.y;VM=T.m;fillTableFilters();renderChips();renderAll();setUpdated();
    ico.className='';ico.textContent='\u2713';txt.textContent='Updated';
    setTimeout(function(){ico.textContent='\u25B6';txt.textContent='Run';b.disabled=false;},1400);
  }).catch(function(){ico.className='';ico.textContent='\u25B6';txt.textContent='Run';b.disabled=false;
    if(location.protocol==='file:'){txt.textContent='Run';}});
};
function setUpdated(){document.getElementById('updlbl').textContent=MONTHS_L[T.m]+' '+T.y+' \u00b7 updated '+((M.generatedAt||'').replace('T',' '));}

/* init */
loadSavedBudgets();
fillTableFilters();
renderChips();
document.getElementById('dim').addEventListener('change',renderMonthly);
document.querySelectorAll('#rangeSeg button').forEach(function(b){b.addEventListener('click',function(){setRange(b.getAttribute('data-r'));});});
['f-m','f-cat','f-a','f-v'].forEach(function(id){var el=document.getElementById(id);el.addEventListener(el.tagName==='SELECT'?'change':'input',function(){tpage=1;renderTable();});});
document.querySelectorAll('#txtable th.th-sort').forEach(function(th){th.addEventListener('click',function(){var k=th.getAttribute('data-sort');if(k===sortKey)sortDir=-sortDir;else{sortKey=k;sortDir=(k==='v'||k==='raw')?-1:1;}tpage=1;renderTable();});});
(function(){var c=document.getElementById('cStart'),e=document.getElementById('cEnd');
  if(M.minDate)c.value=M.minDate;if(M.maxDate)e.value=M.maxDate;
  c.addEventListener('change',function(){cStart=c.value;if(rangeMode==='custom')renderAll();});
  e.addEventListener('change',function(){cEnd=e.value;if(rangeMode==='custom')renderAll();});})();
setUpdated();
renderAll();
})();
</script>
</body>
</html>"""


def render_html(model):
    return _HTML.replace("@@MODEL@@", json.dumps(model))
