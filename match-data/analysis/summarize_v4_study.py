#!/usr/bin/env python3
"""CAMBC v4 study: traceable quantitative opponent analysis from native 0.0.3 replays."""
from __future__ import annotations
import json,sys,statistics,collections,hashlib,math
from pathlib import Path

ROOT=Path(sys.argv[1] if len(sys.argv)>1 else 'results/v4-native')
OUT=Path(sys.argv[2] if len(sys.argv)>2 else 'match-data/analysis/v4-study')
OUT.mkdir(parents=True,exist_ok=True)
data=json.loads((ROOT/'index.json').read_text())
def med(v): return statistics.median(v) if v else 0
def avg(v): return statistics.mean(v) if v else 0
def pct(n,d): return (100*n/d if d else 0)
def nfmt(n): return f"{n:,.1f}" if isinstance(n,float) and n!=int(n) else f"{int(n):,}"
def rnd(n): return round(float(n),2)
def snap_at(rounds,at):
    for v in reversed(rounds):
        if v['round']<=at: return v['score']
    return [0,0]
def summarize_game(record):
    folder=ROOT/record['path']
    summary=json.loads((folder/'summary.json').read_text())
    turns=json.loads((folder/'turns.json').read_text())
    events=json.loads((folder/'events.json').read_text())
    rounds=json.loads((folder/'rounds.json').read_text())
    stats=summary['stats']
    teams=[[],[]]
    for ch in stats: teams[ch['team']].append(ch)
    if len(teams[0])<3 or len(teams[1])<3: raise ValueError(f"Unexpected roster at {record['path']}")
    if [sum(c['submittedGems'] for c in v) for v in teams]!=summary['score']:
        raise ValueError(f"Team gem score mismatch {record['path']}")
    cid_team={c['id']:c['team'] for c in stats}
    by_ch=collections.defaultdict(list)
    for t in turns: by_ch[t['id']].append(t)
    eacts=[collections.Counter(),collections.Counter()]
    enemy_hits=[0,0]; total_enemy_damage=[0,0]; gem_loss_death=[0,0]; deaths_from_events=[0,0]
    captures=[[],[]]; first_score=[None,None]; tribute_sizes=[[],[]]
    lastscore=[0,0]
    for e in events:
        actor=e.get('actor',{})
        aid=actor.get('index') if actor.get('kind')==1 else None
        t=cid_team.get(aid)
        if t is not None:
            eacts[t]['step_'+str(e.get('kind'))]+=1
            if e.get('kind')==5: eacts[t]['basic_attack_steps']+=1
            if e.get('kind')==6: eacts[t]['ability_steps']+=1
        score=e.get('score')
        if score:
            for team in (0,1):
                inc=score[team]-lastscore[team]
                if inc>0:
                    tribute_sizes[team].append(inc)
                    if first_score[team] is None: first_score[team]=e['round']
            lastscore=list(score)
        for d in e.get('changes',[]):
            tid=cid_team.get(d['id'])
            if tid is None: continue
            if d.get('alive') is False:
                deaths_from_events[tid]+=1
                if d.get('gems',0)<0: gem_loss_death[tid]-=d['gems']
            if e.get('phase')==7 and (d.get('gems',0)>0 or d.get('gold',0)>0):
                captures[tid].append(dict(round=e['round'],gems=d.get('gems',0),gold=d.get('gold',0),id=d['id']))
            if t is not None and t!=tid and d.get('health',0)<0:
                enemy_hits[t]+=1; total_enemy_damage[t]-=d['health']
    team_d={}
    for t in (0,1):
        v=teams[t]
        sampled=collections.defaultdict(list)
        behavior=collections.Counter()
        longest_stall=0; stalls15=[]; bag_lengths=[]; first_pickup=None
        collected=sum(c['collectedGems'] for c in v)
        banked=sum(c['submittedGems'] for c in v)
        spent=sum(c['spentGold'] for c in v)
        for c in v:
            hist=by_ch[c['id']]
            prev=None; startbag=None; run=0; runstart=None; beststall=0
            for turn in hist:
                sampled[turn['round']].append(turn)
                pos=turn.get('position') or {}
                key=(pos.get('x'),pos.get('y'),turn.get('gems'),round(turn.get('health',0)))
                bag=turn.get('gems',0)
                if bag>0 and first_pickup is None: first_pickup=turn['round']
                if bag>0:
                    behavior['turns_carried']+=1
                    if startbag is None: startbag=turn['round']
                elif startbag is not None:
                    bag_lengths.append(turn['round']-startbag); startbag=None
                if turn.get('alive') is False: behavior['dead_turns']+=1
                if turn.get('channelType'): behavior['channel_turns']+=1
                if prev and key==prev and bag>0 and turn.get('alive') and not turn.get('channelType'):
                    run+=1
                else:
                    if run>=15: stalls15.append(dict(id=c['id'],round=runstart,length=run,position=pos,gems=bag))
                    run=1;runstart=turn['round']
                beststall=max(beststall,run if bag else 0)
                prev=key
                behavior['champion_turns']+=1
            if run>=15: stalls15.append(dict(id=c['id'],round=runstart,length=run,gems=hist[-1].get('gems')))
            if startbag is not None and hist: bag_lengths.append(hist[-1]['round']-startbag+1)
            longest_stall=max(longest_stall,beststall)
        lifetime_gold=sum(c['earnedGold'] for c in v)
        cp={}
        for at in (50,100,150,200,300,400,500,750,1000,1500):
            if at>summary['round']: continue
            score=snap_at(rounds,at)[t]
            gold_at=0
            for c in v:
                hist=by_ch[c['id']]
                entry=next((x for x in reversed(hist) if x['round']<=at),None)
                if entry: gold_at+=entry.get('earnedGold',0)
            cp[str(at)]={'score':score,'gold':gold_at}
        team_d[str(t)]=dict(score=banked, gold=lifetime_gold, spentGold=spent,
            collected=collected, retained=sum(c['gems'] for c in v),
            lost=collected-banked-sum(c['gems'] for c in v),kills=sum(c['kills'] for c in v),
            deaths=sum(c['deaths'] for c in v),champions=[c['name'] for c in v],
            firstCapture=min((x['round'] for x in captures[t]),default=None),
            firstTribute=first_score[t],firstPickup=first_pickup,
            tributeSizes=tribute_sizes[t],captures=captures[t],checkpoint=cp,
            combatHits=enemy_hits[t],damageVsChampions=rnd(total_enemy_damage[t]),
            recordedAttacks=eacts[t]['basic_attack_steps'],recordedCasts=eacts[t]['ability_steps'],
            deathGemLoss=gem_loss_death[t],turnsCarried=behavior['turns_carried'],
            deadTurns=behavior['dead_turns'],channelTurns=behavior['channel_turns'],
            longestStationaryCarrier=longest_stall,carrierStalls15=stalls15,
            meanCarryDuration=rnd(avg(bag_lengths)),meanTributeSize=rnd(avg(tribute_sizes[t])),
            bankRatio=rnd(banked/collected) if collected else 0)
    teamA=team_d['0'];teamB=team_d['1']
    # Team-A stdout was verified for representative replay folders as Bot1 v4.
    label=record['category'].split('/')[-1]
    a_won=summary['score'][0]>summary['score'][1]
    classification_correct= (label=='wins')==a_won
    return dict(path=record['path'],group=record['group'],
      category=record['category'],sha256=record['sha256'],engine=record['engine']['version'] if 'engine' in record else summary['engine']['version'],
      mapHash=record['mapHash'],mapSize=record['mapSize'],round=summary['round'],outcome=summary['outcome'],
      score=summary['score'],teamA=teamA,teamB=teamB,classifiedCorrectly=classification_correct)

games=[];failures=[]
for rec in data['summaries']:
    try: games.append(summarize_game(rec))
    except Exception as err: failures.append(dict(path=rec['path'],error=str(err)))
unique={}; duplicate=[]
for g in games:
    if g['sha256'] in unique:
        duplicate.append(dict(path=g['path'],original=unique[g['sha256']]['path']))
    else:unique[g['sha256']]=g
unique_games=list(unique.values())
cats=collections.defaultdict(list)
groups=collections.defaultdict(list)
for g in unique_games: cats[g['category']].append(g);groups[(g['category'],g['group'])].append(g)
summary={}
for cat,gs in sorted(cats.items()):
    summary[cat]=dict(games=len(gs),groups=len({x['group'] for x in gs}),
      medianRound=med([x['round'] for x in gs]),
      medianA=med([x['teamA']['score'] for x in gs]),
      medianB=med([x['teamB']['score'] for x in gs]),
      medianGoldA=med([x['teamA']['gold'] for x in gs]),
      medianGoldB=med([x['teamB']['gold'] for x in gs]),
      medianFirstTributeA=med([x['teamA']['firstTribute'] for x in gs if x['teamA']['firstTribute'] is not None]),
      medianFirstTributeB=med([x['teamB']['firstTribute'] for x in gs if x['teamB']['firstTribute'] is not None]),
      medianFirstCaptureA=med([x['teamA']['firstCapture'] for x in gs if x['teamA']['firstCapture'] is not None]),
      medianFirstCaptureB=med([x['teamB']['firstCapture'] for x in gs if x['teamB']['firstCapture'] is not None]),
      medDeathsA=med([x['teamA']['deaths'] for x in gs]),
      medDeathsB=med([x['teamB']['deaths'] for x in gs]),
      medianLostA=med([x['teamA']['lost'] for x in gs]),
      medianLostB=med([x['teamB']['lost'] for x in gs]),
      medianGap100=med([x['teamB']['checkpoint'].get('100',{}).get('score',0)-x['teamA']['checkpoint'].get('100',{}).get('score',0) for x in gs]),
      medianGap200=med([x['teamB']['checkpoint'].get('200',{}).get('score',0)-x['teamA']['checkpoint'].get('200',{}).get('score',0) for x in gs]),
      medianGap400=med([x['teamB']['checkpoint'].get('400',{}).get('score',0)-x['teamA']['checkpoint'].get('400',{}).get('score',0) for x in gs if x['round']>=400]),
      avgCapturesA=rnd(avg([len(x['teamA']['captures']) for x in gs])),
      avgCapturesB=rnd(avg([len(x['teamB']['captures']) for x in gs])),
      stationaryCarrierGamesA=sum(x['teamA']['longestStationaryCarrier']>=15 for x in gs),
      stationaryCarrierGamesB=sum(x['teamB']['longestStationaryCarrier']>=15 for x in gs),
      medianAttacksA=med([x['teamA']['recordedAttacks'] for x in gs]),
      medianAttacksB=med([x['teamB']['recordedAttacks'] for x in gs]),
      medianCastsA=med([x['teamA']['recordedCasts'] for x in gs]),
      medianCastsB=med([x['teamB']['recordedCasts'] for x in gs]))
roster=collections.defaultdict(collections.Counter)
for cat,gs in cats.items():
    for g in gs:
        for side in ('teamA','teamB'):
            roster[(cat,side)].update(g[side]['champions'])
profiles=[]
for (cat,group),gs in sorted(groups.items()):
    p={'category':cat,'group':group,'games':len(gs),
       'medianRound':med([g['round'] for g in gs]),
       'medianScoreUs':med([g['teamA']['score'] for g in gs]),
       'medianScoreOpp':med([g['teamB']['score'] for g in gs]),
       'medianGoldUs':med([g['teamA']['gold'] for g in gs]),
       'medianGoldOpp':med([g['teamB']['gold'] for g in gs]),
       'oppPicks':dict(collections.Counter(n for g in gs for n in g['teamB']['champions'])),
       'avgOpponentCaptures':rnd(avg([len(g['teamB']['captures']) for g in gs])),
       'avgOpponentDeaths':rnd(avg([g['teamB']['deaths'] for g in gs])),
       'avgOpponentAttacks':rnd(avg([g['teamB']['recordedAttacks'] for g in gs])),
       'medianFirstTribute':med([g['teamB']['firstTribute'] for g in gs if g['teamB']['firstTribute'] is not None]),
       'maps':collections.Counter(g['mapSize'] for g in gs)}
    p['maps']=dict(p['maps'])
    profiles.append(p)
# Evidence examples with exact match path and scores, safe to inspect later.
high=cats.get('higher-elo/losses',[])
def evidence(items,key,limit=5,reverse=True):
    return [{'path':g['path'],'round':g['round'],'score':g['score'],
             'ourValue':g['teamA'].get(key),'enemyValue':g['teamB'].get(key)}
             for g in sorted(items,key=lambda g:g['teamB'].get(key,0)-g['teamA'].get(key,0),reverse=reverse)[:limit]]
notable={'high_gold_gaps':evidence(high,'gold'),
         'high_capture_gaps':evidence(high,'captures',limit=0) if False else sorted(
           [{'path':g['path'],'ourCaptures':len(g['teamA']['captures']),'opponentCaptures':len(g['teamB']['captures']),'score':g['score']} for g in high],
           key=lambda x:x['opponentCaptures']-x['ourCaptures'],reverse=True)[:5],
         'high_death_gaps':evidence(high,'deaths'),
         'high_early_score_gaps':[{'path':g['path'],'at':200,'us':g['teamA']['checkpoint'].get('200',{}).get('score'),
           'opp':g['teamB']['checkpoint'].get('200',{}).get('score')} for g in
           sorted(high,key=lambda g:g['teamB']['checkpoint'].get('200',{}).get('score',0)-g['teamA']['checkpoint'].get('200',{}).get('score',0),reverse=True)[:6]],
         'bank_stalls':sorted([{'path':g['path'],'turns':g['teamA']['longestStationaryCarrier'],'score':g['score']}
          for g in unique_games if g['teamA']['longestStationaryCarrier']>=15],key=lambda x:-x['turns'])[:12]}
reportdata={'totalPaths':data['files'],'decoded':data['processed'],'decodeFailures':data['failures'],
'processed':len(games),'analysisFailures':failures,'unique':len(unique_games),'duplicates':duplicate,
'mislabeled':[g['path'] for g in games if not g['classifiedCorrectly']],
'byCategory':summary,'rosters':{f'{k[0]}:{k[1]}':dict(v) for k,v in roster.items()},
'opponentGroups':profiles,'notableMatches':notable,'games':unique_games}
(OUT/'metrics.json').write_text(json.dumps(reportdata,indent=2)+'\n')
lines=[
'# CAMBC Bot1 v4 — Opponent Replay Study',
'',
'> **Engine:** archived CAMBC 0.0.3 (pre–Week 2 balance). Generated from native replay records. This report is observational, not a causal test of proposed strategies.',
'',
'## Data quality',
f"- Folders found: **{data['files']}**. Native decoding: **{data['processed']}**. Analysis: **{len(games)}**. Distinct replay SHA-256 values: **{len(unique_games)}**.",
f"- Decode failures: **{len(data['failures'])}**. Metric extraction failures: **{len(failures)}**. Duplicate replays: **{len(duplicate)}**. Folder outcome mismatches: **{sum(not g['classifiedCorrectly'] for g in games)}**.",
'- Team A is assumed to be Bot1 v4 based on verified repository stdout samples; verify all stdout if applying this report beyond exploratory use.',
'- The categories are a selected set of wins/losses, not random samples. Do not interpret category win rates as an Elo estimate.',
'',
'## Outcome and efficiency by replay category',
'',
'| Category | Unique games | Median score Bot1–Opp | Median gold Bot1–Opp | Median first tribute Bot1–Opp | Median deaths Bot1–Opp | Median captures Bot1–Opp |',
'|---|---:|---|---|---|---|---|'
]
for cat,v in sorted(summary.items()):
    lines.append(f"| {cat} | {v['games']} | {nfmt(v['medianA'])}–{nfmt(v['medianB'])} | {nfmt(v['medianGoldA'])}–{nfmt(v['medianGoldB'])} | {nfmt(v['medianFirstTributeA'])}–{nfmt(v['medianFirstTributeB'])} | {nfmt(v['medDeathsA'])}–{nfmt(v['medDeathsB'])} | {nfmt(v['avgCapturesA'])}–{nfmt(v['avgCapturesB'])} |")
lines+=['','## Early advantage (opponent minus Bot1 score)','',
'| Category | Median advantage by round 100 | By round 200 | By round 400 (games lasting ≥400) |',
'|---|---:|---:|---:|']
for cat,v in sorted(summary.items()):
    lines.append(f"| {cat} | {nfmt(v['medianGap100'])} | {nfmt(v['medianGap200'])} | {nfmt(v['medianGap400'])} |")
lines+=['','## Repeated opponent mechanisms — observations to test','',
'The following patterns are **hypotheses** supported by recorded differences in resources or timing. They do not prove a particular opponent decision policy. First prioritize replay-level reconstruction where the effect size is large.',
'',
'1. **Opening tempo and first-tribute lead.** Compare first reward pickup, first capture, first tribute and score checkpoints. A large lead before round 200 suggests a draft, route, camp-selection or upgrade difference rather than late-match PvP.',
'2. **Economic throughput.** Compare gold earned and capture counts separately from gems secured. Faster gold accumulation suggests efficient farm selection and better upgrades; without item chronology this is not evidence of a specific shard purchase policy.',
'3. **Resource securing versus risk-taking.** Compare captured/collected gems, bank ratio, gem loss on deaths, and stationary carrying episodes. Contested altar losses may be due to navigation or enemy lock timing; quantify before assuming a tactic.',
'4. **Pressure versus passive farming.** Compare opponent champion damage and attacks, but do not assume attacks are on champions without inspecting target-specific records. Champion kills now pay more gold under Week 2.',
'5. **Draft specialization.** Compare opponent champion compositions within a map hash and opponent group, rather than applying one universal roster. Composition frequency in selected elite losses alone does not prove the champions caused victory.',
'',
'## Opponent champion pick frequency',
'']
for cat in sorted(cats):
    lines += [f'### {cat}', '', '| Champion | Bot1 appearances | Opponent appearances |','|---|---:|---:|']
    names=sorted(set(roster[(cat,'teamA')])|set(roster[(cat,'teamB')]),key=lambda n:-roster[(cat,'teamB')][n])
    for name in names: lines.append(f"| {name} | {roster[(cat,'teamA')][name]} | {roster[(cat,'teamB')][name]} |")
    lines.append('')
lines+=['## High-Elo opponent profiles (aggregated over each five-game group)','','| Group | Median score Bot1–Opp | Opp median gold | Opp median first tribute | Opp avg captures | Opp roster frequency |','|---|---|---:|---:|---:|---|']
for g in profiles:
    if g['category']!='higher-elo/losses':continue
    picks=', '.join(f'{k}({v})' for k,v in sorted(g['oppPicks'].items(),key=lambda z:-z[1])[:5])
    lines.append(f"| {g['group']} | {nfmt(g['medianScoreUs'])}–{nfmt(g['medianScoreOpp'])} | {nfmt(g['medianGoldOpp'])} | {nfmt(g['medianFirstTribute'])} | {g['avgOpponentCaptures']} | {picks} |")
lines+=['','## Match-level evidence targets','','### Strongest early score leads']
for x in notable['high_early_score_gaps']:lines.append(f"- \`{x['path']}\`: round {x['at']} score Bot1 {x['us']}, opponent {x['opp']}.")
lines+=['','### Largest opponent capture lead']
for x in notable['high_capture_gaps']:lines.append(f"- \`{x['path']}\`: captures Bot1 {x['ourCaptures']}, opponent {x['opponentCaptures']}; final {x['score']}.")
lines+=['','### Stationary gem carriers (Bot1)']
for x in notable['bank_stalls']:lines.append(f"- \`{x['path']}\`: up to {x['turns']} stationary carrying turns; final {x['score']}.")
lines+=['','## Prioritized v5 experiments (not yet measured)','',
'1. **Fix objective throughput before combat:** first identify the earliest systematic losing checkpoint by map and opponent; test path/camp changes on paired seeds.',
'2. **Tune bank/tribute routing:** ensure a gem carrier can escape local minima and select alternative altars when a lock or threat blocks the closest approach.',
'3. **Test opponent-informed drafting:** map-conditional variants using the most effective draft archetypes; separately account for the Week 2 champion/stat changes.',
'4. **Add combat opportunism conditionally:** quantify which opponents gain via invades/kills, and test against carry-loss risk after the Week 2 kill-gold buff.',
'5. **Rebalance farm valuation for Week 2:** new gem values and 120-HP gem clusters change optimal farming loops; benchmark against frozen v4 only as a pre-patch regression, not as a post-patch estimate.',
'',
'## Reproduction and caveats','',
'- This study uses \`match-data/analysis/extract_v4_study.mjs\` and \`match-data/analysis/summarize_v4_study.py\`; metric data and traceable replay identifiers are in \`metrics.json\`.',
'- Numbers are a first-pass quantitative screening, not proof that an opponent action was intentional, optimal, or legally observable to the bot.',
'- Original map hashes, replay SHA-256 fingerprints and exact relative replay paths are recorded for follow-up deep dives.',
'']
(OUT/'REPORT.md').write_text('\n'.join(lines))
print(json.dumps({'files':data['files'],'decoded':data['processed'],'analyzed':len(games),'unique':len(unique_games),
 'decodeFailures':len(data['failures']),'analysisFailures':len(failures),'duplicates':len(duplicate),
 'outcomeMismatches':sum(not g['classifiedCorrectly'] for g in games),'categories':summary},indent=2))
