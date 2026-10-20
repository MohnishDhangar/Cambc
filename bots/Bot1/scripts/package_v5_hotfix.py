#!/usr/bin/env python3
"""Create the source-only ZIP accepted by the CAMBC 2026a website.

Archives exactly src/{bot.cpp,bot.h,draft.cpp,draft.h,main.cpp,random.h}.
Defaults to the exact Git commit whose v5 WASM passed the 18-match smoke suite.
Do not add CMake, WASM, results, manifest or a surrounding Bot1 directory.
"""
import argparse
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

TESTED_REF = "48c72e9a1edf71b1697d0ce90709f6d65602c8bd"
SOURCE_FILES = ("bot.cpp", "bot.h", "draft.cpp", "draft.h", "main.cpp", "random.h")

def git_file(ref: str, name: str) -> bytes:
    return subprocess.check_output([
        "git", "show", f"{ref}:bots/Bot1/src/{name}"
    ])

def package(ref: str, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    payloads = {f"src/{name}": git_file(ref, name) for name in SOURCE_FILES}
    if not all(payloads.values()):
        raise RuntimeError("Empty source file detected")
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for arcname, payload in payloads.items():
            info = zipfile.ZipInfo(arcname, (2026, 10, 20, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            z.writestr(info, payload)
    with zipfile.ZipFile(output) as z:
        assert z.testzip() is None, "ZIP CRC check failed"
        assert z.namelist() == list(payloads), f"Unexpected ZIP layout: {z.namelist()}"
        for name, source in payloads.items():
            assert z.read(name) == source, f"Packaging altered {name}"
    sha = lambda b: hashlib.sha256(b).hexdigest()
    manifest = {
        "source_ref": ref,
        "archive": output.name,
        "archive_sha256": sha(output.read_bytes()),
        "format": "CAMBC 2026a source ZIP: six files immediately inside src/",
        "files": {k: {"bytes": len(v), "sha256": sha(v)} for k, v in payloads.items()},
        "note": "Official site accepts this source ZIP; no WASM upload required.",
        "test_evidence": "https://github.com/MohnishDhangar/Cambc/actions/runs/39418781975"
    }
    manifest_path = output.with_suffix(".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"archive": str(output), "zip_sha256": manifest["archive_sha256"],
                      "source_ref": ref, "members": list(payloads),
                      "size_bytes": output.stat().st_size}, indent=2))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ref", default=TESTED_REF,
                        help="Git revision containing all six bot source files")
    parser.add_argument("--output", default="submissions/Bot1-v5-hotfix.zip",
                        type=Path)
    args = parser.parse_args()
    package(args.ref, args.output)

if __name__ == "__main__":
    main()
