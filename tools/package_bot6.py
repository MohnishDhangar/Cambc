#!/usr/bin/env python3
"""Build a deterministic six-file CAMBC Bot6 source ZIP and SHA-256 manifest."""
import argparse, hashlib, json, zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FILES=("bot.cpp","bot.h","draft.cpp","draft.h","main.cpp","random.h")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--out",default="submissions/Bot6-v6.0-macro.zip")
    ns=ap.parse_args()
    src=ROOT/"bots/Bot6/src"
    dest=ROOT/ns.out
    dest.parent.mkdir(parents=True,exist_ok=True)
    manifest={"release":"v6.0-macro-experimental","format":"CAMBC source ZIP with exactly six src/ files",
              "status":"requires successful current-client smoke test",
              "files":{}}
    with zipfile.ZipFile(dest,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name in FILES:
            contents=(src/name).read_bytes()
            meta=zipfile.ZipInfo("src/"+name,(1980,1,1,0,0,0))
            meta.compress_type=zipfile.ZIP_DEFLATED
            meta.external_attr=(0o644<<16)
            z.writestr(meta,contents,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
            manifest["files"]["src/"+name]={"bytes":len(contents),"sha256":hashlib.sha256(contents).hexdigest()}
    with zipfile.ZipFile(dest) as z:
        if z.namelist()!=["src/"+n for n in FILES] or z.testzip() is not None:
            raise ValueError("Submission ZIP validation failed")
    manifest["archive_sha256"]=hashlib.sha256(dest.read_bytes()).hexdigest()
    manifest["archive_bytes"]=dest.stat().st_size
    (dest.parent/(dest.stem+".manifest.json")).write_text(json.dumps(manifest,indent=2)+"\n")
    print(json.dumps({"archive":str(dest),"archive_sha256":manifest["archive_sha256"],
                     "files":len(FILES)},indent=2))
if __name__=="__main__":main()
