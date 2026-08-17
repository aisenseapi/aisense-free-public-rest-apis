#!/usr/bin/env python3
"""
render.py - canonical corpus items to every baseline format.

Deterministic on purpose: the same canonical JSON must always produce byte
identical renders, or measurements stop being comparable between runs. This
Python implementation reproduces the renders the published numbers were
measured on byte for byte - `git status` after a run is the proof.

Formats: json_min, json_pretty, yaml, md, tsv, toon.
The TOON render follows the token-oriented notation's core ideas -
uniform arrays declared once as name[N]{fields} with bare comma rows,
indentation for nesting, unquoted strings - and is labelled an
approximation in every report. It exists to be beaten fairly, not to be
misrepresented.

Usage: python render.py  (from anywhere; paths are resolved from this file)
Stdlib only, Python 3.8+.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'corpus' / 'canonical'
DST = ROOT / 'corpus' / 'renders'

# ── scalar helpers ───────────────────────────────────────────────────────────

def sp_scalar(v):
    if v is None:
        return 'null'
    if v is True:
        return 'true'
    if v is False:
        return 'false'
    # integral floats print without the trailing .0, matching the renders
    # the published measurements were taken on
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def yaml_scalar(v):
    if v is None:
        return 'null'
    if v is True:
        return 'true'
    if v is False:
        return 'false'
    if isinstance(v, str) and re.search(r'[:#\[\]{}\n]|^\s|\s$', v):
        return '"' + v.replace('"', '\\"') + '"'
    return sp_scalar(v)


def is_uniform_array(v):
    if not isinstance(v, list) or not v:
        return False
    if not isinstance(v[0], dict):
        return False
    keys = list(v[0].keys())
    for row in v:
        if not isinstance(row, dict) or list(row.keys()) != keys:
            return False
        for cell in row.values():
            if isinstance(cell, (list, dict)):
                return False
    return True


def json_compact(v):
    return json.dumps(v, separators=(',', ':'))


def normalize(v):
    """Integral floats become ints (45.0 -> 45) in every render, JSON
    included - the convention the published measurements were taken on."""
    if isinstance(v, float) and v.is_integer():
        return int(v)
    if isinstance(v, list):
        return [normalize(x) for x in v]
    if isinstance(v, dict):
        return {k: normalize(x) for k, x in v.items()}
    return v

# ── yaml ─────────────────────────────────────────────────────────────────────

def to_yaml(v, ind=0):
    pad = '  ' * ind
    out = ''
    if isinstance(v, list):
        for item in v:
            if isinstance(item, (list, dict)):
                inner = to_yaml(item, ind + 1).lstrip()
                out += pad + '- ' + inner
            else:
                out += pad + '- ' + yaml_scalar(item) + '\n'
    elif isinstance(v, dict):
        for k, val in v.items():
            if isinstance(val, (list, dict)) and val:
                out += pad + str(k) + ':\n' + to_yaml(val, ind + 1)
            elif isinstance(val, (list, dict)):
                out += pad + str(k) + ': []\n'
            else:
                out += pad + str(k) + ': ' + yaml_scalar(val) + '\n'
    return out

# ── markdown ─────────────────────────────────────────────────────────────────

def to_md(v, depth=2):
    out = ''
    for k, val in v.items():
        if is_uniform_array(val):
            keys = list(val[0].keys())
            out += '#' * depth + f' {k}\n\n'
            out += '| ' + ' | '.join(keys) + ' |\n'
            out += '|' + ' --- |' * len(keys) + '\n'
            for row in val:
                out += '| ' + ' | '.join(sp_scalar(c) for c in row.values()) + ' |\n'
            out += '\n'
        elif isinstance(val, list):
            out += '#' * depth + f' {k}\n\n'
            for item in val:
                if isinstance(item, dict):
                    parts = []
                    for ik, iv in item.items():
                        rendered = json_compact(iv) if isinstance(iv, (list, dict)) else sp_scalar(iv)
                        parts.append(f'{ik}: {rendered}')
                    out += '- ' + ', '.join(parts) + '\n'
                elif isinstance(item, list):
                    out += '- ' + json_compact(item) + '\n'
                else:
                    out += '- ' + sp_scalar(item) + '\n'
            out += '\n'
        elif isinstance(val, dict):
            out += '#' * depth + f' {k}\n\n' + to_md(val, min(6, depth + 1))
        else:
            out += f'- **{k}**: ' + sp_scalar(val) + '\n'
    return out

# ── tsv ──────────────────────────────────────────────────────────────────────

def to_tsv(v):
    out = ''
    for k, val in v.items():
        if is_uniform_array(val):
            keys = list(val[0].keys())
            out += f'# {k}\n' + '\t'.join(keys) + '\n'
            for row in val:
                out += '\t'.join(sp_scalar(c) for c in row.values()) + '\n'
        elif isinstance(val, (list, dict)):
            out += f'{k}\t' + json_compact(val) + '\n'
        else:
            out += f'{k}\t' + sp_scalar(val) + '\n'
    return out

# ── toon approximation ───────────────────────────────────────────────────────

def toon_cell(v):
    if v is None:
        return 'null'
    if v is True:
        return 'true'
    if v is False:
        return 'false'
    if isinstance(v, str) and (',' in v or '\n' in v):
        return '"' + v.replace('"', '\\"') + '"'
    return sp_scalar(v)


def to_toon(v, ind=0):
    pad = '  ' * ind
    out = ''
    for k, val in v.items():
        if is_uniform_array(val):
            keys = list(val[0].keys())
            out += pad + f'{k}[{len(val)}]{{' + ','.join(keys) + '}:\n'
            for row in val:
                out += pad + '  ' + ','.join(toon_cell(c) for c in row.values()) + '\n'
        elif isinstance(val, list):
            out += pad + f'{k}[{len(val)}]:\n'
            for item in val:
                if isinstance(item, (list, dict)):
                    out += pad + '  -\n' + to_toon(item, ind + 2)
                else:
                    out += pad + '  - ' + toon_cell(item) + '\n'
        elif isinstance(val, dict):
            out += pad + f'{k}:\n' + to_toon(val, ind + 1)
        else:
            out += pad + f'{k}: ' + toon_cell(val) + '\n'
    return out

# ── main ─────────────────────────────────────────────────────────────────────

def main():
    DST.mkdir(parents=True, exist_ok=True)
    manifest = []
    for file in sorted(SRC.glob('*.json')):
        name = file.stem
        try:
            data = normalize(json.loads(file.read_bytes().decode('utf-8')))
        except ValueError:
            sys.stderr.write(f'bad canonical: {name}\n')
            sys.exit(1)

        renders = {
            'json_min': json_compact(data),
            'json_pretty': json.dumps(data, indent=4),
            'yaml': to_yaml(data),
            'md': to_md(data),
            'tsv': to_tsv(data),
            'toon': to_toon(data),
        }
        for fmt, text in renders.items():
            raw = text.encode('utf-8')
            (DST / f'{name}.{fmt}.txt').write_bytes(raw)
            manifest.append((name, fmt, len(raw)))

    lines = 'item\tformat\tbytes\n'
    for name, fmt, size in manifest:
        lines += f'{name}\t{fmt}\t{size}\n'
    (DST / 'manifest.tsv').write_bytes(lines.encode('utf-8'))
    print(f'{len(manifest)} renders written')


if __name__ == '__main__':
    main()
