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
for version in ("bri", "cen", "dar"):
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
tools = json.loads(text("openai-tools.json"))
profiles = [
    tool.get("function", {}).get("parameters", {}).get("properties", {}).get("profile", {}).get("enum", [])
    for tool in tools
]
check(any("scenario-100" in profile for profile in profiles), "Tool schema must accept scenario-100")

if args.api_root:
    config = (args.api_root / "config/aiq.php").read_text(encoding="utf-8")
    bank = re.search(r"'versions'\s*=>\s*\[\s*'bank'\s*=>\s*'([0-9]+)'", config)
    check(bank is not None, "API bank identity not found")
    if bank:
        for source, label in ((post, "post"), (versions, "versions")):
            check(" | bank " + bank.group(1) + " | " in source, label + " summary uses another bank")
    check("'default_profile'=>'scenario-100'" in config, "API must default BRI to scenario-100")
    check("'dar'=>[ 'date'=>'2026-10-09'" in config, "DAR API release date differs from the site")
    check("'lifetime_seconds'=>86400" in config, "API fixed lifetime changed")
    contract = args.api_root / "libs/func_aiq_dar_contract.php"
    check(contract.is_file(), "DAR contract documented but not implemented")

for failure in failures:
    print("FAIL " + failure)
print("check-aiq-docs: " + str(len(failures)) + " problems")
sys.exit(bool(failures))
