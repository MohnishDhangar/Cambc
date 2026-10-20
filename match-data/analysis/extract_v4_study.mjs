// Replay the original recordings with the matching official 0.0.3 engine.
// No replay headers, draft records, or gameplay inputs are modified.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {WASI} from 'node:wasi';

const root = path.resolve(process.argv[2] ?? 'match-data/v4');
const destination = path.resolve(process.argv[3] ?? 'results/v4-native');
const compact = true;
const assets = path.resolve(process.env.CAMBC_CACHE ?? '.cambc/cache', 'assets');
const assetDirectory = fs.readdirSync(assets)
  .map(name => path.join(assets, name, 'visualiser/assets'))
  .find(dir => fs.existsSync(dir) && fs.readdirSync(dir).some(name => /^v0_0_3-.*\.wasm$/.test(name)));
if (!assetDirectory) throw Error('Initialize the updated client to extract its 0.0.3 engine.');
const panelPath = path.join(assetDirectory, fs.readdirSync(assetDirectory).find(name => /^PanelChrome-.*\.js$/.test(name)));
const panel = fs.readFileSync(panelPath, 'utf8');
const start = panel.indexOf('Gn=184696');
const end = panel.indexOf('function wr(', start);
if (start < 0 || end < start) throw Error('Unrecognized bundled viewer decoder.');
// This trusted decoder comes from the same official client as the engine.
const decode = new Function('Hn', 'var ' + panel.slice(start, end) + ';return {header:xr,timeline:gr,snapshot:Cr};')(Array(42));
const enginePath = path.join(assetDirectory, fs.readdirSync(assetDirectory).find(name => /^v0_0_3-.*\.wasm$/.test(name)));
const engineBytes = fs.readFileSync(enginePath);
const module = await WebAssembly.compile(engineBytes);
const championNames = ['Ryth', 'Vesper Vale', 'Vendetta', 'Cassi', 'Issac', 'Stellar', 'Prism', 'Marcella', 'Willow', 'Ren', 'Varg', 'Tavi'];
const sha256 = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const json = value => JSON.stringify(value, (_, item) => typeof item === 'bigint' ? Number(item) : item);

function replayMetadata(raw) {
  if (raw.subarray(8, 14).toString('hex') !== '000003000003') throw Error('Expected engine/format 0.0.3.');
  let draft = -1;
  for (let pick = 0; pick < 12; pick++) {
    const candidate = raw.indexOf(Buffer.from([4, 1, pick, 0, 0, 0, 255, 3, 0]));
    if (candidate >= 0 && (draft < 0 || candidate < draft)) draft = candidate;
  }
  if (draft < 18) throw Error('Unable to locate input section.');
  const inputCountOffset = draft - 4;
  return {mapBytes: inputCountOffset - 14, inputCount: raw.readUInt32LE(inputCountOffset)};
}

async function extract(file, output) {
  const raw = fs.readFileSync(file);
  const metadata = replayMetadata(raw);
  const sourceHash = sha256(raw);
  const wasi = new WASI({version: 'preview1', args: [], env: {}});
  const instance = await WebAssembly.instantiate(module, {wasi_snapshot_preview1: wasi.wasiImport});
  wasi.initialize(instance);
  const api = instance.exports;
  const view = () => new DataView(api.memory.buffer);
  const out = api.Engine_Malloc(8192);
  const snapshot = api.Engine_Malloc(184696);
  const timelinePointer = api.Engine_Malloc(40152);
  if (api.Game_Visualiser_SnapshotSize() !== 184696 || api.Game_Visualiser_TimelineSnapshotSize() !== 40152) throw Error('Unsupported snapshot layout.');
  function check(code) {
    if (!code) return;
    const pointer = api.GetLastErrorMsg();
    const memory = new Uint8Array(api.memory.buffer);
    let end = pointer;
    while (memory[end]) end++;
    throw Error(`Engine ${code}: ${new TextDecoder().decode(memory.subarray(pointer, end))}`);
  }
  const data = api.Engine_Malloc(raw.length);
  new Uint8Array(api.memory.buffer, data, raw.length).set(raw);
  check(api.Game_FromReplayFileBytes(data, raw.length, out));
  const game = view().getBigUint64(out, true);
  check(api.Game_Visualiser_Timeline_GetMain(game, out));
  const timeline = view().getBigUint64(out, true);
  check(api.Game_Visualiser_Timeline_Info(game, timeline, out, out + 8, out + 16));
  const inputCount = view().getUint32(out, true);
  if (inputCount !== metadata.inputCount) throw Error('Replay input count differs from recorded section.');
  const fullState = () => {
    view().setUint32(out, 2, true);
    view().setUint32(out + 4, 0xffffffff, true);
    check(api.Game_Visualiser_ReadState(game, out, snapshot));
    return decode.snapshot(view(), snapshot);
  };
  const timelineState = () => {
    check(api.Game_Visualiser_ReadTimelineState(game, timelinePointer));
    return decode.timeline(view(), timelinePointer);
  };
  check(api.Game_GetBitboardMetadata(game, out));
  const map = {width: view().getUint32(out, true), height: view().getUint32(out + 4, true), serializedBytes: metadata.mapBytes, sha256: sha256(raw.subarray(14, 14 + metadata.mapBytes))};
  check(api.Game_GetTeamASpawnArea(game, out));
  map.spawnA = {minX: view().getInt32(out, true), minY: view().getInt32(out + 4, true), maxX: view().getInt32(out + 8, true), maxY: view().getInt32(out + 12, true)};
  check(api.Game_GetNumCamps(game, out));
  const campCount = view().getUint32(out, true);
  map.camps = [];
  for (let index = 0; index < campCount; index++) {
    check(api.Game_GetCampHandle(game, index, out));
    const handle = view().getBigUint64(out, true);
    check(api.Game_GetCamp(game, handle, out));
    map.camps.push({handle: Number(handle), type: view().getInt32(out, true), x: view().getInt32(out + 4, true), y: view().getInt32(out + 8, true)});
  }
  map.terrain = {};
  for (const kind of ['Bush', 'Wall', 'Hole', 'Altar']) {
    const coordinates = [];
    for (let y = 0; y < map.height; y++) for (let x = 0; x < map.width; x++) {
      check(api[`Game_Get${kind}`](game, x, y, out));
      if (view().getUint8(out)) coordinates.push([x, y]);
    }
    map.terrain[kind.toLowerCase()] = coordinates;
  }
  check(api.Game_Visualiser_Timeline_Seek(game, timeline, 0, 0));
  let previous = timelineState(), steps = 0, lastRound = -1;
  const events = [], turns = [], rounds = [], replayErrors = [];
  const turnActions = {};
  let liveMapCaptured = false;
  while (true) {
    const state = previous;
    if (!liveMapCaptured && state.round >= 1 && state.champions.length) {
      // The map API before drafting exposes template camps, before symmetry
      // expansion. Read instantiated camps to include BOTH teams' resources.
      const initial = fullState();
      if (initial.camps.some(camp => !camp.position)) throw Error('Missing initial camp position.');
      map.camps = initial.camps.map(camp => ({index: camp.entity.index, type: camp.type,
        x: camp.position.x, y: camp.position.y, group: camp.group}));
      for (const kind of ['Bush', 'Wall', 'Hole', 'Altar']) {
        const coordinates = [];
        for (let y = 0; y < map.height; y++) for (let x = 0; x < map.width; x++) {
          check(api[`Game_Get${kind}`](game, x, y, out));
          if (view().getUint8(out)) coordinates.push([x, y]);
        }
        map.terrain[kind.toLowerCase()] = coordinates;
      }
      liveMapCaptured = true;
    }
    if (state.round !== lastRound && state.champions.length) {
      // Full camp snapshots on every round are expensive and not required for
      // first-pass opponent economics, tribute, movement and upgrade analysis.
      rounds.push({round: state.round, score: state.submittedGems});
      lastRound = state.round;
    }
    if (state.outcome || (state.awaitingInput && state.inputPosition >= inputCount)) break;
    const code = api.Game_Visualiser_Timeline_ReplayNext(game, 1);
    if (code) {
      replayErrors.push({code, round: state.round, inputPosition: state.inputPosition, step: state.step});
      break;
    }
    const next = timelineState();
    steps++;
    if (next.inputPosition === state.inputPosition && next.step.substep === state.step.substep) throw Error('No timeline progress.');
    const step = next.step, actor = step.actor;
    const event = {round: next.round, position: next.inputPosition, substep: step.substep, kind: step.kind, phase: step.phase, actor, from: step.from, to: step.to, abilitySlot: step.abilitySlot, abilityType: step.abilityType};
    if (actor.kind === 1) (turnActions[actor.index] ??= []).push(step.kind);
    const changes = [];
    for (const after of next.champions) {
      const before = state.champions.find(champion => champion.entity.index === after.entity.index);
      if (!before) continue;
      const delta = {id: after.entity.index};
      for (const key of ['health', 'gold', 'gems', 'kills']) if (after[key] !== before[key]) delta[key] = after[key] - before[key];
      if (before.alive !== after.alive) delta.alive = after.alive;
      if (Object.keys(delta).length > 1) changes.push(delta);
    }
    if (changes.length) event.changes = changes;
    if (next.submittedGems.some((score, index) => score !== state.submittedGems[index])) event.score = next.submittedGems;
    if ([2, 5, 6, 11, 12, 18, 20, 21, 22, 23, 24, 26, 27].includes(step.kind) || changes.length || event.score) events.push(event);
    if ([8, 26, 27].includes(step.kind) && actor.kind === 1) {
      const full = fullState();
      const champion = full.champions.find(champion => champion.entity.index === actor.index);
      if (champion) turns.push({round: next.round, id: actor.index, team: champion.team, type: champion.type, position: champion.position, health: champion.health, maxHealth: champion.maxHealth, gold: champion.gold, gems: champion.gems, earnedGold: champion.earnedGold, alive: champion.alive, channelType: champion.channelType, channelTimer: champion.channelTimer, roundFlags: champion.roundFlags, cooldowns: champion.cooldowns, strength: champion.strength?.effective, focus: champion.focus?.effective, items: champion.items, consumables: champion.consumables, actions: turnActions[actor.index] ?? []});
      turnActions[actor.index] = [];
    }
    previous = next;
    if (steps > 1000000) throw Error('Unexpectedly long replay.');
  }
  const final = fullState();
  const stats = final.champions.map(champion => {
    check(api.Game_Statistics_GetChampion(game, champion.entity.index, out));
    const memory = view();
    const uint = offset => memory.getUint32(out + offset, true);
    const uint64 = offset => Number(memory.getBigUint64(out + offset, true));
    const result = {id: uint(0), team: uint(4), type: uint(8), name: championNames[uint(8)], kills: uint(12), deaths: uint(16), assists: uint(20), earnedGold: uint64(24), collectedGems: uint64(32), submittedGems: uint64(40), spentGold: uint64(48), gold: uint(56), gems: uint(60)};
    if (result.id !== champion.entity.index || result.team !== champion.team || result.type !== champion.type || result.kills !== champion.kda[0] || result.deaths !== champion.kda[1] || result.gold !== champion.gold || result.gems !== champion.gems || result.earnedGold !== champion.earnedGold) throw Error('Statistics layout differs from full snapshot.');
    return result;
  });
  for (const team of [0, 1]) {
    if (stats.filter(champion => champion.team === team).reduce((sum, champion) => sum + champion.submittedGems, 0) !== Number(final.submittedGems[team])) throw Error('Champion tribute totals differ from team score.');
  }
  if (sha256(fs.readFileSync(file)) !== sourceHash) throw Error('Source replay changed.');
  const result = {source: file, sha256: sourceHash, engine: {version: '0.0.3', source: enginePath, sha256: sha256(engineBytes), replayModified: false}, map, complete: final.outcome !== 0 && replayErrors.length === 0, round: final.round, outcome: final.outcome, score: final.submittedGems, drafts: final.drafts, stats, final, steps, inputCount, replayErrors};
  fs.mkdirSync(output, {recursive: true});
  for (const [name, value] of Object.entries({summary: {...result, final: undefined}, events, turns, rounds})) fs.writeFileSync(path.join(output, name + '.json'), json(value));
  fs.writeFileSync(path.join(output, 'map.map26a'), raw.subarray(14, 14 + metadata.mapBytes));
  return result;
}


const files = [];
function crawl(folder) {
  for (const entry of fs.readdirSync(folder, {withFileTypes:true})) {
    const at = path.join(folder, entry.name);
    if (entry.isDirectory()) crawl(at);
    else if (entry.isFile() && entry.name === 'replay.repl26a') files.push(at);
  }
}
crawl(root);
files.sort();
if (process.env.REPLAY_SELECT) {
  const needles = process.env.REPLAY_SELECT.split('|').filter(Boolean);
  const chosen = files.filter(f => needles.some(needle => f.includes(needle)));
  files.splice(0, files.length, ...chosen);
}
if (process.env.REPLAY_LIMIT) files.splice(Number(process.env.REPLAY_LIMIT));
const summaries = [];
const failures = [];
for (const [i,file] of files.entries()) {
  const relative = path.relative(root, path.dirname(file));
  try {
    const result = await extract(file, path.join(destination, relative));
    const meta = relative.split(path.sep);
    summaries.push({path:relative, category:meta.slice(0,2).join('/'), group:meta[2], game:meta[3],
      sha256:result.sha256, complete:result.complete, round:result.round,
      score:result.score, outcome:result.outcome, mapHash:result.map.sha256,
      mapSize:result.map.width+'x'+result.map.height, stats:result.stats,
      drafts:result.drafts, replayErrors:result.replayErrors});
    console.log((i+1)+'/'+files.length, relative, 'round='+result.round, 'score='+result.score, 'complete='+result.complete);
  } catch (error) {
    console.error('REPLAY_ERROR', relative, error.stack||String(error));
    failures.push({path:relative, error:String(error)});
  }
}
fs.mkdirSync(destination,{recursive:true});
fs.writeFileSync(path.join(destination, 'index.json'), json({files:files.length,processed:summaries.length,failures,summaries}));
console.log('RESULT', JSON.stringify({files:files.length,processed:summaries.length,failures:failures.length}));
if (summaries.some(x=>!x.complete) || failures.length) process.exitCode = 1;
