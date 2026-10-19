"""Summarize complete 0.0.3 replays and cross-check the original action log."""
from collections import Counter
from pathlib import Path
import json

from raw_metrics import analyze

ROOT = Path(__file__).resolve().parent / 'native-0.0.3'


def stationary_carriers(turns, roster):
    runs = []
    for champion in roster:
        previous = None
        current = []

        def finish():
            if len(current) >= 15:
                runs.append({
                    'champion': champion['name'], 'id': champion['id'],
                    'turns': len(current), 'start': current[0]['round'],
                    'end': current[-1]['round'], 'position': current[0]['position'],
                    'gems': current[0]['gems'], 'health': current[0]['health'],
                })

        for turn in (turn for turn in turns if turn['id'] == champion['id']):
            key = (
                turn.get('position', {}).get('x'), turn.get('position', {}).get('y'),
                turn['gems'], turn['health'],
            ) if turn['alive'] and turn['gems'] > 0 and turn['channelType'] == 0 else None
            if key is not None and key == previous:
                current.append(turn)
            else:
                finish()
                current = [turn] if key is not None else []
            previous = key
        finish()
    return sorted(runs, key=lambda run: run['turns'], reverse=True)


def main():
    results = []
    for file in sorted(ROOT.glob('match-*/*/summary.json')):
        summary = json.loads(file.read_text())
        turns = json.loads((file.parent / 'turns.json').read_text())
        events = json.loads((file.parent / 'events.json').read_text())
        original = analyze(summary)
        native_turns = Counter(turn['id'] for turn in turns)
        assert summary['complete'] and not summary['replayErrors']
        for champion in original['champions']:
            assert champion['metrics'].get('turns', 0) == native_turns[champion['id']]
        teams = []
        for team in (0, 1):
            roster = [champion for champion in summary['stats'] if champion['team'] == team]
            ids = {champion['id'] for champion in roster}
            totals = {key: sum(champion[key] for champion in roster) for key in (
                'kills', 'deaths', 'earnedGold', 'collectedGems', 'submittedGems', 'spentGold', 'gems',
            )}
            totals['lostGems'] = totals['collectedGems'] - totals['submittedGems'] - totals['gems']
            losses_in_events = sum(
                -change.get('gems', 0) for event in events for change in event.get('changes', [])
                if change['id'] in ids and change.get('alive') is False
            )
            assert totals['lostGems'] == losses_in_events
            totals['tributeStarts'] = sum(champion['metrics'].get('tribute', 0) for champion in original['champions'] if champion['team'] == team)
            totals['fuelExhaustions'] = sum(champion['metrics'].get('fuel_exhaustions', 0) for champion in original['champions'] if champion['team'] == team)
            totals['stationaryCarriers'] = stationary_carriers(turns, roster)
            teams.append(totals)
        results.append({'series': file.parent.parent.name, 'game': file.parent.name, 'round': summary['round'], 'score': summary['score'], 'teams': teams, 'rawTurnCountsMatch': True})
    assert len(results) == 15
    (ROOT / 'diagnostics.json').write_text(json.dumps(results, indent=2) + '\n')
    lines = [
        '# Complete 0.0.3 replay results', '',
        'All scores list Bot1 first. Champion deaths include linked Cassi/Issac deaths and camp deaths.', '',
        '| Opponent | Game | Round | Score | Bot1 kills / deaths | Gems lost by Bot1 on death |',
        '| --- | --- | --- | --- | --- | --- |',
    ]
    for result in results:
        ours = result['teams'][0]
        opponent = result['series'].split('team-')[-1]
        lines.append(f"| {opponent} | {result['game']} | {result['round']:,} | {result['score'][0]:,}–{result['score'][1]:,} | {ours['kills']} / {ours['deaths']} | {ours['lostGems']} |")
    (ROOT / 'RESULTS.md').write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))
    print('\nAll 15 native turn counts match the original action logs; gem balances match death events.')


if __name__ == '__main__':
    main()
