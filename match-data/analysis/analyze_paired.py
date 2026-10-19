"""Compare native platform replays; preserve exact evidence and deduplicate inputs."""
from pathlib import Path
from collections import Counter, defaultdict
from bisect import bisect_left
import hashlib, json, statistics
from raw_metrics import analyze
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'paired-v1-v3'
NAMES=['Ryth','Vesper Vale','Vendetta','Cassi','Issac','Stellar','Prism','Marcella','Willow','Ren','Varg','Tavi']
FAMILIES=['Monster','Power','Durability','Treasure','Jungle','Home','Bruiser']
ITEMS=[f'{f} {s} {kind}' for f in FAMILIES for s in ['Strength','Focus','Health'] for kind in ['shard','emblem']]
def load(p): return json.loads(p.read_text())
def xy(p): return (p['x'],p['y'])
def groups_for(m):
    members=defaultdict(list)
    for c in m['camps']:members[c['group']].append(c)
    groups=[];lookup={}
    for group_id,cs in sorted(members.items()):
        i=len(groups);tiles=[(c['x'],c['y']) for c in cs]
        groups.append({'id':i,'engineGroup':group_id,'tiles':sorted(tiles),'types':dict(Counter(['Wolf','Elk','Gem','Gold','Monolith'][c['type']] for c in cs))})
        lookup.update({p:i for p in tiles})
    return groups,lookup

def process(p):
    s=load(p/'summary.json');turns=load(p/'turns.json');events=load(p/'events.json');rounds=load(p/'rounds.json')
    assert s['complete'] and not s['replayErrors']
    assert hashlib.sha256(Path(s['source']).read_bytes()).hexdigest()==s['sha256']
    raw=analyze(s,include_turns=True)
    native=defaultdict(list)
    for t in turns: native[t['id']].append(t)
    roster={c['id']:c for c in s['stats']}; original={c['id']:c for c in raw['champions']}
    for i,ts in native.items():
        assert len(ts)==original[i]['metrics']['turns'],(p,i)
        assert [t['round'] for t in ts]==[t['round'] for t in original[i]['turns']],(p,i,'round attribution')
    groups,lookup=groups_for(s['map']); rnums={i:[t['round'] for t in ts] for i,ts in native.items()}
    captures=[];deaths=[];submissions=[];score=[0,0]
    for e in events:
        if e.get('score'):
            for team in [0,1]:
                if e['score'][team]>score[team]:
                    submissions.append({'round':e['round'],'team':team,'id':e['actor']['index'] if e['actor']['kind']==1 else None,'gems':e['score'][team]-score[team]})
            score=e['score']
        for d in e.get('changes',[]):
            i=d['id']
            if d.get('alive') is False:
                deaths.append({'round':e['round'],'id':i,'team':roster[i]['team'],'gems':-d.get('gems',0),'actor':e['actor'],'kind':e['kind']})
            if e['phase']==7 and (d.get('gold',0)>0 or d.get('gems',0)>0):
                prev=bisect_left(rnums[i],e['round'])-1
                pos=xy(native[i][prev]['position']) if prev>=0 else None
                group=lookup.get(pos)
                assert group is not None,(p,e,pos,'capture location')
                captures.append({'round':e['round'],'id':i,'team':roster[i]['team'],'group':group,'gems':d.get('gems',0),'gold':d.get('gold',0)})
    # Spatial camp targeting is inferred from recorded target coordinates.
    # A capture participant and its rewards are directly observed.
    capture_groups=defaultdict(list)
    for c in captures:capture_groups[(c['round'],c['group'])].append(c)
    combat=defaultdict(list)
    for e in events:
        if e['actor']['kind']!=1 or e['phase']!=10:continue
        if e['kind']!=5 and not (e['kind']==6 and e.get('abilityType') in [2,3,4]):continue
        group=lookup.get(xy(e['to']))
        if group is None:continue
        actor=e['actor']['index']
        # Exclude confirmed attacks on champions standing on a camp tile.
        if any(d['id']!=actor and d.get('health',0)<0 for d in e.get('changes',[])):continue
        combat[group].append({'round':e['round'],'id':actor,'kind':e['kind']})
    engagements=[];last_capture=defaultdict(int)
    for (r,group),caps in sorted(capture_groups.items()):
        prior=last_capture[group];last_capture[group]=r
        strikes=[e for e in combat[group] if prior<e['round']<=r]
        counts=Counter(e['id'] for e in strikes)
        engagements.append({'round':r,'group':group,'capturers':[c['id'] for c in caps],
          'gemReward':sum(c['gems'] for c in caps),'goldReward':sum(c['gold'] for c in caps),
          'firstSpatialAttack':min((e['round'] for e in strikes),default=None),
          'spatialAttackCounts':dict(counts)})
    champion_results=[]
    for i,c in roster.items():
        ts=native[i];activity=Counter(); purchases=[];previtems=[0]*42;bags=[];bag=None;stall=[];current=[];prevkey=None
        for t,a in zip(ts,original[i]['turns']):
            acts=a['actions'];pos=xy(t['position']) if 'position' in t else None
            if not t['alive']: category='dead'
            elif t['channelType']: category={1:'recall_channel',2:'tribute_channel',3:'teleport_channel'}.get(t['channelType'],'other_channel')
            elif 'attack' in acts or 'cast' in acts: category='attack_or_cast'
            elif 'move' in acts: category='move_with_gems' if t['gems'] else 'move_without_gems'
            elif pos in lookup: category='on_camp_tile_without_action'
            else: category='other_without_move_attack_cast'
            activity[category]+=1
            if t['items']!=previtems:
                purchases.append({'round':t['round'],'gold':t['gold'],'health':t['health'],'strength':t['strength'],'focus':t['focus'],'items':{ITEMS[j]:n for j,n in enumerate(t['items']) if n}})
                previtems=t['items']
            if t['alive'] and t['gems']:
                if bag is None: bag={'start':t['round'],'end':t['round'],'maxGems':t['gems']}
                bag['end']=t['round'];bag['maxGems']=max(bag['maxGems'],t['gems'])
            elif bag:
                bag['duration']=bag['end']-bag['start']+1;bags.append(bag);bag=None
            key=(pos,t['gems'],t['health']) if t['alive'] and t['gems'] and not t['channelType'] else None
            if key!=prevkey:
                if len(current)>=15:stall.append({'start':current[0]['round'],'end':current[-1]['round'],'turns':len(current),'position':current[0]['position'],'gems':current[0]['gems']})
                current=[]
            if key is not None:current.append(t)
            prevkey=key
        if len(current)>=15:stall.append({'start':current[0]['round'],'end':current[-1]['round'],'turns':len(current),'position':current[0]['position'],'gems':current[0]['gems']})
        if bag:bag['duration']=bag['end']-bag['start']+1;bags.append(bag)
        champion_results.append({**c,'metrics':original[i]['metrics'],'activity':dict(activity),'equipmentProgression':purchases,'captures':[x for x in captures if x['id']==i],'submissions':[x for x in submissions if x['id']==i],'bagIntervals':bags,'stationaryCarriers':stall})
    teams=[]
    for team in [0,1]:
        cs=[c for c in champion_results if c['team']==team]
        totals={k:sum(c[k] for c in cs) for k in ['kills','deaths','earnedGold','spentGold','collectedGems','submittedGems','gems']}
        totals['lostGems']=totals['collectedGems']-totals['submittedGems']-totals['gems']
        assert totals['lostGems']==sum(d['gems'] for d in deaths if d['team']==team)
        totals['bodies']=len(cs)
        totals['actions']={k:sum(c['metrics'].get(k,0) for c in cs) for k in ['turns','fuel_exhaustions','move','attack_camp','attack_champion','cast','recall','tribute','buy_consumable','use_consumable_0','use_consumable_1','use_consumable_2','use_consumable_3']}
        totals['activity']=dict(sum((Counter(c['activity']) for c in cs),Counter()))
        totals['firstCapture']=min((c['round'] for c in captures if c['team']==team),default=None)
        totals['firstTribute']=min((c['round'] for c in submissions if c['team']==team),default=None)
        totals['meanBagDuration']=statistics.mean([b['duration'] for c in cs for b in c['bagIntervals']]) if any(c['bagIntervals'] for c in cs) else 0
        totals['meanTributeSize']=statistics.mean([x['gems'] for x in submissions if x['team']==team]) if any(x['team']==team for x in submissions) else 0
        teams.append(totals)
    checkpoints=[]
    for n in [50,100,150,200,300,400,500,750,1000,1500,2000]:
        if n>s['round']:continue
        states=[r for r in rounds if r['round']<=n]
        if not states:continue
        r=states[-1];checkpoint={'round':n,'score':r['score'],'teams':[]}
        for team in [0,1]:
            selected=[]
            for i,c in roster.items():
                if c['team']!=team:continue
                at=bisect_left(rnums[i],n)
                if at<len(native[i]) and native[i][at]['round']==n: pass
                else:at-=1
                if at>=0:selected.append(native[i][at])
            checkpoint['teams'].append({'earnedGold':sum(t['earnedGold'] for t in selected),'unspentGold':sum(t['gold'] for t in selected),'gems':sum(t['gems'] for t in selected),'strength':sum(t['strength'] for t in selected),'focus':sum(t['focus'] for t in selected),'deaths':sum(d['round']<=n and d['team']==team for d in deaths)})
        checkpoints.append(checkpoint)
    result={'version':p.parent.parent.name,'series':p.parent.name,'game':p.name,'source':s['source'],'sha256':s['sha256'],'mapHash':s['map']['sha256'],'width':s['map']['width'],'height':s['map']['height'],'round':s['round'],'score':s['score'],'outcome':s['outcome'],'drafts':s['drafts'],'teams':teams,'checkpoints':checkpoints,'champions':champion_results,'groups':groups,'engagements':engagements,'deaths':deaths,'validated':True}
    (p/'strategy.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

def main():
    games=[]
    for v in ['v1','v3']:
        for p in sorted((OUT/v).glob('team-*/*/summary.json')):
            g=process(p.parent);games.append(g)
    unique=[];seen=set()
    for g in games:
        key=(g['version'],g['sha256'])
        if key not in seen:unique.append(g);seen.add(key)
    maps=defaultdict(lambda:defaultdict(list))
    for g in unique: maps[g['mapHash']][g['version']].append(g)
    pairs=[]
    for h,versions in sorted(maps.items()):
        g=next(iter(versions.values()))[0]
        pairs.append({'mapHash':h,'size':f"{g['width']}x{g['height']}",'versions':{v:[{'series':x['series'],'game':x['game'],'score':x['score'],'round':x['round'],'deaths':x['teams'][0]['deaths'],'gold':x['teams'][0]['earnedGold'],'opponentGold':x['teams'][1]['earnedGold'],'fuel':x['teams'][0]['actions']['fuel_exhaustions']} for x in xs] for v,xs in versions.items()}})
    (OUT/'comparison.json').write_text(json.dumps({'games':games,'uniqueGames':len(unique),'pairs':pairs},indent=2)+'\n')
    print('games',len(games),'unique input replays',len(unique),'maps',len(maps))
    for v in ['v1','v3']:
        allgames=[g for g in games if g['version']==v];us=[g for g in unique if g['version']==v]
        print(v,'wins',sum(g['score'][0]>g['score'][1] for g in allgames),'/',len(allgames),'unique wins',sum(g['score'][0]>g['score'][1] for g in us),'/',len(us),'fuel',sum(g['teams'][0]['actions']['fuel_exhaustions'] for g in us))
    for p in pairs:print(p['mapHash'][:8],p['size'],p['versions'])
if __name__=='__main__':main()
