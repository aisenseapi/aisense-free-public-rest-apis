# Tokenizer physics - phase 0 measurement report

Date: 2026-08-17. Inputs: `results/raw/*.tsv` (one TSV per oracle model),
`corpus/renders/manifest.tsv`, `probes/manifest.tsv`, `tools/probes.py`.

Every number below is net tokens: the provider's own prompt-token count minus
that model's calibration constant (empty-message scaffold). Token counts are
provider ground truth (`usage.prompt_tokens` / `prompt_eval_count`), not a
local tokenizer.

Oracle models and calibration constants:

| Column head | Model | Family | cal |
|---|---|---|---|
| nano | openai gpt-4.1-nano | o200k | 7 |
| dsk | deepseek-v4-flash | DeepSeek BPE | 4 |
| qwn | qwen3.5 | Qwen BPE | 10 |
| gma | gemma4 | SentencePiece | 13 |
| mis | mistral-large-3 | Tekken | 3 (estimated, see below) |

Data quality:

- Failed measurements excluded (raw_tokens = -1): **0 rows**. All 63
  measurements succeeded on all five models (315 rows total).
- Exception: the mistral **calibration** call failed (cal recorded as -1 in
  `ollama_mistral-large-3.tsv`). The scaffold constant was recovered from
  internal consistency instead: 19 probes have per-line costs that must be
  integral (all 10 sigils, all 5 separators, num_unix/short/uuid, b64_hex),
  and every one satisfies raw = 24k + 3 exactly. cal = 3 is used for mistral
  throughout and is flagged as estimated, not measured.
- qwen and gemma per-repetition values carry a constant -0.04 offset (their
  calibration seems to include ~1 token that belongs to content, likely BOS
  accounting). It cancels in every comparison and is ignored.

## 1. Corpus: net tokens per item x format x model

30 render measurements per model. Formats: minified JSON, pretty JSON, YAML,
Markdown, TSV, and a TOON approximation.

| item | format | nano | dsk | qwn | gma | mis |
|---|---|---|---|---|---|---|
| agent_plan | json_min | 242 | 268 | 252 | 265 | 272 |
| agent_plan | json_pretty | 379 | 401 | 442 | 454 | 402 |
| agent_plan | yaml | 283 | 299 | 306 | 320 | 304 |
| agent_plan | md | 257 | 275 | 267 | 279 | 277 |
| agent_plan | tsv | 240 | 267 | 252 | 265 | 269 |
| agent_plan | toon | 289 | 305 | 314 | 328 | 309 |
| api_response | json_min | 69 | 73 | 86 | 88 | 91 |
| api_response | json_pretty | 105 | 109 | 138 | 138 | 127 |
| api_response | yaml | 73 | 78 | 93 | 95 | 96 |
| api_response | md | 102 | 96 | 109 | 111 | 114 |
| api_response | tsv | 66 | 72 | 87 | 88 | 90 |
| api_response | toon | 73 | 78 | 93 | 95 | 96 |
| config | json_min | 86 | 97 | 93 | 105 | 103 |
| config | json_pretty | 131 | 140 | 157 | 169 | 146 |
| config | yaml | 97 | 106 | 106 | 119 | 113 |
| config | md | 127 | 124 | 123 | 135 | 130 |
| config | tsv | 85 | 95 | 94 | 107 | 101 |
| config | toon | 99 | 108 | 108 | 121 | 115 |
| note | json_min | 141 | 148 | 145 | 148 | 154 |
| note | json_pretty | 170 | 176 | 190 | 192 | 180 |
| note | yaml | 147 | 151 | 157 | 160 | 156 |
| note | md | 155 | 155 | 159 | 162 | 160 |
| note | tsv | 138 | 144 | 146 | 150 | 149 |
| note | toon | 151 | 155 | 161 | 164 | 160 |
| orders | json_min | 690 | 721 | 904 | 908 | 933 |
| orders | json_pretty | 1134 | 1165 | 1492 | 1497 | 1358 |
| orders | yaml | 896 | 942 | 1109 | 1116 | 1121 |
| orders | md | 563 | 571 | 797 | 804 | 788 |
| orders | tsv | 434 | 465 | 648 | 679 | 682 |
| orders | toon | 491 | 480 | 708 | 702 | 722 |

Per-format totals (sum over the 5 corpus items):

| format | nano | dsk | qwn | gma | mis |
|---|---|---|---|---|---|
| json_min | 1228 | 1307 | 1480 | 1514 | 1553 |
| json_pretty | 1919 | 1991 | 2419 | 2450 | 2213 |
| yaml | 1496 | 1576 | 1771 | 1810 | 1790 |
| md | 1204 | 1221 | 1455 | 1491 | 1469 |
| tsv | 963 | 1043 | 1227 | 1289 | 1291 |
| toon | 1103 | 1126 | 1384 | 1410 | 1402 |

Ratio vs json_min, per model, and the union average (mean of the five
per-model ratios). The union average is the number the charter scores on.

| format | nano | dsk | qwn | gma | mis | **union avg** |
|---|---|---|---|---|---|---|
| json_min | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | **1.000** |
| json_pretty | 1.563 | 1.523 | 1.634 | 1.618 | 1.425 | **1.553** |
| yaml | 1.218 | 1.206 | 1.197 | 1.196 | 1.153 | **1.194** |
| md | 0.980 | 0.934 | 0.983 | 0.985 | 0.946 | **0.966** |
| tsv | 0.784 | 0.798 | 0.829 | 0.851 | 0.831 | **0.819** |
| toon | 0.898 | 0.862 | 0.935 | 0.931 | 0.903 | **0.906** |

The format ranking is identical on all five models:
tsv < toon < md < json_min < yaml < json_pretty. TSV beats the TOON
approximation on every model, by 7.4% (dsk) to 12.7% (nano).

Where the win comes from - union-average ratio vs json_min, per item:

| format | agent_plan | api_response | config | note | orders |
|---|---|---|---|---|---|
| json_pretty | 1.602 | 1.517 | 1.536 | 1.234 | 1.603 |
| yaml | 1.165 | 1.068 | 1.118 | 1.048 | 1.252 |
| md | 1.044 | 1.315 | 1.325 | 1.075 | 0.844 |
| tsv | 0.995 | 0.989 | 0.996 | 0.988 | 0.694 |
| toon | 1.190 | 1.068 | 1.139 | 1.075 | 0.741 |

The entire aggregate win is `orders`, the one genuinely tabular item (TSV
0.694, TOON 0.741). On the four non-tabular items TSV is within 1.2% of
json_min and TOON is 7-19% *worse* than json_min. Totals are also
byte-weighted: orders is the largest item and dominates the sums.

## 2. Probe atoms: tokens per repetition (net / 24)

Each probe repeats one construct R = 24 times (`tools/probes.py`); dividing
net tokens by 24 gives the marginal cost of one instance, with calibration
noise diluted 24x. Values include the trailing newline of each repetition.
dict_ref additionally contains one non-repeated header line (noted below).

| probe | nano | dsk | qwn | gma | mis | union avg |
|---|---|---|---|---|---|---|
| sigil_hash | 3.00 | 3.00 | 2.96 | 2.96 | 3.00 | 2.98 |
| sigil_tilde | 3.00 | 3.00 | 2.96 | 2.96 | 3.00 | 2.98 |
| sigil_at | 3.00 | 3.00 | 2.96 | 2.96 | 3.00 | 2.98 |
| sigil_pct | 3.00 | 3.00 | 2.96 | 2.96 | 3.00 | 2.98 |
| sigil_pipe | 3.00 | 3.00 | 2.96 | 2.96 | 3.00 | 2.98 |
| sigil_semi | 3.00 | 3.00 | 2.96 | 2.96 | 3.00 | 2.98 |
| sigil_bang | 3.00 | 3.00 | 2.96 | 2.96 | 3.00 | 2.98 |
| sigil_caret | 3.00 | 3.00 | 2.96 | 2.96 | 3.00 | 2.98 |
| sigil_gt | 3.00 | 3.00 | 2.96 | 2.96 | 3.00 | 2.98 |
| sigil_dslash | 3.00 | 3.00 | 2.96 | 2.96 | 3.00 | 2.98 |
| key_json | 35.00 | 36.00 | 46.96 | 46.96 | 46.00 | 42.18 |
| key_yaml | 37.00 | 38.00 | 47.96 | 47.96 | 48.00 | 43.78 |
| key_eq | 28.00 | 30.00 | 38.96 | 39.96 | 39.00 | 35.18 |
| key_none | 21.00 | 21.00 | 31.96 | 32.96 | 32.00 | 27.78 |
| dict_full | 13.00 | 14.00 | 15.96 | 15.96 | 16.00 | 14.98 |
| dict_ref | 13.46 | 13.50 | 16.42 | 16.46 | 16.50 | 15.27 |
| num_unix | 5.00 | 5.00 | 10.96 | 10.96 | 11.00 | 8.58 |
| num_iso | 17.00 | 17.00 | 25.96 | 25.96 | 26.00 | 22.38 |
| num_decimal | 16.00 | 16.00 | 20.96 | 20.96 | 21.00 | 18.98 |
| num_uuid | 34.00 | 34.00 | 36.96 | 36.96 | 37.00 | 35.78 |
| num_short | 8.00 | 8.00 | 8.96 | 8.96 | 9.00 | 8.58 |
| sep_space | 8.00 | 8.00 | 7.96 | 6.96 | 7.00 | 7.58 |
| sep_comma | 12.00 | 12.00 | 11.96 | 11.96 | 12.00 | 11.98 |
| sep_tab | 12.00 | 12.00 | 10.96 | 11.96 | 12.00 | 11.78 |
| sep_pipe | 13.00 | 12.00 | 12.96 | 11.96 | 12.00 | 12.38 |
| sep_newline | 13.00 | 12.00 | 12.96 | 11.96 | 12.00 | 12.38 |
| ind_none | 4.00 | 4.00 | 3.96 | 3.96 | 4.00 | 3.98 |
| ind_2sp | 5.00 | 5.00 | 4.92 | 4.92 | 5.00 | 4.97 |
| ind_4sp | 5.00 | 5.00 | 4.92 | 4.92 | 5.00 | 4.97 |
| ind_tab | 4.00 | 5.00 | 3.96 | 4.92 | 4.00 | 4.38 |
| b64_plain | 14.00 | 15.00 | 14.96 | 14.96 | 15.00 | 14.78 |
| b64_base64 | 58.00 | 59.00 | 62.96 | 57.96 | 69.00 | 61.38 |
| b64_hex | 58.00 | 58.00 | 130.96 | 130.96 | 131.00 | 101.78 |

### Sigils

All ten candidates cost exactly the same on all five vocabularies: 3 tokens
per `X section\n` line (sigil + " section" + newline), including the
two-character `//`. There is no cheapest sigil - `# ~ @ % | ; ! ^ >` and `//`
are interchangeable at 1 token each in line-leading position on every
tokenizer in the union. Sigil choice is therefore free to be decided by
comprehension results and collision-avoidance (phase 3), not by token cost.

### Key-value syntax (6 pairs per line; cost per pair = per-rep / 6)

| style | example | nano | dsk | qwn | gma | mis | union avg |
|---|---|---|---|---|---|---|---|
| key_json | `"qty":900` | 5.83 | 6.00 | 7.83 | 7.83 | 7.67 | 7.03 |
| key_yaml | `qty: 900` | 6.17 | 6.33 | 7.99 | 7.99 | 8.00 | 7.30 |
| key_eq | `qty=900` | 4.67 | 5.00 | 6.49 | 6.66 | 6.50 | 5.86 |
| key_none | `900` (position) | 3.50 | 3.50 | 5.33 | 5.49 | 5.33 | 4.63 |

Relative to bare positional values (key_none), naming each field costs on the
union average: `k=v` +1.23 tokens per pair (+27%), JSON quoting +2.40 (+52%),
YAML +2.67 (+58%). `k=v` beats JSON by 1.17 tokens per pair (17% cheaper) and
YAML is the most expensive keyed style on every model.

### The dictionary hypothesis: dict_ref vs dict_full

dict_full: `status:shipped qty:900 price:2.95` x24. dict_ref: one header
`!d s=status q=qty p=price` then `s:shipped q:900 p:2.95` x24.

| model | dict_full (net) | dict_ref (net) | ref - full | ref/full |
|---|---|---|---|---|
| nano | 312 | 323 | +11 | 1.035 |
| dsk | 336 | 324 | -12 | 0.964 |
| qwn | 383 | 394 | +11 | 1.029 |
| gma | 383 | 395 | +12 | 1.031 |
| mis | 384 | 396 | +12 | 1.031 |

**dict_ref loses to dict_full on 4 of 5 models** (+3% each) and wins only on
deepseek (-3.6%). The core .sp hypothesis fails at this scale: common English
keys like `status` and `price` are already single tokens in all five
vocabularies, so abbreviating them to one letter saves nothing per row, while
the header line is pure overhead that 24 rows never amortize. This is a
model-disagreement result: the union average says no (1.018), one vocabulary
says yes.

### Numbers, timestamps, identifiers (per line, incl. newline)

| probe | content | nano | dsk | qwn | gma | mis | union avg |
|---|---|---|---|---|---|---|---|
| num_unix | `1786901617` | 5.00 | 5.00 | 10.96 | 10.96 | 11.00 | 8.58 |
| num_iso | `2026-08-17T15:33:37+00:00` | 17.00 | 17.00 | 25.96 | 25.96 | 26.00 | 22.38 |
| num_decimal | `2.95 14.75 0.18 31.9` | 16.00 | 16.00 | 20.96 | 20.96 | 21.00 | 18.98 |
| num_uuid | full 36-char uuid | 34.00 | 34.00 | 36.96 | 36.96 | 37.00 | 35.78 |
| num_short | `6f8c9e52` | 8.00 | 8.00 | 8.96 | 8.96 | 9.00 | 8.58 |

The union splits into two camps. o200k and DeepSeek chunk digit runs (a
10-digit unix timestamp is 4 tokens); Qwen, Gemma and Mistral tokenize
digit-by-digit (the same timestamp is 10 tokens, one per digit - confirmed
exactly on mistral where raw = bytes + 3 for every pure-digit probe). Unix
beats ISO on every model, but by 3.4x on nano/dsk and only 2.4x on the
digit-splitters. A UUID costs 33-36 tokens everywhere (~1 token per
character on all five); truncating to 8 hex chars costs 7-8.

### Separators (6 words per line, incl. newline)

| probe | nano | dsk | qwn | gma | mis | union avg |
|---|---|---|---|---|---|---|
| sep_space | 8.00 | 8.00 | 7.96 | 6.96 | 7.00 | 7.58 |
| sep_tab | 12.00 | 12.00 | 10.96 | 11.96 | 12.00 | 11.78 |
| sep_comma | 12.00 | 12.00 | 11.96 | 11.96 | 12.00 | 11.98 |
| sep_pipe | 13.00 | 12.00 | 12.96 | 11.96 | 12.00 | 12.38 |
| sep_newline | 13.00 | 12.00 | 12.96 | 11.96 | 12.00 | 12.38 |

Space is the only free separator: BPE merges ` word` into one token, so six
space-separated words cost ~7 tokens per line. Every other separator (comma,
tab, pipe, even newline) breaks the merge and costs ~+0.9 token per field on
every model - a 55-60% surcharge per line on this content. The five
vocabularies agree within 1 token per line.

### Indentation (extra tokens per line vs no indent)

| probe | nano | dsk | qwn | gma | mis | union avg |
|---|---|---|---|---|---|---|
| ind_2sp | +1.00 | +1.00 | +0.96 | +0.96 | +1.00 | +0.98 |
| ind_4sp | +1.00 | +1.00 | +0.96 | +0.96 | +1.00 | +0.98 |
| ind_tab | 0.00 | +1.00 | 0.00 | +0.96 | 0.00 | +0.39 |

Any leading-space indentation costs exactly 1 token per line, and 4 spaces
cost the same as 2 (the space run merges into one token). A leading tab is
free on nano, qwen and mistral but +1 on deepseek and gemma - a 3-vs-2 model
split. YAML-style nesting pays 1 token per line per *use* of indentation
regardless of depth-in-spaces, but the safe union assumption is: indentation
is never free.

### Binary encodings (same 65-byte sentence, three ways)

| model | plain | base64 | penalty | hex | penalty |
|---|---|---|---|---|---|
| nano | 336 | 1392 | 4.14x | 1392 | 4.14x |
| dsk | 360 | 1416 | 3.93x | 1392 | 3.87x |
| qwn | 359 | 1511 | 4.21x | 3143 | 8.75x |
| gma | 359 | 1391 | 3.87x | 3143 | 8.75x |
| mis | 360 | 1656 | 4.60x | 3144 | 8.73x |

Base64 costs 3.9-4.6x the tokens of the plaintext it encodes (union average
4.15x); the "roughly 2-3x" folk figure is an *underestimate* on this
union. Hex splits the union hard: about 4x on nano/dsk (which pair hex
chars) but about 8.7x on qwn/gma/mis, where it degenerates to exactly 1
token per character. Union average 6.85x - hex is the single most expensive
encoding measured.

## 3. Design implications for .sp

1. **The bar for .sp is 0.819, not 1.0.** Plain TSV already delivers
   0.819x json_min on the union average and beats the TOON approximation
   (0.906) on all five models. If a .sp candidate cannot beat TSV on
   tabular payloads it is adding syntax for nothing.

2. **Tabular blocks are the only large win; do not sp-ify prose.** On
   `orders`, TSV is 0.694x json_min (union avg); on the four non-tabular
   items it is 0.988-0.996x, i.e. noise. A .sp document should switch to a
   table block for repeated records and leave key-value or prose sections
   close to conventional forms, because there is no measured token win to
   buy comprehension risk with outside tables.

3. **Drop the single-letter key dictionary as designed.** dict_ref lost to
   dict_full on 4 of 5 models (+2.9% to +3.5%) and won only on deepseek
   (-3.6%). Common keys are already 1 token everywhere, so `s=status`
   headers are pure overhead at 24 rows. The dictionary idea only survives
   in a different shape: declare keys once as a *column header* and emit
   bare positional values, which measures at 4.63 tokens/pair vs 7.03 for
   JSON (-34%) - that is the TSV/TOON mechanism, and it works on all five
   models. This is a minste-felles-multiplum finding: the union kills the
   per-row abbreviation, not any single vocabulary.

4. **When keys must be inline, use `k=v`.** 5.86 tokens per pair on the
   union vs 7.03 for JSON quoting (-17%) and 7.30 for YAML (-20%). The
   ranking none < eq < json < yaml is identical on all five models.

5. **Separate fields with spaces wherever values cannot contain spaces.**
   Space is the only separator that merges into the following token on all
   five vocabularies (7.58 vs 11.78-12.38 per 6-word line). Comma, tab,
   pipe and newline all cost ~1 extra token per field; there is no
   union disagreement here. Where a stronger delimiter is unavoidable, tab,
   comma and pipe are equivalent within measurement noise, so pick for
   collision-safety, not cost.

6. **Sigil choice is token-free; spend it on unambiguity.** All ten
   candidates, including two-character `//`, cost exactly 1 token in
   line-leading position on all five models (2.98 per `X section\n` line
   vs 2 tokens for the words alone). Choose header/section sigils for
   phase-3 comprehension and for not colliding with payload characters
   (which rules out `|` and `>` if pipes or quotes appear in data), with
   zero token cost either way.

7. **Flat over nested: every indented line costs 1 token.** 2-space and
   4-space indents cost identically (+0.98/line union avg), so *depth* is
   free but *using indentation at all* is not. A 100-line nested layout
   pays ~100 tokens over a flat one. Tabs are free on 3 of 5 models but +1
   on deepseek and gemma - the union says do not rely on tab indentation
   being free. Prefer flat table blocks and explicit section sigils
   (1 token, line-leading) over indentation-as-structure.

8. **Numbers: prefer raw integers, and expect the union to split.** Unix
   timestamps beat ISO-8601 on every model (8.58 vs 22.38 per line, union
   avg) - but the margin is 4 vs 16 tokens on nano/dsk and 10 vs 25 on
   qwn/gma/mis, because Qwen, Gemma and Mistral tokenize one digit per
   token. Consequences: (a) always emit unix/plain integers over formatted
   dates on the a2a profile; (b) digit-packing tricks tuned on o200k
   (where 10 digits = 4 tokens) will not transfer - on 3 of 5 vocabularies
   a digit is a token, full stop; (c) the self profile MAY exploit
   o200k/DeepSeek digit chunking, the a2a profile MUST NOT assume it.

9. **Never embed base64 or hex; UUIDs are near-poison.** Base64 is 3.9-4.6x
   plaintext (union 4.15x), hex is about 4x on nano/dsk but about 8.7x on the
   digit-per-token camp (union 6.85x). A full UUID costs 33-36 tokens on
   every model (~1 token/char); an 8-char prefix costs 7-8. .sp should
   forbid inline binary in the a2a profile (reference it by URL/handle
   instead) and prefer short decimal row ids over UUIDs wherever the
   producer controls the id space.

10. **Pretty-printing is the most expensive decision in the baseline set.**
    json_pretty is 1.551x json_min on the union (1.42x mis to 1.63x qwn) -
    the whitespace costs more than the entire jump from JSON to TSV saves.
    Any .sp rendering rule that adds alignment padding or blank lines must
    be justified by phase-3 comprehension gains, because sections 2 (ind_*)
    and this ratio show whitespace is charged nearly full price by every
    vocabulary.

Model-disagreement register (the minste-felles-multiplum list): dict_ref
(deepseek yes, other four no), tab indentation (free on nano/qwn/mis, +1 on
dsk/gma), digit chunking (nano/dsk chunk, qwn/gma/mis are digit-per-token),
hex penalty (about 4x vs 8.7x, same split as digits), base64 penalty spread
(3.87x-4.60x). Everything else measured here - format ranking, sigil parity,
key-syntax ranking, separator ranking, space-indent cost - is unanimous
across the union.

## 4. Honesty

- **Single-run measurements.** Every cell is one API call (N=1 per model per
  item). In the most recent full run, two deepseek calls failed transiently
  and were re-measured individually; both reproduced the previous run's
  values exactly, and every unchanged text in the corpus returned exactly
  the same count as the run before it, on all five models. Token counting is deterministic per tokenizer, so re-runs should
  reproduce exactly, but provider-side scaffold changes (chat template
  updates, BOS handling) would shift the calibration constant and would not
  be caught until a re-run. No confidence intervals exist or are implied.
- **The mistral calibration constant is estimated, not measured.** The
  empty-message calibration call failed (recorded -1). cal = 3 was inferred
  from 19 probes whose per-line costs must be integral and which all satisfy
  raw = 24k + 3. The corpus tables inherit this estimate; if the true
  scaffold differs by d tokens, every mistral net value shifts by d and the
  mistral ratios move by well under 1%. The qwen/gemma -0.04 per-rep offset
  is a related, equally harmless calibration artifact.
- **TOON is an approximation.** The `*.toon` renders follow this project's
  reading of the TOON idea, not a validated implementation of the real spec.
  The 0.906 figure is evidence about this approximation only; a conformant
  TOON encoder could score differently and must be re-measured before any
  public comparison is made.
- **Comprehension is NOT yet measured.** Per the charter, the metric is
  fewest tokens *at equal or better task accuracy*. Phase 3 has not run.
  Nothing in this report shows that any model can read TSV, TOON, or a
  future .sp with the accuracy it reads JSON; positional (key-free) values -
  the mechanism behind the entire measured win - are exactly the kind of
  compression most likely to cost accuracy. No compression claim in this
  report survives unless phase 3 confirms it at equal accuracy.
- **Corpus weighting.** The per-format totals are sums over five items of
  very different sizes; `orders` dominates. The per-item ratio table in
  section 1 is provided so no one mistakes a tabular-corpus result for a
  universal one.
- The corpus is small (5 items) and drawn from this project's own API
  traffic; the probe set measures marginal costs of isolated constructs,
  and constructs can interact (e.g. a sigil adjacent to a digit may merge
  differently). Composition effects are a phase-1 measurement task.
