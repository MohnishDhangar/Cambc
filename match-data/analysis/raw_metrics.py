"""Count recorded platform actions without executing them in an older engine."""
from pathlib import Path
from collections import Counter, defaultdict
import json
import struct

ROOT = Path(__file__).resolve().parent
LENGTHS = {0:4,1:8,2:9,3:17,4:0,5:8,6:8,7:0,8:8,9:9,10:8,11:4}
ACTION = {0:'priority',1:'move',2:'attack',3:'cast',4:'recall',5:'tribute',6:'buy_item',7:'cancel_channel',8:'buy_consumable',9:'use_consumable',10:'ward',11:'sell'}


def parse(file):
    b = file.read_bytes()
    start = min(x for pick in range(11) if (x := b.find(bytes([4,1,pick,0,0,0,255,3,0]))) >= 0)
    count = struct.unpack_from('<I', b, start - 4)[0]
    records = []
    pos = start
    for _ in range(count):
        begin = pos
        kind = b[pos]
        pos += 1
        sub = None
        if kind == 0:
            sub = b[pos]
            pos += 1 + LENGTHS[sub]
        elif kind == 3:
            pos += 1
        elif kind == 4:
            assert b[pos] == 1 and b[pos+5] == 255
            pos += 6
        else:
            assert kind == 5, (file, pos, kind)
        records.append((kind, sub, b[begin:pos], begin))
    assert pos == len(b)
    return records


def analyze(summary, include_turns=False):
    roster = summary['final']['champions']
    teams = [[c['entity']['index'] for c in roster if c['team'] == t] for t in (0,1)]
    priority = {c['entity']['index']:0 for c in roster}
    current = {}
    moves = defaultdict(list)
    actions = defaultdict(Counter)
    turns = defaultdict(list)
    round_number = 1

    def order():
        groups = [sorted(ids, key=lambda i:(-priority[i],i)) for ids in teams]
        first = 0 if round_number % 2 else 1
        return [groups[t][i] for i in range(max(map(len,groups))) for t in (first,1-first) if i < len(groups[t])]

    sequence = order()
    offset = 0
    drafting = True
    picks = 0
    for kind, sub, data, byte in parse(Path(summary['source'])):
        if kind == 4:
            picks += 1
            continue
        if drafting:
            assert kind == 3
            if picks == sum(summary['final']['draftCounts']):
                drafting = False
            continue
        actor = sequence[offset]
        if kind == 3:
            actions[actor]['turns'] += 1
            if data[1] == 1:
                actions[actor]['fuel_exhaustions'] += 1
            turns[actor].append({'round':round_number,'actions':current.pop(actor,[]),'position':moves[actor][-1][1:] if moves[actor] else None})
            offset += 1
            if offset == len(sequence):
                round_number += 1
                sequence = order()
                offset = 0
        elif kind == 0:
            action = ACTION[sub]
            actions[actor][action] += 1
            current.setdefault(actor,[]).append(action)
            payload = data[2:]
            if sub == 0:
                priority[actor] = struct.unpack('<i',payload)[0]
            elif sub == 1:
                moves[actor].append((round_number,*struct.unpack('<ii',payload)))
            elif sub == 2:
                actions[actor]['attack_champion' if payload[0] == 1 else 'attack_camp' if payload[0] == 2 else 'attack_lock'] += 1
            elif sub == 3:
                slot = struct.unpack_from('<I',payload)[0]
                target_kind = payload[4]
                actions[actor][f'cast_slot_{slot}'] += 1
                if target_kind == 1:
                    actions[actor]['cast_champion_target'] += 1
            elif sub == 6:
                item,count = struct.unpack('<II',payload)
                actions[actor]['shards_bought'] += count
            elif sub == 9:
                actions[actor]['use_consumable_'+str(payload[0])] += 1
    result = {'source':summary['source'],'rounds_from_recorded_turns':round_number,'champions':[]}
    for c in roster:
        i = c['entity']['index']
        ts = turns[i]
        a = dict(actions[i])
        a['idle_turns'] = sum(not x['actions'] for x in ts)
        a['moving_turns'] = sum('move' in x['actions'] for x in ts)
        a['combat_turns'] = sum('attack' in x['actions'] or 'cast' in x['actions'] for x in ts)
        entry = {'id':i,'team':c['team'],'type':c['type'],'metrics':a,'moves':moves[i]}
        if include_turns:
            entry['turns'] = ts
        result['champions'].append(entry)
    return result


if __name__ == '__main__':
    summaries = [json.loads(p.read_text()) for p in sorted(ROOT.glob('match-*/*/summary.json'))]
    results = [analyze(s) for s in summaries]
    (ROOT/'recorded-action-metrics.json').write_text(json.dumps(results,indent=2)+'\n')
    for s,r in zip(summaries,results):
        label = Path(r['source']).parts[-3]+' '+Path(r['source']).parts[-2][:2]
        print(label,'round',r['rounds_from_recorded_turns'])
        for team in (0,1):
            ms = [c['metrics'] for c in r['champions'] if c['team']==team]
            print(' team',team, {k:sum(c.get(k,0) for c in ms) for k in ['turns','fuel_exhaustions','idle_turns','move','attack_champion','attack_camp','cast','recall','tribute','buy_consumable']})
