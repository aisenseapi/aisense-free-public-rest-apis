#!/usr/bin/env bash
#
# measure.sh - the token oracle. Feeds a text file to a provider and reads
# back the provider's own prompt token count, which is the only ground truth.
#
#   ./measure.sh openai gpt-4.1-nano file.txt        -> raw prompt tokens
#   ./measure.sh ollama deepseek-v4-flash:preview f  -> raw prompt tokens
#   ./measure.sh <provider> <model> --calibrate      -> scaffold tokens (empty msg)
#   ./measure.sh <provider> <model> --all <outfile>  -> TSV over corpus + probes
#
# Keys are read from ../.o-tokens relative to this script and never printed.
# Completion is capped at 1 token; the cost of a full --all run on a nano
# model is on the order of a few hundredths of a dollar, logged to
# results/cost-log.txt.

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$HERE")"
# php from PATH, or point SP_PHP at a binary.
PHP="${SP_PHP:-php}"

# Keys: environment first, then a local .o-tokens file (gitignored, format
# "openai:sk-..." and "ollama:..." one per line). Never printed by anything.
OPENAI_KEY="${SPEEDUP_OPENAI_KEY:-$(grep '^openai:' "$ROOT/.o-tokens" 2>/dev/null | cut -d: -f2- | tr -d ' \r\n')}"
OLLAMA_KEY="${SPEEDUP_OLLAMA_KEY:-$(grep '^ollama:' "$ROOT/.o-tokens" 2>/dev/null | cut -d: -f2- | tr -d ' \r\n')}"

provider="$1"; model="$2"; arg="$3"

# Build the request body with PHP so escaping is always correct - the corpus
# contains quotes, newlines and tabs, and hand-rolled JSON around those is how
# measurements silently rot.
build_req() { # file -> json on stdout ("" file means empty content)
    "$PHP" -r '
        $f = $argv[1]; $m = $argv[2]; $p = $argv[3];
        $t = ($f === "") ? "" : file_get_contents($f);
        if ($p === "openai") {
            echo json_encode([
                "model" => $m,
                "messages" => [["role" => "user", "content" => $t]],
                "max_completion_tokens" => 1,
            ]);
        } else {
            echo json_encode([
                "model" => $m,
                "messages" => [["role" => "user", "content" => $t]],
                "stream" => false,
                "options" => ["num_predict" => 1],
            ]);
        }' "$1" "$model" "$provider"
}

extract() { # resp-file field -> value or -1
    "$PHP" -r '
        $j = json_decode(file_get_contents($argv[1]), true);
        if (isset($j["usage"]["prompt_tokens"]))  { echo $j["usage"]["prompt_tokens"];  exit; }
        if (isset($j["prompt_eval_count"]))       { echo $j["prompt_eval_count"];       exit; }
        fwrite(STDERR, substr(file_get_contents($argv[1]), 0, 200) . "\n");
        echo "-1";' "$1"
}

oracle() { # file("" for empty) -> tokens
    local req resp
    req="$(mktemp)"; resp="$(mktemp)"
    build_req "$1" > "$req"
    if [ "$provider" = "openai" ]; then
        curl -s -m 60 https://api.openai.com/v1/chat/completions \
            -H "Authorization: Bearer $OPENAI_KEY" -H 'Content-Type: application/json' \
            --data-binary @"$req" > "$resp"
    else
        curl -s -m 120 https://ollama.com/api/chat \
            -H "Authorization: Bearer $OLLAMA_KEY" -H 'Content-Type: application/json' \
            --data-binary @"$req" > "$resp"
    fi
    extract "$resp"
    rm -f "$req" "$resp"
}

case "$arg" in
--calibrate)
    oracle ""
    echo
    ;;
--all)
    out="$4"
    cal="$(oracle "")"
    calls=1
    {
        echo -e "item\tkind\tbytes\traw_tokens\tcal"
        for f in "$ROOT"/corpus/renders/*.txt; do
            [ "$(basename "$f")" = "manifest.tsv" ] && continue
            t="$(oracle "$f")"; calls=$((calls+1))
            echo -e "$(basename "$f" .txt)\trender\t$(wc -c < "$f")\t$t\t$cal"
        done
        for f in "$ROOT"/probes/*.txt; do
            t="$(oracle "$f")"; calls=$((calls+1))
            echo -e "$(basename "$f" .txt)\tprobe\t$(wc -c < "$f")\t$t\t$cal"
        done
    } > "$out"
    echo "$(date -u '+%Y-%m-%d %H:%M:%S') $provider $model calls=$calls out=$(basename "$out")" >> "$ROOT/results/cost-log.txt"
    echo "wrote $out ($calls calls, calibration $cal)"
    ;;
*)
    oracle "$arg"
    echo
    ;;
esac
