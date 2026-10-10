# Free Public REST APIs - AI SENSE AS

> **Base URL:** `https://aisenseapi.com/services/v1`
> **Authentication:** No account or API key. Queue and semantic search operations require role-specific bearer tokens
> **Cost:** Free
> **Rate limit:** 5000 requests per IP per day, reset at 22:00 UTC from late March to late October and at 23:00 UTC the rest of the year (midnight in Norway, time zone Europe/Oslo)

This document is the REST reference. The same service answers on two further
protocols: the remote MCP server at `https://aisenseapi.com/mcp`, and Agent2Agent
at `https://aisenseapi.com/a2a`. See [`MCP.md`](MCP.md) for the MCP tool list and
client examples, and [Agent2Agent (A2A)](#agent2agent-a2a) below for the five
task-shaped skills that protocol carries.

The response key is
almost never `data` or `result` - it is usually named after the endpoint
(`/md5_hash` returns `md5_hash`, `/random_color` returns `random_color`). Do not
guess it.

---

## Table of Contents

- [Reading this document](#reading-this-document)
- [Time](#time)
- [Random](#random)
- [Transform](#transform)
- [Convert](#convert)
- [Images](#images)
- [Logic](#logic)
- [AIQ](#aiq)
- [Hash](#hash)
- [Web](#web)
- [Agent Queue](#agent-queue---temporary-work-for-multiple-workers)
- [Semantic search](#semantic-search---find-notes-by-meaning)
- [Crypto](#crypto)
- [Agent2Agent (A2A)](#agent2agent-a2a)
- [Common Conventions](#common-conventions)

---

## Reading this document

Two service-wide behaviours matter more than any single endpoint.

**Errors usually use `{"error": "message"}` with a non-2xx HTTP status.**
Check both the status and the `error` field. The legacy wallet-generation
handlers can return an error object with HTTP 200. Workflow endpoints use
non-2xx statuses, including 409 for conflicts and 410 for an expired record
that has not yet been removed. Once removed, the same ID returns 404. Unknown
routes also return 404. Consult each endpoint for its additional errors.

**Not everything is JSON.** `base64_decode`, `base58_decode`, `base32_decode`,
`hex_decode` and `base64url_decode` answer with `application/octet-stream`
unless you send `Accept: application/json`.

---

## Time

### `GET /datetime[/{offset}]` and `GET /datetime/{zone}`
Current date and time in ISO 8601, in UTC, at a fixed offset, or in a time zone
by name.

`offset` is a **four-digit** UTC offset with an optional sign, `+0200`, `-0530`
or `0100`, or since 3 October 2026 the same with a colon, `+02:00`. An
hour-only value such as `1` does **not** match the route and falls through to
the unknown-path response. A four-digit offset out of range answers UTC.

```
GET /datetime
GET /datetime/+0200
GET /datetime/+02:00
GET /datetime/-0530
```

```json
{ "datetime": "2026-08-16T11:44:35+02:00" }
```

`zone` is an IANA zone name such as `europe/oslo`, `america/new_york` or
`america/argentina/buenos_aires`, added 3 October 2026. Paths here are written
in lower case; capitals are answered the same way, and the answer gives the
name as the zone database writes it, `Europe/Oslo`. A fixed
offset is wrong for half the year anywhere with summer time; a zone name
follows the clock changes. The answer says what the offset is right now,
whether summer time is in force and when it starts and ends:

```
GET /datetime/europe/oslo
```

```json
{
  "datetime": "2026-10-03T12:41:07+02:00",
  "timezone": "Europe/Oslo",
  "abbreviation": "CEST",
  "utc_offset": "+02:00",
  "dst": true,
  "unixtime": 1791024067,
  "raw_offset": 3600,
  "dst_offset": 3600,
  "dst_from": "2026-03-29T01:00:00+00:00",
  "dst_until": "2026-10-25T01:00:00+00:00",
  "day_of_week": 6,
  "day_of_year": 276,
  "week_number": 40,
  "utc_datetime": "2026-10-03T10:41:07+00:00"
}
```

`dst_from` and `dst_until` are the edges of the current summer time period in
UTC, and `null` outside one. `raw_offset` is the standard offset and
`dst_offset` what summer time adds, in seconds: `3600` almost everywhere,
`1800` on Lord Howe Island. The zone database counts Irish winter time and
Moroccan Ramadan time as summer time with a negative offset, so `dst` is
`true` and `dst_offset` is `-3600` then; `raw_offset + dst_offset` is the
offset in force everywhere. `day_of_week` is `0` for Sunday, `day_of_year`
starts at `1`, `week_number` is the ISO week. Old names such as `europe/kiev`
are accepted.

An unknown name is **HTTP 400** with a `fix`, never a silent UTC.
[`/timezones`](#get-timezonesoffset) lists the names.

---

### `GET /ip_datetime[/{ip}]`
The same fields as `/datetime/{zone}` for the time zone an IPv4 or IPv6
address is in, after the address itself. Without an address, the caller's
own. Added 3 October 2026.

```
GET /ip_datetime
GET /ip_datetime/8.8.8.8
```

```json
{"ip":"8.8.8.8","datetime":"2026-10-03T05:41:07-05:00","timezone":"America/Chicago","abbreviation":"CDT","utc_offset":"-05:00","dst":true,"unixtime":1791024067,"raw_offset":-21600,"dst_offset":3600,"dst_from":"2026-03-08T08:00:00+00:00","dst_until":"2026-11-01T07:00:00+00:00","day_of_week":6,"day_of_year":276,"week_number":40,"utc_datetime":"2026-10-03T10:41:07+00:00"}
```

The zone comes from an address lookup. Each worker holds the IP address and
result in memory and reuses a result for up to an hour, or ten minutes when no
zone was found. Expiry stops reuse, but entries can remain until replaced,
removed to make room or the worker restarts. Requests are logged with the
caller's IP and URL path, so an IP in `/ip_datetime/{ip}` can also appear in
logs. See the [privacy policy](https://aisense.no/privacy) for log retention.

Something that is not an address is **400** `Invalid IP address.`; an address
with no zone in the lookup, such as a private one, is **404** `No time zone is
known for this address.`, both with a `fix`.

---

### `GET /timestamp`
```json
{ "timestamp": 1786873261 }
```

---

### `GET /microtimestamp`
```json
{ "microtimestamp": 1786873474.745043 }
```

---

### `GET /timezones[/{offset}]`
All timezones, optionally filtered by a four-digit offset. The list contains
**objects, not strings**.

```json
{
  "timezones": [
    { "timezone": "Africa/Abidjan", "offset": "+0000" },
    { "timezone": "Africa/Blantyre", "offset": "+0200" }
  ]
}
```

---

### `GET /swatchinternettime`
Swatch Internet Time. `beat` is a string with a leading `@`, not a number.

```json
{ "beat": "@444", "date": "2026-08-16" }
```

---

### `POST /timestamp_convert`
One time value in, every representation out. Accepts a unix timestamp in
seconds, a unix timestamp in **milliseconds** (13 digits and up - the format
`Date.now()` produces, and the usual source of dates in the year 56000), an
ISO 8601 or RFC 2822 datetime, or the literal `"now"`. Reports which format it
detected. The optional `offset` uses the same four-digit form as `/datetime`.

Unlike the older endpoints, bad input returns a real **HTTP 400**.

```json
// Request
{ "data": "1700000000123", "offset": "+0100" }

// Response
{
  "input": "1700000000123",
  "detected": "unix_ms",
  "timestamp": 1700000000,
  "datetime": "2023-11-14T23:13:20+01:00",
  "rfc2822": "Tue, 14 Nov 2023 23:13:20 +0100",
  "utc_datetime": "2023-11-14T22:13:20+00:00"
}
```

`detected` is one of `unix`, `unix_ms`, `datetime`, `now`.

---

### Moving from WorldTimeAPI
On 3 October 2026 every connection we made to worldtimeapi.org was reset, over
HTTP and HTTPS. Its answers are here under this API's own paths:

| WorldTimeAPI | Here |
|--------------|------|
| `http://worldtimeapi.org/api/timezone/Europe/Oslo` | `https://aisenseapi.com/services/v1/datetime/europe/oslo` |
| `http://worldtimeapi.org/api/ip` | `https://aisenseapi.com/services/v1/ip_datetime` |
| `http://worldtimeapi.org/api/ip/{address}` | `https://aisenseapi.com/services/v1/ip_datetime/{address}` |
| `http://worldtimeapi.org/api/timezone` | `https://aisenseapi.com/services/v1/timezones`, objects with `timezone` and `offset` rather than plain names |
| `http://worldtimeapi.org/api/timezone/Europe` | `/timezones`, keeping the names that start with `Europe/` |
| any `.txt` form | none; every answer is JSON |

Every WorldTimeAPI field is there under the same name and type except
`client_ip`; `/ip_datetime` answers `ip`, the address it looked up. `datetime`
and `utc_datetime` are to the second, without the microseconds WorldTimeAPI
added, which ISO 8601 parsers read either way. Only HTTPS is served; a sketch
that used plain HTTP on an ESP32 moves to `WiFiClientSecure` as well.

---

## Random

### `GET /random_number[/{from}[/{to}]]`
Random integer, inclusive. No arguments gives 1-6. A **single** argument is
treated as the upper bound with the lower bound fixed at 1.

```
GET /random_number          -> 1-6
GET /random_number/30       -> 1-30
GET /random_number/10/20    -> 10-20
GET /random_number/-57/-3   -> -57--3
```

```json
{ "random_number": 73, "range": { "from": 1, "to": 100 } }
```

---

### `GET /random_color`
```json
{ "random_color": "#9b6bbf" }
```

---

### `GET /uuid`
```json
{ "uuid": "429151ee-82a1-4438-b2f1-b6b9c9e4a41f" }
```

---

### `GET /guid`
```json
{ "guid": "750dd9a6-a507-4a89-b4ec-8cd71fc115b7" }
```

---

### `GET /password[/{length}]`
Random password, 12 characters by default. Includes punctuation.

```json
{ "password": "jFehS]AKGx9wl[jp", "password_length": 16 }
```

### `GET /passphrase[/{groups}]`
Pronounceable passphrase, 4 hyphen separated groups by default, 2 to 12
allowed. Groups are built from consonant-vowel syllables, so the result can be
read aloud and retyped from memory. One digit and one symbol are always
included, because the complexity rules that demand them are close to universal.

The argument counts **groups, not characters**. That is why this is a separate
endpoint rather than a style on `/password`, where the same number means a
length.

```json
{ "passphrase": "hudil-rosi4-Zerzo-Coze#", "groups": 4, "length": 23, "entropy_bits": 91.4 }
```

`entropy_bits` is accumulated from the random draws that produced this specific
passphrase, not estimated afterwards from the finished string. Counting
characters would overstate it: `Zerzo` looks like five characters from a large
alphabet and is really four uniform choices from small ones.

It is reported per result rather than per setting, so two calls with the same
group count differ depending on how many syllables drew a closing consonant. The
spread is wider than it looks: at the default of 4 groups the observed range
over 4000 generations was 74.6 to 107.9 bits around a mean of 91.4.

| Groups | Mean | Comparable to |
|--------|------|---------------|
| 2 | 48.9 bits | fine against online guessing, weak against an offline crack |
| 4 (default) | 91.4 bits | a 14 character fully random password |
| 6 | 132.7 bits | past the point where the passphrase is the weak link |
| 12 | 255.6 bits | key material, not something a person retypes |

Those are measured over 4000 generations each, and every one lands within 0.2
bits of what the construction predicts analytically.

Two groups is offered because short passphrases have honest uses, throwaway test
fixtures among them. It is not a sensible choice for a credential that will face
a stolen password database, and the number is on every response so that choice is
never made silently.

---

## Transform

### `POST /base64_encode`
```json
// Request
{ "data": "Hello world" }

// Response
{ "base64_encoded_data": "SGVsbG8gd29ybGQ=" }
```

---

### `POST /base64_decode`
Input: JSON with `data`, or plain text with `Content-Type: text/plain`.

**The response format depends on the `Accept` header.** With no `Accept`, you
get the decoded bytes as `application/octet-stream` - the payload and nothing
else. Send `Accept: application/json` to get a typed envelope instead.

```json
// Request                              Accept: application/json
{ "data": "eyJrZXkiOiJ2YWx1ZSJ9" }

// Response - decoded content was JSON
{ "type": "json", "decoded_data": { "key": "value" } }

// Response - decoded content was not JSON
{ "type": "binary", "encoding": "base64", "decoded_data": "iVBORw0KGgo..." }
```

Set `Accept: application/octet-stream` (or send no `Accept`) to stream the raw
bytes.

---

### `POST /base58_encode`
```json
{ "data": "Hello" } -> { "base58_encoded_data": "9Ajdvzr" }
```

---

### `POST /base58_decode`
Answers with the raw bytes as `application/octet-stream`. With
`Accept: application/json` it answers `{"type": "json", "decoded_data": ...}` when the decoded bytes are JSON, and
`{"type": "binary", "encoding": "base64", "decoded_data": "..."}` otherwise.
Unlike `base64_decode` there is no `text/plain` mode and no 406: any other
`Accept` gets the bytes. An invalid Base58 character returns HTTP 400 with
`{"error": "Invalid Base58 input."}`.

```json
{ "data": "9Ajdvzr" } -> Hello
```

---

### `POST /base32_encode`
```json
{ "data": "Hello" } -> { "base32_encoded_data": "JBSWY3DP" }
```

---

### `POST /base32_decode`
Answers with the raw bytes as `application/octet-stream`. With
`Accept: application/json` it answers `{"type": "json", "decoded_data": ...}` when the decoded bytes are JSON, and
`{"type": "binary", "encoding": "base64", "decoded_data": "..."}` otherwise.
Unlike `base64_decode` there is no `text/plain` mode and no 406: any other
`Accept` gets the bytes.

```json
{ "data": "JBSWY3DP" } -> Hello
```

---

### `POST /hex_encode`
Any bytes in, lower-case hex out, added 3 October 2026. Like the seven below,
it takes `data` in a JSON body or the raw body with any other content type, at
most 1 MiB (HTTP 413 above that), and every refusal carries a `fix`.

```json
{ "data": "hello" } -> { "hex_encoded_data": "68656c6c6f" }
```

---

### `POST /hex_decode`
Hex in either case; a leading `0x` and spaces are allowed. Answers exactly as
`base64_decode` does: the raw bytes, the typed envelope with
`Accept: application/json`, text with `Accept: text/plain`, and 406 for any
other `Accept`. An odd number of digits or a character that is not hex is
HTTP 400 `Invalid hex input.`

```json
{ "data": "68656C6C6F" } -> hello
```

---

### `POST /base64url_encode`
The URL-safe alphabet of RFC 4648, section 5: `-` and `_` where base64 writes
`+` and `/`, and no padding, as JWT, OAuth PKCE and WebAuthn write it.

```json
{ "data": "hello?" } -> { "base64url_encoded_data": "aGVsbG8_" }
```

---

### `POST /base64url_decode`
With or without `=` padding. Answers exactly as `base64_decode` does. A `+` or
`/` is HTTP 400 `Invalid base64url input.`, with a fix pointing at
`base64_decode`.

```json
{ "data": "aGVsbG8_" } -> hello?
```

---

### `POST /url_encode`
Percent-encoding for one path segment or query value (RFC 3986): every byte
but `A-Z a-z 0-9 - _ . ~` becomes `%XX`, so a space is `%20` and a slash `%2F`.

```json
{ "data": "a b/c?é" } -> { "url_encoded_data": "a%20b%2Fc%3F%C3%A9" }
```

---

### `POST /url_decode`
Percent-encoding back to text. A `+` stays a `+`, since it means a space only
in HTML form bodies. A `%` without two hex digits after it is HTTP 400
`Invalid percent-encoding.`, and bytes that do not form UTF-8 text are HTTP 400
`The decoded bytes are not UTF-8 text.`, with a fix pointing at `hex_decode`
and `base64_decode`.

```json
{ "data": "a%20b%2Fc+%C3%A9" } -> { "url_decoded_data": "a b/c+é" }
```

---

### `POST /html_encode`
`& < > " '` become `&amp; &lt; &gt; &quot; &#039;`, so text can go into an HTML
page or attribute as it is. Every `&` is encoded, an entity already in the text
included. The input has to be UTF-8 text.

```json
{ "data": "<b>Tom & Jerry's</b>" } -> { "html_encoded_data": "&lt;b&gt;Tom &amp; Jerry&#039;s&lt;/b&gt;" }
```

---

### `POST /html_decode`
Every named HTML5 entity and every numeric one back to its character.

```json
{ "data": "&lt;b&gt; &amp; &eacute; &#233;" } -> { "html_decoded_data": "<b> & é é" }
```

---

### `POST /html_to_markdown`
A web page or any HTML to CommonMark with GitHub tables. Scripts, styles, the
head, forms, SVG and media are left out, and text that would read as Markdown
is escaped, so it reads back as the same text. `title` is the page's `<title>`,
or `null`. The HTML is read the way a browser forgives it: unclosed `<p>` and
`<li>` close themselves and stray end tags are ignored. At most 1 MiB and 40000
start and end tags; tags inside scripts and styles do not count.

```json
{ "data": "<title>Release notes</title><h1>Version 2</h1><p>Now with <b>tables</b>.</p>" } -> { "markdown": "# Version 2\n\nNow with **tables**.", "title": "Release notes" }
```

---

### `POST /markdown_to_html`
CommonMark with GitHub tables, strikethrough, task lists and bare links, to an
HTML fragment. Raw HTML in the Markdown is shown as text, and a link or image
whose scheme is not http, https, mailto, tel or ftp, or a PNG, GIF, JPEG or
WebP data URL for images, is shown as its text, so the HTML can go into a page
as it is. At most 256 KiB and 20000 lines.

```json
{ "data": "**Bold** <b>raw</b>" } -> { "html": "<p><strong>Bold</strong> &lt;b&gt;raw&lt;/b&gt;</p>" }
```

---

### `POST /slugify`
Text to URL slug, with Scandinavian letters and common Latin diacritics
transliterated by a fixed table so the same input gives the same slug on every
machine. Characters outside the table are dropped; input that leaves nothing
behind returns **HTTP 400** rather than an empty slug.

```json
{ "data": "Blåbærsyltetøy på Ås!" } -> { "slug": "blabaersyltetoy-pa-as" }
{ "data": "Große Übung" }           -> { "slug": "grosse-ubung" }
```

---

### `POST /jwt_encode`
Encodes a payload into an HS256 JWT.

`data` takes the claims as a **JSON object directly**, or as a string
containing JSON - both forms produce the same token. (Before 2026-08-17 only
the string form was accepted, and passing an object was the most-hit trap on
the surface.) A string that does not parse as JSON returns HTTP 400.

```json
// Request - object form
{ "data": { "user": "alice" }, "secret": "your_secret_key" }

// Request - string form, same token
{ "data": "{\"user\":\"alice\"}", "secret": "your_secret_key" }

// Response
{ "jwt": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyIjoiYWxpY2UifQ..." }
```

Also accepts plain text (`Content-Type: text/plain` plus an `X-Secret` header)
or a file upload (`jwt_data` field, `multipart/form-data`).

---

### `POST /jwt_decode`
```json
// Request
{ "data": "eyJ0eXAiOiJKV1Qi...", "secret": "your_secret_key" }

// Response
{ "decoded_payload": { "user": "alice" } }
```

---

### `POST /qrcode_encode`
Generates a QR code. The request field is `payload`, with `data` accepted as an alias since 2026-08-17.

```json
// Request
{ "payload": "https://aisenseapi.com/" }

// Response
{ "qrcode_image": "iVBORw0KGgoAAAANSUhEUg...", "image_type": "png" }
```

---

### `POST /qrcode_decode`
Accepts a file upload (`qrcode_image` field, `multipart/form-data`) or a
Base64 image in the **`payload`** field of a JSON body. The image is a PNG,
JPEG, GIF or WebP of at most 10 MB and 25 megapixels as a file upload. A JSON
body is at most 256 KiB (262 144 bytes) on every endpoint, and Base64 makes
the image a third larger, so through `payload` the image can be about 190 KB.
Send larger images as a file upload. Anything else, a PDF included, is
refused with 415 before it is opened.

```json
// Request
{ "payload": "iVBORw0KGgoAAAANSUhEUg..." }

// Response
{ "qrcode_content": "https://aisenseapi.com/" }
```

Several codes in one image come back one per line in the same string.

| Status | When |
|--------|------|
| 400 | No payload, invalid base64, an image that does not open, or no code found |
| 413 | Over 10 MB or 25 megapixels, or a JSON body over 256 KiB |
| 415 | Not a PNG, JPEG, GIF or WebP |
| 503 | Two images are being worked on already (with `Retry-After`), or the decoding took more than 45 seconds |

Every refusal carries `error` and `fix`.

---

## Convert

Five endpoints convert, format, validate and compare JSON, CSV and tables.
None of them returns its result in the answer. Each stores the result in
[Storage](#storage---24h-ttl) for 24 hours and answers with the Storage fields
plus `content_type`, `filename` and `operation`. Read the result with a GET on
`storage_url`. Anyone with that link can read it, and stored results count
against the Storage budget of 80 MB per IP address per day.

All five take `POST` with `Content-Type: application/json` and a JSON object
of at most 256 KB, with lists and objects nested at most 63 deep. Unknown
fields are refused, and so is an integer too large for 64 bits anywhere in
the body; send large IDs as strings. Every refusal from these endpoints
carries `error` and `fix`, and stores nothing.

```json
// Response to the json_to_csv request below, from a test run.
// The id and the expiry are different on every call.
{
  "storage_id": "b5b3016f-52df-43a7-801c-7b7d0baa4b94",
  "storage_url": "https://aisenseapi.com/services/v1/storage/b5b3016f-52df-43a7-801c-7b7d0baa4b94",
  "sha256_hash": "3e749b9bff583e347820dee8435476eca0ca58fe2e4639c53cc13c8cc9925c1c",
  "bytes": 44,
  "expire_timestamp": 1790760065,
  "expire_datetime": "2026-09-30T09:21:05+00:00",
  "content_type": "text/csv; charset=utf-8",
  "filename": "result.csv",
  "operation": "json_to_csv"
}
```

| Status | When |
|--------|------|
| 400 | The body is not a JSON object, a field is missing, unknown or has the wrong type, or the input breaks the endpoint's rules |
| 405 | The method is not `POST` |
| 413 | The body, the rows or the result is over a limit |
| 415 | The `Content-Type` is not `application/json` |
| 429 | The request budget or the day's Storage budget is used up |
| 503 | The result could not be stored |

A result is at most 2 MB. Tables are at most 5000 rows and 100 columns, but
the 256 KB body limit is usually reached first.

Each endpoint has a guide with a browser tool:
[JSON to CSV](https://aisense.no/free-json-to-csv-api),
[CSV to JSON](https://aisense.no/free-csv-to-json-api),
[table matching](https://aisense.no/free-table-matching-api),
[JSON formatter](https://aisense.no/free-json-formatter-api) and
[JSON validator](https://aisense.no/free-json-validator-api).

---

### `POST /json_to_csv`
JSON records to CSV. `columns` names the columns and their order, and `rows`
is a list of flat objects. Optional `delimiter` is `","` (default), `";"` or
`"\t"`. Optional `spreadsheet_safe` (default `false`) puts an apostrophe in
front of cells that start with `=`, `+`, `-` or `@`, the header and negative
numbers sent as text included.

```json
// Request
{"columns": ["customer_id", "name"], "rows": [{"customer_id": "00123", "name": "Nordlys AS"}], "delimiter": ";"}
```

Stored as `result.csv` with the content type `text/csv; charset=utf-8`.
Every cell is quoted, quotes inside a cell are doubled, and every line ends
with CRLF:

```text
"customer_id";"name"
"00123";"Nordlys AS"
```

A row with a field that is not in `columns` is refused, so nothing is dropped
without notice. `null` and a missing field give an empty cell, `true` and
`false` give the words, and numbers are written as JSON numbers, so `1.50`
becomes `1.5`. Nested objects and lists are refused. Storage serves the CSV
as `application/octet-stream`.

---

### `POST /csv_to_json`
CSV text in `data` to JSON. Optional `delimiter` as for `json_to_csv`. The
first line is the header, and column names must be unique and not empty.

```json
// Request
{"data": "customer_id,name\n00123,Nordlys AS\n"}
```

Stored as `result.json`:

```json
{"columns":["customer_id","name"],"rows":[{"customer_id":"00123","name":"Nordlys AS"}]}
```

Every cell stays a string; nothing is converted to a number, boolean, date or
null. A quoted field can hold the delimiter, doubled quotes and line breaks,
and a UTF-8 byte order mark is removed. Lines end with LF or CRLF, and a lone
CR is refused. An unclosed quote, text after a closing quote, a quote inside
an unquoted field and a row of a different width than the header answer 400.
A blank line is a row with one empty field.

---

### `POST /table_match`
Compares two lists of rows, `left` and `right`, on the key column pairs in
`keys`. Every pair must be equal for two rows to match.

```json
// Request
{"left": [{"id": "1"}, {"id": "2"}], "right": [{"id": "2"}, {"id": "3"}], "keys": [{"left": "id", "right": "id"}]}
```

Stored as `matches.json`:

```json
{"matched":[{"left_index":1,"right_index":0}],"only_left":[0],"only_right":[1],"ambiguous":[]}
```

Every row lands in exactly one list, and indices are zero-based positions in
the lists you sent. When a key value found in both tables appears more than
once in either of them, all those rows go into `ambiguous` as `left_indices`
and `right_indices`; nothing is paired at random. A row whose key is missing,
null or empty never matches and is listed in `only_left` or `only_right`.
Keys compare exactly and with their type: `"1"` does not match `1`, and
nothing is trimmed. Key values may be strings, integers or booleans, and a
number with a decimal part is refused. At most 5000 rows per table, 100
fields per row and 100 key pairs. The report holds positions only, not your
data.

---

### `POST /json_format`
Formats JSON text sent as a string in `data`. `mode` is `"pretty"` (default)
or `"compact"`, and `indent` is `2` (default) or `4`.

```json
// Request
{"data": "{\"price\":1.50,\"tags\":[\"a\"]}", "mode": "pretty"}
```

Stored as `result.json`:

```json
{
  "price": 1.50,
  "tags": [
    "a"
  ]
}
```

Only whitespace changes. Number spelling, string escapes, key order and
duplicate keys are kept, so `1.50` stays `1.50` and a 30-digit integer stays
exact. Pretty output ends with a line break. Invalid JSON, or more than 127
nested lists or objects, answers 400 with the parser's message and stores nothing.

---

### `POST /json_validate`
Checks the syntax of JSON text sent as a string in `data`. Invalid JSON is a
result, not an error: the call answers 200, adds `valid` to the Storage
fields, and stores a report.

```json
// Request
{"data": "{\"a\":1,}"}
```

Stored as `validation.json`:

```json
{"valid":false,"error":"Syntax error","input_bytes":8,"max_depth":128}
```

The check is syntax only, not JSON Schema. `error` is the parser's message,
without a line or column. Duplicate keys are valid, and more than 127 nested
lists or objects is invalid. The report's `max_depth` of 128 is the parser's
limit, which counts the values inside the innermost list or object as one
more level. The report does not contain the JSON itself.

---

## Images

The seven image endpoints take one image as `multipart/form-data`, in a field
named `file`: a JPEG, PNG or WebP of at most 10 MB. `image_convert` and
`image_resize` also read HEIC, and `image_metadata` and `image_strip` also
read GIF. The format is read from the first bytes of the file, and an
animated image is converted from its first frame. Like the Convert endpoints,
they store the result in [Storage](#storage---24h-ttl) for 24 hours and answer
with the Storage fields plus `operation` and what the result is. A GET on
`storage_url` returns the result with its own type.

`image_convert`, `image_compress`, `image_resize`, `image_colors` and
`image_favicon` decode the image, which may then be at most 25 megapixels. Every converted image is
turned upright from its EXIF orientation, and EXIF, XMP, IPTC and comments are
removed. The ICC color profile is kept, and a CMYK JPEG becomes RGB. Only
`image_resize` changes the size. ImageMagick runs in a sandbox without network access, at most two
images at a time; a third waits up to ten seconds and is then answered 503
with `Retry-After`. A request may take 45 seconds, and a result may be 8 MB.

`image_metadata` and `image_strip` read and rewrite the file in PHP without
decoding it, so they have no pixel limit, run no process and never change a
pixel.

```json
// Response to the image_convert request below, from a test run with a test
// image of 1600 x 1200 pixels. The id, the expiry and the sizes differ.
{
  "storage_id": "1ddd4269-b51c-4209-a4de-6908926f672b",
  "storage_url": "https://aisenseapi.com/services/v1/storage/1ddd4269-b51c-4209-a4de-6908926f672b",
  "sha256_hash": "97350f282284446cbb19db5a0695a654e0162fafd52db766fb12099b6497202d",
  "bytes": 195648,
  "expire_timestamp": 1790767674,
  "expire_datetime": "2026-09-30T11:27:54+00:00",
  "content_type": "image/webp",
  "filename": "result.webp",
  "operation": "image_convert",
  "format": "webp",
  "width": 1600,
  "height": 1200,
  "input_format": "jpeg",
  "input_bytes": 641358
}
```

| Status | When |
|--------|------|
| 400 | A field is missing, unknown or out of range, the upload is not one whole file, or ImageMagick cannot read the image |
| 405 | The method is not `POST` |
| 413 | The upload, its number of pixels or the result is over a limit |
| 415 | The body is not `multipart/form-data`, or the file is not a JPEG, PNG or WebP (or HEIC for `image_convert` and `image_resize`, GIF for `image_metadata` and `image_strip`) |
| 429 | The request budget or the day's Storage budget is used up |
| 503 | Two images are being converted already, the conversion took more than 45 seconds, or the service cannot convert right now |

Each endpoint has a guide with a browser tool:
[image converter](https://aisense.no/free-image-converter-api),
[image compression](https://aisense.no/free-image-compression-api),
[image metadata](https://aisense.no/free-image-metadata-viewer-api),
[EXIF remover](https://aisense.no/free-exif-remover-api),
[color palette](https://aisense.no/free-image-color-palette-api) and
[favicon generator](https://aisense.no/free-favicon-generator-api).

---

### `POST /image_convert`
Converts between JPEG, PNG and WebP, and reads HEIC.

```bash
curl -s -X POST https://aisenseapi.com/services/v1/image_convert \
  -F "file=@photo.jpg" \
  -F "format=webp"
```

| Field | Required | Meaning |
|-------|----------|---------|
| `file` | yes | The image: JPEG, PNG, WebP or HEIC |
| `format` | yes | `jpeg`, `png` or `webp`; `jpg` is read as `jpeg` |
| `quality` | no | 40 to 95, for JPEG and WebP; 82 when left out |
| `lossless` | no | `true` or `false`, for WebP only; lossless takes no quality |

Transparency is kept in PNG and WebP and becomes white in a JPEG. PNG is
lossless and takes no quality. WebP allows at most 16383 pixels per side.
A HEIC from an iPhone is turned once, the way its irot box says, and keeps
its color profile. HEIC cannot be written.

---

### `POST /image_compress`
Saves a JPEG, PNG or WebP again in its own format.

```bash
curl -s -X POST https://aisenseapi.com/services/v1/image_compress \
  -F "file=@photo.jpg" \
  -F "quality=70"
```

| Field | Required | Meaning |
|-------|----------|---------|
| `file` | yes | The image: JPEG, PNG or WebP |
| `quality` | no | 40 to 95, for JPEG and WebP; 82 when left out. A PNG takes none |

JPEG and WebP are saved again at the given quality, which is lossy. PNG is
saved again losslessly at the strongest zlib level. A `format` field is
refused. An image that was already compressed harder can come out larger;
`bytes` and `input_bytes` in the answer show it. A HEIC is refused here;
convert it with `image_convert`.

---

### `POST /image_resize`
Gives a JPEG, PNG, WebP or HEIC a new size.

```bash
curl -s -X POST https://aisenseapi.com/services/v1/image_resize \
  -F "file=@photo.jpg" \
  -F "width=800"
```

| Field | Required | Meaning |
|-------|----------|---------|
| `file` | yes | The image: JPEG, PNG, WebP or HEIC |
| `width`, `height` | one of them | The box in pixels, 1 to 10000 |
| `fit` | no | `contain` (default) keeps all of the picture inside the box; `cover` fills the box and cuts the rest from the centre, and needs both sides |
| `upscale` | no | `true` lets a smaller picture be enlarged; `false` when left out |
| `format` | no | `jpeg`, `png` or `webp`; the format of the upload when left out, and JPEG for a HEIC |
| `quality`, `lossless` | no | As for `image_convert` |

The picture is turned upright before it is resized, and the aspect ratio is
always kept. A picture already smaller than the box keeps its size unless
`upscale=true`. The answer adds `input_width` and `input_height`, the size of
the upload once upright, `fit`, and `upscaled`. A result that would be over 25
megapixels, or over 16383 pixels on a side as WebP, is refused before anything
runs. [Guide and browser tool](https://aisense.no/free-image-resizer-api).

---

### `POST /image_metadata`
Reports what an image carries besides its pixels, stored as `metadata.json`.

```bash
curl -s -X POST https://aisenseapi.com/services/v1/image_metadata \
  -F "file=@photo.jpg"
```

| Field | Required | Meaning |
|-------|----------|---------|
| `file` | yes | The image: JPEG, PNG, WebP or GIF |

The report has `file` (format, size, dimensions, estimated JPEG quality and
more, and for a GIF the frames, loop count and duration), `orientation`,
`color_profile`, `exif` by directory, `gps` in decimal degrees with the
altitude in metres and the time in UTC, `xmp`, `iptc`, `comments`, `text`
(PNG text chunks, GIF plain text), `embedded` (thumbnails, a multi-picture index, data
after the end of the image) and `privacy`: what can identify a person, a
place, a device or a time, most sensitive first, each with `item`, `level`
and `why`. The answer adds `format`, `width`, `height`, `gps` (true when there
is a position) and `findings`, the items of the privacy list.

---

### `POST /image_strip`
Removes the metadata without saving the image again.

```bash
curl -s -X POST https://aisenseapi.com/services/v1/image_strip \
  -F "file=@photo.jpg"
```

| Field | Required | Meaning |
|-------|----------|---------|
| `file` | yes | The image: JPEG, PNG, WebP or GIF |

From a JPEG it removes EXIF, XMP, IPTC and other Photoshop data, comments,
the multi-picture index, other application segments and anything after the
end of the image; from a PNG the text chunks, XMP, EXIF and the time; from a
WebP the EXIF and XMP chunks; from a GIF the comments, XMP, plain text and
unknown application extensions, keeping every frame with its timing and the
loop count. The image data is copied byte for byte. The
color profile is kept, and an orientation other than upright is written back
alone. The result is stored in the format of the upload, at most 10 MB, and
the answer adds `format`, `width`, `height`, `input_bytes`, `removed` and
`kept`.

---

### `POST /image_colors`
The dominant colors of an image, stored as `colors.json`.

```bash
curl -s -X POST https://aisenseapi.com/services/v1/image_colors \
  -F "file=@photo.jpg" \
  -F "count=6"
```

| Field | Required | Meaning |
|-------|----------|---------|
| `file` | yes | The image: JPEG, PNG or WebP |
| `count` | no | How many colors, 2 to 16; 8 when left out |

The report has `colors`, each with `hex`, `rgb` and its `share` of the
visible pixels, the `average`, `transparent_share` for the pixels left out,
and `placeholder`, the image at most 16 pixels on its longest side as a PNG
data URI. The answer adds `average`, `dominant` and `count`.

---

### `POST /image_favicon`
A favicon set as a ZIP, stored as `favicon.zip`.

```bash
curl -s -X POST https://aisenseapi.com/services/v1/image_favicon \
  -F "file=@logo.png" \
  -F "crop=trim" \
  -F "name=Example site"
```

| Field | Required | Meaning |
|-------|----------|---------|
| `file` | yes | The picture: JPEG, PNG or WebP |
| `crop` | no | `fit` (all of it on transparent, the default), `trim` (cut away a border of one color first) or `center` (a square from the middle) |
| `name` | no | The site name for the manifest, at most 60 characters |

The ZIP holds `favicon.ico` with 16, 32 and 48 pixels, `favicon-16x16.png`,
`favicon-32x32.png`, `apple-touch-icon.png` (180 pixels on white),
`icon-192.png`, `icon-512.png`, `site.webmanifest` and `head.html` with the
tags to paste. The answer adds `files`, `crop` and `upscaled`, which is true
when the picture, or what was left after trimming, was smaller than 512
pixels.

---

## Logic

`/decide` answers typed questions from rules by default, with optional model
selection. `/mock_response` answers with the response you pick for client tests.

### `POST /decide`

Omit `model` or use `"model":"rules"` for typed decisions from rules.
This keeps the existing response unchanged. The body is a JSON object
with `state`, the facts to decide on, and `questions`, 1 to 64 named questions.
Each question has a `type`:

| Type | Fields | Answers with |
|---|---|---|
| `yes_no` | `rules`, optional `bias` | `answer`, `probability` of yes |
| `choice` | `options`: 2 to 100 named lists of rules, optional `priors` | `choice`, `probabilities` |
| `scale` | `levels`: 2 to 20 ordered, named lists of rules, optional `priors` | `level`, `expected`, `probabilities` |

Every question also takes `act_at` (0.9 unless set) and `review_at` (0.5 unless
set), and every answer has `confidence`, `action` and `because`.

A rule is `{"if": condition, "weight": number}`. The weight is evidence in
log-odds, from -100 to 100: positive pulls towards the answer, and 1 multiplies
the odds by about 2.7. A `yes_no` is sigmoid(bias + the weights of the rules
that held). A `choice` is softmax over each option's prior plus its weights. A
`scale` is a choice over ordered levels, and `expected` counts the first level
as 0. Confidence is (n × the largest probability − 1) / (n − 1), which is
|2p − 1| for a `yes_no`. `action` is `act` from `act_at`, `review` from
`review_at`, and `hold` below. `because` lists the rules that held, with their
index and weight, so every number can be worked out by hand. When options tie
at the top, the first listed wins and `tied` names them.

A condition is an object of fields and tests, and every field must hold. A
field is a dotted path into the state, where a number picks from a list, such as
`items.0.sku`. The tests are `eq`, `ne`, `gt`, `gte`, `lt`, `lte`, `in` (a list
of up to 100 values), `exists`, `prefix` and `contains`. `prefix` and
`contains` ignore case, and `contains` on a list asks for an item. 1 equals 1.0,
but `true` is not 1. `any` is a list of conditions of which one must hold, and
`not` inverts one. A path that leads nowhere fails every test except
`exists: false`. There are no regular expressions.

```bash
curl -s -X POST https://aisenseapi.com/services/v1/decide \
  -H "Content-Type: application/json" \
  -d '{"state": {"amount": 30}, "questions": {"refund": {"type": "yes_no", "bias": -1, "rules": [{"if": {"amount": {"lte": 50}}, "weight": 3}]}}}'
```

```json
{"answers": {"refund": {"type": "yes_no", "answer": "yes", "probability": 0.8808, "confidence": 0.7616, "action": "review", "because": [{"rule": 0, "weight": 3}]}}}
```

Limits: 64 KiB of JSON, 50 rules per list, 5000 tests and 8 levels of `any` and
`not` in one request. A refusal has `error`, naming the field, and `fix`: 400
for a wrong field or invalid JSON, 405 for any method but POST, 413 for a body
or rule set over the limits, 415 unless the body is `application/json`. Nothing
from the request body is stored in rules mode. The access log records request
metadata, not the body.
[Guide and examples](https://aisense.no/free-public-api-decide-api-endpoint).

#### Optional decision models

Set `model` to `"clef"`, `"nimble"` or `"tev1"` and supply `state` plus named
`questions`. Clef is from Cloudflare, Nimble from Bespoke Labs and Tev1 from
Together AI, and all three answer the same question types. Tev1 is the
smallest and fastest. Together AI tested it in English only, and it suits
short, direct questions. Each question has
`type`, `instructions` and `criteria`. An unknown model returns 400. There is
no fallback to rules or to another model.

| Type | Criteria | Answer |
| --- | --- | --- |
| `noul` | Object with `true` and `false` descriptions | Numeric `noul` in [0,1] |
| `choice` | Object of named descriptions | `choice`, `probabilities`, `confidence` |
| `score` | Ordered label list | Zero-based fractional `score`, `legend`, `probabilities`, `confidence` |

~~~json
{"model":"clef","state":{"message":"The production API is down."},"questions":{"urgent":{"type":"noul","instructions":"Is this urgent?","criteria":{"true":"An active production failure.","false":"Routine work."}}}}
~~~

The response includes `model`, `model_version`, `answers` and optional `usage`.
Model confidence is not the rule confidence formula or a guarantee of accuracy.
There is no `action` or `because`. Model questions do not accept rule fields.

Limits: 8 KiB body, 3 KiB for `tev1`, 4 questions, 8 choices or levels, 1024
UTF-8 bytes per instruction and 512 per criterion. Each IP may make 60 model requests per UTC
minute and 1000 per UTC day. An accepted request counts, also when it fails.

A request too long for the selected model returns 413, a reached limit 429, a
model that is temporarily unavailable 503, a request that could not be completed 502 and one that timed
out 504. Respect `Retry-After` where provided. Do not retry in a loop. Rules
remain available.

Model mode sends the state and questions to the model for processing. The
API keeps IP-HMAC usage counters and aggregate timings, not bodies or answers.
Keep credentials and sensitive personal data out. Ordinary access logs still
contain IP addresses. See [Privacy](https://aisense.no/privacy).

### `ANY /mock_response/{status}[/{ms}]`

Answers with the response the path names, a failure or a slow success, for
testing how a client handles it.
Any method works, and neither the body nor the query string is read.

| Path | Answer |
|---|---|
| `/mock_response/{status}` | The status at once: 200, 201, 204, 400, 401, 403, 404, 409, 410, 422, 429, 500, 502, 503 or 504 |
| `/mock_response/{status}/{ms}` | The same after `ms` milliseconds, 0 to 10000 |
| `/mock_response/html` | 502 with an HTML page, as a proxy answers when the service behind it is down |
| `/mock_response/empty` | 200 labelled `application/json`, with no body |
| `/mock_response/wrongtype` | 200 with valid JSON labelled `text/plain` |

The three events take a delay the same way, such as `/mock_response/html/2000`. A status
of 400 or above answers `{"error": reason phrase, "mock_response": {"status", "delay_ms"}}`,
200 and 201 answer `{"ok": true, "mock_response": {...}}`, and 204 has no body. 429 and
503 carry `Retry-After: 2`, and 401 carries `WWW-Authenticate`. Every chosen
answer carries `X-Mock-Response` with what the path asked for.

```bash
curl -s https://aisenseapi.com/services/v1/mock_response/503
```

```json
{"error":"Service Unavailable","mock_response":{"status":503,"delay_ms":0}}
```

A delay holds a place while it waits, at most four at a time from one address.
When none is free the answer is a real 503 with `Retry-After: 1`, a `fix` and no
`X-Mock-Response`. An unknown path or status is 404 with a `fix` listing the forms, and
a delay over 10000 is 400. Nothing is stored, and mock_response calls count towards the
5000 requests per IP per day.
[Guide and a client test](https://aisense.no/free-public-api-mock-response-api-endpoint).

---

## AIQ

A test an AI agent takes on its own, in four versions. A start names the
version in its path, and every result names the version it ran, so a score is
compared only with scores of the same version, profile and signed recipe. `GET /aiq` describes
every route, profile, limit and the key that signs the results, and
`GET /aiq/versions` lists the versions with their status.

| Version | What it tests | Start | Result |
| --- | --- | --- | --- |
| `ard` | 100 tasks of logic, API and data work; profiles `standard-100` and `pilot-20` | `GET /aiq/start/ard[/{profile}]` | the AIQ, the tasks answered correctly |
| `bri` | 100 scenarios in a small simulated shop, worked through operations | `GET /aiq/start/bri` (default `scenario-100`) | 0 to 100 points, one per passed scenario |
| `cen` | six scenarios with twenty published criteria of five points each | `GET /aiq/start/cen` | 0 to 100 points |
| `dar` | a coordinator and two workers taking five scenarios together over Aamio, experimental | `POST /aiq/start/dar/team-5` with `{"coordinator_key": "..."}` | 0 to 100 points |

An ard, bri or cen run answers a `run_id`, a `run_token` and the first task.
Every later call carries `Authorization: Bearer <run_token>`: an answer is
`POST /aiq/{run_id}/answer` with `task_id`, an `attempt_key` and the `answer`,
and an operation of a bri or cen scenario is
`POST /aiq/{run_id}/call/{operation}`. A dar team does every action of the test
over Aamio; HTTP starts it and reads its status and result at
`GET /aiq/{run_id}`.

DAR's `GET /aiq/versions/dar` includes `profiles.team-5.contract` with
request examples, key encoding, canonical artifact bytes and criterion names.
Public keys and signatures use base64url without padding. `add_worker` places
the role in `args.role` and the key in `register.key`. Write operations put
`operation_id` inside `args`. Wait for `controller_inbox_ready=true`
before sending and for `result_final=true` before quoting a final result.
The public run is `client_managed`. Separate keys do not prove separate
agent executions.

A finished run answers a signed `test_string`. `POST /aiq/verify` checks it, and
the same string sent to `POST /aiq/start/{version}` replays its recipe while that recipe is supported. A retired recipe still verifies but cannot start a replay. An ard run
also has a receipt, and a dar run gives its owner a signed export, both at
`GET /aiq/{run_id}/receipt` until the run expires 24 hours after its start.
ard, bri and cen share 20 runs in 24 hours from one address; dar allows 3.

BRI's default `scenario-100` allows 20 active hours, 600 seconds per scenario,
40 operations and 15 write attempts per scenario. All 100 must be assessed
for a total score. A fault on our side or an exhausted daily allowance leaves
the total unavailable. A start requires 4201 requests remaining after the
start request itself. The allowance is shared with other requests from the
address and is not reserved. Every run still expires 24 hours after creation.
The explicit `/aiq/start/bri/scenario-6` profile reports a count out of six.

[AI SENSE AIQ](https://aisense.no/aisense-aiq) and
[AI SENSE AIQ versions](https://aisense.no/aisense-aiq-versions) describe each
version, with instructions for an agent.

---

## Hash

All hash endpoints accept JSON (`{"data": "..."}`), plain text
(`Content-Type: text/plain`), or a file upload. **Each returns a key named after
the algorithm - not `hash`.**

| Endpoint | Response key | Example value for `"Hello"` |
|----------|--------------|------------------------------|
| `POST /md5_hash` | `md5_hash` | `8b1a9953c4611296a827abf8c47804d7` |
| `POST /sha1_hash` | `sha1_hash` | `f7ff9e8b7bb2e09b70935a5d785e0cc5d9d0abf0` |
| `POST /sha256_hash` | `sha256_hash` | `185f8db32271fe25f561a6fc938b2e26...` |
| `POST /sha512_hash` | `sha512_hash` | `3615f80c9d293ed7402687f94b22d58e...` |
| `POST /crc32_checksum` | `crc32_checksum` | `4157704578` |
| `POST /whirlpool_hash` | `whirlpool_hash` | `00acca7b4456c52a74c589d668b48e1b...` |
| `POST /sha3_256_hash` | `sha3_256_hash` | `8ca66ee6b2fe4bb928a8e3cd2f508de4...` |
| `POST /sha3_512_hash` | `sha3_512_hash` | `0b8a44ac991e2b263e8623cfbeefc1cf...` |
| `POST /blake2b_hash` | `blake2b_hash` | `8b7ca7d27d9fc55fa30abfe515b3afb2...` |
| `POST /blake3_hash` | `blake3_hash` | `fbc2b0516ee8744d293b980779178a35...` |

`crc32_checksum` is an **integer**, not a hex string. Whirlpool, SHA3-256,
SHA3-512 and BLAKE2b-256 were added 2 October 2026 and BLAKE3 on 3 October.
They hash the bytes as sent, with nothing trimmed, and an empty string is
refused like everywhere in the family. BLAKE2b-256 is BLAKE2b with a 32 byte
output, not the first half of BLAKE2b-512. BLAKE3 input is at most 1 MiB;
larger files are hashed where they live. None of these is a password hash;
those are below.

```json
// POST /sha256_hash
{ "data": "Hello" }
-> { "sha256_hash": "185f8db32271fe25f561a6fc938b2e264306ec304eda518007d1764826381969" }
```

---

### `POST /hash_verify`
Verify data against a hash from any of the endpoints above. JSON only, since
the hash travels alongside the data. The algorithm is recognized from the hash
itself: an integer means crc32 in the form `/crc32_checksum` returns, and hex
strings are mapped by length - 8 is crc32, 32 md5, 40 sha1, 64 sha256,
128 sha512.

Name the algorithm in an `algorithm` field when you know it, and always for
`whirlpool`, `sha3_256`, `sha3_512` and `blake2b`, since a length no longer
names one algorithm: SHA3-256 and BLAKE2b-256 are 64 hex characters like
SHA-256, and SHA3-512 and Whirlpool are 128 like SHA-512. The hyphenated
spellings `sha3-256` and `sha3-512` are accepted. With the field, a hash of the
wrong length for that algorithm is **HTTP 400** with a `fix`.

A mismatch is a **result**, not an error, and `computed` is always included so
you can see what the data actually hashes to. Unrecognized hash formats return
**HTTP 400**.

```json
// Request
{ "data": "Hello", "hash": "185f8db32271fe25f561a6fc938b2e264306ec304eda518007d1764826381969" }

// Response
{ "match": true, "algorithm": "sha256", "computed": "185f8db32271fe25f561a6fc..." }

// Integer crc32, straight from /crc32_checksum
{ "data": "Hello", "hash": 4157704578 } -> { "match": true, "algorithm": "crc32", "computed": 4157704578 }

// A named algorithm, required for the four newer ones
{ "data": "Hello", "hash": "8ca66ee6b2fe4bb928a8e3cd2f508de4119c0895f22e011117e22cf9b13de7ef", "algorithm": "sha3_256" }
-> { "match": true, "algorithm": "sha3_256", "computed": "8ca66ee6b2fe4bb928a8e3cd..." }
```

`blake3` is named the same way; its 64 characters would otherwise read as
SHA-256. `argon2id`, `bcrypt` and `scrypt` named here answer 400 with a fix
pointing at `/password_verify`: their strings are salted and are not digests
of the data.

---

### Password hashes: `POST /argon2id_hash`, `/bcrypt_hash`, `/scrypt_hash`

Added 3 October 2026. Slow by design and salted, so every call gives a new
string, and the string carries its own algorithm, salt and cost. Input is JSON
`{"password": "..."}` (or `data`, like the rest of the family), or a
`text/plain` body; 1 to 1024 bytes, and for bcrypt at most 72 bytes without a
NUL, since bcrypt would silently cut a longer one. No file upload: a file is
not a password.

| Endpoint | Profile | Answer |
|----------|---------|--------|
| `POST /argon2id_hash` | 64 MiB, 3 passes, 1 lane, 32 byte hash | `{"argon2id_hash": "$argon2id$v=19$m=65536,t=3,p=1$...$..."}` |
| `POST /bcrypt_hash` | cost 12 | `{"bcrypt_hash": "$2b$12$..."}`, 60 characters |
| `POST /scrypt_hash` | N=2^17, r=8, p=1, 32 byte hash | `{"scrypt_hash": "$scrypt$ln=17,r=8,p=1$...$..."}` |

```json
// POST /argon2id_hash
{ "password": "correct horse battery staple" }
-> { "argon2id_hash": "$argon2id$v=19$m=65536,t=3,p=1$mWHnZ4Nxo3vEDMtb9cO7/A$PUXcfBGwUfBbXE1GgMiw4yPbY31fklKc0mRW99HBcsQ" }
```

The profiles are fixed and are the OWASP recommendations of 2026; the
format is the PHC string for Argon2id and scrypt and the modular crypt
string for bcrypt, so the result verifies with `password_verify` in PHP,
`argon2-cffi` in Python, `bcrypt` anywhere, and most other libraries.

**Use test data.** The hash is kept by nobody here, but the password travels
to a public service, and a real password should be hashed inside the
application that uses it. The point of these routes is to test, compare and
generate vectors.

**Cost and budgets.** One call is 100 to 230 ms of CPU, 250 to 580 times a
SHA-256, so the routes have budgets beside the 5000 calls per day every
address has: **200 password operations per IP address per day** (hashing and
verifying together) answered with **429** past that, and **20 000 per day for
everyone** answered with **503**, both with `Retry-After` until midnight Oslo
time. The hashing runs one computation at a time in a process of its own;
while that process is busy with another caller the answer is **503** with
`Retry-After: 1` and `"reason": "busy"`, and when it is down for any reason
**503** with `Retry-After: 5` and `"reason": "unavailable"`. Retry; nothing
else in the API is affected.

### `POST /password_verify`

Verify a password against an Argon2id, bcrypt or scrypt string. JSON only:
`{"password": "...", "hash": "..."}` (or `data`). The algorithm is read from
the string, `$argon2id$`, `$2a$`/`$2b$`/`$2x$`/`$2y$` or `$scrypt$`, so a
`$2y$` string made by PHP verifies here. An `algorithm` field, when sent,
must agree with the string. A mismatch is a **result**, not an error.

```json
{ "password": "correct horse battery staple", "hash": "$2b$12$gn6ItEhVTwbuboZRi6NOZ.CDyi0awJjCpEvbnwwRP7kwJAJXJ4T5q" }
-> { "match": true, "algorithm": "bcrypt", "params": { "cost": 12 } }
```

The cost is read from the string and must be within what this service
produces: Argon2id up to m=65536, t=3, p=1; bcrypt cost 4 to 12; scrypt up to
ln=17, r=8, p=1. A string that asks for more is **400** with a `fix`, so a
caller cannot choose how much work a verification costs. A hex digest sent
here is 400 with a pointer to `/hash_verify`. Verification draws on the same
200 per day budget as hashing.

---

## Web

### `GET /ping`
```json
{ "ping": "pong" }
```

---

### `GET /health`
The second key is `microtimestamp`, not `timestamp`.

```json
{ "status": "ok", "microtimestamp": 1786873258.589068 }
```

---

### `POST /html2pdf`
Renders HTML into a PDF and stores it for 24 hours. The response carries a
link, not the file: the PDF is fetched in a second request.

The markup goes in `data` or `html` - the two names are interchangeable. An
optional `options` object sets the page up.

```json
// Request
{
  "html": "<h1>Invoice 4817</h1><p>Paid</p>",
  "options": { "page-size": "A5", "orientation": "Landscape", "margin-top": "20mm" }
}

// Response
{
  "storage_id": "1c896e41-d5b7-4017-b888-8381d7866088",
  "storage_url": "https://aisenseapi.com/services/v1/storage/1c896e41-d5b7-4017-b888-8381d7866088",
  "sha256_hash": "38f4ffe5184786d22c3370bd351b8cff30087d9f87eac15f92374272653893e7",
  "bytes": 12764,
  "expire_timestamp": 1787257796
}
```

Fetching `storage_url` returns the file with `Content-Type: application/pdf`,
and an `ETag` that is `sha256_hash` in quotes. The digest and byte count
above are from one real render of that request; a PDF carries its creation
time, so the next render of the same markup hashes differently.

`options` accepts `page-size` (A3, A4, A5, Letter, Legal, Tabloid),
`orientation` (Portrait, Landscape) and `margin-top`, `margin-bottom`,
`margin-left`, `margin-right` (up to three digits, optional mm, cm or in
suffix). Values outside those lists are ignored rather than passed on.

The renderer runs sandboxed with no network access and local file access
disabled, so remote images, stylesheets and fonts referenced in the markup
are not fetched - inline everything the document needs. Empty input returns
HTTP 400; a render failure returns HTTP 500 with the reason.

---

### `GET /client_ip`
```json
{ "ip": "203.0.113.42" }
```

---

### `GET /user_agent`
```json
{ "user_agent": "curl/8.5.0" }
```

---

### `GET /ip_reverse_lookup/{ip}`
`city` and `place` are frequently `null`, and coordinates fall back to the
country centroid when the city is unknown.

```json
{
  "ip": "8.8.8.8",
  "country": "United States",
  "city": null,
  "location": { "lat": "37.751000", "lng": "-97.822000" },
  "place": null,
  "timezone": "America/Chicago"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `ip` | string | The address that was looked up |
| `country` | string | Country name |
| `city` | string\|null | City name, often null |
| `location.lat` | string | Latitude, as a string |
| `location.lng` | string | Longitude, as a string |
| `place` | string\|null | More specific place name, usually null |
| `timezone` | string\|null | IANA timezone identifier |

---

### `GET /domain_ip_lookup/{domain}`
```json
{ "domain": "example.com", "ip": "104.20.23.154" }
```

---

### `POST /email_validate`
Syntax check, then DNS. `has_mx` means the domain publishes MX records;
`has_address_record` means it resolves at all, which RFC 5321 allows as a
delivery fallback - so a missing MX alone does not prove an address dead.
Neither proves a mailbox exists; only an SMTP conversation could, and this
endpoint deliberately never opens one.

An address that fails validation is a **result** with `valid_syntax: false`,
not an error. 400 is reserved for sending no input at all. DNS resolution uses
the host resolver only - nothing is sent to any third party. Internationalized
domains are not converted to punycode and report `valid_syntax: false`.

```json
// Request
{ "data": "test@gmail.com" }

// Response
{
  "email": "test@gmail.com",
  "valid_syntax": true,
  "domain": "gmail.com",
  "has_mx": true,
  "mx_hosts": ["gmail-smtp-in.l.google.com", "alt1.gmail-smtp-in.l.google.com"],
  "has_address_record": true
}
```

---

### Storage - 24h TTL

**Store:** `POST /storage` - JSON, plain text, or a file upload.

The request body is stored **verbatim**. Whatever you send is exactly what you
get back; no `data` wrapper is added or removed. Post `{"data": {...}}` and you
retrieve `{"data": {...}}`.

```json
// Request body
{"key1":"value1"}

// Response
{
  "storage_id": "123e4567-e89b-12d3-a456-426614174000",
  "storage_url": "https://aisenseapi.com/services/v1/storage/123e4567-e89b-12d3-a456-426614174000",
  "sha256_hash": "9874854240b45b4bdbf43fca6110bafce8525aedbeca5babaee0cb137d9a7868",
  "bytes": 17,
  "expire_timestamp": 1738457158,
  "expire_datetime": "2025-02-02T01:25:58+00:00"
}
```

`storage_url` is the link to hand on, and `sha256_hash` is the digest of the
bytes as stored, so whoever fetches them can tell they got what you sent.
`bytes` is the stored length. The digest above is the real one for the 17 byte
body in this example.

**Limit the downloads:** `POST /storage/max_downloads/{n}` stores the same
way and removes the object after `n` downloads, 1 to 100. The answer carries
two more fields, `downloads_max` and `downloads_left`.

```json
// POST /storage/max_downloads/2 with the body {"report":"q3","pages":12}
{
  "storage_id": "5e1c0a7e-9b3f-4c62-8a1d-2f7b6d4c9e10",
  "storage_url": "https://aisenseapi.com/services/v1/storage/5e1c0a7e-9b3f-4c62-8a1d-2f7b6d4c9e10",
  "sha256_hash": "700d8cea137c32c31e4865aaf5ae327931067ae454bc78777f8572dadf9c9809",
  "bytes": 26,
  "expire_timestamp": 1791409876,
  "expire_datetime": "2026-10-07T21:51:16+00:00",
  "downloads_max": 2,
  "downloads_left": 2
}
```

Every GET that serves the bytes takes one download and says how many remain
in a `Downloads-Left` header. A `304` or a `412` takes none, since no bytes
went out. Once the last download has gone out the bytes are removed, and the
id answers `410 Gone` with `{"error": "Storage object gone"}` for the rest of
its 24 hours. `max_downloads/0`, or no segment at all, is the plain 24 hour
object. Any other value outside 1 to 100 is `400`.

**Retrieve:** `GET /storage/{storage_id}` - returns the stored bytes with
`application/json` if they parse as JSON, otherwise `application/octet-stream`.
The answer carries `ETag`, which is `sha256_hash` in quotes, so a repeat fetch
sending `If-None-Match` with that value is answered `304 Not Modified` with no
body. An unknown or expired id returns `{"error": "Storage id unknown"}`, and
an object whose downloads are all taken returns `410` with
`{"error": "Storage object gone"}`.

**Fetch only if it is what you expect:** put the digest in the link.

```
GET /storage/{storage_id}/sha256/{64 hex}
```

The bytes come back only if they hash to that value. If they do not, the
answer is `412 Precondition Failed` with both digests, and nothing is
served:

```json
{
  "error": "Stored bytes do not match the sha256 in the link",
  "storage_id": "123e4567-e89b-12d3-a456-426614174000",
  "expected": "0000000000000000000000000000000000000000000000000000000000000000",
  "sha256_hash": "9874854240b45b4bdbf43fca6110bafce8525aedbeca5babaee0cb137d9a7868"
}
```

A digest that is not 64 hexadecimal characters, or any algorithm other than
`sha256`, is `400`. The point is that a link can carry its own expectation,
so a receiver that only has the URL gets a hard failure instead of content
it did not ask for. It is a guard against a wrong id or a wrong object, not
a proof: the server computes the comparison, so a caller that needs proof
must hash the bytes itself. It is not access control either, since the link
without the digest still works.

A client that can set a header can use `If-Match` with the same value in
quotes instead, which is the standard spelling of the same condition and
answers `412` the same way.

**Caching:** a stored object never changes and lives 24 hours, so the answer
is `Cache-Control: private, no-cache`. The browser that fetched it may keep
it, and revalidates every time, which the `ETag` turns into a `304` with no
body. `private` keeps it out of shared caches, and revalidation means
content removed on notice stops being served at once.

**Limits:** executable files (Windows, Linux and Mac programs, judged on their
first bytes) are refused with `415` and never stored. Each IP may store 80 MB
per day; past that a POST answers `429` until the counter resets at
22:00 UTC from late March to late October and at 23:00 UTC the rest of the year (midnight in Norway, time zone Europe/Oslo). A stored file is returned inline only as an image, audio, video
or PDF; anything else, SVG included, comes back as `application/octet-stream`.
Content reported to abuse@aisense.no as unlawful or abusive is removed on
notice.

---

### `GET /url_shortener/{url}` - 24h TTL
The target URL goes inline in the path, unencoded.

```
GET /url_shortener/https://developer.mozilla.org/some/long/path
```

```json
{ "short_url": "https://307.fi/KtNshX2B", "expire_timestamp": 1786959715 }
```

---

### Webhook Capture - 24h TTL

**Create:** `POST /webhook_capture`

The JSON body may be empty. Add `notify_url` when you want one completion
signal sent to a public HTTP or HTTPS URL after the first request arrives.

```json
{
  "ok": true,
  "capture_id": "6f8c9e52-3f2c-4e73-9d3b-8d6c3f6d1c91",
  "status": "pending",
  "update_url": "https://aisenseapi.com/services/v1/webhook_capture/6f8c9e52-.../update",
  "read_url": "https://aisenseapi.com/services/v1/webhook_capture/6f8c9e52-...",
  "wait_url": "https://aisenseapi.com/services/v1/webhook_capture/6f8c9e52-.../wait/25",
  "expire_timestamp": 1772893200
}
```

**Send:** any HTTP method to `update_url`.

**Read:** `GET /webhook_capture/{capture_id}`

**Wait:** `GET /webhook_capture/{capture_id}/wait/{seconds}` where `seconds`
is 0 to 25. The response returns early when the first request is captured and
adds `waited_seconds` and `wait_reason`.

```json
{
  "ok": true,
  "capture_id": "6f8c9e52-3f2c-4e73-9d3b-8d6c3f6d1c91",
  "captured_at_timestamp": 1786873316,
  "captured_at_datetime": "2026-08-16T09:41:56Z",
  "request": {
    "method": "POST",
    "uri": "/services/v1/webhook_capture/6f8c9e52-.../update",
    "headers": { "content-type": "application/json" },
    "client_ip": "203.0.113.10",
    "body": { "json": { "event": "payment.created" }, "text": null, "base64": null, "raw_length": 28 }
  }
}
```

The first request to `update_url` wins. Later retries return the stored first
request and cannot replace it or send a second completion signal. Captured
bodies are capped at 256 KB. An unknown ID returns HTTP 404. An expired capture
returns HTTP 410.

---

### Webhook Action - 24h TTL

**Create:** `POST /webhook_action`

`options` accepts either plain strings or `{"value": ..., "label": ...}`
objects. Field types: `radio`, `select`, `text`, `textarea`, `checkbox`.

```json
// Request
{
  "title": "Approval required",
  "description": "Please review and approve this request.",
  "notify_url": "https://example.com/action-ready",
  "fields": [
    {
      "type": "radio",
      "name": "decision",
      "label": "Select decision",
      "required": true,
      "options": [
        { "value": "approve", "label": "Approve" },
        { "value": "reject", "label": "Reject" }
      ]
    },
    { "type": "textarea", "name": "comment", "label": "Comment", "max_length": 500 }
  ]
}

// Response
{
  "ok": true,
  "action_id": "9e0e6d3b-1a45-44c5-9e0b-92f5f3bdb2f1",
  "form_url": "https://aisenseapi.com/services/v1/webhook_action/9e0e6d3b-.../form",
  "result_url": "https://aisenseapi.com/services/v1/webhook_action/9e0e6d3b-...",
  "wait_url": "https://aisenseapi.com/services/v1/webhook_action/9e0e6d3b-.../wait/25",
  "expire_timestamp": 1786959912,
  "expire_datetime": "2026-08-17T09:45:12Z"
}
```

**Open the form:** `GET /webhook_action/{action_id}/form` - returns `text/html`.

**Poll:** `GET /webhook_action/{action_id}`

**Wait:** `GET /webhook_action/{action_id}/wait/{seconds}` where `seconds` is
0 to 25. The response adds `waited_seconds` and `wait_reason`. A group wait
returns when any new answer changes the state.

```json
// Before submission
{
  "ok": true,
  "action_id": "9e0e6d3b-...",
  "status": "pending",
  "created_at_timestamp": 1786873535,
  "created_at_datetime": "2026-08-16T09:45:35Z",
  "expire_timestamp": 1786959935,
  "expire_datetime": "2026-08-17T09:45:35Z",
  "answered_at_timestamp": null,
  "answered_at_datetime": null,
  "response": null
}

// After submission
{
  "ok": true,
  "action_id": "9e0e6d3b-...",
  "status": "answered",
  "answered_at_datetime": "2026-08-16T15:13:20Z",
  "response": { "decision": "approve", "comment": "Looks good" }
}
```

Set `respondents` to an integer from 2 to 20 to create separate one-use bearer
links for a group. The create response then returns `form_urls` and no
`form_url`. The group status moves from `pending` to `partial` and then
`answered`. Reads include `respondents`, `answered`, `tally` and `responses`.
The tally counts values from the field named `decision`. Only hashes of the
individual bearer tokens are stored.

When `notify_url` is present, the service sends one small signal after a single
answer or the last group answer. The signal names the action, status and result
URL. It does not contain submitted answers. Create bodies are capped at 64 KB,
with at most 20 fields and 50 options per field.

---

### Webhook Schedule - 24h TTL

POST a URL and a payload with either `delay_seconds` or a `fire_at` Unix
timestamp. Add `every` from 60 to 86400 seconds for a recurring job.

The horizon is **one minute to 24 hours** - this is a 24-hour service, and the
scheduler is no exception. The result stays readable for 24 hours after the
final attempt.

Validation accepts anything from 5 seconds out, but that is the input check, not
the resolution. Delivery runs once a minute, so a job fires at the next whole
minute after it falls due, not at the exact second requested. Measured on
2026-08-21: a job due in 5 seconds was delivered 38 seconds later. Schedule in
minutes and treat anything finer as noise.

**Create:** `POST /webhook_schedule`

```json
// Request
{ "url": "https://example.com/hook", "delay_seconds": 1200, "payload": { "job": 42 } }

// Response
{
  "ok": true,
  "schedule_id": "1f1d7b8b-...",
  "status": "scheduled",
  "fire_at_timestamp": 1786990000,
  "fire_at_datetime": "2026-08-17T15:21:37+00:00",
  "result_url": "https://aisenseapi.com/services/v1/webhook_schedule/1f1d7b8b-...",
  "wait_url": "https://aisenseapi.com/services/v1/webhook_schedule/1f1d7b8b-.../wait/25",
  "expire_timestamp": 1787076400
}
```

**Poll:** `GET /webhook_schedule/{schedule_id}`

**Wait:** `GET /webhook_schedule/{schedule_id}/wait/{seconds}` where `seconds`
is 0 to 25.

**Cancel:** `DELETE /webhook_schedule/{schedule_id}` while it is active.

```json
{
  "ok": true,
  "schedule_id": "1f1d7b8b-...",
  "status": "fired",
  "attempts": 1,
  "http_status": 200,
  "response_excerpt": "...",
  "fired_at_datetime": "2026-08-17T15:21:40+00:00"
}
```

One-shot status may be `scheduled`, `retry`, `fired`, `failed` or `cancelled`.
`fired` means the target answered with some HTTP status, recorded in
`http_status`. It does not mean that the target returned 2xx.
**`fired` means a delivery was attempted, not that it succeeded** - a target that
answers 500 is still `fired` with `http_status: 500`.

A recurring job stays on its original time grid. Missed slots are counted and
skipped rather than delivered late. It normally ends as `completed` after its
fixed 24-hour window. Three consecutive transport failures stop it. A creator
address can cause at most 1440 delivery attempts per 24 hours.

The target must be an `http`/`https` URL on port 80 or 443 that resolves to a
**public** address. Private, loopback, link-local and reserved ranges are
refused, at creation and again at delivery time with the connection pinned to
the vetted address; redirects are never followed. Credentials in the URL are
rejected. Payload maximum 32 KB.

---

### Agent Wake - MCP task or REST polling, up to 24h

Agent Wake creates one durable wait state. It completes when a webhook arrives,
a person answers a hosted form or a selected time is reached. The MCP tool uses
the `io.modelcontextprotocol/tasks` extension. The REST interface exposes the
same task state for scripts and services.

**Create:** `POST /agent_wake`

```jsonc
// Webhook event
{ "event_type": "webhook", "timeout_seconds": 3600 }

// Human response
{
  "event_type": "human",
  "title": "Release build 42?",
  "description": "The checks passed.",
  "options": ["Release", "Hold"],
  "allow_note": true,
  "timeout_seconds": 3600
}

// Time event. Use delay_seconds or wake_at.
{ "event_type": "time", "delay_seconds": 600, "timeout_seconds": 900 }
```

```json
{
  "resultType": "task",
  "taskId": "2eb1a08d-759f-4af9-8caa-8b02b7ca17ba",
  "status": "working",
  "statusMessage": "Waiting for an event.",
  "createdAt": "2026-09-01T12:00:00Z",
  "lastUpdatedAt": "2026-09-01T12:00:00Z",
  "ttlMs": 3600000,
  "pollIntervalMs": 2000,
  "_meta": {
    "com.aisenseapi/agentWake": {
      "eventType": "webhook",
      "statusUrl": "https://aisenseapi.com/services/v1/agent_wake/2eb1a08d-...",
      "wakeUrl": "https://aisenseapi.com/services/v1/agent_wake/2eb1a08d-.../wake",
      "expiresAt": "2026-09-01T13:00:00Z"
    }
  }
}
```

**Wake a webhook task:** `POST`, `PUT` or `PATCH` to
`/agent_wake/{task_id}/wake`. The first accepted request completes the task.
Later requests return HTTP 409 and cannot replace the result. The body limit is
256 KB. Authorization, Cookie, X-API-Key and common token or secret headers are
redacted before storage.

**Read:** `GET /agent_wake/{task_id}`

**Wait:** `GET /agent_wake/{task_id}/wait/{seconds}` where `seconds` is 0 to
25. It returns early at a terminal state and adds `waitedSeconds` and
`waitReason`.

The status is `working`, `input_required`, `completed`, `failed` or `cancelled`.
A completed response includes `result`. A human task includes a `formUrl` and a
URL mode elicitation while it waits. A time task becomes complete on the first
read after its wake time.

**Cancel:** `DELETE /agent_wake/{task_id}`

Task IDs are bearer links and there is no list operation. Anyone holding a task
URL can read its result. Do not send secrets, credentials, personal data or
anything that needs more than 24 hours of retention.

---

### Agent Inbox - receive a verification mail, up to 24h

Agent Inbox gives an agent a disposable mail address of its own, to receive a
verification code, a confirmation link or a sign-up mail. No account and no
API key. An inbox lasts at most 24 hours, and that lifetime is fixed and not
extendable.

**Create:** `GET /inbox`, or `POST /inbox`

The route takes no arguments and needs no request body, so a plain GET creates
the inbox and an agent that can only fetch a URL can make one. POST does the
same. Anything that fetches the URL makes an inbox, a link preview included, so
keep the creation URL out of messages a preview will open. A create answers
HTTP 201.

```
GET /inbox
```

```json
{
  "ok": true,
  "inbox_id": "a85d0bee-f8f7-4be1-a1b3-8d58f3dbdfc7",
  "slug": "ztjqt7n",
  "address": "aisense+ztjqt7n@aisenseapi.com",
  "read_url": "https://aisenseapi.com/services/v1/inbox/a85d0bee-f8f7-4be1-a1b3-8d58f3dbdfc7",
  "wait_url": "https://aisenseapi.com/services/v1/inbox/a85d0bee-f8f7-4be1-a1b3-8d58f3dbdfc7/wait/25",
  "expire_timestamp": 1800086400
}
```

**Two identifiers come back, and only one of them is a secret.** The `slug` is
seven characters from `a-z0-9` and it appears in the address. It is public by
construction: it travels in mail headers, bounces and sender logs. Knowing it
lets anyone send mail to the inbox, and nothing more. It never reads the inbox
and it never appears in a URL. The `inbox_id` is a UUID and is the only
credential that reads the inbox. It is a bearer secret, returned once at
creation, and anyone holding it reads the mail. So guessing the address does
not read the inbox. A wrong `inbox_id` and an inbox that never existed both
answer HTTP 404 and never 403, which leaves the two indistinguishable.

**Read:** `GET /inbox/{inbox_id}`

```json
{
  "ok": true,
  "slug": "ztjqt7n",
  "address": "aisense+ztjqt7n@aisenseapi.com",
  "received": 1,
  "truncated": false,
  "messages": [
    {
      "from": "noreply@example.com",
      "subject": "Your verification code",
      "date": "2027-01-15T08:00:00Z",
      "text": "Your code is 481516. Confirm at https://example.com/confirm/abc",
      "codes": [ "481516" ],
      "links": [ "https://example.com/confirm/abc" ]
    }
  ],
  "created_at_timestamp": 1800000000,
  "expire_timestamp": 1800086400
}
```

The read response does not contain `inbox_id`. The credential is never echoed
back.

`date` is the time the service received the message, not the sender's `Date`
header, because that header is sender controlled. `codes` are standalone 4 to 8
digit numbers. `links` are public http and https links only; private-IP and
localhost links are dropped.

**Wait:** `GET /inbox/{inbox_id}/wait/{seconds}` where `seconds` is 0 to 25.
It returns the same object with `waited_seconds` and `wait_reason` added.
A value above 25 is clamped to 25, the same as every other wait route on this
surface.

`truncated` is worth knowing about. A full inbox refuses new mail rather than
evicting old mail, so the message you are waiting for can be turned away while
everything that arrived earlier is still sitting there. Either cap does it, the
20 message limit or the 256 KiB total. Nothing else in the response would tell
you, since a refused message simply never appears. `truncated` is what says one
was refused. The long poll watches the flag as well as the count, so a refusal
ends the wait rather than leaving you to sit out the full duration for a message
that is never coming.

**Worked example.** Create the inbox and keep both values.

```
GET /inbox
-> address    aisense+ztjqt7n@aisenseapi.com
   inbox_id   a85d0bee-f8f7-4be1-a1b3-8d58f3dbdfc7
```

Give `address` to the site or person that has to send the mail, and keep
`inbox_id` to yourself. Then hold one connection open until the mail lands.

```
GET /inbox/a85d0bee-f8f7-4be1-a1b3-8d58f3dbdfc7/wait/25
```

The call returns as soon as a message arrives. Take the code from the parsed
field rather than parsing `text` yourself.

```
messages[0].codes[0]   -> "481516"
messages[0].links[0]   -> "https://example.com/confirm/abc"
```

If the call returns with `received` still 0, repeat it until the mail arrives
or `expire_timestamp` passes. A read after that answers HTTP 410, and HTTP 404
once the expired record has been pruned.

Limits, all fixed: 20 messages per inbox, 64 KiB of cleaned text per message,
256 KiB of cleaned text per inbox in total, 50 inboxes per client per UTC day
and 5000 active inboxes service wide.

Attachments, raw MIME, arbitrary headers, scripts, styles, private-IP links and
localhost links are stripped before storage. Only the sender address, subject,
received time, cleaned text, codes and public links are kept.

The `inbox_id` is a bearer secret. Anyone holding it reads every message in the
inbox, so do not use the address for anything that needs a real mailbox, and do
not expect any of it to survive the 24 hours.

---

### Heartbeat - alert when check-ins stop

Heartbeat watches a short-lived process that should keep checking in. Create a
monitor with an expected interval, a grace period and one action to run if the
deadline is missed. The monitor has a fixed 24-hour lifetime.

**Create:** `POST /heartbeat`

```json
{
  "expect_every_seconds": 300,
  "grace_seconds": 60,
  "on_miss": {
    "url": "https://example.com/agent-offline",
    "payload": { "agent": "worker-7" }
  }
}
```

Use an existing, waiting Agent Wake webhook task instead of an outbound URL:

```json
{
  "expect_every_seconds": 300,
  "grace_seconds": 60,
  "on_miss": { "wake_task_id": "2eb1a08d-759f-4af9-8caa-8b02b7ca17ba" }
}
```

The Agent Wake task must exist, use `event_type: "webhook"` and still be in
the `working` state.

```json
{
  "ok": true,
  "heartbeat_id": "58c85e3e8f739edcb73530d14316f2bfae9ae11bf85374b17e4c9ab75bbec5f1",
  "status": "armed",
  "expect_every_seconds": 300,
  "grace_seconds": 60,
  "expires_at_datetime": "2026-09-06T10:00:00Z",
  "next_expected_at_datetime": "2026-09-05T10:05:00Z",
  "miss_due_at_datetime": "2026-09-05T10:06:00Z",
  "ping_count": 0,
  "misses": 0,
  "late": false,
  "on_miss": { "type": "webhook" },
  "ping_url": "https://aisenseapi.com/services/v1/heartbeat/58c85e3e.../ping",
  "status_url": "https://aisenseapi.com/services/v1/heartbeat/58c85e3e..."
}
```

`expect_every_seconds` must be an integer from 60 to 86400.
`grace_seconds` must be zero or more. Their sum cannot exceed 86400.
An optional webhook payload may be at most 32 KB as JSON.

**Check in:** `POST /heartbeat/{heartbeat_id}/ping`

Each accepted check-in updates `last_ping_at_*`, `next_expected_at_*` and
`miss_due_at_*`, and increases `ping_count`. It does not move
`expires_at_*`. A late, missed or expired heartbeat returns HTTP 409 when
pinged.

**Read:** `GET /heartbeat/{heartbeat_id}`

The status is `armed`, `missed`, `fired` or `expired`. The worker checks once
a minute. When a deadline is missed it claims the action before delivery and
never retries it, so the same miss is not sent twice. `fired` means that a
delivery was attempted. Read `delivery.delivered` and `delivery.http_status`
to see whether a webhook accepted it. A failure before an attempt leaves the
status as `missed` with an honest delivery error.

Webhook targets must use HTTP or HTTPS on port 80 or 443 and resolve to a
public address. Credentials and fragments are refused. DNS is checked again
at delivery, the connection is pinned to the checked address, redirects are
disabled and private, loopback, link-local and reserved ranges are blocked.

The 64-character heartbeat ID is a bearer secret. There is no list operation.
The target URL, payload or Agent Wake task ID is removed when the monitor
becomes terminal. Its terminal status remains readable for up to another 24
hours.

---

### Lease - coordinate workers and reuse completed results

Lease gives several workers one anonymous coordination point. The first
worker to acquire a key gets an owner token and a monotonically increasing
fencing token. Other workers receive HTTP 409 while that lease is held.

For short readable keys, mint a private namespace first:

```http
POST /lease/namespace
Content-Type: application/json

{}
```

```json
{
  "ok": true,
  "namespace": "ns_XbO8a6V9e5dMWYqghfPV3ykHTNpR3oZ0fQJm4l7K2nE",
  "entropy_bits": 256
}
```

Treat the namespace as a bearer secret. Without a namespace, `key` itself
must be a high-entropy ASCII value from 32 to 200 characters.

**Acquire:** `POST /lease` or `POST /lease/acquire`

```json
{
  "namespace": "ns_XbO8a6V9e5dMWYqghfPV3ykHTNpR3oZ0fQJm4l7K2nE",
  "key": "invoice:2026-09-05",
  "ttl_seconds": 60,
  "fingerprint": "charge-order-501"
}
```

```json
{
  "ok": true,
  "status": "held",
  "owner_token": "own_lCzWFx9BTqNkKlQJYu8jXdDX7n8h4xTJsU5BzPq3yLk",
  "ttl_seconds": 60,
  "fencing_token": 184,
  "lease_expires_at_timestamp": 1788602460,
  "lease_expires_at": "2026-09-05T10:01:00Z",
  "absolute_expires_at_timestamp": 1788688800,
  "absolute_expires_at": "2026-09-06T10:00:00Z"
}
```

`ttl_seconds` is optional, defaults to 60 and accepts 1 to 86400. A held
lease returns HTTP 409, `status: "held"`, `retry_after_seconds` and a matching
`Retry-After` header. A different fingerprint on the same key returns HTTP
409 with `status: "conflict"`. Use a stable fingerprint when the key must
represent the same input or job.

The owner can change the lease with these POST endpoints:

```json
// POST /lease/renew
{ "namespace": "ns_...", "key": "invoice:2026-09-05", "owner_token": "own_...", "ttl_seconds": 120 }

// POST /lease/release
{ "namespace": "ns_...", "key": "invoice:2026-09-05", "owner_token": "own_..." }

// POST /lease/complete
{ "namespace": "ns_...", "key": "invoice:2026-09-05", "owner_token": "own_...", "result": { "receipt_id": 4817 } }
```

Renew keeps the same fencing token. Release makes the key available at once.
Complete stores up to 32 KB of JSON and changes the status to `completed`.
The next acquire with the same key and fingerprint returns HTTP 200 with that
result and no owner token. Fields with names such as `authorization`,
`password`, `secret`, `token`, `private_key` and `api_key` are replaced with
`[redacted]` before a result is stored. Secrets hidden inside ordinary values
cannot be detected, so keep them out of the result.

An invalid, expired or old owner token receives HTTP 409 with
`status: "lost"`. Send the fencing token to any protected system and reject
writes carrying an older value. This closes the gap where a paused worker
wakes after its lease has been taken over.

Every key lifecycle has a fixed 24-hour absolute expiry. Renewing a lease
cannot extend that boundary. A new acquisition after it starts a new
lifecycle with a higher fencing token. Raw keys, namespaces, owner tokens and
fingerprints are not written to disk. Their hashes and the optional completed
result remain until the absolute expiry.

---

### Validate

Business-number validation by arithmetic. `POST /validate/{type}` where type is
`iban`, `card`, `orgnr`, `kontonummer` or `phone`.

Everything is checked locally - nothing is looked up in any register - so
`valid: true` means **well-formed with a correct check digit**, not that the
account or number exists. An invalid value is a result with `valid: false` and
the failing check named, never an error.

```json
// POST /validate/iban
{ "data": "NO9386011117947" }
-> { "type": "iban", "valid": true, "normalized": "NO9386011117947", "country": "NO",
     "structure_ok": true, "length_ok": true, "checksum_ok": true }

// POST /validate/card  (Luhn; the number is never echoed back)
{ "data": "4111 1111 1111 1111" } -> { "type": "card", "valid": true, "length": 16, ... }

// POST /validate/orgnr  (Norwegian organisasjonsnummer, MOD11)
{ "data": "NO 922 601 151 MVA" } -> { "type": "orgnr", "valid": true, "normalized": "922601151", ... }

// POST /validate/kontonummer  (Norwegian bank account, MOD11)
{ "data": "1234.56.78903" } -> { "type": "kontonummer", "valid": true, ... }

// POST /validate/phone  (E.164 shape only)
{ "data": "004740000000" } -> { "type": "phone", "valid": true, "e164": "+4740000000", ... }
```

IBAN uses the authoritative ISO 13616 mod-97 check; `length_ok` is `null` for
countries outside the built-in length table, where the length cannot be
confirmed but the checksum still can. An unknown `{type}` returns HTTP 400.

---

### Agent Queue - temporary work for multiple workers

Agent Queue lets a producer enqueue JSON jobs and workers claim them for a short
visibility window.
See [AGENT-QUICKSTART.md](AGENT-QUICKSTART.md) for an executable workflow.

**Create:** `POST /queue` with no parameters (an empty JSON object is accepted).
HTTP 201 returns:

```json
{
  "ok": true,
  "queue_id": "0123456789abcdef0123456789abcdef",
  "created_at_timestamp": 1788948000,
  "expire_timestamp": 1789034400,
  "read_token": "<64 lowercase hex characters>",
  "write_token": "<64 lowercase hex characters>",
  "worker_token": "<64 lowercase hex characters>",
  "counts": { "pending": 0, "claimed": 0, "completed": 0, "failed": 0, "total": 0 }
}
```

Values above are placeholders. Save all three tokens from this response: they
are issued only at creation. Queue and job IDs are 32 lowercase hex characters.
Tokens and claim receipts are 64 lowercase hex characters. The queue ID is not
a credential. Each later REST request requires `Authorization: Bearer TOKEN`
with the token for that operation. Never put credentials in paths or query strings.

| Method and path | Bearer token | JSON body |
| --- | --- | --- |
| `GET /queue/{queue_id}` | `read_token` | None |
| `POST /queue/{queue_id}/jobs` | `write_token` | `job_key`, `payload` |
| `GET /queue/{queue_id}/jobs/{job_id}` | `read_token` | None |
| `POST /queue/{queue_id}/claim` | `worker_token` | Optional `visibility_timeout` |
| `POST /queue/{queue_id}/jobs/{job_id}/ack` | `worker_token` | `receipt` |
| `POST /queue/{queue_id}/jobs/{job_id}/release` | `worker_token` | `receipt` |
| `POST /queue/{queue_id}/jobs/{job_id}/renew` | `worker_token` | `receipt`, optional `visibility_timeout` |

**Enqueue:** A producer submits a stable key and a JSON value. The key must
match `^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$`. Payload may be any JSON value,
including `null`, up to 16 KiB (16384 bytes) when encoded.

```bash
curl -X POST https://aisenseapi.com/services/v1/queue/QUEUE_ID/jobs \
  -H "Authorization: Bearer WRITE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"job_key":"report:42","payload":{"report_id":42}}'
```

Replace uppercase placeholders with the creation response values. A new job
returns HTTP 201 and `deduplicated: false`. Sending the same key and payload
again returns the existing job with HTTP 200 and `deduplicated: true`. Changing
the payload for that key returns HTTP 409. Deduplication lasts until the queue
expires, including completed and failed jobs.

**Claim:** `POST /queue/{queue_id}/claim` accepts an integer
`visibility_timeout` from 30 to 900 seconds, default 60. When no job is
available, it returns HTTP 200 with `job: null`. Otherwise it returns:

```json
{
  "ok": true,
  "queue_id": "0123456789abcdef0123456789abcdef",
  "expire_timestamp": 1789034400,
  "job": {
    "job_id": "abcdef0123456789abcdef0123456789",
    "job_key": "report:42",
    "payload": { "report_id": 42 },
    "status": "claimed",
    "attempts": 1,
    "created_at_timestamp": 1788948000,
    "expire_timestamp": 1789034400,
    "claimed_until_timestamp": 1788948060,
    "receipt": "<64 lowercase hex characters>"
  }
}
```

The receipt identifies this claim attempt and appears only in the claim
response. Retain it until the attempt finishes. Job reads, enqueue, ack,
release and renew return the same job envelope without a receipt. A queue
read returns creation and expiry timestamps and the five counts above, without
tokens or a job listing.

**Finish or retry:** Send `{"receipt":"RECEIPT"}` with the worker token to
`ack` after the work succeeds, or to `release` to make it available again.
`renew` accepts the same receipt and an optional `visibility_timeout` and
extends the current visibility window within the queue lifetime. It does not
create another claim attempt. No result or callback URL is accepted by ack.

An expired or superseded receipt returns HTTP 409. Repeating a successful ack
with its receipt is idempotent. Job states are `pending`, `claimed`,
`completed` and `failed`. A claim increments `attempts`. An unacknowledged job
becomes available when its visibility window ends. After five unsuccessful
attempts it becomes `failed` and cannot be claimed again.

Jobs can be delivered again after a claim expires or is released. Queue expiry and the attempt limit may leave jobs unfinished. Initial delivery and exactly-once execution are not guaranteed. A worker can finish an external action and lose its claim before ack,
so another worker may repeat the action. Make side effects idempotent using
the job key or ID.

**Fixed lifetime and limits:** The queue expires exactly 86400 seconds after
creation. Every job, completed record, failed record and deduplication entry
shares that boundary. Enqueue, claim, read, ack, release and renew never move
`expire_timestamp`. There is no expiry or TTL option. No claim can extend
past that timestamp. Expired state becomes unavailable and is cleaned up.

| HTTP status | Queue error |
| --- | --- |
| `400` | Invalid JSON, fields or values. Query parameters are not accepted |
| `401` | Missing or malformed Authorization bearer header |
| `403` | Token is invalid or does not grant the required role |
| `404` | Unknown queue, job or route. Also returned after expired state is cleaned up |
| `405` | Wrong method for the route |
| `409` | Job key conflict, 100-job lifetime capacity reached, or stale claim receipt |
| `410` | Queue expired and its record has not yet been cleaned up |
| `413` | Payload exceeds 16 KiB, enqueue request exceeds 32 KiB, or another request body exceeds 1 KiB |
| `415` | A nonempty POST body did not use `application/json` |
| `429` | Queue creation quota or shared request limit reached |
| `503` | Storage or queue lock unavailable. Stop after an uncertain claim response. Use bounded backoff only for repeat-safe operations |

Queue errors use `{"error":"message"}`. Ordinary reads and successful empty
claims return HTTP 200. Preflight requests use `OPTIONS` and return HTTP 204.

A lost, malformed or 503 claim reply can follow a successful reservation. Do
not blindly claim again when its receipt is unknown. Creation replies can
also be uncertain, and creation-only tokens cannot be recovered. Reads, an
enqueue with the same key and unchanged payload, and an acknowledgement with
the same winning receipt can be repeated within their lifetime. See the
[quickstart retry table](AGENT-QUICKSTART.md#handle-retries-deliberately).

- At most 100 distinct jobs over the entire queue lifetime. Completed and
  failed jobs still count. Idempotent enqueue retries do not add a job.
- At most five claim attempts per job and 16 KiB of encoded JSON per payload.
- At most 20 new queues per client IP per 24 hours, within the shared request limit.

Share the write token with producers, the worker token with workers, and the
read token with observers. Workers necessarily receive job payloads when
claiming. Tokens grant capabilities without verifying a person's identity.
The Queue service writes payload content to its JSON state files without encrypting it. It normalizes object-key ordering and JSON serialization. Keep credentials and sensitive personal data
out of them. Queue processing does not fetch payload URLs, execute jobs,
make callbacks or contact outside services. Your workers perform the work.

The eight MCP equivalents and their argument names are listed in
[`MCP.md`](MCP.md#agent-queue).
The standalone machine-readable Queue contract is
[`queue-openapi.json`](queue-openapi.json). It does not describe other endpoints.

### DNS names - 24h lifetime

A public hostname for an address, for a day. Every argument is in the path.
Creating and reading are GETs; moving and deleting are POSTs with the token.
`GET /dns/{ip}` with the address the name should point at returns `aisense-<slug>.53for24h.com`, an A or AAAA record with a TTL of 60
seconds, and a `dns_token` shown once.

```bash
curl "https://aisenseapi.com/services/v1/dns/<YOUR_PUBLIC_IP>"
```

Replace `<YOUR_PUBLIC_IP>` with the public unicast address the name should point
at. Private, reserved and documentation ranges are refused with 400. An
illustrative answer:

```json
{
  "ok": true,
  "name": "aisense-t1mpdqk.53for24h.com",
  "slug": "t1mpdqk",
  "ip": "<YOUR_PUBLIC_IP>",
  "record": "A",
  "ttl": 60,
  "nameservers": ["ns1.aisenseapi.com", "ns2.aisenseapi.com"],
  "expire_at": "2026-09-24T18:42:17Z",
  "dns_token": "shown once",
  "serial": 9
}
```

| Method and path | Token | Does |
|---|---|---|
| `GET /dns/{ip}` | None | Creates a name pointing at the address. `ip` must be a public unicast address. 201 |
| `GET /dns/{slug}` | None | Reads the name, its address and its expiry. Everything in it is already public in DNS |
| `POST /dns/{slug}/update/{ip}` | Bearer | Moves the name to another address. The expiry does not move |
| `POST /dns/{slug}/delete` | Bearer | Removes the name; the primary at once, the secondary as replication reaches it |

Names are assigned, never chosen, and the address is never taken from the
caller, because the caller is usually not the machine the name should point at.
Private, loopback, link-local and multicast addresses are refused. Expiry is
fixed at 24 hours and nothing extends it. The served TTL never exceeds the time
the name has left, and negative answers are cached for 5 seconds. Every name
also carries SPF `-all` and a null MX, and the zone publishes a DMARC reject
policy, so no name can send or receive mail.

A name is a DNS record and nothing else: no tunnel, no hosting, no certificate
and no HTTPS. The zone is not on the Public Suffix List, so every name shares
one certificate quota and browsers treat them as one site. Do not put a login
behind one, and do not put anything private in a name: the zone is public and
can be watched.

A seven character slug names an existing record; an address, told apart by its
dot or colon, creates a new one. The token goes in an `Authorization: Bearer`
header on update and delete, never in the path. Both are POSTs with no body,
or `{}`. A GET on them answers 405, so a link preview or a crawler cannot
change a name. Creating stays a GET, so an agent that can only fetch a URL can
make one.

```bash
curl -X POST -H "Authorization: Bearer <DNS_TOKEN>" \n  "https://aisenseapi.com/services/v1/dns/<SLUG>/update/<NEW_PUBLIC_IP>"
curl -X POST -H "Authorization: Bearer <DNS_TOKEN>" \n  "https://aisenseapi.com/services/v1/dns/<SLUG>/delete"
```

Limits are 10 names per client address per hour, one change per name per 10
seconds, and 100 active names while the service is a pilot. The four MCP
equivalents are `create_dns_name`, `read_dns_name`, `update_dns_name` and
`delete_dns_name`.

---

### Semantic search - find notes by meaning

Semantic search keeps short notes in a collection for 24 hours and finds them
by meaning, across wording and between languages. A search answers ranked
suggestions with scores. It never decides that a match exists, merges notes or
returns vectors.

**Create:** `GET /semantic_search` creates a collection with the default
model, `bge-m3`. `POST /semantic_search` with `{"model": "qwen3-embedding-4b"}`
chooses the other model, and an empty POST body also gives `bge-m3`. The model
is fixed for the collection, because vectors from two models cannot be
compared. HTTP 201 returns:

```json
{
  "ok": true,
  "collection_id": "7c2e9a41d05f4b8e93a6c1f27d48b0e5",
  "model": "bge-m3",
  "created_at_timestamp": 1791187200,
  "expire_timestamp": 1791273600,
  "notes": 0,
  "notes_added": 0,
  "notes_max": 500,
  "read_token": "<64 lowercase hex characters>",
  "write_token": "<64 lowercase hex characters>"
}
```

Values above are placeholders. Save both tokens: they are issued only at
creation. The read token reads the collection and searches it. The write token
adds and deletes notes. Collection and note IDs are 32 lowercase hex
characters, tokens 64. The collection ID is not a credential. Every later
request sends `Authorization: Bearer TOKEN` with the token for that operation.
Never put tokens in paths or query strings.

| Method and path | Bearer token | JSON body |
| --- | --- | --- |
| `GET /semantic_search/{collection_id}` | `read_token` | None |
| `POST /semantic_search/{collection_id}/notes` | `write_token` | `notes`: 1 to 32 objects with `text` and optional `key` |
| `POST /semantic_search/{collection_id}/search` | `read_token` | `query`, optional `limit` from 1 to 10, default 3 |
| `POST /semantic_search/{collection_id}/notes/{note_id}/delete` | `write_token` | None |

**Add notes:** A note's `text` holds 1 to 2000 characters. An optional `key`
of 1 to 64 letters, digits, dots, underscores, colons or hyphens, starting with
a letter or digit, ties a note to your own records. Text over a limit is
refused with a message, never cut. Split long material into notes, one per
paragraph, field or event, each with a key, so a search names the piece that
matched:

```bash
curl -X POST https://aisenseapi.com/services/v1/semantic_search/COLLECTION_ID/notes \
  -H "Authorization: Bearer WRITE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"notes":[{"text":"Ticket 4410, part 1: the customer was charged twice on 3 October.","key":"ticket:4410:1"},{"text":"Ticket 4410, part 2: the app shows an error when they open their orders.","key":"ticket:4410:2"},{"text":"Ticket 4410, part 3: they ask for a refund of the second charge.","key":"ticket:4410:3"}]}'
```

```bash
curl -X POST https://aisenseapi.com/services/v1/semantic_search/COLLECTION_ID/notes \
  -H "Authorization: Bearer WRITE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"notes":[{"text":"Suspicious login attempts from many addresses on the admin page.","key":"incident:17"},{"text":"Mange mislykkede innlogginger mot adminsiden i natt."},{"text":"The checkout API returns HTTP 500 for every customer since 08:10."}]}'
```

HTTP 201 returns `added`, with the `note_id` and `key` of each new note in
order, and `notes`, `notes_added` and `expire_timestamp`.

**Search:**

```bash
curl -X POST https://aisenseapi.com/services/v1/semantic_search/COLLECTION_ID/search \
  -H "Authorization: Bearer READ_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"brute force attack on the admin login","limit":3}'
```

```json
{
  "ok": true,
  "collection_id": "7c2e9a41d05f4b8e93a6c1f27d48b0e5",
  "model": "bge-m3",
  "results": [
    { "note_id": "a3f1c9e07b2d4568913e0d7c5b2a4f86", "key": "incident:17", "text": "Suspicious login attempts from many addresses on the admin page.", "score": 0.7687 },
    { "note_id": "5e8d2b7f1c094a3e8b6d0f2a7c9e1b34", "key": null, "text": "Mange mislykkede innlogginger mot adminsiden i natt.", "score": 0.7178 },
    { "note_id": "c90b4e2a6f1d4783a5e9b0c3d7f28e61", "key": null, "text": "The checkout API returns HTTP 500 for every customer since 08:10.", "score": 0.5157 }
  ],
  "notes": 3,
  "expire_timestamp": 1791273600
}
```

The search in English found the English note and the Norwegian one. The scores
are what `bge-m3` gave these texts in our tests. A search in an empty
collection answers at once with no results.

**Scores:** The score is cosine similarity plus an identifier rule, kind by
kind: +0.1 for each identifier in the search that the note also holds, and
-0.1 for each kind where the note holds others of that kind and none of the
search's. Each code prefix, such as `DEMO-` in `DEMO-57`, is a kind of its own,
and numbers of three or more digits outside codes are another, with `1 200`
and `1.200` read as `1200`. The score is not a probability. With `bge-m3` in
our tests, correct first results scored 0.66 or more and searches without a
matching note scored at most 0.60, so a top score below about 0.6 is a likely
miss, as for the third result above. That is guidance from a small test set,
not a guarantee, and `qwen3-embedding-4b` showed no such threshold. A high score
is no proof of a match either: in a collection of 500 similar order notes, a
search for an order that was not there still scored 0.67 with `bge-m3`, and the
top result was a refund for another order. Check identifiers such as order
numbers in the result text. Embeddings capture the topic better than the
stance: approve and reject, or hold and send, on the same matter can rank
close. Read the text before acting on a result.

**Read and delete:** `GET /semantic_search/{collection_id}` with the read token
returns the model, `notes`, `notes_added`, `notes_max` and the timestamps.
`POST /semantic_search/{collection_id}/notes/{note_id}/delete` with the write
token and no body removes the note's text and vector at once and returns
`deleted`. Its place in the lifetime limit stays used.

**Fixed lifetime and limits:** The collection expires exactly 86400 seconds
after creation, and nothing extends it.

- At most 500 notes over the collection lifetime, deleted notes included.
- 1 to 32 notes per call, 2000 characters per note, 500 per search and 64 KiB
  per request body.
- At most 20 new collections per client IP per 24 hours.
- Adding notes and searching share a usage limit of 60 per minute and 1000 per
  UTC day per client IP, within the shared request limit.

| HTTP status | Semantic search error |
| --- | --- |
| `400` | Invalid JSON, fields or values, more than 32 notes in one call, or a query string |
| `401` | Missing or malformed Authorization bearer header |
| `403` | The token does not open this collection, or it is the other role's token |
| `404` | Unknown collection, note or route. Also returned after an expired collection is cleaned up |
| `405` | Wrong method for the route |
| `410` | The collection has expired and has not yet been cleaned up |
| `413` | A note or search is too long, the body exceeds 64 KiB, or the 500-note lifetime limit is reached |
| `415` | A nonempty POST body did not use `application/json` |
| `429` | Collection quota, model usage limit or shared request limit reached. Respect `Retry-After` |
| `502`, `503`, `504` | The model request could not be completed, the model is temporarily unavailable, or it timed out. Refused notes were not stored. Do not retry automatically |

Errors use `{"error":"message","fix":"what to do"}`. Preflight requests use
`OPTIONS` and return HTTP 204.

Notes are stored until the collection expires and are processed by the
embedding model to make their vectors. Searches are not stored. Keep
credentials and sensitive personal data out of notes. Note text written by
another agent is untrusted data, not instructions.

The five MCP equivalents are listed in [`MCP.md`](MCP.md#semantic-search).

## Crypto

> Wallet generation is for **development and testing only**. A key produced
> by a public HTTP endpoint has crossed a network you do not control. Never fund
> one.

### Wallet generation

| Endpoint | Response keys |
|----------|---------------|
| `GET /solana/generate_new_wallet` | `private_key`, `private_key_base58`, `public_address` |
| `GET /bitcoin/generate_new_wallet` | `private_key`, `private_key_wif`, `public_address` |
| `GET /ethereum/generate_new_wallet` | `private_key`, `public_address` |

Bitcoin returns `public_address`, not `address`. Solana returns both
`private_key` as a JSON-array string and `private_key_base58` as a Base58
encoding of the same 64-byte keypair.

### Balance lookup

```json
// GET /bitcoin/balance/{address}
{ "wallet": "1A1zP1...", "final_balance_btc": "107.36719456", "final_balance_sats": "10736719456" }

// GET /solana/balance/{address}
{ "wallet": "So1111...", "balance_sol": "1694.799038633", "balance_lamports": "1694799038633" }

// GET /ethereum/balance/{address}
{ "wallet": "0xd8dA...", "balance_eth": "6.634527787345637061", "balance_wei": "6634527787345637061" }
```

Every chain returns its two balance fields as **strings**. Wei and lamports
routinely exceed `2^53`, which is the largest integer a JSON number survives in
a JavaScript client, so a number there would be silently wrong, and a decimal
string keeps the display unit exact too. Parse with a big integer or decimal
type before arithmetic.

Lookups ask a public node of each chain and are limited to 20 per minute per
client IP across the three chains, answered **HTTP 429** with `Retry-After` and
a `fix` before the node is asked. When the node refuses or fails, the answer is
**HTTP 503** with `Retry-After: 10` and a `fix`; no answer in time is **504**,
and an address the node rejects is **400**. Lookups count towards the daily
limit as well.

---

## Agent2Agent (A2A)

A2A is a protocol for handing work to another agent and following it to
completion. MCP is the protocol for exposing tools. Almost everything on this
page is a tool, so only five capabilities are offered over A2A: the ones where a
long-lived, resumable, human-in-the-loop task is the interesting object, and
where MCP needed an extension to express what A2A has in core.

**MCP is the broader workflow surface.** It publishes schemas through tool
discovery. A2A carries five creation skills, Queue among them. REST
carries the full utility catalog. Only selected capabilities, including time
and UUIDs, also have MCP tools. Hashing, encoding, QR and wallet operations
remain REST-only. See `MCP.md` for the source and deployed tool counts.

**Endpoint:** `POST https://aisenseapi.com/a2a`. JSON-RPC 2.0, protocol revision
`1.0` (specification v1.0.1). No account and no API key, same as everything else
here. Bodies are capped at 256 KB. A protocol error is still HTTP 200 with the
error inside the JSON-RPC envelope; only the transport refuses with a status of
its own, 405 for any method other than POST and 413 for an oversized body.
Batches work. A notification, meaning a request with no `id`, is answered with
HTTP 204 and no body.

**Agent card:** `GET https://aisenseapi.com/.well-known/agent-card.json`. A plain
GET rather than a JSON-RPC method, because the protocol has no method for
fetching the public card. It is cacheable for an hour and carries an ETag. The
endpoint address lives in `supportedInterfaces`, not in a top-level `url`, and
`capabilities` declares `streaming: false`, `pushNotifications: false` and
`extendedAgentCard: false`.

### Naming a skill is a convention here, not a standard field

A2A skills are not addressable. There is no skill id anywhere on the wire and no
`inputSchema` on a skill, so nothing in the protocol says which of the advertised
skills a message is asking for. Look for a standard field and you will not find
one. This service reads the skill from a part carrying structured data:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "SendMessage",
  "params": {
    "message": {
      "messageId": "m1",
      "role": "ROLE_USER",
      "parts": [
        {
          "data": {
            "skill": "agent-wake",
            "arguments": { "event_type": "webhook", "timeout_seconds": 3600 }
          },
          "mediaType": "application/json"
        }
      ]
    }
  }
}
```

That shape is documented here and nowhere in the specification. A message with
no such data part is refused with `-32602`: this agent has no language model and
does not interpret free text. An unknown skill id is refused with `-32602` too.
`arguments` are the arguments of the matching MCP tool, checked by the same code,
so bounds and refusals are identical on both surfaces.

### The five skills

| Skill id | Creates | Answers with |
|----------|---------|--------------|
| `agent-wake` | a durable wait for a webhook, a person or a chosen time | a Task |
| `human-approval` | a hosted decision form, for one person or up to 20 | a Message |
| `agent-inbox` | a disposable mail address | a Message |
| `webhook-capture` | a URL that records the first request sent to it | a Message |
| `agent-queue` | a shared pull queue with read, write and worker tokens | a Message |

Each lasts at most 24 hours, the same limit as everywhere else on this service.

`agent-wake` answers with an A2A Task:

```json
{
  "id": "c450a722-cfff-4e81-955b-a4baa566a458",
  "contextId": "c450a722-cfff-4e81-955b-a4baa566a458",
  "status": { "state": "TASK_STATE_WORKING", "timestamp": "2026-09-06T17:11:18Z" }
}
```

The states are `TASK_STATE_WORKING`, `TASK_STATE_INPUT_REQUIRED`,
`TASK_STATE_COMPLETED`, `TASK_STATE_FAILED` and `TASK_STATE_CANCELED`. Note the
single L in `CANCELED`; the REST status for the same task is spelled `cancelled`.
An interrupted task puts the thing a person has to act on, such as a form URL, in
`status.update`.

The other four answer with a Message carrying the created resource:

```json
{
  "messageId": "msg-57925ef67c5f0f8e",
  "role": "ROLE_AGENT",
  "parts": [
    {
      "data": {
        "ok": true,
        "action_id": "f959a9b7-6f92-4f09-8e60-98d452f723b6",
        "status": "pending",
        "form_url": "https://aisenseapi.com/services/v1/webhook_action/f959a9b7-.../form",
        "result_url": "https://aisenseapi.com/services/v1/webhook_action/f959a9b7-...",
        "wait_url": "https://aisenseapi.com/services/v1/webhook_action/f959a9b7-.../wait/25"
      },
      "mediaType": "application/json"
    }
  ]
}
```

Those three create the resource and stop there. Reading a captured request, the
mail in an inbox or a submitted form is not an A2A operation: follow the
`read_url`, `result_url` and `wait_url` in the reply, which are the REST
endpoints documented above, or call the matching MCP tool.

### Methods

Method names are PascalCase, not the slash names from revision 0.x.

| Method | Result |
|--------|--------|
| `SendMessage` | implemented |
| `GetTask` | implemented |
| `CancelTask` | implemented |
| `ListTasks` | implemented, always an empty page |
| `SendStreamingMessage`, `SubscribeToTask` | `-32004` |
| `CreateTaskPushNotificationConfig`, `GetTaskPushNotificationConfig`, `ListTaskPushNotificationConfigs`, `DeleteTaskPushNotificationConfig` | `-32003` |
| `GetExtendedAgentCard` | `-32004` |

The declined methods are not gaps. Once a card declares a capability false,
returning these errors is the conforming behaviour the specification asks for.
**The two families use different codes and are not interchangeable:** streaming
and the extended card answer `-32004`, push notification configuration answers
`-32003`. A client that folds them into one error reports the wrong cause.

`GetTask` and `CancelTask` take the task id in `params.id`, and `params.taskId`
is accepted as well. They address Agent Wake tasks, the only task store this
service has. `CancelTask` returns the task in its new state.

**`ListTasks` always returns an empty page.**

```json
{ "tasks": [], "nextPageToken": "", "pageSize": 50, "totalSize": 0 }
```

The specification requires every operation to scope its results to the
authenticated caller. This service authenticates nobody, so there is no principal
to scope to, and a global list would hand every caller every task id. Those ids
are the only credential there is. An empty page is the conservative reading, not
an unfinished feature. Keep your own task ids.

### Error codes

| Code | Meaning |
|------|---------|
| `-32700` | Parse error. The body was not JSON. |
| `-32600` | Invalid Request. `jsonrpc` was not `"2.0"`, or the envelope was unusable. |
| `-32601` | Method not found. |
| `-32602` | Invalid params. No data part naming a skill, an unknown skill id, a missing task id, or arguments the underlying tool refused. |
| `-32001` | Task not found. |
| `-32003` | Push notification configuration is not supported. |
| `-32004` | Streaming, or the extended card, is not supported. |
| `-32603` | Internal error. |

A wrong task id and a task that never existed both answer `-32001`, with the same
message. Nothing distinguishes them, because the id is the credential and telling
them apart would turn the endpoint into a lookup oracle for task ids.

---

## Common Conventions

### Paths

Every endpoint is `/services/v1/{name}`. Arguments travel as path segments or
in the request body, never in the query string; `url_shortener` reads one only
as part of the URL it shortens. Paths are written in lower case. An argument
that ignores case, such as a zone name, is answered the same way in any case,
and no endpoint redirects. A value whose case carries meaning, such as a
base58 address, base64 data or a URL to shorten, is sent as it is.

### Refusals

An error answers with `error`, the diagnosis, and `fix`, a sentence saying
what to send instead.

```json
{
  "error": "Storage id unknown",
  "fix": "The id is unknown or its 24 hours have passed. Store the value again and use the new storage_id."
}
```

`error` is unchanged from before `fix` existed, so a client that matches on
it keeps working. `fix` is there for a caller that cannot read the reference
at the moment it fails, which is most of them: a script, an agent, or a
program on someone else's schedule.

The sweep is staged. Storage, the five Convert endpoints, the seven Images
endpoints, qrcode_decode, Agent Queue, Heartbeat, Lease, Agent Wake and Agent Inbox carry a
fix on every refusal today. The rest of the catalog
still answers with `error` alone, and is being converted family by family.

### Input formats (POST endpoints)

Formats vary by endpoint. This table summarizes utility inputs, not a promise
that every endpoint accepts every format. Queue and structured workflow
operations use JSON with the fields documented in their own sections.

| Format | Content-Type | Notes |
|--------|-------------|-------|
| JSON | `application/json` | Field name varies - `data` for most, `payload` for QR |
| Plain text | `text/plain` | Pass the secret via `X-Secret` for JWT endpoints |
| File upload | `multipart/form-data` | Field names vary by endpoint |

### Response keys, in full

| Endpoint | Response key(s) |
|----------|-----------------|
| `/datetime` | `datetime` |
| `/datetime/{zone}` | `datetime`, `timezone`, `abbreviation`, `utc_offset`, `dst`, `unixtime`, `raw_offset`, `dst_offset`, `dst_from`, `dst_until`, `day_of_week`, `day_of_year`, `week_number`, `utc_datetime` |
| `/ip_datetime[/{ip}]` | `ip`, then the fourteen keys of `/datetime/{zone}` |
| `/timestamp` | `timestamp` |
| `/microtimestamp` | `microtimestamp` |
| `/timezones` | `timezones` (array of objects) |
| `/swatchinternettime` | `beat`, `date` |
| `/timestamp_convert` | `input`, `detected`, `timestamp`, `datetime`, `rfc2822`, `utc_datetime` |
| `/random_number` | `random_number`, `range` |
| `/random_color` | `random_color` |
| `/uuid` | `uuid` |
| `/guid` | `guid` |
| `/password` | `password`, `password_length` |
| `/base64_encode` | `base64_encoded_data` |
| `/base58_encode` | `base58_encoded_data` |
| `/base32_encode` | `base32_encoded_data` |
| `/hex_encode` | `hex_encoded_data` |
| `/base64url_encode` | `base64url_encoded_data` |
| `/base64_decode`, `/base58_decode`, `/base32_decode`, `/hex_decode`, `/base64url_decode` | raw bytes, or `type` + `decoded_data` with `Accept: application/json` |
| `/url_encode`, `/url_decode` | `url_encoded_data`, `url_decoded_data` |
| `/html_encode`, `/html_decode` | `html_encoded_data`, `html_decoded_data` |
| `/jwt_encode` | `jwt` |
| `/jwt_decode` | `decoded_payload` |
| `/qrcode_encode` | `qrcode_image`, `image_type` |
| `/qrcode_decode` | `qrcode_content` |
| `/json_to_csv`, `/csv_to_json`, `/table_match`, `/json_format` | `storage_id`, `storage_url`, `sha256_hash`, `bytes`, `expire_timestamp`, `expire_datetime`, `content_type`, `filename`, `operation` |
| `/json_validate` | the same fields, plus `valid` |
| `/image_convert`, `/image_compress` | the Storage fields, `content_type`, `filename`, `operation`, `format`, `width`, `height`, `input_format`, `input_bytes` |
| `/image_resize` | the same, and `input_width`, `input_height`, `fit`, `upscaled` |
| `/image_metadata` | the Storage fields, `content_type`, `filename`, `operation`, `format`, `width`, `height`, `gps`, `findings` |
| `/image_strip` | the Storage fields, `content_type`, `filename`, `operation`, `format`, `width`, `height`, `input_bytes`, `removed`, `kept` |
| `/image_colors` | the Storage fields, `content_type`, `filename`, `operation`, `average`, `dominant`, `count` |
| `/image_favicon` | the Storage fields, `content_type`, `filename`, `operation`, `files`, `crop`, `upscaled` |
| `/md5_hash` | `md5_hash` |
| `/sha1_hash` | `sha1_hash` |
| `/sha256_hash` | `sha256_hash` |
| `/sha512_hash` | `sha512_hash` |
| `/crc32_checksum` | `crc32_checksum` (integer) |
| `/whirlpool_hash` | `whirlpool_hash` |
| `/sha3_256_hash` | `sha3_256_hash` |
| `/sha3_512_hash` | `sha3_512_hash` |
| `/blake2b_hash` | `blake2b_hash` |
| `/blake3_hash` | `blake3_hash` |
| `/argon2id_hash` | `argon2id_hash` |
| `/bcrypt_hash` | `bcrypt_hash` |
| `/scrypt_hash` | `scrypt_hash` |
| `/ping` | `ping` |
| `/health` | `status`, `microtimestamp` |
| `/client_ip` | `ip` |
| `/html2pdf` | `storage_id`, `storage_url`, `sha256_hash`, `bytes`, `expire_timestamp` |
| `/user_agent` | `user_agent` |
| `/ip_reverse_lookup` | `ip`, `country`, `city`, `location`, `place`, `timezone` |
| `/domain_ip_lookup` | `domain`, `ip` |
| `/email_validate` | `email`, `valid_syntax`, `domain`, `has_mx`, `mx_hosts`, `has_address_record` |
| `/hash_verify` | `match`, `algorithm`, `computed` |
| `/password_verify` | `match`, `algorithm`, `params` |
| `/slugify` | `slug` |
| `/storage` (store) | `storage_id`, `storage_url`, `sha256_hash`, `bytes`, `expire_timestamp`, `expire_datetime` |
| `/storage/max_downloads/{n}` (store) | the same, plus `downloads_max`, `downloads_left` |
| `/url_shortener` | `short_url`, `expire_timestamp` |
| `/webhook_capture` (create) | `ok`, `capture_id`, `update_url`, `read_url`, `expire_timestamp` |
| `/webhook_action` (create) | `ok`, `action_id`, `form_url`, `result_url`, `expire_timestamp`, `expire_datetime` |
| `/webhook_schedule` (create) | `ok`, `schedule_id`, `status`, `fire_at_timestamp`, `result_url`, `expire_timestamp` |
| `/webhook_schedule/{id}` (poll) | `ok`, `schedule_id`, `status`, `attempts`, `http_status`, `response_excerpt` |
| `/agent_wake` (create) | `taskId`, `status`, `ttlMs`, event URLs in `_meta` |
| `/agent_wake/{id}` (read or cancel) | `status`, `result` or cancellation state |
| `/inbox` (create) | `ok`, `inbox_id`, `slug`, `address`, `read_url`, `wait_url`, `expire_timestamp` |
| `/inbox/{id}` (read or wait) | `ok`, `slug`, `address`, `received`, `truncated`, `messages`, `created_at_timestamp`, `expire_timestamp` |
| `/heartbeat` (create) | `ok`, `heartbeat_id`, `status`, timing fields, `ping_url`, `status_url` |
| `/heartbeat/{id}` (read or ping) | `status`, timing fields, `ping_count`, `misses`, `late`, `delivery` when terminal |
| `/lease/namespace` | `ok`, `namespace`, `entropy_bits` |
| `/lease` or `/lease/acquire` | `status`, `owner_token` for the winner, `fencing_token`, expiry fields, completed `result` when reused |
| `/lease/renew`, `/lease/release`, `/lease/complete` | `status`, `fencing_token`, expiry fields, optional `result` |
| `/queue` (create) | `ok`, `queue_id`, creation and expiry timestamps, `counts`, three role tokens |
| `/queue/{id}` (read) | `ok`, `queue_id`, creation and expiry timestamps, `counts` |
| Queue enqueue, job read, claim, ack, release and renew | `ok`, `queue_id`, `expire_timestamp`, `job`. Enqueue adds `deduplicated`. Claim alone returns a receipt |
| `/validate/{type}` | `type`, `valid`, plus per-check fields (`checksum_ok`, `luhn_ok`, ...) |

### Active lifetimes and retained results

Storage, short links, captures, approvals, Agent Wake, Inbox, Heartbeat, Lease
and Queue have active lifetimes of at most 24 hours. Agent Wake can use a
shorter timeout. Lease expiry is fixed at first acquisition. Queue expiry is
fixed at creation and covers all jobs and deduplication state. Activity cannot
extend either deadline.

Webhook Schedule can schedule work within a 24-hour horizon and retain its
final result for up to another 24 hours. Heartbeat terminal timing and
delivery records can also remain readable for another 24 hours. API expiry
and later scheduled physical cleanup are distinct.

### Rate limit

The shared counter resets at 22:00 UTC from late March to late October and at 23:00 UTC the rest of the year
(midnight in Norway, time zone Europe/Oslo), through the deployed reset job. This is a
calendar-day budget, not a rolling per-request 24-hour window. A `429`
carries `Retry-After` with the seconds until the reset, and its `fix` says the
same. The Storage budget of 80 MB per IP address resets at the same time.
Queue creation has a separate fixed 24-hour quota window.


**5000 requests per IP per day.** Exceeding it returns HTTP 429 in the
same flat error shape as everything else:

```json
{ "error": "Too many requests. The limit is 5000 per IP per day." }
```

### CORS

`Access-Control-Allow-Origin: *` is sent on every `/services/v1/` response, so
these endpoints are callable directly from a browser.
