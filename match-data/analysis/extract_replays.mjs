// Historical fallback using engine 0.0.1. Results are provisional.
// Use extract_native_replays.mjs for the authoritative 0.0.3 analysis.
// Decode local replay inputs with the bundled visualiser, preserving originals.
// Platform v3 adds explicit draft yields and a spawn selector. This converter
// accepts only its default (0xff) spawn selector; all gameplay bytes are kept.
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import crypto from 'node:crypto';
import {WASI} from 'node:wasi';

const base=path.join(os.homedir(),'.cache/cambc/assets');
const dir=fs.readdirSync(base).map(v=>path.join(base,v,'visualiser/assets')).find(p=>fs.existsSync(p));
const panel=fs.readFileSync(path.join(dir,fs.readdirSync(dir).find(p=>p.startsWith('PanelChrome-'))),'utf8');
const decode=new Function('Hn','var '+panel.slice(panel.indexOf('Gn=184696'),panel.indexOf('function Cr('))+';return {header:br,timeline:hr,snapshot:Sr};')(Array(42));
const module=await WebAssembly.compile(fs.readFileSync(path.join(dir,fs.readdirSync(dir).find(p=>p.endsWith('.wasm')))));
const lengths={0:4,1:8,2:9,3:17,4:0,5:8,6:8,7:0,8:8,9:9,10:8,11:4};
const names=['Ryth','Vesper Vale','Vendetta','Cassi','Issac','Stellar','Prism','Marcella','Willow','Ren','Varg','Tavi'];
const clean=(v)=>JSON.stringify(v,(k,x)=>typeof x==='bigint'?Number(x):x);
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
function convert(b){
 let draft=-1;
 for(let pick=0;pick<=10;pick++){
  const candidate=b.indexOf(Buffer.from([4,1,pick,0,0,0,255,3,0]));
  if(candidate>=0&&(draft<0||candidate<draft))draft=candidate;
 }
 if(draft<4)throw Error('No supported v3 draft marker');
 const endMap=draft-4, count=b.readUInt32LE(endMap);
 let pos=endMap+4, pendingDraft=false;
 const records=[], originalCounts={};
 for(let i=0;i<count;i++){
  const start=pos,kind=b[pos++];let sub;
  if(kind===0){sub=b[pos++];if(!(sub in lengths))throw Error(`Unknown action ${sub} at ${start}`);pos+=lengths[sub];}
  else if(kind===3)pos++;
  else if(kind===4){sub=b[pos++];if(sub!==1||b[pos+4]!==255)throw Error('Unsupported draft spawn');pos+=5;}
  else if(kind!==5)throw Error(`Unknown input ${kind} at ${start}`);
  if(pos>b.length)throw Error('Truncated input');
  const r=b.subarray(start,pos),key=`${kind}:${sub??''}`;originalCounts[key]=(originalCounts[key]??0)+1;
  if(kind===4){records.push(Buffer.from([4,0,...r.subarray(2,6)]));pendingDraft=true;}
  else if(kind===3&&pendingDraft){if(r[1]!==0)throw Error('Draft exhausted fuel');pendingDraft=false;}
  else records.push(r);
 }
 if(pos!==b.length)throw Error(`Unconsumed replay bytes: ${b.length-pos}`);
 const head=Buffer.from(b.subarray(0,endMap));head[10]=1;head[13]=1;
 const num=Buffer.alloc(4);num.writeUInt32LE(records.length);
 return {bytes:Buffer.concat([head,num,...records]),mapBytes:endMap-14,originalCount:count,originalCounts,convertedCount:records.length};
}

async function extract(file,outDir){
 const raw=fs.readFileSync(file),converted=convert(raw);
 const wasi=new WASI({version:'preview1',args:[],env:{}});
 const instance=await WebAssembly.instantiate(module,{wasi_snapshot_preview1:wasi.wasiImport});wasi.initialize(instance);
 const api=instance.exports,view=()=>new DataView(api.memory.buffer);
 const out=api.Engine_Malloc(8192),snapshot=api.Engine_Malloc(184696),timelinePtr=api.Engine_Malloc(40152);
 function check(code){if(code){const p=api.GetLastErrorMsg();let e=p;const m=new Uint8Array(api.memory.buffer);while(m[e])e++;throw Error(`Engine ${code}: `+new TextDecoder().decode(m.subarray(p,e)));}}
 const data=api.Engine_Malloc(converted.bytes.length);new Uint8Array(api.memory.buffer,data,converted.bytes.length).set(converted.bytes);
 check(api.Game_FromReplayFileBytes(data,converted.bytes.length,out));const game=view().getBigUint64(out,true);
 check(api.Game_Visualiser_Timeline_GetMain(game,out));const timeline=view().getBigUint64(out,true);
 check(api.Game_Visualiser_Timeline_Info(game,timeline,out,out+8,out+16));const size=view().getUint32(out,true);
 check(api.Game_Runner_SetCheckpointsEnabled(game,1));
 const getFull=()=>{view().setUint32(out,2,true);view().setUint32(out+4,0xffffffff,true);check(api.Game_Visualiser_ReadState(game,out,snapshot));return decode.snapshot(view(),snapshot);};
 const getTimeline=()=>{check(api.Game_Visualiser_ReadTimelineState(game,timelinePtr));return decode.timeline(view(),timelinePtr);};
 check(api.Game_GetBitboardMetadata(game,out));const map={width:view().getUint32(out,true),height:view().getUint32(out+4,true),serializedBytes:converted.mapBytes};
 check(api.Game_GetTeamASpawnArea(game,out));map.spawnA={minX:view().getInt32(out,true),minY:view().getInt32(out+4,true),maxX:view().getInt32(out+8,true),maxY:view().getInt32(out+12,true)};
 check(api.Game_GetNumCamps(game,out));const numCamps=view().getUint32(out,true);
 map.camps=[];
 for(let i=0;i<numCamps;i++){
  check(api.Game_GetCampHandle(game,i,out));const handle=view().getBigUint64(out,true);
  check(api.Game_GetCamp(game,handle,out));map.camps.push({handle:Number(handle),type:view().getInt32(out,true),x:view().getInt32(out+4,true),y:view().getInt32(out+8,true)});
 }
 // Terrain is exported with the same chunked bitboard layout as the SDK.
 const metadata=api.Engine_Malloc(32);check(api.Game_GetBitboardMetadata(game,metadata));
 const meta=Array.from(new Uint32Array(api.memory.buffer,metadata,5));
 map.terrain={};
 for(const kind of ['Bush','Wall','Hole','Altar']){
  check(api[`Game_Get${kind}Buffer`](game,out));const p=view().getUint32(out,true),coords=[];
  for(let y=0;y<map.height;y++)for(let x=0;x<map.width;x++){
   // Ask the engine instead of interpreting its chunk layout.
   check(api[`Game_Get${kind}`](game,x,y,out));if(view().getUint8(out))coords.push([x,y]);
  }
  map.terrain[kind.toLowerCase()]=coords;
 }
 check(api.Game_Visualiser_Timeline_Seek(game,timeline,0,0));
 const replayErrors=[];
 const events=[],turns=[],rounds=[];let previous=getTimeline(),steps=0,lastRound=-1;let turnActions={};
 while(true){
  const state=previous;
  if(state.round!==lastRound&&state.champions.length){
   rounds.push({round:state.round,score:state.submittedGems,champions:state.champions});lastRound=state.round;
  }
  if(state.outcome||(state.awaitingInput&&state.inputPosition>=size-replayErrors.length))break;
  const code=api.Game_Visualiser_Timeline_ReplayNext(game,1);
  if(code){
   const failed=getTimeline();
   replayErrors.push({code,before:{round:state.round,inputPosition:state.inputPosition,step:state.step},after:{round:failed.round,inputPosition:failed.inputPosition,step:failed.step}});
   console.error('REPLAY DIVERGENCE',path.basename(path.dirname(file)),JSON.stringify(replayErrors.at(-1)));
   // Stop at the first incompatible input; do not alter or skip gameplay.
   break;
  }
  const next=getTimeline();steps++;
  if(!code&&next.inputPosition===state.inputPosition&&next.step.substep===state.step.substep)throw Error('No timeline progress');
  const step=next.step,actor=step.actor;const event={round:next.round,position:next.inputPosition,substep:step.substep,kind:step.kind,phase:step.phase,actor,from:step.from,to:step.to,abilitySlot:step.abilitySlot,abilityType:step.abilityType};
  if(actor.kind===1){const key=actor.index;turnActions[key]??=[];turnActions[key].push(step.kind);}
  const changes=[];
  for(const after of next.champions){
   const before=state.champions.find(c=>c.entity.index===after.entity.index);if(!before)continue;
   const delta={id:after.entity.index};
   for(const k of ['health','gold','gems','kills'])if(after[k]!==before[k])delta[k]=after[k]-before[k];
   if(before.alive!==after.alive)delta.alive=after.alive;
   if(Object.keys(delta).length>1)changes.push(delta);
  }
  if(changes.length)event.changes=changes;
  if(next.submittedGems.some((v,i)=>v!==state.submittedGems[i]))event.score=next.submittedGems;
  if(step.kind===2||step.kind===5||step.kind===6||step.kind===11||step.kind===12||step.kind===18||step.kind===20||step.kind===21||step.kind===22||step.kind===23||step.kind===24||step.kind===26||changes.length||event.score)events.push(event);
  if((step.kind===8||step.kind===26)&&actor.kind===1){
   const full=getFull();const c=full.champions.find(c=>c.entity.index===actor.index);
   if(c)turns.push({round:next.round,id:actor.index,team:c.team,type:c.type,position:c.position,health:c.health,maxHealth:c.maxHealth,gold:c.gold,gems:c.gems,earnedGold:c.earnedGold,alive:c.alive,channelType:c.channelType,channelTimer:c.channelTimer,roundFlags:c.roundFlags,cooldowns:c.cooldowns,strength:c.strength?.effective,focus:c.focus?.effective,actions:turnActions[actor.index]??[]});
   turnActions[actor.index]=[];
  }
  previous=next;
  if(steps>500000)throw Error('Too many timeline steps');
 }
 const final=getFull(),stats=[];
 for(const c of final.champions){
  if(replayErrors.length){
   stats.push({id:c.entity.index,team:c.team,type:c.type,name:names[c.type],kills:c.kda[0],deaths:c.kda[1],assists:c.kda[2],earnedGold:c.earnedGold,gold:c.gold,gems:c.gems,partial:true});
   continue;
  }
  check(api.Game_Statistics_GetChampion(game,c.entity.index,out));const m=view(),u=o=>m.getUint32(out+o,true),u64=o=>Number(m.getBigUint64(out+o,true)),d=o=>m.getFloat64(out+o,true);
  stats.push({id:u(0),team:u(4),type:u(8),name:names[u(8)],kills:u(12),deaths:u(16),assists:u(20),earnedGold:u64(24),collectedGems:u64(32),submittedGems:u64(40),spentGold:u64(48),gold:u(56),gems:u(60),itemsBought:Array.from({length:42},(_,i)=>u64(64+i*8)),consumablesBought:Array.from({length:4},(_,i)=>u64(400+i*8)),items:Array.from({length:42},(_,i)=>u(480+i*4)),consumables:Array.from({length:4},(_,i)=>u(648+i*4))});
 }
 const stdout=fs.readFileSync(path.join(path.dirname(file),'team-a.stdout')).toString().replaceAll('\0','');
 const result={source:file,sha256:sha(raw),conversion:{originalEngine:'0.0.3',simulationEngine:'0.0.1',...converted,bytes:undefined},map,complete:final.outcome!==0&&replayErrors.length===0,round:final.round,outcome:final.outcome,score:final.submittedGems,drafts:final.drafts,stats,final,steps,stdout,replayErrors};
 fs.mkdirSync(outDir,{recursive:true});
 fs.writeFileSync(path.join(outDir,'summary.json'),clean(result));
 fs.writeFileSync(path.join(outDir,'events.json'),clean(events));
 fs.writeFileSync(path.join(outDir,'turns.json'),clean(turns));
 fs.writeFileSync(path.join(outDir,'rounds.json'),clean(rounds));
 fs.writeFileSync(path.join(outDir,'map.map26a'),raw.subarray(14,14+converted.mapBytes));
 return result;
}
const root=path.resolve('match-data'),dest=path.join(root,'analysis');const summaries=[];
for(const series of fs.readdirSync(root).filter(p=>p.startsWith('match-')).sort())for(const game of fs.readdirSync(path.join(root,series)).filter(p=>/^\d\d-/.test(p)).sort()){
 const file=path.join(root,series,game,'replay.repl26a');if(!fs.existsSync(file))continue;
 const output=path.join(dest,series,game.slice(0,2));const result=await extract(file,output);summaries.push({...result,final:undefined});
 console.log(series,game.slice(0,2),`${result.map.width}x${result.map.height}`,result.round,result.score.map(Number),result.stats.filter(c=>c.team===0).map(c=>`${c.name}:${c.kills}/${c.deaths},${c.collectedGems}->${c.submittedGems}`).join(' '));
}
fs.writeFileSync(path.join(dest,'summaries.json'),clean(summaries));
