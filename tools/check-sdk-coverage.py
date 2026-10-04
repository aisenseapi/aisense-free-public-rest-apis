"""Every documented endpoint is in both SDKs and in openai-tools.json.

python tools/check-sdk-coverage.py

Reads the endpoint headings of API.md, such as "### `POST /json_to_csv`", and
looks for each first path segment in aisense-api.js, aisense_api.py and the
tool descriptions, which end with the method and path. The other way round,
every path the SDKs call and every path a tool names must be documented, so a
removed endpoint does not linger in a client. Exits 1 and names each gap.
"""

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


METHOD_PATH = r"(?:GET|POST|PUT|DELETE|ANY)(?:, ?(?:GET|POST|PUT|DELETE))* (/[a-z0-9_][^\s`|)]*)"


def documented() -> tuple:
    """The endpoints API.md names with a method, and every path name it uses.

    API.md writes a path in a heading, a table, a code sample or a full URL, so
    every method-and-path pair counts. The second set adds the names deeper in
    a path, such as wait in /inbox/{id}/wait/{seconds}, which clients spell as
    their own string literals.
    """
    api = (ROOT / "API.md").read_text(encoding="utf-8")
    paths = re.findall(METHOD_PATH, api) + re.findall(r"/services/v1(/[a-z0-9_][^\s\"`)]*)", api)
    endpoints = {re.match(r"/([a-z0-9_]+)", p).group(1) for p in re.findall(METHOD_PATH, api)}
    names = {name for p in paths for name in re.findall(r"/([a-z0-9_]+)", p)}
    return endpoints, names


def used(text: str, pattern: str) -> set:
    return {m.group(1) for m in re.finditer(pattern, text)}


def main() -> int:
    docs, names = documented()
    js = (ROOT / "aisense-api.js").read_text(encoding="utf-8")
    py = (ROOT / "aisense_api.py").read_text(encoding="utf-8")
    tools = json.loads((ROOT / "openai-tools.json").read_text(encoding="utf-8"))
    descriptions = " ".join(t["function"]["description"] for t in tools)
    # A path is a string or template literal that starts with "/" and a name.
    clients = {
        "aisense-api.js": used(js, r"[`'\"]/([a-z0-9_]+)"),
        "aisense_api.py": used(py, r"f?[\"']/([a-z0-9_]+)"),
        "openai-tools.json": used(descriptions, r"(?:GET|POST|PUT|DELETE|ANY) /([a-z0-9_]+)"),
    }
    problems = []
    for name, paths in clients.items():
        for segment in sorted(docs - paths):
            problems.append(f"{name} lacks /{segment}, which API.md documents")
        for segment in sorted(paths - names):
            problems.append(f"{name} calls /{segment}, which API.md does not document")
    for line in problems:
        print("  FAIL  " + line)
    print(f"check-sdk-coverage: {len(docs)} documented endpoints, {len(problems)} gaps")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
