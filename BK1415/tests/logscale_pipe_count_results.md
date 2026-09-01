# LogScale Case Block Pipe Count - Test Results

## PROVEN FORMULA (Corrected 2026-03-03)

**LogScale counts pipes as follows:**
1. Each top-level `|` pipe operator = 1 pipe (NOT inside strings, regex, or braces)
2. `|` inside `"..."` string literals: NOT counted
3. `|` inside `/.../` regex literals: NOT counted
4. `|` inside `{ }` brace blocks (including case blocks): NOT counted
5. LogScale adds +1 implicit pipe for the query itself
6. Limit: `API count <= 100` (i.e., max 99 top-level `|` characters)

**Previous formula was WRONG**: The old formula of `count('|') + extra_case_branches` double-counted
`|` inside format strings and case blocks. The case branch penalty was also incorrect — branches
inside `case { }` are entirely internal and don't add to the pipe count.

## Test Results (Verified against LogScale API, XDRholdings environment)

### Test 1: Boundary - 99 vs 100 vs 101 top-level pipes (no strings/regex/cases)
| Top-level `\|` chars | API count | Result |
|---|---|---|
| 99 | 100 | ✅ PASS |
| 100 | 101 | ❌ FAIL: `Too many pipes/subqueries in query. count=101. max=100` |
| 101 | 102 | ❌ FAIL: `count=102` |

### Test 2: `|` inside format strings are NOT counted
- 98 real pipes + 10 `|` inside `format(format="%s | %s | ... | %s", field=[...])` = 108 total `|` chars
- **Result:** ✅ PASS (API count = 99, only real pipes counted)

### Test 3: `|` inside regex literals are NOT counted
- 98 real pipes + 4 `|` inside `p1 = /aaa|bbb|ccc|ddd|eee/` = 102 total `|` chars
- **Result:** ✅ PASS (API count = 99, only real pipes counted)

### Test 4: `|` inside case blocks are NOT counted
- 97 real pipes (including `| case`) + 5-branch case block (4 extra `|` inside `{}`) = 102 total `|` chars
- **Result:** ✅ PASS (API count = 98, branch `|`s not counted)
- Scaling test: 97, 98, 99 real pipes with case all PASS; 100 real pipes FAIL at count=101

## Validator Fix

Updated `InlineQueryPipesRule._count_pipes()` to use `_count_top_level_pipes()` — a character-level
parser that skips `|` inside strings, regex, and brace blocks. Removed incorrect case branch penalty.

MDDA CRA query: was falsely reported as 202 pipes (ERROR), now correctly reports 98 (WARNING: approaching limit).
