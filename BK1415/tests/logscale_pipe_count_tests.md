# LogScale Case Block Pipe Count Testing

## Hypothesis
LogScale counts each branch within a `case {}` block as an additional pipe/subquery beyond the case statement itself.

## Test Plan

### Test 1: Baseline (No Case Blocks)
- Create query with exactly 98 top-level pipes
- Expected: Should execute successfully (under 100 limit)
- Validates: Basic pipe counting works

### Test 2: One Case Block with 2 Branches
- Start with 98 top-level pipes
- Add 1 case block with 2 branches
- Top-level count: 99 (98 + 1 for the case line)
- Expected API count: 99 + 1 (additional branch) = 100
- Should: Execute successfully (at limit)

### Test 3: One Case Block with 3 Branches
- Start with 98 top-level pipes
- Add 1 case block with 3 branches
- Top-level count: 99
- Expected API count: 99 + 2 (additional branches) = 101
- Should: FAIL with "Too many pipes/subqueries" error

### Test 4: Multiple Case Blocks
- Start with 95 top-level pipes
- Add 2 case blocks, each with 3 branches (= 2 pipes, + 4 extra branches)
- Top-level count: 97
- Expected API count: 97 + 4 = 101
- Should: FAIL with "Too many pipes/subqueries" error

## Test Queries

### Test 1: 98 pipes baseline
```
#repo=new-balance
| test := 1
| test := 2
... (repeat to 98 total)
```

### Test 2: 98 pipes + case with 2 branches
```
#repo=new-balance
| test := 1
... (repeat to 97)
| case {
    test = 1 | result := "a";
    * | result := "b";
  }
```

### Test 3: 98 pipes + case with 3 branches
```
#repo=new-balance
| test := 1
... (repeat to 97)
| case {
    test = 1 | result := "a";
    test = 2 | result := "b";
    * | result := "c";
  }
```

## Results
(To be filled in after testing)
