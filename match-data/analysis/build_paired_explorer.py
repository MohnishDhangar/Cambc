"""Build a self-contained, offline comparison viewer from validated replay data."""
from pathlib import Path
from bisect import bisect_left
import json, hashlib
ROOT=Path(__file__).resolve().parent/'paired-v1-v3'
D=json.loads((ROOT/'comparison.json').read_text())
unique={}
for g in D['games']:unique.setdefault((g['version'],g['mapHash']),g)
labels={'116b2c56':'31×31 — paired camps','37b8ace8':'30×30 — elkring','9696d128':'30×30 — compact','50365c96':'50×50 — rows','61bcbc25':'50×50 — mixed camps','c76debb1':'50×50 — monolith only','43362dd0':'60×50 — one gem objective','bf50fd85':'90×30 — 18 altars','95a4e642':'80×80 — spacious','ee68ccad':'71×71 — open'}
games=[]
for (v,h),g in unique.items():
 p=ROOT/v/g['series']/g['game'];s=json.loads((p/'summary.json').read_text());rounds=json.loads((p/'rounds.json').read_text());turns=json.loads((p/'turns.json').read_text())
 by={c['id']:[] for c in g['champions']}
 for t in turns:by[t['id']].append(t)
 nums={i:[t['round'] for t in ts] for i,ts in by.items()}
 keyrounds={x['round']+1 for x in g['engagements']}
 frames=[]
 for r in rounds:
  n=r['round']
  if n>200 and n%5 and n not in keyrounds and r is not rounds[-1]:continue
  gold=[0,0]
  for c in g['champions']:
   at=bisect_left(nums[c['id']],n)-1
   if at>=0:gold[c['team']]+=by[c['id']][at]['earnedGold']
  cs=[]
  for c in r['champions']:
   pos=c.get('position',{'x':-1,'y':-1})
   cs.append([c['entity']['index'],pos['x'],pos['y'],c['health'],c['maxHealth'],int(c['alive']),c['gems'],c['gold'],c['items']])
  frames.append([n,*r['score'],*gold,cs])
 roster=[{k:c[k] for k in ['id','team','name','submittedGems','earnedGold','deaths','activity']} for c in g['champions']]
 games.append({'version':v,'mapHash':h,'label':labels.get(h[:8],f"{g['width']}×{g['height']}")+' · '+h[:8],
 'round':g['round'],'score':g['score'],'map':s['map'],'roster':roster,'frames':frames,'engagements':g['engagements'],
 'source':f"{v}/{g['series']}/{g['game']}/strategy.json",'groups':g['groups']})
# Replay links are relative to this analysis directory.
for game,g in zip(games,unique.values()):
 import os
 game['replay']=os.path.relpath(g['source'],ROOT)
html='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Bot1 versus lll — replay evidence</title>
<style>
:root{color-scheme:dark;font:15px system-ui,sans-serif;background:#111820;color:#e8edf5}body{max-width:1380px;margin:24px auto;padding:0 20px}h1{font-size:25px;margin-bottom:8px}p{line-height:1.5;color:#bac8d8}a{color:#78c2ff}select,button{font:inherit;background:#243142;color:#fff;border:1px solid #5c7088;border-radius:5px;padding:8px}label{margin-right:18px;display:inline-block;margin-bottom:10px}.controls{background:#192330;padding:16px;border-radius:8px}.layout{display:grid;grid-template-columns:minmax(300px,1fr) minmax(340px,1fr);gap:22px;margin-top:20px}canvas{width:100%;background:#15202b;border:1px solid #354557;border-radius:6px}#map{aspect-ratio:1}#plot{height:190px}table{width:100%;border-collapse:collapse;font-size:13px}th,td{text-align:left;padding:7px;border-bottom:1px solid #344151}td.num{text-align:right}.a{color:#70b7ff}.b{color:#ffb273}#slider{width:65%;vertical-align:middle}#facts{font-size:18px;line-height:1.7;margin:14px 0}.small{font-size:12px}.scroll{max-height:270px;overflow:auto}button{cursor:pointer}.badge{padding:5px;background:#243142;border-radius:5px}tr.selected{background:#304354}@media(max-width:850px){.layout{grid-template-columns:1fr}}:focus-visible{outline:3px solid #9cd5ff;outline-offset:2px}
</style><h1>Bot1 versus lll: where the advantage develops</h1>
<p>50 supplied recordings reduce to 34 distinct action sequences: 17 identical maps per version. Repeated files are excluded here. Choose a map, switch versions at the same round, and inspect captures. <a href="REPORT.md">Read the findings</a> · <a href="STRATEGY-PLAN.md">Next strategy</a></p>
<div class="controls"><label>Map <select id="maps" aria-label="Map"></select></label><label>Our bot <select id="version"><option>v1</option><option selected>v3</option></select></label><label>Chart <select id="metric"><option value="score">Submitted gems</option><option value="gold">Gold earned</option></select></label><div><button id="play">Play</button> <input type="range" id="slider" min="0" value="0" aria-label="Replay round"> <span id="round"></span></div></div>
<div id="facts"></div><div class="layout"><section><canvas id="map" width="700" height="700" aria-label="Champion positions and camp locations"></canvas><p class="small"><span class="a">Blue: Bot1</span> · <span class="b">Orange: lll</span>. Champion labels are entity IDs. Fixed camp markers: wolf W, elk E, gems G, gold $, monolith M. Markers do not indicate whether a camp is alive. Dark tiles are walls/holes; purple tiles are altars. Positions are observed at round start. After round 200, frames are sampled every five rounds plus capture boundaries.</p></section>
<section><canvas id="plot" width="700" height="220" aria-label="Resource timeline"></canvas><div id="links" class="small"></div><p class="small">Gold earned uses the last completed turn before each frame. At the final frame, the completed match score is shown separately above. Click a champion row to follow its path over the preceding 60 rounds.</p><div class="scroll"><table><thead><tr><th>Champion</th><th>HP</th><th>Bag</th><th>Gold held</th></tr></thead><tbody id="champions"></tbody></table></div><p id="equipment" class="small"></p><p><strong>Recent captures</strong> — click to jump just after the reward</p><div class="scroll"><table><thead><tr><th>Round</th><th>Group</th><th>Recipient</th><th>Reward</th></tr></thead><tbody id="captures"></tbody></table></div></section></div>
<p class="small">These are reconstructed observations, not the opponent’s source code or decision logs. The opponent’s current rank and exact upload binary cannot be established from these files. Official engine 0.0.3; original inputs preserved and hashed.</p>
<script id="data" type="application/json">__DATA__</script><script>
const games=JSON.parse(document.querySelector('#data').textContent),$=id=>document.getElementById(id);
const mapSelect=$('maps'),versions=$('version'),slider=$('slider');let selected=null,game,timer=null;
const choices=[...new Map(games.map(g=>[g.mapHash,g.label])).entries()].sort((a,b)=>a[1].localeCompare(b[1]));
for(const [hash,label] of choices){let o=document.createElement('option');o.value=hash;o.textContent=label;mapSelect.append(o)}
mapSelect.value=games.find(g=>g.mapHash.startsWith('50365c96')).mapHash;
const colors=['#70b7ff','#ffb273'];const names=['Monster','Power','Durability','Treasure','Jungle','Home','Bruiser'];
function itemsText(items){return items.flatMap((n,i)=>n?[`${n} ${names[Math.floor(i/6)]} ${['Strength','Focus','Health'][Math.floor(i%6/2)]} ${i%2?'emblem':'shard'}`]:[]).join(', ')||'No equipment'}
function choose(){const old=game?.frames[+slider.value]?.[0]||0;game=games.find(g=>g.mapHash===mapSelect.value&&g.version===versions.value);slider.max=game.frames.length-1;let i=game.frames.findIndex(f=>f[0]>=old);slider.value=i<0?game.frames.length-1:i;selected=null;render()}
function jump(round){let i=game.frames.findIndex(f=>f[0]>=round);slider.value=i<0?game.frames.length-1:i;render()}
function render(){const f=game.frames[+slider.value],r=f[0];$('round').textContent=`Round ${r} / ${game.round}`;
$('facts').innerHTML=`<span class="a">Bot1 ${game.version}: ${f[1]}</span> · <span class="b">lll: ${f[2]}</span> gems <span class="small">— completed match: ${game.score[0]}–${game.score[1]} at round ${game.round}</span>`;
$('links').innerHTML=`<a href="${game.source}">Detailed evidence JSON</a> · <a href="${game.replay}">Original replay</a>`;
const c=$('map').getContext('2d'),m=game.map,W=700,pad=20,scale=Math.min((W-2*pad)/m.width,(W-2*pad)/m.height),ox=(W-m.width*scale)/2,oy=(W-m.height*scale)/2;
c.clearRect(0,0,W,W);const tile=(x,y)=>[ox+x*scale,oy+y*scale];
c.fillStyle='#223226';c.fillRect(ox,oy,m.width*scale,m.height*scale);
for(const [kind,color] of [['bush','#284f38'],['hole','#080e15'],['wall','#596571'],['altar','#c584e8']]){c.fillStyle=color;for(const [x,y] of m.terrain[kind])c.fillRect(...tile(x,y),scale,scale)}
for(const a of m.camps){let [x,y]=tile(a.x,a.y);c.fillStyle=['#c3bd9c','#dbb78c','#69dcb3','#e2c65e','#f48fca'][a.type];c.fillRect(x+scale*.13,y+scale*.13,scale*.74,scale*.74);if(scale>12){c.fillStyle='#111';c.font=`${Math.max(9,scale*.6)}px system-ui`;c.textAlign='center';c.fillText(['W','E','G','$','M'][a.type],x+scale/2,y+scale*.75)}}
if(selected!==null){const owner=game.roster.find(x=>x.id===selected);c.strokeStyle=colors[owner.team];c.lineWidth=2;c.beginPath();let started=false;for(const old of game.frames){if(old[0]<r-60||old[0]>r)continue;const a=old[5].find(x=>x[0]===selected);if(!a||!a[5]){started=false;continue}let [x,y]=tile(a[1]+.5,a[2]+.5);if(started)c.lineTo(x,y);else c.moveTo(x,y);started=true}c.stroke()}
for(const a of f[5]){if(!a[5]||a[1]<0)continue;let [x,y]=tile(a[1]+.5,a[2]+.5);const owner=game.roster.find(x=>x.id===a[0]);c.fillStyle=colors[owner.team];c.beginPath();c.arc(x,y,Math.max(4,scale*.43),0,Math.PI*2);c.fill();c.strokeStyle=selected===a[0]?'#fff':'#101820';c.lineWidth=selected===a[0]?3:1;c.stroke();c.fillStyle='#fff';c.font='bold 11px system-ui';c.textAlign='center';c.fillText(a[0],x,y-5)}
$('champions').replaceChildren();for(const a of f[5]){const owner=game.roster.find(x=>x.id===a[0]);const tr=document.createElement('tr');tr.className=selected===a[0]?'selected':'';tr.innerHTML=`<td class="${owner.team?'b':'a'}">${a[0]} ${owner.name}${a[5]?'':' (dead)'}</td><td>${Math.round(a[3])}/${Math.round(a[4])}</td><td>${a[6]}</td><td>${a[7]}</td>`;tr.tabIndex=0;tr.onclick=()=>{selected=a[0];render()};tr.onkeydown=e=>{if(e.key==='Enter')tr.onclick()};$('champions').append(tr)}
const chosen=f[5].find(a=>a[0]===selected);$('equipment').textContent=chosen?itemsText(chosen[8]):'Select a champion to inspect its equipment and route.';
$('captures').replaceChildren();const recent=game.engagements.filter(e=>e.round<=r).slice(-14).reverse();for(const e of recent){const tr=document.createElement('tr');const owners=e.capturers.map(id=>game.roster.find(c=>c.id===id));tr.innerHTML=`<td>${e.round}</td><td>${e.group}</td><td class="${owners[0].team?'b':'a'}">${owners.map(o=>o.name).join(' + ')}</td><td>${e.gemReward} gems · ${e.goldReward} gold</td>`;tr.tabIndex=0;tr.onclick=()=>jump(e.round+1);tr.onkeydown=x=>{if(x.key==='Enter')tr.onclick()};$('captures').append(tr)}
drawChart(r)}
function drawChart(round){const c=$('plot').getContext('2d');c.clearRect(0,0,700,220);const gold=$('metric').value==='gold',index=gold?3:1;const max=Math.max(100,...game.frames.flatMap(f=>[f[index],f[index+1]]));const left=50,top=20,w=625,h=170;c.font='12px system-ui';c.textAlign='right';for(let k=0;k<=4;k++){const y=top+h-k*h/4;c.strokeStyle='#344151';c.beginPath();c.moveTo(left,y);c.lineTo(left+w,y);c.stroke();c.fillStyle='#bac8d8';c.fillText(Math.round(max*k/4),left-7,y+4)}for(let team=0;team<2;team++){c.strokeStyle=colors[team];c.lineWidth=2;c.beginPath();game.frames.forEach((f,i)=>{let x=left+w*f[0]/game.round,y=top+h-h*f[index+team]/max;i?c.lineTo(x,y):c.moveTo(x,y)});c.stroke()}c.strokeStyle='#fff';let x=left+w*round/game.round;c.beginPath();c.moveTo(x,top);c.lineTo(x,top+h);c.stroke();c.fillStyle='#bac8d8';c.textAlign='left';c.fillText('Round 0',left,212);c.textAlign='right';c.fillText(game.round,left+w,212)}
mapSelect.onchange=choose;versions.onchange=choose;slider.oninput=render;$('metric').onchange=render;
$('play').onclick=()=>{if(timer){clearInterval(timer);timer=null;$('play').textContent='Play'}else{$('play').textContent='Pause';timer=setInterval(()=>{if(+slider.value>=+slider.max){$('play').click();return}slider.value=+slider.value+1;render()},100)}};choose();
</script></html>'''
html=html.replace('__DATA__',json.dumps(games,separators=(',',':')).replace('</','<\\/'))
(ROOT/'explorer.html').write_text(html)
print('Wrote',ROOT/'explorer.html',len(html),'bytes; games',len(games))
