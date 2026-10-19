#!/usr/bin/env python3
"""Run release-mode paired comparisons on the supplied platform maps."""
import argparse, hashlib, json, os, subprocess, sys, zipfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'match-data/analysis'))
from raw_metrics import analyze,parse
CLI=str(ROOT/'tools/cambc')
ENV={**os.environ,'CAMBC_OFFLINE':'1','CAMBC_NO_UPDATE_CHECK':'1'}
NAMES=['Ryth','Vesper Vale','Vendetta','Cassi','Issac','Stellar','Prism','Marcella','Willow','Ren','Varg','Tavi']
def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--candidate',default='Bot1');p.add_argument('--opponents',nargs='+',default=['BaselineV1','BaselineV3'])
 p.add_argument('--maps',nargs='*');p.add_argument('--sides',nargs='+',default=['A','B']);p.add_argument('--jobs',type=int,default=2)
 p.add_argument('--output',required=True);args=p.parse_args();out=ROOT/args.output
 out.mkdir(parents=True,exist_ok=True)
 comparison=json.loads((ROOT/'match-data/analysis/paired-v1-v3/comparison.json').read_text())
 maps={}
 for g in comparison['games']:
  h=g['mapHash'];maps.setdefault(h,ROOT/'match-data/analysis/paired-v1-v3'/g['version']/g['series']/g['game']/'map.map26a')
 selected=[]
 for h,path in sorted(maps.items()):
  if not args.maps or any(h.startswith(m) for m in args.maps):selected.append((h[:8],path))
 if args.maps and len(selected)!=len(args.maps):raise SystemExit('Use one unique map-hash prefix per map')
 for bot in dict.fromkeys([args.candidate]+args.opponents):
  subprocess.run([CLI,'build',bot,'--release'],cwd=ROOT,env=ENV,check=True,stdout=subprocess.DEVNULL)
 manifest={'candidate':args.candidate,'opponents':args.opponents,'release':True,'fuel':'client default','sources':{}}
 for bot in dict.fromkeys([args.candidate]+args.opponents):
  manifest['sources'][bot]={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'bots'/bot/'src').rglob('*') if p.is_file()}
 (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 def play(job):
  opponent,h,path,side=job;folder=out/f'{h}-{opponent}-{side}';folder.mkdir(exist_ok=True)
  if (folder/'result.json').exists():raise RuntimeError(f'Existing result: {folder}; use a fresh output')
  team='team'+side;other='team'+('B' if side=='A' else 'A');bots=[args.candidate,opponent] if side=='A' else [opponent,args.candidate]
  run=subprocess.run([CLI,'run',*bots,'--release','--map',str(path),'--out-dir',str(folder),'--statistics',str(folder/'statistics.json'),'--json'],cwd=ROOT,env=ENV,capture_output=True,text=True,timeout=300)
  (folder/'runner.log').write_text(run.stdout+run.stderr)
  row={'map':h,'side':side,'opponent':opponent}
  if run.returncode or not (folder/'statistics.json').exists():return {**row,'error':(run.stdout+run.stderr)[-2000:]}
  s=json.loads((folder/'statistics.json').read_text());bundle=next(folder.glob('*.repl26a'))
  with zipfile.ZipFile(bundle) as z:
   raw=folder/'inputs.repl26a';raw.write_bytes(z.read('replay.repl26a'))
   log=z.read(f'team-{side.lower()}.stdout').replace(b'\0',b'').decode(errors='replace')
   (folder/'candidate.stdout').write_text(log)
  records=parse(raw);picks=sum(kind==4 for kind,sub,data,byte in records)
  roster=[{'entity':{'index':c['id']},'team':0 if c['team']=='teamA' else 1,'type':NAMES.index(c['name'])} for c in s['champions']]
  actions=analyze({'source':str(raw),'final':{'champions':roster,'draftCounts':[picks,0]}})
  champs=[c for c in s['champions'] if c['team']==team];enemies=[c for c in s['champions'] if c['team']==other]
  metrics=lambda cs:{k:sum(float(c['metrics'][k]) for c in cs) for k in ['earnedGold','collectedGems','submittedGems','deaths','monsterDamageDone']}
  result={**row,'win':s['match']['outcome']==team,'round':s['match']['roundsStarted'],'gems':int(sum(int(c['metrics']['submittedGems']) for c in champs)),
   'opponentGems':int(sum(int(c['metrics']['submittedGems']) for c in enemies)), 'metrics':metrics(champs),'opponentMetrics':metrics(enemies),
   'faults':s['diagnostics']['botFaults'][team], 'errors':[x for x in log.splitlines() if 'bot error' in x],
   'spillMessages':[x for x in log.splitlines() if 'fuel spill' in x],
   'fuelExhaustions':sum(c['metrics'].get('fuel_exhaustions',0) for c in actions['champions'] if c['team']==(0 if side=='A' else 1)),
   'replay':str(bundle.relative_to(ROOT)),'engine':s['match']['engineVersion']}
  (folder/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 jobs=[(o,h,path,side) for o in args.opponents for h,path in selected for side in args.sides];results=[]
 with ThreadPoolExecutor(max_workers=args.jobs) as pool:
  for future in as_completed([pool.submit(play,job) for job in jobs]):
   r=future.result();results.append(r);(out/'summary.json').write_text(json.dumps(results,indent=2)+'\n')
   if 'error' in r:print(r,flush=True)
   else:print(f"{r['map']} {r['opponent']} {r['side']} {'WIN' if r['win'] else 'LOSS'} {r['gems']}-{r['opponentGems']} round={r['round']} deaths={r['metrics']['deaths']:.0f} fuel={r['fuelExhaustions']} errors={len(r['errors'])} faults={r['faults']}",flush=True)
 print(f"{sum(r.get('win',False) for r in results)}/{len(results)} wins",flush=True)
 return int(any('error' in r or r.get('faults') or r.get('errors') or r.get('fuelExhaustions') for r in results))
if __name__=='__main__':sys.exit(main())
