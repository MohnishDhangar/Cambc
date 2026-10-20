// Validate recordings with their matching bundled official engine.
// Loading and reading initial metadata only: no ReplayNext, Seek, or gameplay metrics.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {WASI} from 'node:wasi';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const assets = path.join(root, '.cambc/cache/assets');
const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const records = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const modules = new Map();
const results = {};
for (const record of records) {
  try {
    if (!modules.has(record.engine_version)) {
      const prefix = `v${record.engine_version.replaceAll('.', '_')}-`;
      const candidates = fs.readdirSync(assets).sort().flatMap(folder => {
        const dir = path.join(assets, folder, 'visualiser/assets');
        return fs.existsSync(dir) ? fs.readdirSync(dir).filter(n => n.startsWith(prefix) && n.endsWith('.wasm'))
          .map(n => path.join(dir, n)) : [];
      });
      if (!candidates.length) throw Error(`No bundled engine ${record.engine_version}`);
      const bytes = fs.readFileSync(candidates[0]);
      modules.set(record.engine_version, {module: await WebAssembly.compile(bytes),
        path: path.relative(root, candidates[0]), sha256: sha(bytes)});
    }
    const engine = modules.get(record.engine_version);
    const wasi = new WASI({version: 'preview1', args: [], env: {}, preopens: {}});
    const instance = await WebAssembly.instantiate(engine.module, {wasi_snapshot_preview1: wasi.wasiImport});
    wasi.initialize(instance);
    const api = instance.exports;
    const view = () => new DataView(api.memory.buffer);
    const out = api.Engine_Malloc(8192);
    const raw = fs.readFileSync(record.replay);
    const input = api.Engine_Malloc(raw.length);
    new Uint8Array(api.memory.buffer, input, raw.length).set(raw);
    function check(code) {
      if (!code) return;
      const pointer = api.GetLastErrorMsg();
      const memory = new Uint8Array(api.memory.buffer);
      let end = pointer;
      while (memory[end]) end++;
      throw Error(`Engine ${code}: ${new TextDecoder().decode(memory.subarray(pointer, end))}`);
    }
    check(api.Game_FromReplayFileBytes(input, raw.length, out));
    const game = view().getBigUint64(out, true);
    check(api.Game_Visualiser_Timeline_GetMain(game, out));
    const timeline = view().getBigUint64(out, true);
    check(api.Game_Visualiser_Timeline_Info(game, timeline, out, out + 8, out + 16));
    const count = view().getUint32(out, true);
    check(api.Game_GetBitboardMetadata(game, out));
    const dimensions = {width: view().getUint32(out, true), height: view().getUint32(out + 4, true)};
    results[record.match_id] = {engine_parse_valid: true, recorded_input_count: count,
      map_dimensions: dimensions, validator_engine: engine.path, validator_engine_sha256: engine.sha256,
      gameplay_replayed: false, completion_verified: false};
    api.Game_Destroy(game);
    api.Engine_Free(input);
    api.Engine_Free(out);
  } catch (error) {
    results[record.match_id] = {engine_parse_valid: false, error: String(error),
      gameplay_replayed: false, completion_verified: false};
  }
}
fs.writeFileSync(process.argv[3], JSON.stringify(results, null, 2) + '\n');
console.log(`Parsed ${records.length} recordings; ${Object.values(results).filter(r => !r.engine_parse_valid).length} failures. No gameplay advanced.`);
