#!/usr/bin/env python3
"""
measure.py - the token oracle. Feeds a text file to a provider and reads
back the provider's own prompt token count, which is the only ground truth.

  python measure.py openai gpt-4.1-nano file.txt         -> raw prompt tokens
  python measure.py ollama deepseek-v4-flash:preview f   -> raw prompt tokens
  python measure.py <provider> <model> --calibrate       -> scaffold tokens (empty msg)
  python measure.py <provider> <model> --all <outfile>   -> TSV over corpus + probes

Keys are read from the SPEEDUP_OPENAI_KEY / SPEEDUP_OLLAMA_KEY environment
variables, or from a .o-tokens file next to the speedup README (gitignored,
one "openai:sk-..." / "ollama:..." per line). They are never printed.

Completion is capped at 1 token; the cost of a full --all run on a nano
model is on the order of a few hundredths of a dollar, logged to
results/cost-log.txt.

Stdlib only, Python 3.8+. No pip installs, no curl.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

ENDPOINTS = {
    'openai': ('https://api.openai.com/v1/chat/completions', 60),
    'ollama': ('https://ollama.com/api/chat', 120),
}


def key_for(provider):
    env = os.environ.get(f'SPEEDUP_{provider.upper()}_KEY')
    if env:
        return env.strip()
    tokens = ROOT / '.o-tokens'
    if tokens.exists():
        for line in tokens.read_text(encoding='utf-8').splitlines():
            if line.startswith(provider + ':'):
                return line.split(':', 1)[1].strip()
    sys.exit(f'no key for {provider}: set SPEEDUP_{provider.upper()}_KEY '
             f'or add a "{provider}:..." line to {tokens}')


def build_request(provider, model, text):
    if provider == 'openai':
        return {
            'model': model,
            'messages': [{'role': 'user', 'content': text}],
            'max_completion_tokens': 1,
        }
    return {
        'model': model,
        'messages': [{'role': 'user', 'content': text}],
        'stream': False,
        'options': {'num_predict': 1},
    }


def oracle(provider, model, key, path):
    """path '' means empty message (calibration). Returns tokens or -1."""
    text = Path(path).read_bytes().decode('utf-8') if path else ''
    url, timeout = ENDPOINTS[provider]
    req = urllib.request.Request(
        url,
        data=json.dumps(build_request(provider, model, text)).encode('utf-8'),
        headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        sys.stderr.write(e.read().decode('utf-8', 'replace')[:200] + '\n')
        return -1
    except (urllib.error.URLError, TimeoutError, ValueError) as e:
        sys.stderr.write(f'{type(e).__name__}: {e}\n')
        return -1
    usage = body.get('usage') or {}
    if 'prompt_tokens' in usage:
        return usage['prompt_tokens']
    if 'prompt_eval_count' in body:
        return body['prompt_eval_count']
    sys.stderr.write(json.dumps(body)[:200] + '\n')
    return -1


def main():
    if len(sys.argv) < 4:
        sys.exit(__doc__.strip())
    provider, model, arg = sys.argv[1], sys.argv[2], sys.argv[3]
    if provider not in ENDPOINTS:
        sys.exit(f'provider must be one of: {", ".join(ENDPOINTS)}')
    key = key_for(provider)

    if arg == '--calibrate':
        print(oracle(provider, model, key, ''))
        return

    if arg == '--all':
        if len(sys.argv) < 5:
            sys.exit('usage: measure.py <provider> <model> --all <outfile>')
        out = Path(sys.argv[4])
        cal = oracle(provider, model, key, '')
        calls = 1
        lines = ['item\tkind\tbytes\traw_tokens\tcal']
        for kind, folder in (('render', ROOT / 'corpus' / 'renders'),
                             ('probe', ROOT / 'probes')):
            for f in sorted(folder.glob('*.txt')):
                tokens = oracle(provider, model, key, f)
                calls += 1
                lines.append(f'{f.stem}\t{kind}\t{f.stat().st_size}\t{tokens}\t{cal}')
                print(f'  {f.stem}: {tokens}', file=sys.stderr)
        out.write_bytes(('\n'.join(lines) + '\n').encode('utf-8'))
        stamp = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
        log = ROOT / 'results' / 'cost-log.txt'
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open('a', encoding='utf-8', newline='\n') as fh:
            fh.write(f'{stamp} {provider} {model} calls={calls} out={out.name}\n')
        print(f'wrote {out} ({calls} calls, calibration {cal})')
        return

    print(oracle(provider, model, key, arg))


if __name__ == '__main__':
    main()
