#!/usr/bin/env python3
"""Trace our bot's per-champion actions on two permitted objective maps; no heldouts."""
import collections, hashlib, json, os, re, subprocess, zipfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "match-data/analysis/v6-contest-siege-diagnostics"
MAPS = ("00contest",)
REVISIONS = {"v6.8": "0ddd5338b94db824f9f53261a17f020490b7017f"}
FILES = ("bot.cpp","bot.h","draft.cpp","draft.h","main.cpp","random.h")
ENV = {**os.environ,"CAMBC_NO_UPDATE_CHECK":"1","CAMBC_OFFLINE":"1"}
INSERT = r'''
        if (!cambc::is_draft() && (cambc::round_number() < 20 || cambc::round_number() % 25 == 0)) {
            const auto ch = cambc::self();
            const auto p = ch.position();
            std::cout << "OBS," << cambc::round_number()
                << "," << static_cast<unsigned>(static_cast<cambc::handle_champion_t>(ch))
                << "," << static_cast<int>(ch.champion_name())
                << "," << p.x << "," << p.y
                << "," << static_cast<int>(ch.is_alive())
                << "," << ch.health() << "," << ch.gem_count()
                << "," << ch.gold_count() << "," << bot.action << "\n";
        }
'''
INSERT += r'''
        if (!cambc::is_draft() && cambc::round_number() == 1)
            for (auto altar : cambc::map::altars().positions())
                std::cout << "ALTAR," << altar.x << "," << altar.y << "\n";
'''
def run(args, timeout=300):
    p = subprocess.run(args,cwd=ROOT,env=ENV,capture_output=True,text=True,timeout=timeout)
    if p.returncode: raise RuntimeError(str(args)+": "+(p.stdout+p.stderr)[-1000:])
    return p
def make_bots():
    with zipfile.ZipFile(ROOT/"bots/Bot1/Bot1-v4.zip") as z:
        for name in z.namelist():
            if not name.endswith((".cpp",".h")): continue
            d=ROOT/"bots/Bot4Frozen/src"/Path(name).name;d.parent.mkdir(parents=True,exist_ok=True);d.write_bytes(z.read(name))
    for label,sha in REVISIONS.items():
        name="Bot6Trace68" if label=="v6.8" else "Bot6Trace14"
        for file in FILES:
            content=subprocess.check_output(["git","show",sha+":bots/Bot6/src/"+file],cwd=ROOT)
            if file=="main.cpp":
                text=content.decode()
                needle="        cambc::end_turn();"
                assert text.count(needle)==1
                content=text.replace(needle,INSERT+"\n"+needle).encode()
            if file=="bot.cpp":
                text=content.decode()
                needle="    auto origin = me.position();\n    float current = field.get(origin);"
                assert text.count(needle)==1
                replacement=needle+r'''
    if (me.gem_count() && round % 100 == 0)
        std::cout << "NAVFIELD," << round << "," << origin.x << "," << origin.y
                  << "," << current << "," << static_cast<int>(escape) << "\n";
'''
                text=text.replace(needle,replacement)
                needle2="    if (goals.is_empty()) return false;"
                assert text.count(needle2)==1
                replacement2=r'''    if (goals.is_empty()) {
        if (me.gem_count() && round % 100 == 0)
            std::cout << "NAVEMPTY," << round << "," << me.position().x << "," << me.position().y << "\n";
        return false;
    }'''
                content=text.replace(needle2,replacement2).encode()
            if file=="bot.cpp":
                text=content.decode()
                init_needle="    me.set_priority(100 - slot);"
                assert text.count(init_needle)==1
                text=text.replace(init_needle,r'''
    if (slot==0) {
        std::cout << "MAPCLASS," << static_cast<int>(objective_map)
                  << "," << static_cast<int>(caster_build)
                  << "," << groups.size() << "\n";
        for (const auto& g : groups)
            if (g.camp.gem_value())
                std::cout << "GEMGROUP," << g.camp.gem_value() << ","
                    << g.health << "," << g.damage << "," << g.members
                    << "," << static_cast<int>(g.major) << ","
                    << g.centre.x << "," << g.centre.y << "\n";
    }
''' + init_needle)
                plan_needle="    if (returning) { recover(); return; }"
                assert text.count(plan_needle)==1
                text=text.replace(plan_needle,r'''
    if (round % 100 == 0)
        std::cout << "STRATEGY," << round << "," << slot << ","
            << me.gem_count() << "," << me.gold_count() << ","
            << static_cast<int>(objective_map) << ","
            << static_cast<int>(caster_build) << ","
            << target << "," << static_cast<int>(returning) << "\n";
''' + plan_needle)
                siege_needle='    if (firing.is_empty()) return false;'
                assert text.count(siege_needle)==1
                text=text.replace(siege_needle,r'''
    if (round % 100 == 0)
        std::cout << "SIEGEPATH," << round << "," << slot << ","
                  << index << "," << static_cast<int>(firing.is_empty())
                  << "," << me.health() << "," << me.focus() << "\n";
''' + siege_needle)
                content=text.encode()
            path=ROOT/"bots"/name/"src"/file;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(content)
    for name in ("Bot4Frozen","Bot6Trace68"):
        run(["cambc","build",name,"--release"],timeout=260)
        print("compiled",name,flush=True)
def main():
    make_bots()
    OUT.mkdir(parents=True,exist_ok=True)
    result=[]
    for label in REVISIONS:
      name="Bot6Trace68" if label=="v6.8" else "Bot6Trace14"
      for mapname in MAPS:
       for side in "AB":
        out=OUT/"replays"/(label+"-"+mapname+"-"+side);out.mkdir(parents=True,exist_ok=True)
        team=("teamA" if side=="A" else "teamB")
        bots=(name,"Bot4Frozen") if side=="A" else ("Bot4Frozen",name)
        run(["cambc","run",*bots,"--release","--map",str(ROOT/"maps"/(mapname+".map26a")),
             "--out-dir",str(out),"--statistics",str(out/"stats.json"),"--json"],timeout=300)
        st=json.loads((out/"stats.json").read_text())
        score=lambda t:sum(int(c["metrics"]["submittedGems"]) for c in st["champions"] if c["team"]==t)
        replay=list(out.glob("*.repl26a"))
        assert len(replay)==1
        with zipfile.ZipFile(replay[0]) as z:
            txt=z.read("team-"+side.lower()+".stdout").replace(b"\0",b"").decode(errors="replace")
        trace=[]
        for ln in txt.splitlines():
            if not ln.startswith("OBS,"):continue
            parts=ln.split(",",10)
            if len(parts)!=11: continue
            try:
                rnd,handle,champ,x,y,alive,hp,bag,gold=map(float,parts[1:10])
            except ValueError: continue
            trace.append({"round":int(rnd),"champion":int(champ),"id":int(handle),
                          "x":int(x),"y":int(y),"alive":bool(alive),"hp":hp,
                          "bag":int(bag),"gold":int(gold),"action":parts[10]})
        debug=[ln for ln in txt.splitlines() if ln.startswith(("ALTAR,","NAVFIELD,","NAVEMPTY,","MAPCLASS,","GEMGROUP,","STRATEGY,","SIEGEPATH,"))]
        reports={"version":label,"map":mapname,"side":side,"games_rounds":st["match"]["roundsStarted"],
                 "gems":score(team),"opponent_gems":score("teamB" if side=="A" else "teamA"),
                 "samples":len(trace),"sample_actions":dict(collections.Counter(t["action"] for t in trace)),
                 "sample_holding_gems":sum(x["bag"]>0 for x in trace),
                 "sample_positions":len(set((x["id"],x["x"],x["y"]) for x in trace)),
                 "debug":debug,"trace":trace}
        result.append(reports)
        print(label,mapname,side,"gems",reports["gems"],"samples",len(trace),flush=True)
    (OUT/"summary.json").write_text(json.dumps(result,indent=2)+"\n")
if __name__=="__main__":main()
