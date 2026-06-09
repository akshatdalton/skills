#!/usr/bin/env python3
"""embed_media.py <image> [<image> ...]

Print a JSON object mapping each image path -> a base64 data-URI. /visualize-via-html is
hard-constrained to be self-contained (zero external requests), so contact sheets must be
inlined as data-URIs rather than referenced as files. Missing paths map to null.
"""
import os, sys, json, base64, mimetypes


def data_uri(path):
    mime = mimetypes.guess_type(path)[0] or "image/jpeg"
    with open(path, "rb") as f:
        b = base64.b64encode(f.read()).decode("ascii")
    return f"data:{mime};base64,{b}"


def main():
    out = {}
    for p in sys.argv[1:]:
        out[p] = data_uri(p) if os.path.exists(p) else None
    print(json.dumps(out))


if __name__ == "__main__":
    main()
