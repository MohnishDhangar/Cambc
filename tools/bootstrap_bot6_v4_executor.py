#!/usr/bin/env python3
"""Reconstruct Bot6's proven action executor from immutable v4 release source.

Requires the hash-pinned frozen ZIP, then applies *only* an explicit macro
policy overlay and distinct Bot6 banner. Never mutates Bot1 or frozen baselines.
Use --check after materializing to assert deterministic source generation.
"""
import argparse, hashlib, re, zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/"bots/Bot1/Bot1-v4.zip"
SHA256="b296e83d43e8b16709e655ee4470a526e9e84160ee02fbad0e8c483661e1a062"
NAMES=("bot.cpp","bot.h","draft.cpp","draft.h","main.cpp","random.h")

def replace_once(s, a, b, what):
    n=s.count(a)
    if n!=1: raise RuntimeError(f"Expected exactly one {what} anchor in frozen v4, found {n}")
    return s.replace(a,b,1)

def build():
    if hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()!=SHA256:
        raise RuntimeError("Frozen v4 ZIP checksum mismatch; refusing to bootstrap")
    with zipfile.ZipFile(ARCHIVE) as z:
        files={}
        for n in NAMES:
            p=[k for k in z.namelist() if k.endswith("/"+n)]
            if len(p)!=1:raise RuntimeError(f"Bad frozen v4 ZIP membership: {n}: {p}")
            files[n]=z.read(p[0]).decode("utf-8")
    bot=files["bot.cpp"]
    marker="""float v6_macro_adjust(float score, float value, float gold, int distance,
                      float work, float bank_trip, float danger_cost,
                      unsigned round, bool major) {
#ifndef V6_MACRO_MODE
#define V6_MACRO_MODE 5
#endif
    // 0: exact v4 reward, 1: economy, 2: tempo, 3: contest,
    // 4: objective, 5: adaptive. One compile-time policy per tournament bot.
    int mode=V6_MACRO_MODE;
    if (mode==5) {
        const auto me=cambc::self();
        if (round<300 && me.gold_count()<150) mode=1;
        else if (major && round>400) mode=4;
        else if (me.gem_count()>0) mode=2;
        else mode=2;
    }
    if (mode==0) return score;
    if (mode==1) {
        // Invest in early gold when upgrades still have time to pay back.
        return score * (round<650 ? (1.f+std::min(.65f, gold/std::max(1.f,value))) : 1.f);
    }
    if (mode==2) {
        // Penalize long walks harder; target high bankable gem throughput.
        return score * (0.8f + 12.f / std::max(12.f,12.f+distance*.9f+bank_trip*.15f));
    }
    if (mode==3) {
        // Prize accessible contested groups, but do not reward suicidal attacks.
        return score * (1.f+(danger_cost<1.f ? .2f : 0.f));
    }
    if (mode==4) {
        return score * (major?1.5f:(work>45.f?.8f:1.f));
    }
    return score;
}
"""
    bot=replace_once(bot, "void Bot::initialize() {",
                     marker+"\nvoid Bot::initialize() {", "macro-overlay declaration")
    anchor="float score = value / (distance + wait + work / (assigned + 1) + 6 + bank_trip * .35f);"
    swap=anchor+"""
        const float cost = expected_damage(g)/std::max(1.f,me.health());
        score=v6_macro_adjust(score,value,g.camp.gold_value()*.32f,distance,
                              work,bank_trip,cost,round,g.major);"""
    bot=replace_once(bot, anchor,swap,"camp utility")
    files["bot.cpp"]=bot
    main=files["main.cpp"]
    main=replace_once(main,'"Bot1 strategy v4 (SDK 2.2.5)"',
                      '"Bot6 v6.1 frozen-v4 executor + macro policy"',"unique version banner")
    files["main.cpp"]=main
    return files

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--check",action="store_true")
    a=ap.parse_args()
    out=ROOT/"bots/Bot6/src"
    files=build()
    for name,content in files.items():
        path=out/name
        if a.check:
            if not path.exists() or path.read_text()!=content:
                raise RuntimeError(f"Generated source drift: {path}")
        else:
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(content)
    print("Verified frozen v4 SHA256, materialized Bot6 v6.1 macro source",list(files),flush=True)

if __name__=="__main__":main()
