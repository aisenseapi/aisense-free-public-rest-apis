"""Offline checks of three counts the public texts state by hand.

The catalog's table of all endpoints is the count of endpoints, the AIQ
entries of the site menu are the count of AIQ versions, and the tool tables of
the MCP page are the count of MCP tools, which the tool list of MCP.md and the
tool catalog of AGENT-GUIDE.md must repeat name for name. A text that states the
endpoint count says "more than N", where N is the largest multiple of ten below
the table's row count; a text that states the version count uses the menu's
number; a text that states the tool count uses the page's number. The home page
said "more than 40" and "five versions" for weeks after the catalog listed 95
endpoints in eight versions; this check fails first.

Run: python tools/check-site-counts.py
No network requests or credentials. With --live it also asks the public MCP
server for tools/list and names every tool the page and the server do not share.
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
MCP_URL = "https://aisenseapi.com/mcp"
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

# MCP tools: the tool tables of the MCP page, outside the sections whose heading says Separate
# (the endpoints of other servers), repeated name for name by MCP.md and AGENT-GUIDE.md.
tools = []
for section in re.finditer(r'<section id="[a-z0-9-]+">([\s\S]*?)</section>', text(ROOT / "web/free-public-mcp-server.html")):
    title = re.search(r"<h2>([\s\S]*?)</h2>", section.group(1))
    if title and "Separate" in plain(title.group(1)):
        continue
    for table in re.findall(r"<table[^>]*>[\s\S]*?</table>", section.group(1)):
        heads = [plain(head).strip() for head in re.findall(r"<th[^>]*>([\s\S]*?)</th>", table)]
        if heads[:1] != ["Tool"]:
            continue
        for row in re.findall(r"<tr[^>]*>([\s\S]*?)</tr>", table):
            cells = re.findall(r"<td[^>]*>([\s\S]*?)</td>", row)
            if cells:
                tools.append(plain(cells[0]).strip())
tool_count = len(tools)
check(tool_count >= 50 and tool_count == len(set(tools)), "MCP page: every tool table row names one tool once, " + str(tool_count) + " rows")


def same_tools(source, names):
    missing = sorted(set(tools) - set(names))
    extra = sorted(set(names) - set(tools))
    check(not missing and not extra and len(names) == len(set(names)), source + " must list the " + str(tool_count) + " tools of the MCP page once each; missing " + (", ".join(missing) or "none") + ", extra " + (", ".join(extra) or "none"))


mcp_md = text(ROOT / "MCP.md")
start = mcp_md.find("\n## Available tools")
end = mcp_md.find("\n## ", start + 1) if start > 0 else -1
check(start > 0 and end > start, "MCP.md: a section Available tools lists the tools")
same_tools("MCP.md tool list", re.findall(r"^\| `([a-z_]+)` \|", mcp_md[start:end], re.M) if start > 0 else [])
block = re.search(r"<!-- mcp-tool-catalog:start -->([\s\S]*?)<!-- mcp-tool-catalog:end -->", text(ROOT / "AGENT-GUIDE.md"))
check(block is not None, "AGENT-GUIDE.md: the tool catalog sits between the mcp-tool-catalog markers")
same_tools("AGENT-GUIDE.md tool catalog", re.findall(r"^- `([a-z_]+)` - ", block.group(1), re.M) if block else [])
forms = (r"\b(\d+) tools at one URL\b", r"\boffers (\d+) tools\b", r"\bCatalog size: (\d+) MCP tools\b", r"\bprovides (\d+) (?:public )?tools\b")
generic = re.compile(r"\b(\d+) (?:MCP |public )?tools\b")
for path in PUBLIC:
    body = plain(text(path))
    said = {number for form in forms for number in re.findall(form, body)} | {number for number in generic.findall(body) if int(number) >= 40}
    for number in sorted(said):
        check(int(number) == tool_count, path.name + " says " + number + " tools; the MCP page lists " + str(tool_count))
for name, form in (("web/llms.txt", forms[0]), ("README.md", forms[1]), ("MCP.md", forms[1]), ("AGENT-GUIDE.md", forms[2])):
    check(re.search(form, plain(text(ROOT / name))) is not None, name + " must state the tool count")

live = ""
if "--live" in sys.argv[1:]:
    import json
    import urllib.request

    def call(method, params, session, rpc_id):
        body = json.dumps({"jsonrpc": "2.0", "id": rpc_id, "method": method, "params": params}).encode("utf-8")
        headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
        if session:
            headers["Mcp-Session-Id"] = session
        with urllib.request.urlopen(urllib.request.Request(MCP_URL, data=body, headers=headers, method="POST"), timeout=60) as response:
            raw = response.read().decode("utf-8")
            if "text/event-stream" in response.headers.get("Content-Type", ""):
                raw = [line[5:].strip() for line in raw.splitlines() if line.startswith("data:")][-1]
            return json.loads(raw), response.headers.get("Mcp-Session-Id")

    try:
        answer, session = call("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "check-site-counts", "version": "1"}}, None, 1)
        names, cursor, page = [], None, 2
        while True:
            answer, _ = call("tools/list", {"cursor": cursor} if cursor else {}, session, page)
            names += [tool["name"] for tool in answer.get("result", {}).get("tools", [])]
            cursor = answer.get("result", {}).get("nextCursor")
            page += 1
            if not cursor or page > 20:
                break
        same_tools("live tools/list", names)
        live = ", live tools/list " + str(len(names))
    except Exception as error:  # the check must report a server it cannot read, not stop on it
        check(False, "live tools/list could not be read: " + type(error).__name__ + " " + str(error)[:120])

for failure in failures:
    print("FAIL " + failure)
print("check-site-counts: " + str(len(failures)) + " problems, " + str(endpoints) + " endpoints, " + str(count) + " AIQ versions, " + str(tool_count) + " MCP tools" + live)
sys.exit(bool(failures))
