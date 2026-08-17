# SpeedUp: serialization cost measured across five tokenizer vocabularies

Every serialization format marketed for LLM input carries a token-saving
claim. Nearly all of those claims were measured against a single tokenizer,
usually OpenAI's o200k, and assumed to transfer. This directory contains what
happened when we measured instead of assumed: the same corpus, rendered in six
formats, priced by five different vocabularies using the providers' own token
counters as ground truth.

The result changed our own plans. We set out to design a new format and the
data talked us out of it. The findings are in
[results/tokenizer-physics.md](results/tokenizer-physics.md); the conventions
that survived measurement are in [SP-PROFILE.md](../SP-PROFILE.md); the whole
rig is here so you can rerun everything with your own keys.

## Method

- Six renders per corpus item: minified JSON, pretty JSON, YAML, Markdown,
  TSV, and a TOON approximation. Deterministic renderer, byte-identical
  across runs (tools/render.php).
- 33 single-construct probes: sigil characters, key-value syntaxes, a header
  dictionary vs repeated keys, number and identifier formats, separators,
  indentation, and base64/hex against plaintext (tools/probes.php).
- Five oracles, one per vocabulary family: OpenAI gpt-4.1-nano (o200k),
  deepseek-v4-flash (DeepSeek BPE), qwen3.5 (Qwen BPE), gemma4
  (SentencePiece), mistral-large-3 (Tekken), the last four via Ollama Cloud.
- Ground truth is the provider's own count: usage.prompt_tokens on OpenAI,
  prompt_eval_count on Ollama, with a per-model calibration row (empty
  message) subtracted so chat scaffolding does not pollute the numbers
  (tools/measure.sh).
- 315 measurements, zero failures, spot-checked by re-measurement. Raw data
  in results/raw/, one TSV per oracle.

## The five findings

1. Plain TSV beats the token-oriented formats on the union average: 0.819x
   minified JSON, ahead of our TOON approximation (0.906x) on all five
   models. The entire win is tabular data; on non-tabular items TSV sits
   within 1.2 percent of JSON.
2. Short-key dictionaries do not work: a header mapping keys to single
   letters LOSES to repeating full keys on four of five vocabularies,
   because common English keys are already one token everywhere. The real
   mechanism is declaring columns once and sending values positionally:
   4.63 vs 7.03 tokens per key-value pair, minus 34 percent.
3. Sigil characters are free. All ten candidates cost exactly one token in
   line-leading position on all five vocabularies.
4. The union splits on digits: o200k and DeepSeek chunk a ten-digit
   timestamp into 4 tokens, Qwen, Gemma and Mistral price it at one digit
   per token. Any digit-packing trick tuned on one family loses on the
   other. Base64 costs 3.3-4.3x plaintext; hex up to 8.3x.
5. Space is the only free field separator; comma, tab, pipe and newline all
   cost about 0.9 token per field. Space indentation costs one token per
   line regardless of depth.

## Reproduce it

You need PHP (any 8.x, no extensions), curl, and keys:

    export SPEEDUP_OPENAI_KEY=sk-...
    export SPEEDUP_OLLAMA_KEY=...        # ollama.com cloud key

    php tools/render.php
    php tools/probes.php
    bash tools/measure.sh openai gpt-4.1-nano --all results/raw/my_run.tsv

Keys can also live in a local .o-tokens file next to this README (gitignored).
Completion is capped at one token per call; a full 64-call run on a nano
model costs a few hundredths of a dollar and every run appends to
results/cost-log.txt.

To add a vocabulary, point measure.sh at any model whose API reports prompt
token counts, and rerun. To challenge a finding, rerun it - token counting is
deterministic, and a number you cannot reproduce is a bug report we want.

## Honest limits

Single-run measurements (spot-checks reproduced exactly, but rerun before
betting a company on a decimal). The TOON render is our approximation of that
spec, labelled as such. And token counts say nothing about comprehension: the
published accuracy benchmarks for compressed formats are unflattering, which
is exactly why the conventions in SP-PROFILE.md stop where measured savings
end and comprehension risk begins.

Corpus, probes and results are MIT licensed with the rest of this repository.
Provided by AI SENSE AS, Oslo - https://aisense.no
