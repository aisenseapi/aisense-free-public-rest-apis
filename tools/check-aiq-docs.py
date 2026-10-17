"""Offline checks of AIQ instructions and public profile descriptions.

Run: python tools/check-aiq-docs.py [--api-root PATH]
No network requests, test runs or credentials.
"""
import argparse
import html
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser()
parser.add_argument("--api-root", type=pathlib.Path)
args = parser.parse_args()
failures = []


def check(condition, message):
    if not condition:
        failures.append(message)


def text(path):
    return (ROOT / path).read_text(encoding="utf-8")


def instructions(source, element_id):
    found = re.search(r'<code id="' + re.escape(element_id) + r'">([\s\S]*?)</code>', source)
    check(found is not None, "Missing instructions: " + element_id)
    return html.unescape(found.group(1)).strip() if found else ""


post = text("web/aisense-aiq.html")
versions = text("web/aisense-aiq-versions.html")
api = text("API.md")
llms = text("web/llms.txt")
nav = text("tools/site_nav.py")
for version in ("bri", "cen", "dar", "emi", "fup"):
    left = instructions(post, "aiq-" + version + "-instructions")
    right = instructions(versions, version + "-agent-instructions")
    check(left == right, version + " copy buttons must give identical instructions")
    check("https://aisenseapi.com/services/v1/aiq" in left, version + " must name the API")

bri = instructions(post, "aiq-bri-instructions")
dar = instructions(post, "aiq-dar-instructions")
check("/start/bri/scenario-100" in bri, "BRI instructions must select 100 scenarios")
check("AIQ bri | scenario-100 | 92/100 points | fresh (1 in 24 h)" in versions,
      "BRI example must name the profile, 100-point scale and origin")
check("no total score" in versions, "Incomplete BRI runs must not advertise a total")
check("20 hours" in post and "20 hours" in versions, "BRI active lifetime must be documented")
check("24 hours" in post and "24 hours" in versions, "Fixed expiry must remain documented")
check("4201" in api and "4201" in versions, "BRI admission must name remaining request budget")
check("100 scenarios" in nav and "bri, six scenarios" not in nav, "Navigation must describe BRI100")
check("bri with 100 scenarios" in llms, "llms.txt must describe BRI100")
for required in ("controller_inbox_ready", "result_final=true", "args", "register", "base64url"):
    check(required in dar, "DAR instructions missing " + required)
check("separate AI sessions" in versions and "client_managed" in versions,
      "Public DAR must not claim independently verified agent execution")
dar_section = re.search(r'<details class="aiq-version" id="dar">([\s\S]*?)</details>', versions)
check(dar_section is not None and '<time datetime="2026-10-09">9 October 2026</time>' in dar_section.group(1),
      "DAR release date must be 9 October 2026")
check("Since 9 October 2026, experimental" in post, "DAR information panel has another date")
emi = instructions(post, "aiq-emi-instructions")
for required in ("POST https://aisenseapi.com/services/v1/aiq/start/emi", "observer_handoff", "/begin", "expected_revision", "next_action", "module manifest", "observer_link_shown"):
    check(required in emi, "EMI instructions missing " + required)
emi_section = re.search(r'<details class="aiq-version" id="emi">([\s\S]*?)</details>', versions)
check(emi_section is not None and '<time datetime="2026-10-12">12 October 2026</time>' in emi_section.group(1),
      "EMI release date must be 12 October 2026")
check("Since 12 October 2026, experimental" in post, "EMI information panel has another date")
replay_post = instructions(post, "aiq-emi-replay-example")
replay_versions = instructions(versions, "emi-replay-example")
check(replay_post == replay_versions, "EMI replay examples must agree")
for required in ("POST https://aisenseapi.com/services/v1/aiq/start/emi", "Content-Type: application/json",
                 '{"test_string":"COMPLETED_EMI_TEST_STRING"}'):
    check(required in replay_post, "EMI replay example missing " + required)
check("coordinator_key" not in replay_post and "run_token" not in replay_post,
      "EMI replay starts from the signed result, not credentials from another run")
for source, label in ((post, "post"), (versions, "versions"), (api, "API")):
    normalized = " ".join(source.split())
    for required in ("completed EMI run", "authenticates", "exact recipe remains supported",
                     "origin", "replay", "not playback", "read_url", "write_urls",
                     "same start and active-run", "its own begin", "one hour", "24 hours",
                     "before replay support", "still verify"):
        check(required in normalized, label + " EMI replay contract missing " + required)
    check("does not replay" not in normalized, label + " retains the retired blanket EMI replay refusal")
    check("15 seconds" not in normalized and "countdown" not in normalized, label + " still describes the retired 15-second countdown")
check('and the body {}' in emi, "EMI fresh-run instructions must remain separate from replay")
check("emi, a factory and its panel" in nav and "emi, an experimental factory run" in llms, "Navigation and llms.txt must list EMI")
check("HTML and CSS" not in versions and "HTML page with CSS" not in versions, "EMI is described with its module panel, not the retired HTML profile")
fup = instructions(post, "aiq-fup-instructions")
for required in ("GET https://aisenseapi.com/services/v1/aiq/start/fup", "observer.message", "Never show the run_token", "attempt_key",
                 "copied without retyping", "Do not carry out any action in the real world"):
    check(required in fup, "FUP instructions missing " + required)
fup_section = re.search(r'<details class="aiq-version" id="fup">([\s\S]*?)</details>', versions)
check(fup_section is not None and '<time datetime="2026-10-16">16 October 2026</time>' in fup_section.group(1),
      "FUP release date must be 16 October 2026")
check("Since 16 October 2026, experimental" in post, "FUP information panel has another date")
check("fup, judgment under pressure" in nav and "fup, 100 short scenarios answered four times over" in llms, "Navigation and llms.txt must list FUP")
fup_post = text("web/does-your-ai-agent-keep-its-judgment-under-pressure.html")
check(instructions(fup_post, "post-fup-instructions") == fup, "The FUP post must give the same instructions as the AIQ page")
for source, label in ((post, "post"), (versions, "versions"), (api, "API"), (llms, "llms.txt"), (fup_post, "FUP post")):
    normalized = " ".join(source.split()).lower()
    check("five versions" not in normalized, label + " still counts five versions")
    for leak in ("not your score", "rewarded worse", "true points"):
        check(leak not in normalized, label + " must not say what the FUP points are: " + leak)
    check(re.search(r"\blure\b", normalized) is None, label + " must not say what the FUP points are: lure")
tools = json.loads(text("openai-tools.json"))
profiles = [
    tool.get("function", {}).get("parameters", {}).get("properties", {}).get("profile", {}).get("enum", [])
    for tool in tools
]
check(any("scenario-100" in profile for profile in profiles), "Tool schema must accept scenario-100")
replay_tools = [tool["function"] for tool in tools if tool.get("function", {}).get("name") == "replay_aiq_run"]
check(len(replay_tools) == 1, "Tool schema must contain exactly one replay_aiq_run")
if replay_tools:
    replay_params = replay_tools[0]["parameters"]
    check(replay_params["properties"]["version"]["enum"] == ["ard", "bri", "cen", "dar", "emi", "fup"],
          "Replay tool must support EMI and FUP while preserving the other versions")
    check(replay_params["required"] == ["version", "test_string"],
          "EMI replay must not require a coordinator key or an existing run token")
start_tools = [tool["function"] for tool in tools if tool.get("function", {}).get("name") == "start_aiq_run"]
check(len(start_tools) == 1, "Tool schema must contain exactly one start_aiq_run")
if start_tools:
    start_params = start_tools[0]["parameters"]["properties"]
    check("fup" in start_params["version"]["enum"] and "pressure-400" in start_params["profile"]["enum"],
          "Start tool must offer fup and its profile pressure-400")

if args.api_root:
    config = (args.api_root / "config/aiq.php").read_text(encoding="utf-8")
    bank = re.search(r"'versions'\s*=>\s*\[\s*'bank'\s*=>\s*'([0-9]+)'", config)
    check(bank is not None, "API bank identity not found")
    if bank:
        for source, label in ((post, "post"), (versions, "versions")):
            check(" | bank " + bank.group(1) + " | " in source, label + " summary uses another bank")
    check("'default_profile'=>'scenario-100'" in config, "API must default BRI to scenario-100")
    check("'dar'=>[ 'date'=>'2026-10-09'" in config, "DAR API release date differs from the site")
    check("'emi'=>[ 'date'=>'2026-10-12'" in config and "'factory_profiles'=>[ 'factory-100'=>[ 'engine'=>'emi' ] ]" in config,
          "EMI must be in the API version registry with its factory profile and the site date")
    check((args.api_root / "emi/src/Modules/Panel.php").is_file(), "EMI module panel documented but not implemented")
    check("'fup'=>[ 'date'=>'2026-10-16'" in config, "FUP API release date differs from the site")
    check(re.search(r"'pressure-400'=>\[ 'scenario_version'=>'fup-h[0-9]+', 'scenarios'=>400, 'seconds'=>60, 'active_seconds'=>24000 \]", config) is not None,
          "FUP profile pressure-400 must run 400 tasks of 60 seconds in 24000 active seconds")
    check((args.api_root / "libs/func_aiq_fup_observer.php").is_file(), "FUP observer documented but not implemented")
    check("'lifetime_seconds'=>86400" in config, "API fixed lifetime changed")
    contract = args.api_root / "libs/func_aiq_dar_contract.php"
    check(contract.is_file(), "DAR contract documented but not implemented")

for failure in failures:
    print("FAIL " + failure)
print("check-aiq-docs: " + str(len(failures)) + " problems")
sys.exit(bool(failures))
