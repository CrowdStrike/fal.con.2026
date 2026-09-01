# Bug: Pipe Count False Positive (202 instead of 98)

**Date**: 2026-03-03
**Severity**: False positive ERROR blocking deployment validation
**Component**: `InlineQueryPipesRule` (`inline_query_pipes.py`)

## Symptom

The MDDA v4.12.0-TEST CRA inline query was flagged as having 202 pipes (ERROR: exceeds 100-pipe limit), when the actual LogScale API count is 98.

## Root Cause

Two bugs in `_count_pipes()`:

1. **Regex `.*?` can't handle nested braces**: The old code used `re.sub(r'\|\s*case\s*\{.*?\}', ...)` with `re.DOTALL` to extract case blocks. The lazy `.*?` matched the FIRST `}` it found, not the matching one. This fragmented case blocks into many small pieces, leaving `|` characters inside case blocks to be counted as top-level pipes.

2. **Incorrect case branch penalty**: The old formula added +1 per extra case branch (beyond the first per block). Testing against the LogScale API proved that `|` characters inside `case { }` blocks are NOT counted as pipes at all — they're part of the case construct, similar to `|` inside strings.

## Verified LogScale Pipe Counting Rules

Tested against the LogScale API (XDRholdings environment, 2026-03-03):

| Test | Result |
|------|--------|
| 99 `\|` chars (no strings/regex) | PASS (API count=100) |
| 100 `\|` chars (no strings/regex) | FAIL (API count=101) |
| 98 real `\|` + 10 `\|` inside format string | PASS (API count=99) |
| 98 real `\|` + 5 `\|` inside regex `/a\|b/` | PASS (API count=99) |
| 97 real `\|` + 5-branch case block | PASS (API count=98) |

**Correct formula**: `API count = top_level_pipe_chars + 1`. Where top-level means outside strings `"..."`, regex `/.../`, and brace blocks `{...}`. Limit: `API count <= 100`.

## Fix

Replaced regex-based extraction with a character-level parser (`_count_top_level_pipes()`) that tracks:
- String literal context (`"..."`)
- Regex literal context (`/.../`)
- Brace depth (anything inside `{...}` at depth > 0 is skipped)

Removed incorrect case branch penalty entirely.

## Fixture

`bug-pipe-count-false-positive-202.yaml` contains the full CRA inline query action from the MDDA v4.12.0-TEST workflow that triggered this bug.

Expected: API count = 98 (97 top-level pipes + 1 implicit). Should produce a WARNING (approaching limit), NOT an ERROR.
