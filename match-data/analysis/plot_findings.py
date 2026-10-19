"""Write a standalone SVG illustrating the two clearest failures."""
from pathlib import Path
from collections import deque
from html import escape
import json
import subprocess
import shutil

ROOT = Path(__file__).resolve().parent
p = ROOT / 'native-0.0.3/match-1- team-Forged-Tokens/02'
summary = json.loads((p/'summary.json').read_text())
events = json.loads((p/'events.json').read_text())
parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="1120" height="740" viewBox="0 0 1120 740">', '<rect width="1120" height="740" fill="#f8fafc"/>', '<style>text{font-family:Arial,sans-serif;fill:#243345}.small{font-size:13px}.label{font-size:16px}.title{font-size:22px;font-weight:bold}</style>']

def text(x,y,s,cls='label',extra=''):
    parts.append(f'<text x="{x}" y="{y}" class="{cls}" {extra}>{escape(s)}</text>')

def rect(x,y,w,h,color,opacity=1):
    parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{color}" opacity="{opacity}"/>')

def line(points,color,width=2,dash=''):
    coords=' '.join(f'{x:.1f},{y:.1f}' for x,y in points)
    parts.append(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="{width}" stroke-dasharray="{dash}"/>')

text(36,43,'Bot1: two actionable failures in the lobby games','title')
text(45,87,'Rows: gems stop reaching the altar','title')
x0,y0,w,h=75,130,435,280
sx=lambda r:x0+r/429*w
sy=lambda g:y0+h-g/1100*h
rect(sx(189),y0,sx(303)-sx(189),h,'#187899',.08)
rect(sx(233),y0,sx(303)-sx(233),h,'#187899',.08)
for n in range(0,1100,200):
    y=sy(n);line([(x0,y),(x0+w,y)],'#d9e1e8',1);text(30,y+5,str(n),'small')
for n in range(0,450,100):text(sx(n)-8,y0+h+22,str(n),'small')
score=[0,0];paths=[[(sx(0),sy(0))],[(sx(0),sy(0))]]
for e in events:
    if 'score' not in e:continue
    for team in [0,1]:
        paths[team].extend([(sx(e['round']),sy(score[team])),(sx(e['round']),sy(e['score'][team]))])
    score=e['score']
line(paths[0],'#187899',3);line(paths[1],'#cc5a38',3)
text(80,115,'Bot1: 462','label',extra='style="fill:#187899"')
text(255,115,'Forged Tokens: 1,056','label',extra='style="fill:#cc5a38"')
text(245,200,'Varg: 115 rounds stuck','small');text(245,221,'Vendetta: 71 rounds stuck','small')
text(235,455,'Round','small')
text(45,482,'Each carrier held 66 gems near (22,2) / (22,3).','small')
text(45,503,'Shading marks their overlapping stalls.','small')
text(45,524,'Verified with the matching official engine 0.0.3.','small')
text(45,545,'Both carriers remain alive with no channel running.','small')

text(610,87,'A safe detour exists, but the bot rejects it','title')
m=summary['map'];walls=set(map(tuple,m['terrain']['wall']));altars=set(map(tuple,m['terrain']['altar']))
zone={(x,y) for x in range(15,22) for y in range(0,7)}
scale=19
xy=lambda x,y:(635+(x-10)*scale,470-y*scale)
for x in range(10,27):
    for y in range(0,19):
        xx,yy=xy(x,y)
        rect(xx-scale/2,yy-scale/2,scale,scale,'#fff')
for x,y in walls:
    if 10<=x<=26 and 0<=y<=18:
        xx,yy=xy(x,y);rect(xx-scale/2,yy-scale/2,scale,scale,'#344254')
for x,y in zone:
    xx,yy=xy(x,y);rect(xx-scale/2,yy-scale/2,scale,scale,'#cc5a38',.2)
start=(22,3);goal=(15,15);q=deque([start]);parent={start:None};blocked=walls|zone|altars
while q:
    here=q.popleft()
    if here==goal:break
    for dx in [-1,0,1]:
        for dy in [-1,0,1]:
            n=here[0]+dx,here[1]+dy
            if 0<=n[0]<50 and 0<=n[1]<50 and n not in blocked and n not in parent:
                parent[n]=here;q.append(n)
route=[];current=goal
while current is not None:route.append(xy(*current));current=parent[current]
line(route[::-1],'#268450',3,'5 4')
for pos,label,color in [((18,3),'Wolf','#cc5a38'),((22,3),'Carrier','#187899'),((15,16),'Altar','#997811')]:
    x,y=xy(*pos);parts.append(f'<circle cx="{x}" cy="{y}" r="6" fill="{color}"/>');text(x+9,y-9,label,'small')
text(635,503,'Red: modeled danger near a damaged wolf.','small')
text(635,524,'Green: possible detour around that danger.','small')
text(635,545,'Illustration uses one wolf’s danger zone.','small')

rect(35,580,1050,118,'#eaf0f5')
text(55,612,'The other decisive failure: no monolith plan','title')
text(55,640,'lll game 2 lasted 1,931 rounds on a map whose only camp gem source was monoliths.','label')
text(55,667,'Recorded tribute starts: Bot1 = 0; opponent = 5. No replay simulation is needed for this count.','label')
text(36,725,'All 15 original replays completed under engine 0.0.3 with zero replay errors. Original files remain unchanged.','small')
parts.append('</svg>')
svg=ROOT/'findings.svg';svg.write_text('\n'.join(parts)+'\n')
if shutil.which('rsvg-convert'):
    subprocess.run(['rsvg-convert',str(svg),'-o',str(ROOT/'findings.png')],check=True)
