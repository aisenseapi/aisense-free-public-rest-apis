"""Offline checks of two counts the public texts state by hand.

The catalog's table of all endpoints is the count of endpoints, and the AIQ
entries of the site menu are the count of AIQ versions. A text that states the
endpoint count says "more than N", where N is the largest multiple of ten below
the table's row count, and a text that states the version count uses the menu's
number. The home page said "more than 40" and "five versions" for weeks after
the catalog listed 95 endpoints in eight versions; this check fails first.

Run: python tools/check-site-counts.py
No network requests or credentials.
"""
import html
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
WORDS = {3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve"}
PUBLIC = sorted(ROOT.glob("web/*.html")) + [ROOT / "web/llms.txt"] + [
    ROOT / name for name in ("README.md", "API.md", "MCP.md", "SKILL.md", "AGENT-GUIDE.md", "AGENT-QUICKSTART.md") if (ROOT / name).is_file()
]
failures = []


def check(condition, message):
    if not condition:
        failures.append(message)


def text(path):
    return pathlib.Path(path).read_text(encoding="utf-8")


def plain(source):
    return html.unescape(re.sub(r"<[^>]+>", " ", source))


# Endpoints: the data rows of the catalog's table of all endpoints, one path each.
catalog = text(ROOT / "web/free-public-apis.html")
heading = catalog.find("All endpoints")
tables = re.findall(r"<table[^>]*>[\s\S]*?</table>", catalog[heading:]) if heading > 0 else []
check(tables != [], "catalog: the table of all endpoints follows the heading All endpoints")
rows = [row for row in re.findall(r"<tr[^>]*>([\s\S]*?)</tr>", tables[0]) if "<td" in row] if tables else []
paths = [plain(cells[1]).strip() for cells in (re.findall(r"<td[^>]*>([\s\S]*?)</td>", row) for row in rows) if len(cells) > 1]
endpoints = len(set(paths))
check(endpoints >= 50 and endpoints == len(rows), "catalog: every row of the table names one path, " + str(endpoints) + " paths in " + str(len(rows)) + " rows")
tens = (endpoints - 1) // 10 * 10
stated = re.compile(r"\bmore than (\d+)\+? (?:utility |REST )?endpoints\b", re.I)
for path in PUBLIC:
    for number in stated.findall(plain(text(path))):
        check(int(number) == tens, path.name + " says more than " + number + " endpoints; the catalog lists " + str(endpoints) + ", so it is more than " + str(tens))
for name in ("web/index.html", "web/llms.txt", "web/free-public-mcp-server.html"):
    check(stated.search(plain(text(ROOT / name))) is not None, name + " must state the endpoint count")

# AIQ versions: the menu's entries, the versions page's boxes and every count a text states.
nav = text(ROOT / "tools/site_nav.py")
menu = re.findall(r"\('/aisense-aiq-versions#([a-z]{3})'", nav)
boxes = re.findall(r'<details class="aiq-version" id="([a-z]{3})"', text(ROOT / "web/aisense-aiq-versions.html"))
check(len(menu) >= 5 and len(menu) == len(set(menu)), "site menu: AIQ versions listed once each")
check(sorted(menu) == sorted(boxes), "versions page: one box per menu entry, " + ", ".join(menu) + " in the menu and " + ", ".join(boxes) + " on the page")
count = len(menu)
word = WORDS.get(count)
check(word is not None, "no number word for " + str(count) + " versions; extend WORDS")
numbers = "|".join(list(WORDS.values()) + [r"\d+"])
counted = re.compile(r"\b(?:in|has|comes in|offers|with) (" + numbers + r") versions\b|\b(" + numbers + r") versions:", re.I)
for path in PUBLIC:
    for found in counted.findall(plain(text(path))):
        said = (found[0] or found[1]).lower()
        check(said == word or said == str(count), path.name + " counts " + said + " versions; the menu lists " + str(count))
check("in " + str(word) + " versions" in plain(text(ROOT / "web/free-public-apis.html")), "catalog grid must state the version count")
check(str(word).capitalize() + " versions:" in plain(text(ROOT / "web/index.html")), "home page must state the version count")

for failure in failures:
    print("FAIL " + failure)
print("check-site-counts: " + str(len(failures)) + " problems, " + str(endpoints) + " endpoints, " + str(count) + " AIQ versions")
sys.exit(bool(failures))
