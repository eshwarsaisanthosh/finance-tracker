"""Render the dashboard model into one self-contained HTML string.

No external assets: all CSS/JS inline, works offline, adapts to light/dark,
sized for mobile. Safe to open from a synced folder on a phone.
"""
import json

_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Spend">
<title>Spend dashboard</title>
<style>
:root{
  --bg:#faf9f5;--card:#ffffff;--line:#e8e6df;--tx:#26251f;--tx2:#6b6a63;--tx3:#9b9a91;
  --acbg:#e1f5ee;--actx:#0f6e56;--good:#1d9e75;--over:#d85a30;--track:#f1efe8;
}
@media (prefers-color-scheme:dark){
  :root{
    --bg:#1a1a18;--card:#242422;--line:#33332f;--tx:#f0efe9;--tx2:#a8a79f;--tx3:#78766e;
    --acbg:#0f3d31;--actx:#9fe1cb;--good:#5dcaa5;--over:#f0997b;--track:#2f2f2c;
  }
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--tx);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  -webkit-font-smoothing:antialiased;}
.wrap{max-width:460px;margin:0 auto;padding:16px 16px 40px;}
h1{font-size:17px;font-weight:600;margin:0;}
.muted{color:var(--tx2);}
.hint{color:var(--tx3);font-size:11px;}
.tabs{display:grid;grid-template-columns:1fr 1fr;gap:4px;background:var(--track);
  border:0.5px solid var(--line);border-radius:10px;padding:3px;margin:12px 0 16px;}
.tabs button{border:none;border-radius:8px;padding:8px;font-size:13px;font-weight:500;
  background:transparent;color:var(--tx2);cursor:pointer;}
.tabs button.on{background:var(--card);color:var(--tx);}
.card{background:var(--card);border:0.5px solid var(--line);border-radius:12px;padding:16px;margin-bottom:12px;}
.row{display:flex;align-items:center;justify-content:space-between;}
.big{font-size:30px;font-weight:600;letter-spacing:-0.5px;}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px;}
.stat .k{font-size:12px;color:var(--tx2);}
.stat .v{font-size:20px;font-weight:600;margin-top:2px;}
.cal{display:grid;grid-template-columns:repeat(7,1fr);gap:4px;}
.dow{text-align:center;font-size:10px;color:var(--tx3);}
.cell{aspect-ratio:1;border-radius:6px;display:flex;flex-direction:column;justify-content:space-between;
  padding:3px 4px;cursor:pointer;}
.cell .n{font-size:9px;opacity:.7;}
.cell .a{font-size:10px;font-weight:600;text-align:right;}
.cell.future{background:var(--track);opacity:.45;cursor:default;}
.cell.empty{background:transparent;cursor:default;}
.legend{font-size:11px;color:var(--tx3);display:flex;align-items:center;gap:4px;}
.sw{width:11px;height:11px;border-radius:3px;display:inline-block;}
.bar{height:6px;background:var(--track);border-radius:3px;overflow:hidden;}
.bar>span{display:block;height:6px;border-radius:3px;background:var(--good);}
.navbtn{border:0.5px solid var(--line);background:var(--card);color:var(--tx);border-radius:8px;
  padding:6px 11px;font-size:15px;cursor:pointer;line-height:1;}
.badge{width:26px;height:26px;border-radius:50%;background:var(--acbg);color:var(--actx);
  font-size:10px;font-weight:600;display:flex;align-items:center;justify-content:center;}
.txr{display:flex;justify-content:space-between;align-items:center;padding:6px 0;}
.section-title{font-size:14px;font-weight:600;margin-bottom:10px;}
a{color:var(--actx);}
</style>
</head>
<body>
<div class="wrap">
  <div class="row">
    <h1>Spending</h1>
    <span class="hint" id="gen"></span>
  </div>
  <div class="tabs">
    <button id="tb-ov" class="on" onclick="showTab('overview')">Overview</button>
    <button id="tb-dt" onclick="showTab('detail')">By day</button>
  </div>
  <div id="tab-overview"></div>
  <div id="tab-detail" style="display:none"></div>
</div>
<script>
var MODEL = @@MODEL@@;
(function(){
  var M=MODEL, DOW=['S','M','T','W','T','F','S'];
  var HEAT=['#e1f5ee','#9fe1cb','#5dcaa5','#1d9e75'];
  function money(n){return '$'+Math.round(n||0).toLocaleString();}
  function shade(v){if(!v)return null;var h=M.heat;if(v<=h[0])return HEAT[0];if(v<=h[1])return HEAT[1];if(v<=h[2])return HEAT[2];return HEAT[3];}

  function spark(){
    var c=M.cumulative||[];if(c.length<2)return '';
    var n=M.todayDay,mx=M.mtd||1,W=330,H=66,x0=8,x1=322;
    function X(i){return x0+(x1-x0)*(i/(n-1||1));}
    function Y(v){return H-4-(H-14)*(v/(mx||1));}
    var pts=c.map(function(p){return X(p.d-1).toFixed(1)+','+Y(p.v).toFixed(1);});
    var line='M'+pts.join(' L');
    var area=line+' L'+X(n-1).toFixed(1)+','+H+' L'+x0+','+H+' Z';
    return '<svg viewBox="0 0 330 72" width="100%" height="56" style="display:block;margin-top:10px">'+
      '<path d="'+area+'" fill="#e1f5ee"/><path d="'+line+'" fill="none" stroke="#1d9e75" stroke-width="2"/></svg>';
  }

  function paceHtml(){
    if(M.pacePct===null||M.pacePct===undefined)return '<span class="hint">no prior month</span>';
    var p=M.pacePct,under=p<=0,col=under?'var(--good)':'var(--over)';
    return '<span style="font-size:13px;color:'+col+'">'+(under?'▼ ':'▲ ')+Math.abs(p)+'% '+(under?'under':'over')+' last month</span>';
  }

  function calHtml(){
    var h='<div class="row" style="margin-bottom:4px"><span class="section-title" style="margin:0">Daily spend</span>'+
      '<span class="legend">less <span class="sw" style="background:'+HEAT[0]+'"></span><span class="sw" style="background:'+HEAT[1]+'"></span><span class="sw" style="background:'+HEAT[2]+'"></span><span class="sw" style="background:'+HEAT[3]+'"></span> more</span></div>'+
      '<div class="hint" style="margin-bottom:10px">Tap a day for the account breakdown</div>'+
      '<div class="cal">'+DOW.map(function(d){return '<div class="dow">'+d+'</div>';}).join('')+'</div>'+
      '<div class="cal" style="margin-top:4px" id="calgrid"></div>';
    return h;
  }
  function fillCal(){
    var g=document.getElementById('calgrid');if(!g)return;var h='';
    for(var i=0;i<M.offset;i++)h+='<div class="cell empty"></div>';
    for(var d=1;d<=M.daysInMonth;d++){
      if(d>M.todayDay){h+='<div class="cell future"><span class="n">'+d+'</span></div>';continue;}
      var v=M.dailySpend[d]||0,bg=shade(v),sel=(d===SEL)?'outline:2px solid var(--actx);outline-offset:1px;':'';
      var style=bg?('background:'+bg+';color:#04342c;'):('background:var(--track);color:var(--tx3);');
      h+='<div class="cell" style="'+style+sel+'" onclick="selectDay('+d+')"><span class="n">'+d+'</span><span class="a">'+(v||'')+'</span></div>';
    }
    g.innerHTML=h;
  }

  function catHtml(){
    var cs=M.categories||[];if(!cs.length)return '';
    var mx=cs[0][1]||1;
    var rows=cs.map(function(c){return '<div style="margin-bottom:9px"><div class="row" style="font-size:12px;margin-bottom:3px"><span>'+c[0]+'</span><span class="muted">'+money(c[1])+'</span></div><div class="bar"><span style="width:'+Math.round(c[1]/mx*100)+'%"></span></div></div>';}).join('');
    return '<div class="card"><div class="section-title">Top categories · '+M.windowDays+' days</div>'+rows+'</div>';
  }

  function renderOverview(){
    var el=document.getElementById('tab-overview');
    el.innerHTML=
      '<div class="card"><div class="muted" style="font-size:13px;margin-bottom:4px">Spent this month</div>'+
      '<div style="display:flex;align-items:baseline;gap:10px"><span class="big">'+money(M.mtd)+'</span>'+paceHtml()+'</div>'+
      spark()+'<div class="hint">Cumulative, month-to-date</div></div>'+
      '<div class="grid2"><div class="card stat" style="margin:0"><div class="k">Daily avg ('+M.windowDays+'d)</div><div class="v">'+money(M.dailyAvg90)+'</div></div>'+
      '<div class="card stat" style="margin:0"><div class="k">Projected total</div><div class="v">'+money(M.projected)+'</div></div></div>'+
      '<div class="card">'+calHtml()+'</div>'+catHtml();
    fillCal();
  }

  function renderDetail(){
    var el=document.getElementById('tab-detail');
    var dt=new Date(M.year,M.month-1,SEL);
    var title=dt.toLocaleDateString(undefined,{weekday:'short',month:'short',day:'numeric'});
    var items=(M.detail[String(SEL)]||[]);
    var total=items.reduce(function(a,b){return a+b.amt;},0);
    var body;
    if(!items.length){body='<div class="card" style="text-align:center;color:var(--tx3);padding:28px 0">No spending on this day</div>';}
    else{
      var groups={},order=[];
      items.forEach(function(t){if(!groups[t.acct]){groups[t.acct]={code:t.code,items:[],sum:0};order.push(t.acct);}groups[t.acct].items.push(t);groups[t.acct].sum+=t.amt;});
      order.sort(function(a,b){return groups[b].sum-groups[a].sum;});
      body=order.map(function(nm){var gp=groups[nm];
        var rows=gp.items.map(function(t,i){return '<div class="txr" style="'+(i<gp.items.length-1?'border-bottom:0.5px solid var(--line)':'')+'"><span><span style="font-size:13px">'+t.merchant+'</span><br><span class="hint">'+t.cat+'</span></span><span style="font-size:13px">'+money(t.amt)+'</span></div>';}).join('');
        return '<div class="card"><div class="row" style="margin-bottom:8px"><span style="display:flex;align-items:center;gap:8px"><span class="badge">'+gp.code+'</span><span style="font-size:14px;font-weight:600">'+nm+'</span></span><span class="muted" style="font-size:13px">'+money(gp.sum)+'</span></div>'+rows+'</div>';
      }).join('')+'<div class="hint" style="text-align:center">'+order.length+' account'+(order.length>1?'s':'')+' active</div>';
    }
    el.innerHTML=
      '<div class="row" style="margin-bottom:12px"><button class="navbtn" onclick="stepDay(-1)" aria-label="Previous day">‹</button>'+
      '<div style="text-align:center"><div style="font-size:15px;font-weight:600">'+title+'</div><div class="hint">daily transactions by account</div></div>'+
      '<button class="navbtn" onclick="stepDay(1)" aria-label="Next day">›</button></div>'+
      '<div class="card row" style="padding:14px 16px"><span class="muted" style="font-size:13px">Total this day</span><span style="font-size:24px;font-weight:600">'+money(total)+'</span></div>'+
      body;
  }

  var SEL=M.todayDay||1;
  window.showTab=function(n){var ov=n==='overview';
    document.getElementById('tab-overview').style.display=ov?'block':'none';
    document.getElementById('tab-detail').style.display=ov?'none':'block';
    document.getElementById('tb-ov').className=ov?'on':'';
    document.getElementById('tb-dt').className=ov?'':'on';};
  window.selectDay=function(d){SEL=d;fillCal();renderDetail();showTab('detail');};
  window.stepDay=function(s){var d=SEL+s;if(d<1||d>M.todayDay)return;SEL=d;fillCal();renderDetail();};

  document.getElementById('gen').textContent='as of '+(M.generatedAt||'').replace('T',' ');
  renderOverview();renderDetail();
})();
</script>
</body>
</html>"""


def render_html(model):
    return _HTML.replace("@@MODEL@@", json.dumps(model))
