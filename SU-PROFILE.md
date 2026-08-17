# The SpeedUp profile (.su) v0.1

Not another serialization format. The world has TOON at a million weekly
downloads and at least five challengers, and our own measurements say the
headroom above plain TSV is a few percent bought with comprehension risk.
What was missing is a set of conventions that are MEASURED - across five
tokenizer vocabularies, with provider ground truth - instead of tuned on one
vendor and assumed to transfer. This is that set. Every rule cites its
number; the full data lives in [speedup/](speedup/).

A .su document is plain text a model writes to another model, or to itself.
It is valid input to any LLM with no decoder, and every rule degrades
gracefully: break one and you lose its saving, nothing else.

## The header

    ~su a2a

One line, first line. `~su` marks the profile (sigil choice is token-free:
all ten candidates we measured cost exactly one leading token in all five
vocabularies - the tilde is chosen for collision-avoidance, since `#`, `-`
and `>` carry Markdown meanings a model may act on). The second word is the
profile: `a2a` when the reader may be any model, `self` when the writer will
be its own reader. Under `self`, a writer may add vocabulary-specific tricks;
under `a2a` the rules below are the whole contract.

## The rules, each with its price tag

1. Tabular data declares columns once and sends values positionally.

       orders[20] id sku qty price status ts
       1001 BOLT-M8 50 9.99 shipped 1786900001
       1002 NUT-M8 200 4.5 shipped 1786900102

   Measured: 4.63 vs 7.03 tokens per key-value pair against minified JSON,
   minus 34 percent, and the mechanism behind TSV's 0.819x union score.
   This is where all the real savings live.

2. Fields separate with single spaces when values are space-free; a row
   containing a value with spaces switches that row to tab separation.
   Measured: space merges into the following token on all five vocabularies
   (free); tab, comma, pipe and newline each cost about 0.9 token per field.
   Tabs are the fallback because they cannot appear in unquoted prose by
   accident.

3. Outside tables, use full English keys, one per line, `key: value`.
   Measured: single-letter key dictionaries LOSE to full keys on four of
   five vocabularies (+3 percent), because `status`, `price` and their kin
   are already one token everywhere. Abbreviation is a tax dressed as a
   discount.

4. Structure is flat. Sections open with a sigil line (`~name`), never with
   indentation. Measured: any space indentation costs one token per line
   regardless of depth; tabs are free on only three of five vocabularies.

5. Numbers stay as plain decimals, timestamps as unix seconds.
   Measured: unix beats ISO-8601 on every vocabulary; but the union splits
   on digits (4 tokens per 10-digit number on o200k and DeepSeek, 10 on
   Qwen, Gemma and Mistral), so no digit-packing scheme transfers - leave
   numbers alone.

6. Never base64, never hex, never "compressed" glyphs.
   Measured: base64 costs 3.9-4.6x the plaintext it encodes; hex up to
   8.75x on digit-splitting vocabularies. If binary must travel, send a URL
   to it.

7. Empty is `-`, null is `null`, and a cell is never simply omitted from a
   row - positional encoding dies silently when columns drift.

## Where the profile deliberately stops

Positional values are the whole saving and also the known risk: independent
accuracy benchmarks price aggressive tabular compression at several points of
task accuracy on weaker models. So the profile's own rule 8:

8. Use tables for machine-verifiable payloads - records a program or test
   will check. Keep `key: value` for anything a model must reason about
   where a misread costs more than the tokens saved. When in doubt, keys.

Comprehension across the vocabulary union is the unfinished measurement, and
until it is done, no .su document should carry a claim beyond what the
numbers above support.

## Example

    ~su a2a
    goal: Deploy build 42 if the smoke suite passes
    budget_tokens: 50000
    ~steps[4] n tool status result
    1 run_tests done "109 passed"
    2 create_human_approval done "approved by ops"
    3 webhook_schedule pending -
    4 read_webhook_capture pending -
    ~notes
    Roll back with the build 41 image if step 4 shows 5xx from the canary.

Version 0.1, 2026-08-17. Changes to this profile require a rerun of the
measurement rig in [speedup/](speedup/) - rules follow numbers here, not the
other way around.
