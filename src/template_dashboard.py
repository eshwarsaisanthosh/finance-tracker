"""Render the dashboard model into one self-contained HTML string.

No external assets: all CSS/JS inline, works offline, adapts to light/dark,
sized for mobile.
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
:root{--bg:#faf9f5;--card:#fff;--line:#e8e6df;--tx:#26251f;--tx2:#6b6a63;--tx3:#9b9a91;
  --acbg:#e1f5ee;--actx:#0f6e56;--good:#1d9e75;--over:#d85a30;--track:#eeece4;}
@media (prefers-color-scheme:dark){:root{--bg:#1a1a18;--card:#242422;--line:#33332f;--tx:#f0efe9;--tx2:#a8a79f;--tx3:#78766e;
  --acbg:#0f3d31;--actx:#9fe1cb;--good:#5dcaa5;--over:#f0997b;--track:#33332f;}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--tx);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;-webkit-font-smoothing:antialiased;}
.wrap{max-width:460px;margin:0 auto;padding:16px 16px 40px;}
.muted{color:var(--tx2);} .hint{color:var(--tx3);font-size:11px;}
.tabs{display:grid;grid-template-columns:1fr 1fr;gap:4px;background:var(--track);border:0.5px solid var(--line);border-radius:10px;padding:3px;margin:12px 0 14px;}
.tabs button{border:none;border-radius:8px;padding:8px;font-size:13px;font-weight:500;background:transparent;color:var(--tx2);cursor:pointer;}
.tabs button.on{background:var(--card);color:var(--tx);}
.card{background:var(--card);border:0.5px solid var(--line);border-radius:12px;padding:16px;margin-bottom:12px;}
.row{display:flex;align-items:center;justify-content:space-between;}
.big{font-size:30px;font-weight:600;letter-spacing:-0.5px;}
.stat .k{font-size:12px;color:var(--tx2);} .stat .v{font-size:20px;font-weight:600;margin-top:2px;}
.cell{aspect-ratio:1;border-radius:6px;display:flex;flex-direction:column;justify-content:space-between;padding:3px 4px;cursor:pointer;}
.bar{height:6px;background:var(--track);border-radius:3px;overflow:hidden;} .bar>span{display:block;height:6px;border-radius:3px;background:var(--good);}
.navbtn{border:0.5px solid var(--line);background:var(--card);color:var(--tx);border-radius:8px;padding:6px 11px;font-size:15px;cursor:pointer;line-height:1;}
.badge{width:24px;height:24px;border-radius:50%;background:var(--track);color:var(--tx2);font-size:9px;font-weight:600;display:flex;align-items:center;justify-content:center;}
.stitle{font-size:14px;font-weight:500;}
.icobtn{border:0.5px solid var(--line);background:var(--card);color:var(--tx2);border-radius:8px;padding:5px 8px;font-size:12px;cursor:pointer;}
/* Account filter pills */
.acct-bar{display:flex;flex-wrap:wrap;align-items:center;gap:6px;margin-bottom:10px;}
.alabel{font-size:11px;color:var(--tx3);margin-right:2px;}
.apill{display:inline-flex;align-items:center;gap:5px;border:0.5px solid var(--line);border-radius:20px;
  padding:4px 10px 4px 8px;font-size:12px;font-weight:500;cursor:pointer;background:var(--card);
  color:var(--tx2);transition:background .15s,border-color .15s,color .15s;user-select:none;}
.apill.on{background:var(--acbg);border-color:var(--actx);color:var(--actx);}
.apill .chk{width:13px;height:13px;border-radius:3px;border:1.5px solid currentColor;
  display:flex;align-items:center;justify-content:center;flex-shrink:0;font-size:9px;font-weight:700;}
.apill.on .chk::after{content:'✓';}
</style>
</head>
<body>
<div class="wrap">
  <div class="row" style="margin-bottom:2px">
    <span style="font-size:17px;font-weight:600">Spending</span>
    <button class="icobtn" id="refreshBtn" onclick="doRefresh()" aria-label="Refresh">↻ refresh</button>
  </div>
  <div id="updated" class="hint" style="margin-bottom:8px"></div>
  <div class="acct-bar" id="acctBar"></div>
  <div class="tabs">
    <button id="tb-ov" class="on" onclick="showTab('overview')">Overview</button>
    <button id="tb-dt" onclick="showTab('detail')">By day</button>
  </div>
  <div class="row" style="margin-bottom:14px">
    <button id="mprev" class="navbtn" onclick="stepMonth(-1)" aria-label="Previous month">‹</button>
    <span id="mlabel" style="font-size:15px;font-weight:500"></span>
    <button id="mnext" class="navbtn" onclick="stepMonth(1)" aria-label="Next month">›</button>
  </div>
  <div id="tab-overview"></div>
  <div id="tab-detail" style="display:none"></div>
</div>
<script>
var MODEL = @@MODEL@@;
(function(){
  var M=MODEL, HEAT=['#e1f5ee','#9fe1cb','#5dcaa5','#1d9e75'];
  var MONTHS=['','January','February','March','April','May','June','July','August','September','October','November','December'];
  function money(n){return '$'+Math.round(n||0).toLocaleString();}
  function pad(n){return String(n).padStart(2,'0');}
  function daysIn(y,m){return new Date(y,m,0).getDate();}
  function key(y,m,d){return y+'-'+pad(m)+'-'+pad(d);}
  var T=M.today, VY=T.y, VM=T.m, SEL=T.d;
  var minD=M.minDate?M.minDate.split('-').map(Number):[T.y,T.m,1];
  function isCurrent(){return VY===T.y&&VM===T.m;}
  function atMin(){return VY<minD[0]||(VY===minD[0]&&VM<=minD[1]);}

  // ── Account filter state ──────────────────────────────────────────────
  // Derive all unique account names from detailByDate
  var ALL_ACCTS=(function(){
    var seen={},out=[];
    for(var d in M.detailByDate)(M.detailByDate[d]||[]).forEach(function(t){
      if(t.acct&&!seen[t.acct]){seen[t.acct]=1;out.push(t.acct);}
    });
    return out;
  })();
  // ACCTS: set of currently-enabled account names
  var ACCTS={};
  ALL_ACCTS.forEach(function(a){ACCTS[a]=true;});

  function acctOn(name){return !!ACCTS[name];}
  function anyAcct(){return ALL_ACCTS.some(function(a){return ACCTS[a];});}

  window.toggleAcct=function(name){
    ACCTS[name]=!ACCTS[name];
    renderAcctBar();
    renderOverview();
    renderDetail();
  };

  function renderAcctBar(){
    var bar=document.getElementById('acctBar');
    if(ALL_ACCTS.length===0){bar.innerHTML='';return;}
    var pills=ALL_ACCTS.map(function(a){
      var on=acctOn(a);
      var label=a.length>18?a.split(/\s+/).map(function(w){return w[0];}).join('').slice(0,4).toUpperCase():a;
      return '<span class="apill'+(on?' on':'')+'" onclick="toggleAcct(\''+a.replace(/'/g,"\\'")+'\')" title="'+a+'">'+
        '<span class="chk"></span>'+label+'</span>';
    }).join('');
    bar.innerHTML='<span class="alabel">Accounts</span>'+pills;
  }

  // ── Filtered data helpers ─────────────────────────────────────────────
  // Recompute a day's total from detailByDate, respecting ACCTS filter
  function filteredDayAmt(dateKey){
    if(!anyAcct()) return 0;
    return (M.detailByDate[dateKey]||[]).reduce(function(s,t){
      return s+(acctOn(t.acct)&&t.amt>0?t.amt:0);
    },0);
  }

  // Compute month total using filtered per-day sums derived from detailByDate
  function monthSum(y,m){
    var s=0,p=y+'-'+pad(m)+'-';
    for(var k in M.dailyByDate){if(k.indexOf(p)===0) s+=filteredDayAmt(k);}
    return s;
  }

  // hasMonth: true if any filtered spend exists in that month
  function hasMonth(y,m){
    var p=y+'-'+pad(m)+'-';
    for(var k in M.dailyByDate){
      if(k.indexOf(p)===0&&filteredDayAmt(k)>0) return true;
    }
    // fall back to raw presence (so we can still navigate even if filtered to 0)
    for(var k in M.dailyByDate){if(k.indexOf(p)===0) return true;}
    return false;
  }

  // ── Pace / cumulative chart ───────────────────────────────────────────
  function paceChart(y,m,point){
    var tc=[],r=0;
    for(var d=1;d<=point;d++){r+=filteredDayAmt(key(y,m,d));tc.push(r);}
    var pm=m-1,py=y;if(pm<1){pm=12;py--;}
    var lc=null;
    // only draw last-month line if raw data exists (even if filtered to 0)
    var lp=y+'-'+pad(pm===0?12:pm)+'-';
    var rawHasLast=Object.keys(M.dailyByDate).some(function(k){return k.indexOf(lp)===0;});
    if(rawHasLast){lc=[];var rr=0;for(var d=1;d<=point;d++){rr+=filteredDayAmt(key(py,pm,d));lc.push(rr);}}
    var end=tc[tc.length-1]||0,lend=lc?lc[lc.length-1]||0:0,mx=Math.max(end,lend,1),W=322,x0=8,H=64;
    function X(i){return x0+(W-x0)*(i/((point-1)||1));}
    function Y(v){return H-4-(H-14)*(v/mx);}
    function pth(a){return 'M'+a.map(function(v,i){return X(i).toFixed(1)+','+Y(v).toFixed(1);}).join(' L');}
    var s='<svg viewBox="0 0 330 70" width="100%" height="58" style="display:block;margin-top:2px">';
    if(lc)s+='<path d="'+pth(lc)+'" fill="none" stroke="var(--tx3)" stroke-width="1.5" stroke-dasharray="4 3"/>';
    s+='<path d="'+pth(tc)+' L'+X(point-1).toFixed(1)+',66 L'+x0+',66 Z" fill="var(--acbg)"/>';
    s+='<path d="'+pth(tc)+'" fill="none" stroke="var(--good)" stroke-width="2"/></svg>';
    s+=lc?'<div style="display:flex;gap:14px;font-size:11px;color:var(--tx3);margin-top:2px"><span><span style="display:inline-block;width:14px;height:2px;background:var(--good);vertical-align:middle"></span> this month</span><span><span style="display:inline-block;width:14px;border-top:2px dashed var(--tx3);vertical-align:middle"></span> last month</span></div>':'<div class="hint">cumulative this month</div>';
    return s;
  }

  // ── Rolling-90 panels (filtered) ─────────────────────────────────────
  function renderPanels(){
    // Recompute from detailByDate so filtering is reflected
    var today=new Date(T.y,T.m-1,T.d);
    var catMap={},accMap={};
    for(var date in M.detailByDate){
      var diff=Math.floor((today-new Date(date))/86400000);
      if(diff<0||diff>=M.windowDays) continue;
      (M.detailByDate[date]||[]).forEach(function(t){
        if(!acctOn(t.acct)||t.amt<=0) return;
        catMap[t.cat]=(catMap[t.cat]||0)+t.amt;
        accMap[t.acct]=(accMap[t.acct]||0)+t.amt;
      });
    }
    var cats=Object.keys(catMap).map(function(k){return[k,Math.round(catMap[k])];})
                .sort(function(a,b){return b[1]-a[1];}).slice(0,5);
    var accs=Object.keys(accMap).map(function(k){
      var code=k.split(/\s+/).map(function(w){return w[0];}).join('').slice(0,2).toUpperCase();
      return[k,Math.round(accMap[k]),code];
    }).sort(function(a,b){return b[1]-a[1];});

    var amx=accs.length?accs[0][1]:1;
    var accRows=accs.map(function(a){
      return '<div style="margin-bottom:11px"><div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">'+
        '<span class="badge">'+a[2]+'</span>'+
        '<span style="font-size:13px;flex:1">'+a[0]+'</span>'+
        '<span style="font-size:13px;color:var(--tx2)">'+money(a[1])+'</span></div>'+
        '<div class="bar" style="margin-left:32px"><span style="width:'+Math.round(a[1]/amx*100)+'%"></span></div></div>';
    }).join('') || '<div class="hint">No account data.</div>';

    var cmx=cats.length?cats[0][1]:1;
    var catRows=cats.map(function(c){
      return '<div style="margin-bottom:9px"><div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:3px">'+
        '<span>'+c[0]+'</span><span style="color:var(--tx2)">'+money(c[1])+'</span></div>'+
        '<div class="bar"><span style="width:'+Math.round(c[1]/cmx*100)+'%"></span></div></div>';
    }).join('') || '<div class="hint">No category data.</div>';

    return '<div class="card"><div class="row" style="margin-bottom:12px"><span class="stitle">By account</span><span class="hint">last '+M.windowDays+' days</span></div>'+accRows+'</div>'+
           '<div class="card"><div class="row" style="margin-bottom:10px"><span class="stitle">Top categories</span><span class="hint">last '+M.windowDays+' days</span></div>'+catRows+'</div>';
  }

  // ── Overview ─────────────────────────────────────────────────────────
  function renderOverview(){
    document.getElementById('mlabel').textContent=MONTHS[VM]+' '+VY;
    document.getElementById('mnext').style.opacity=isCurrent()?0.3:1;
    document.getElementById('mprev').style.opacity=atMin()?0.3:1;
    var el=document.getElementById('tab-overview');
    if(!hasMonth(VY,VM)){
      el.innerHTML='<div class="card" style="text-align:center;color:var(--tx3);padding:2.25rem 1rem">'+
        '<div style="font-size:24px">◵</div>'+
        '<div style="font-size:13px;margin-top:8px">No data for '+MONTHS[VM]+' '+VY+'</div></div>'+renderPanels();
      return;
    }
    var dim=daysIn(VY,VM),point=isCurrent()?T.d:dim,total=monthSum(VY,VM);
    // daily avg & biggest: use filtered amounts
    var dayAmts=[];
    for(var d=1;d<=dim;d++){var v=filteredDayAmt(key(VY,VM,d));if(v>0)dayAmts.push({d:d,v:v});}
    var avg=dayAmts.length?Math.round(total/point):0;
    var big=dayAmts.reduce(function(mx,x){return x.v>mx.v?x:mx;},{d:1,v:0});
    // pace vs last month
    var pm=VM-1,py=VY;if(pm<1){pm=12;py--;}
    var lp=py+'-'+pad(pm)+'-';
    var rawHasLast=Object.keys(M.dailyByDate).some(function(k){return k.indexOf(lp)===0;});
    var pt=0;if(rawHasLast)for(var d=1;d<=point;d++)pt+=filteredDayAmt(key(py,pm,d));
    var pace=(rawHasLast&&pt>0)?Math.round((total-pt)/pt*100):null;
    var paceH=pace===null?'<span style="font-size:12px;color:var(--tx3)">no prior month</span>':
      '<span style="font-size:13px;color:'+(pace<=0?'var(--good)':'var(--over)')+'">'+(pace<=0?'▼ ':'▲ ')+Math.abs(pace)+'% vs last month</span>';

    // calendar shading based on filtered values
    var filtVals=dayAmts.map(function(x){return x.v;});
    var mx=filtVals.length?Math.max.apply(null,filtVals):1;
    function shade(v){if(!v)return null;var h=[mx*.25,mx*.5,mx*.75];if(v<=h[0])return HEAT[0];if(v<=h[1])return HEAT[1];if(v<=h[2])return HEAT[2];return HEAT[3];}

    var fd=new Date(VY,VM-1,1).getDay(),cal='';
    for(var i=0;i<fd;i++)cal+='<div></div>';
    for(var d=1;d<=dim;d++){
      if(isCurrent()&&d>T.d){cal+='<div class="cell" style="background:var(--track);opacity:.4;cursor:default"><span style="font-size:8px;color:var(--tx3)">'+d+'</span></div>';continue;}
      var v=filteredDayAmt(key(VY,VM,d)),bg=shade(v),sel=(d===SEL&&isCurrent())?'outline:2px solid var(--actx);outline-offset:1px;':'';
      var st=bg?('background:'+bg+';color:#04342c;'):('background:var(--track);color:var(--tx3);');
      cal+='<div class="cell" style="'+st+sel+'" onclick="selectDay('+d+')"><span style="font-size:8px;opacity:.55">'+d+'</span><span style="font-size:10px;font-weight:600;text-align:right;line-height:1.1">'+(v?'$'+Math.round(v):'')+'</span></div>';
    }
    var dows='SMTWTFS'.split('').map(function(x){return '<div style="text-align:center;font-size:10px;color:var(--tx3)">'+x+'</div>';}).join('');

    el.innerHTML=
      '<div class="card"><div class="muted" style="font-size:13px;margin-bottom:3px">Spent in '+MONTHS[VM]+'</div>'+
      '<div style="display:flex;align-items:baseline;gap:10px;margin-bottom:6px"><span class="big">'+money(total)+'</span>'+paceH+'</div>'+
      paceChart(VY,VM,point)+'</div>'+
      '<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px">'+
        '<div class="card stat" style="margin:0"><div class="k">Daily average</div><div class="v">'+money(avg)+'</div></div>'+
        '<div class="card stat" style="margin:0"><div class="k">Biggest day</div><div class="v">'+money(big.v)+'</div></div>'+
      '</div>'+
      '<div class="card"><div class="row" style="margin-bottom:10px"><span class="stitle">Daily spend</span><span class="hint">tap a day →</span></div>'+
      '<div style="display:grid;grid-template-columns:repeat(7,1fr);gap:4px;margin-bottom:4px">'+dows+'</div>'+
      '<div style="display:grid;grid-template-columns:repeat(7,1fr);gap:4px">'+cal+'</div></div>'+
      renderPanels();
  }

  // ── By day ────────────────────────────────────────────────────────────
  function renderDetail(){
    var el=document.getElementById('tab-detail');
    var dt=new Date(VY,VM-1,SEL),title=dt.toLocaleDateString(undefined,{weekday:'short',month:'short',day:'numeric'});
    // Filter transactions by active accounts
    var allItems=M.detailByDate[key(VY,VM,SEL)]||[];
    var items=allItems.filter(function(t){return acctOn(t.acct)&&t.amt>0;});
    var total=items.reduce(function(a,b){return a+b.amt;},0),body;
    if(!items.length){
      body='<div class="card" style="text-align:center;color:var(--tx3);font-size:13px;padding:28px 0">No spending on this day</div>';
    } else {
      var g={},ord=[];
      items.forEach(function(t){
        if(!g[t.acct]){g[t.acct]={code:t.code,items:[],sum:0};ord.push(t.acct);}
        g[t.acct].items.push(t);g[t.acct].sum+=t.amt;
      });
      ord.sort(function(a,b){return g[b].sum-g[a].sum;});
      body=ord.map(function(nm){
        var gp=g[nm];
        var rows=gp.items.map(function(t,i){
          return '<div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0;'+
            (i<gp.items.length-1?'border-bottom:0.5px solid var(--line)':'')+'">'+
            '<span><span style="font-size:13px">'+t.merchant+'</span><br><span class="hint">'+t.cat+'</span></span>'+
            '<span style="font-size:13px">'+money(t.amt)+'</span></div>';
        }).join('');
        return '<div class="card"><div class="row" style="margin-bottom:8px">'+
          '<span style="display:flex;align-items:center;gap:8px">'+
          '<span class="badge">'+gp.code+'</span>'+
          '<span style="font-size:14px;font-weight:500">'+nm+'</span></span>'+
          '<span class="muted" style="font-size:13px">'+money(gp.sum)+'</span></div>'+rows+'</div>';
      }).join('')+'<div class="hint" style="text-align:center">'+ord.length+' account'+(ord.length>1?'s':'')+' active</div>';
    }
    el.innerHTML=
      '<div class="row" style="margin-bottom:12px">'+
      '<button class="navbtn" onclick="stepDay(-1)" aria-label="Previous day">‹</button>'+
      '<div style="text-align:center"><div style="font-size:15px;font-weight:500">'+title+'</div>'+
      '<div class="hint">transactions by account</div></div>'+
      '<button class="navbtn" onclick="stepDay(1)" aria-label="Next day">›</button></div>'+
      '<div class="card row" style="padding:14px 16px"><span class="muted" style="font-size:13px">Total this day</span>'+
      '<span style="font-size:24px;font-weight:600">'+money(total)+'</span></div>'+body;
  }

  // ── Nav ───────────────────────────────────────────────────────────────
  window.showTab=function(n){
    var ov=n==='overview';
    document.getElementById('tab-overview').style.display=ov?'block':'none';
    document.getElementById('tab-detail').style.display=ov?'none':'block';
    document.getElementById('tb-ov').className=ov?'on':'';
    document.getElementById('tb-dt').className=ov?'':'on';
  };
  window.stepMonth=function(s){
    if(s>0&&isCurrent())return;if(s<0&&atMin())return;
    var m=VM+s,y=VY;if(m<1){m=12;y--;}if(m>12){m=1;y++;}
    VY=y;VM=m;SEL=isCurrent()?T.d:1;renderOverview();renderDetail();
  };
  window.selectDay=function(d){SEL=d;renderOverview();renderDetail();showTab('detail');};
  window.stepDay=function(s){
    var max=isCurrent()?T.d:daysIn(VY,VM),d=SEL+s;
    if(d<1||d>max)return;SEL=d;renderDetail();
  };

  function setUpdated(){document.getElementById('updated').textContent='Updated '+(M.generatedAt||'').replace('T',' ');}
  window.doRefresh=function(){
    var b=document.getElementById('refreshBtn');b.textContent='↻ refreshing…';
    fetch('/api/refresh',{method:'POST'})
      .then(function(r){if(!r.ok)throw 0;return r.json();})
      .then(function(nm){
        M=nm;MODEL=nm;T=M.today;VY=T.y;VM=T.m;SEL=T.d;
        minD=M.minDate?M.minDate.split('-').map(Number):[VY,VM,1];
        // re-init account list
        ALL_ACCTS.length=0;var seen={};
        for(var d in M.detailByDate)(M.detailByDate[d]||[]).forEach(function(t){
          if(t.acct&&!seen[t.acct]){seen[t.acct]=1;ALL_ACCTS.push(t.acct);}
        });
        ALL_ACCTS.forEach(function(a){if(!(a in ACCTS))ACCTS[a]=true;});
        renderAcctBar();renderOverview();renderDetail();setUpdated();b.textContent='↻ refresh';
      }).catch(function(){location.reload();});
  };

  renderAcctBar();
  setUpdated();
  renderOverview();
  renderDetail();
})();
</script>
</body>
</html>"""


def render_html(model):
    return _HTML.replace("@@MODEL@@", json.dumps(model))
