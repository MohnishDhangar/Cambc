#!/usr/bin/env python3
"""Exact recorded decision patterns in selected high-value CAMBC v4 replays."""
import json,sys,collections,statistics
from pathlib import Path
from bisect import bisect_right
root=Path(sys.argv[1] if len(sys.argv)>1 else 'results/v4-tactics')
dest=Path(sys.argv[2] if len(sys.argv)>2 else 'match-data/analysis/v4-study/TACTICS.md')
names=['Monster','Power','Durability','Treasure','Jungle','Home','Bruiser']
itemnames=[f'{family} {stat} {kind}' for family in names for stat in ['Strength','Focus','Health'] for kind in ['shard','emblem']]
files=sorted(root.rglob('summary.json'))
result=[]
for p in files:
    d=p.parent;summary=json.loads(p.read_text());turns=json.loads((d/'turns.json').read_text());events=json.loads((d/'events.json').read_text())
    roster={c['id']:c for c in summary['stats']};cidteam={i:c['team'] for i,c in roster.items()}
    tby=collections.defaultdict(list)
    for t in turns:tby[t['id']].append(t)
    upgrades=[collections.Counter(),collections.Counter()]
    upgradesearly=[collections.Counter(),collections.Counter()]
    purchase_examples=[[],[]]
    visits=[0,0];visits_early=[0,0]
    victims=[collections.Counter(),collections.Counter()]
    focus=[collections.defaultdict(set),collections.defaultdict(set)]
    deaths=[[],[]];round_kills=[[],[]]
    hits=[0,0];damage=[0,0]
    spawn=summary['map']['spawnA']
    x0=(spawn['minX']+spawn['maxX'])/2;y0=(spawn['minY']+spawn['maxY'])/2
    perchamp={}
    for c in summary['stats']:
        t=c['team'];hist=tby[c['id']];prior=[0]*42;u=[]
        near=0
        for turn in hist:
            curr=turn.get('items',[]) or []
            if len(curr)==42:
                for idx,(a,b) in enumerate(zip(prior,curr)):
                    if b>a:
                        upgrades[t][itemnames[idx]]+=(b-a)
                        if turn['round']<=150:upgradesearly[t][itemnames[idx]]+=(b-a)
                        u.append((turn['round'],itemnames[idx],b-a))
                prior=curr
            pos=turn.get('position')
            if t==1 and pos and turn['round']<=250 and turn.get('alive'):
                if max(abs(pos['x']-x0),abs(pos['y']-y0))<=9: near+=1
        perchamp[c['name']+"#"+str(c['id'])]={'team':t,'purchases':u[:10],'turnsNearEnemySpawnUnder250':near,'gemScore':c['submittedGems'],'kills':c['kills'],'deaths':c['deaths']}
        visits[t]+=near
    for e in events:
        aid=e['actor'].get('index') if e['actor'].get('kind')==1 else None
        attacker=cidteam.get(aid)
        for delta in e.get('changes',[]):
            victim_id=delta['id'];victim_team=cidteam.get(victim_id)
            if victim_team is None:continue
            if delta.get('alive') is False:
                deaths[victim_team].append((e['round'],victim_id,roster[victim_id]['name'],aid))
                if attacker is not None and attacker!=victim_team: round_kills[attacker].append(e['round'])
            if attacker is not None and attacker != victim_team and delta.get('health',0)<0:
                hits[attacker]+=1;damage[attacker]-=delta['health']
                victims[attacker][roster[victim_id]['name']]+=1
                focus[attacker][(e['round'],victim_id)].add(aid)
    same_round_focus=[sum(len(ids)>=2 for ids in f.values()) for f in focus]
    initial=summary['map']
    result.append(dict(path=str(d.relative_to(root)),score=summary['score'],round=summary['round'],
      size=f"{initial['width']}x{initial['height']}",
      earlyUpgrades=[c.most_common(8) for c in upgradesearly],
      totalUpgrades=[c.most_common(8) for c in upgrades],
      topEnemyChampionDamage=[c.most_common(5) for c in victims],hits=hits,damage=damage,
      alliedMultiAttackRounds=same_round_focus,
      opponentTurnsNearOurSpawnBy250=visits[1],
      killings=[len(x) for x in round_kills],firstKill=[min(x) if x else None for x in round_kills],
      deathRounds=[a[:25] for a in deaths],byChampion=perchamp))
dest.parent.mkdir(parents=True,exist_ok=True)
out=['# Opponent micro-tactics — inspected replay case studies','','Each case below uses full 0.0.3 replay actions, turn states and champion statistics. Unlike the quantitative screening, these case studies inspect purchasing and positioning at champion-turn resolution.','',
'> The match data are *pre–Week 2*. The metrics describe behavior, not evidence of a player’s intention or the success of an unobserved counterfactual.','']
for g in result:
    out+=['## '+g['path'],f"- Map: {g['size']}; final score Bot1–Opponent: {g['score']}; length: {g['round']} rounds",
          f"- Recorded attacks reducing opponent champion HP: Bot1 {g['hits'][0]} versus opponent {g['hits'][1]}; champion damage Bot1 {round(g['damage'][0])} versus opponent {round(g['damage'][1])}.",
          f"- Successful champion kills (credited action window): Bot1 {g['killings'][0]} versus opponent {g['killings'][1]}; first successful kill rounds {g['firstKill']}.",
          f"- Times in the opening 250 rounds that an opponent champion was recorded within nine Chebyshev tiles of Bot1 spawn: {g['opponentTurnsNearOurSpawnBy250']} (counts champion-turns, not distinct rounds).",
          f"- Multi-attacker same-round focus opportunities against an enemy champion: Bot1 {g['alliedMultiAttackRounds'][0]}, opponent {g['alliedMultiAttackRounds'][1]}.",
          '', '**Top item additions before round 150**',
          '| Side | Purchased shards (recorded count increases) |','|---|---|',
          '| Bot1 | '+(', '.join(f'{a} ×{b}' for a,b in g['earlyUpgrades'][0]) or 'No observations')+' |',
          '| Opponent | '+(', '.join(f'{a} ×{b}' for a,b in g['earlyUpgrades'][1]) or 'No observations')+' |',
          '','**Champion contributions and initial item sequences**','',
          '| Side | Champion | Tributed gems | Kills / Deaths | First item additions (round, item) |','|---|---|---:|---|---|']
    for key,c in sorted(g['byChampion'].items(),key=lambda x:(x[1]['team'],x[0])):
        item='; '.join(f"{a} {b}" for a,b,num in c['purchases'][:5]) or 'None observed'
        out.append(f"| {'Bot1' if c['team']==0 else 'Opp'} | {key} | {c['gemScore']} | {c['kills']}/{c['deaths']} | {item} |")
    out.append('')
out+=['## Methodology and limitations','','- “Focus opportunity” counts two *different* allied actors dealing damage to the same champion in the same round; it excludes knock-on splash or shield damage when no distinct actor is recorded.','- Early item additions are inferred from item-array changes in recorded champion turns; they can miss purchases on turns not represented by the extracted timeline.','- Proximity to Bot1 spawn does not prove intentional invasion; it can reflect normal farming or objective placement. Compare with map geometry and several matches before treating it as an invasion policy.','- This report investigates selected extreme cases, not a random sample of opponents. Use the separate 245-game metrics to evaluate prevalence.','']
dest.write_text('\n'.join(out))
(dest.with_suffix('.json')).write_text(json.dumps(result,indent=2))
print('TACTICAL_CASES',len(result),'PUBLISHED',dest)
for g in result:print(g['path'],g['score'],'kills',g['killings'],'damage',list(map(round,g['damage'])),'nearspawn',g['opponentTurnsNearOurSpawnBy250'])
