#!/usr/bin/env python3
"""
probes.py - the atom tests.

Before composing a format, measure its alphabet. Each probe is one
construct repeated enough times for the per-construct cost to dominate the
calibration noise. The design questions each group answers:

  sigil_*   which section/marker characters are cheap across vocabularies
  key_*     what a key-value pair costs in each syntax style
  dict_*    whether a header dictionary plus short references beats
            repeating full keys (the core .su hypothesis)
  num_*     how numbers, timestamps and uuids tokenize
  sep_*     newline vs space vs tab vs pipe as separators
  ind_*     what indentation costs per level
  b64_*     the base64 trap, quantified once and for all

Usage: python probes.py
Stdlib only, Python 3.8+. Byte-identical output on every run.
"""

import base64
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DST = ROOT / 'probes'

R = 24  # repetitions per probe


def main():
    DST.mkdir(parents=True, exist_ok=True)
    probes = {}

    # sigils - each candidate marker, repeated on its own line
    sigils = {'hash': '#', 'tilde': '~', 'at': '@', 'pct': '%', 'pipe': '|',
              'semi': ';', 'bang': '!', 'caret': '^', 'gt': '>', 'dslash': '//'}
    for n, s in sigils.items():
        probes[f'sigil_{n}'] = f'{s} section\n' * R

    # key-value syntax styles, same 6 keys repeated
    kv = {'id': 1017, 'sku': 'NUT-M6', 'qty': 900, 'price': 2.95,
          'status': 'shipped', 'ts': 1786901617}
    json_lines = yaml_lines = eq_lines = short_lines = ''
    for _ in range(R):
        j = [f'"{k}":"{v}"' if isinstance(v, str) else f'"{k}":{v}' for k, v in kv.items()]
        json_lines += '{' + ','.join(j) + '}\n'
        yaml_lines += '\n'.join(f'{k}: {v}' for k, v in kv.items()) + '\n'
        eq_lines += ' '.join(f'{k}={v}' for k, v in kv.items()) + '\n'
        short_lines += '1017,NUT-M6,900,2.95,shipped,1786901617\n'
    probes['key_json'] = json_lines
    probes['key_yaml'] = yaml_lines
    probes['key_eq'] = eq_lines
    probes['key_none'] = short_lines  # values only, order carries meaning

    # the dictionary hypothesis: header once, short refs after
    probes['dict_full'] = 'status:shipped qty:900 price:2.95\n' * R
    probes['dict_ref'] = '!d s=status q=qty p=price\n' + 's:shipped q:900 p:2.95\n' * R

    # numbers and identifiers
    probes['num_unix'] = '1786901617\n' * R
    probes['num_iso'] = '2026-08-17T15:33:37+00:00\n' * R
    probes['num_decimal'] = '2.95 14.75 0.18 31.9\n' * R
    probes['num_uuid'] = '6f8c9e52-3f2c-4e73-9d3b-8d6c3f6d1c91\n' * R
    probes['num_short'] = '6f8c9e52\n' * R

    # separators around the same tokens
    words = 'alpha beta gamma delta epsilon zeta'
    probes['sep_space'] = (words + '\n') * R
    probes['sep_comma'] = (words.replace(' ', ',') + '\n') * R
    probes['sep_tab'] = (words.replace(' ', '\t') + '\n') * R
    probes['sep_pipe'] = (words.replace(' ', '|') + '\n') * R
    probes['sep_newline'] = (words.replace(' ', '\n') + '\n') * R

    # indentation cost per level
    probes['ind_none'] = 'key: value\n' * R
    probes['ind_2sp'] = '  key: value\n' * R
    probes['ind_4sp'] = '    key: value\n' * R
    probes['ind_tab'] = '\tkey: value\n' * R

    # the base64 trap, same payload three ways
    payload = 'The retry loop came from a stale cache key under the nightly job.'
    probes['b64_plain'] = (payload + '\n') * R
    probes['b64_base64'] = (base64.b64encode(payload.encode()).decode() + '\n') * R
    probes['b64_hex'] = (payload.encode().hex() + '\n') * R

    manifest = 'probe\tbytes\n'
    for name, text in probes.items():
        raw = text.encode('utf-8')
        (DST / f'{name}.txt').write_bytes(raw)
        manifest += f'{name}\t{len(raw)}\n'
    (DST / 'manifest.tsv').write_bytes(manifest.encode('utf-8'))
    print(f'{len(probes)} probes written')


if __name__ == '__main__':
    main()
