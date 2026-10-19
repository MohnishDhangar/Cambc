#!/usr/bin/env python3
"""Play completed local matches on every map and inspect Bot1's replay logs."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[3]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--opponent', default='starter-cpp')
    parser.add_argument('--maps', nargs='*', help='Default: every local map')
    parser.add_argument('--jobs', type=int, default=2)
    parser.add_argument('--output', default='replays/Bot1-evaluation')
    args = parser.parse_args()
    out = (ROOT / args.output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    for bot in ('Bot1', args.opponent):
        subprocess.run(['cambc', 'build', bot], cwd=ROOT, check=True)
    maps = args.maps or sorted(p.stem for p in (ROOT / 'maps').glob('*.map26a'))

    def play(job):
        map_name, side = job
        folder = out / f'{map_name}-{side}'
        folder.mkdir(exist_ok=True)
        stats_path = folder / 'statistics.json'
        bots = ['Bot1', args.opponent] if side == 'A' else [args.opponent, 'Bot1']
        result = subprocess.run(
            ['cambc', 'run', *bots, '--map', map_name,
             '--out-dir', str(folder), '--statistics', str(stats_path)],
            cwd=ROOT, capture_output=True, text=True, timeout=120)
        (folder / 'runner.log').write_text(result.stdout + result.stderr)
        if result.returncode or not stats_path.exists():
            return {'map': map_name, 'side': side, 'error': result.stderr[-1000:]}
        stats = json.loads(stats_path.read_text())
        team = 0 if side == 'A' else 1
        log_name = f'team-{side.lower()}.stdout'
        errors, spills = [], []
        replay = max(folder.glob('*.repl26a'), key=lambda p: p.stat().st_mtime)
        with zipfile.ZipFile(replay) as archive:
            lines = archive.read(log_name).replace(b'\0', b'').decode(errors='replace').splitlines()
        errors = [line for line in lines if 'bot error' in line]
        spills = [line for line in lines if 'fuel spill' in line]
        champs = [c for c in stats['champions'] if c['team'] == team]
        return {
            'map': map_name, 'side': side,
            'win': stats['outcome'] == f'team{side}', 'rounds': stats['round'],
            'gems': stats['teams'][team]['submittedGems'],
            'opponent_gems': stats['teams'][1 - team]['submittedGems'],
            'deaths': sum(c['deaths'] for c in champs),
            'crashes': stats['botFaults'][team], 'errors': errors, 'fuel_spills': spills,
            'replay': str(replay.relative_to(ROOT)),
        }

    jobs = [(name, side) for name in maps for side in ('A', 'B')]
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as executor:
        results = list(executor.map(play, jobs))
    (out / 'summary.json').write_text(json.dumps(results, indent=2) + '\n')
    for row in results:
        if 'error' in row:
            print(f"{row['map']:12} {row['side']} RUN FAILED {row['error']}")
            continue
        print(f"{row['map']:12} {row['side']} {'WIN ' if row['win'] else 'LOSS'} "
              f"{row['gems']:4}-{row['opponent_gems']:<4} round {row['rounds']:4} "
              f"deaths {row['deaths']:2} errors {len(row['errors'])} spills {len(row['fuel_spills'])}")
    wins = sum(r.get('win', False) for r in results)
    print(f'{wins}/{len(results)} wins; report: {out / "summary.json"}')
    return int(any('error' in r or r.get('errors') or r.get('crashes') or r.get('fuel_spills') for r in results))


if __name__ == '__main__':
    sys.exit(main())
