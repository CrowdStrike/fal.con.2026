"""Tests for InlineQueryPipesRule - validates inline LogScale query pipe/subquery limits.

Verified pipe counting behavior against LogScale API (2026-03-03):
- LogScale counts top-level '|' pipe operators only
- '|' inside strings, regex, and brace blocks (case {}) are NOT counted
- API adds +1 implicit pipe; limit is count <= 100
- Therefore max 99 top-level '|' characters allowed
"""

from workflow_validator.rules.inline_query_pipes import InlineQueryPipesRule, _count_top_level_pipes
from workflow_validator.models.context import ValidationContext
from workflow_validator.models.errors import ErrorSeverity


class TestInlineQueryPipesRule:
    def setup_method(self):
        self.rule = InlineQueryPipesRule()
        self.context = ValidationContext(file_path="test.yaml")

    def test_name(self):
        assert self.rule.name == "Inline Query Pipe Count"

    def test_no_actions(self):
        assert self.rule.validate({}, self.context) == []

    def test_query_under_soft_limit(self):
        query = "\n".join(["| step"] * 10)
        workflow = {
            "actions": {
                "Step1": {
                    "id": "123",
                    "inline_configuration": {"config": {"search_query": query}},
                }
            }
        }
        errors = self.rule.validate(workflow, self.context)
        assert len(errors) == 0

    def test_query_at_soft_limit_warns(self):
        """95 | chars + 1 implicit = API count 96 => warning."""
        query = "\n".join(["| step"] * 95)
        workflow = {
            "actions": {
                "Step1": {
                    "id": "123",
                    "inline_configuration": {"config": {"search_query": query}},
                }
            }
        }
        errors = self.rule.validate(workflow, self.context)
        assert len(errors) == 1
        assert errors[0].severity == ErrorSeverity.WARNING
        assert errors[0].code == "INLINE_QUERY_PIPE_WARNING"
        assert "96" in errors[0].message  # 95 pipes + 1 implicit = 96

    def test_query_at_hard_limit_errors(self):
        """100 | chars + 1 implicit = API count 101 => error (exceeds 100)."""
        query = "\n".join(["| step"] * 100)
        workflow = {
            "actions": {
                "Step1": {
                    "id": "123",
                    "inline_configuration": {"config": {"search_query": query}},
                }
            }
        }
        errors = self.rule.validate(workflow, self.context)
        assert len(errors) == 1
        assert errors[0].severity == ErrorSeverity.ERROR
        assert errors[0].code == "INLINE_QUERY_PIPE_EXCEEDED"

    def test_only_counts_lines_starting_with_pipe(self):
        """All top-level pipe characters should be counted."""
        query = "base query\n| step1\nnot a pipe\n| step2\n  | indented pipe"
        workflow = {
            "actions": {
                "Step1": {
                    "id": "123",
                    "inline_configuration": {"config": {"search_query": query}},
                }
            }
        }
        errors = self.rule.validate(workflow, self.context)
        # 3 pipes + 1 implicit = 4 total - well under limit
        assert len(errors) == 0

    def test_counts_inline_chained_pipes(self):
        """Chained pipes on same line should all be counted."""
        # Line with 50 chained pipes: | p1 | p2 | p3 | ... | p50
        query = "| " + " | ".join([f"p{i}:={i}" for i in range(1, 51)])
        workflow = {
            "actions": {
                "Step1": {
                    "id": "123",
                    "inline_configuration": {"config": {"search_query": query}},
                }
            }
        }
        errors = self.rule.validate(workflow, self.context)
        # 50 pipes + 1 implicit = 51 - under soft limit
        assert len(errors) == 0

    def test_case_block_pipes_not_counted(self):
        """| inside case { } blocks should NOT be counted as top-level pipes."""
        query = """| p1:=1
| case {
    p1 = 1 | result := "a";
    p1 = 2 | result := "b";
    p1 = 3 | result := "c";
    p1 = 4 | result := "d";
    * | result := "e";
  }"""
        # Only 2 top-level pipes: '| p1' and '| case'
        # The 5 branch |'s are inside { } and don't count
        assert _count_top_level_pipes(query) == 2

    def test_format_string_pipes_not_counted(self):
        """| inside format("...") strings should NOT be counted.

        Regression test for the MDDA CRA query false positive where
        risk_breakdown := format(format="GuestAcct: %s | File: %s | ...")
        caused 13 extra false-positive pipe counts.
        """
        query = '| risk_breakdown := format(format="GuestAcct: %s | File: %s | Volume: %s | MultiIP: %s | Burst: %s | IOC: %s | Behavior: %s", field=[a,b,c,d,e,f,g])'
        # Only 1 top-level pipe, the leading |
        assert _count_top_level_pipes(query) == 1

    def test_regex_pipes_not_counted(self):
        """| inside regex literals /.../ should NOT be counted.

        Verified against LogScale API: | in /pattern|alt/ are not pipes.
        """
        query = '| p1 = /aaa|bbb|ccc|ddd|eee/\n| head(1)'
        # 2 top-level pipes, the 4 regex |'s don't count
        assert _count_top_level_pipes(query) == 2

    def test_nested_case_blocks(self):
        """Nested braces (case inside case) should be handled."""
        query = """| p1:=1
| case {
    p1 = 1 | case { p1 = 1 | r := "a"; * | r := "b"; };
    * | r := "c";
  }
| head(1)"""
        # 3 top-level pipes: | p1, | case, | head
        # Everything inside the outer { } doesn't count
        assert _count_top_level_pipes(query) == 3

    def test_case_block_with_multiple_branches_near_limit(self):
        """Query with 99 real pipes including case block stays under limit."""
        # 98 chained pipes + | case { ... } = 99 top-level | chars
        pipes = " | ".join([f"p{i}:={i}" for i in range(1, 98)])
        query = f"""| {pipes}
| case {{
    p97 = 97 | result := "a";
    * | result := "b";
  }}"""
        # 98 top-level pipes + 1 implicit = 99. The case branch |'s don't count.
        pipe_count = _count_top_level_pipes(query) + 1
        assert pipe_count == 99  # At limit but not over

    def test_multiple_case_blocks_with_branches(self):
        """Multiple case blocks: only the '| case' lines count."""
        query = """| p1:=1
| case {
    p1 = 1 | r1 := "a";
    p1 = 2 | r1 := "b";
    * | r1 := "c";
  }
| case {
    r1 = "a" | r2 := "x";
    * | r2 := "y";
  }"""
        # 3 top-level pipes: | p1, | case, | case
        assert _count_top_level_pipes(query) == 3

    def test_real_world_cra_query_under_limit(self):
        """The MDDA CRA query (97 top-level pipes) should NOT trigger an error.

        This is the regression test for the bug where the old regex-based
        counter reported 202 pipes instead of 97, causing a false positive
        ERROR on the production workflow's CRA query.
        """
        # Build a representative query with the problematic patterns:
        # - format strings with | separators
        # - regex literals with | alternation
        # - case blocks with multiple branches
        lines = []
        # 90 simple pipes
        for i in range(1, 91):
            lines.append(f"| p{i}:={i}")
        # 1 format string with many | inside (should not count)
        lines.append('| breakdown := format(format="A: %s | B: %s | C: %s | D: %s | E: %s", field=[p1,p2,p3,p4,p5])')
        # 1 case block with regex | inside (none should count as top-level)
        lines.append("| case {\n    p1 = /foo|bar|baz/ | r := \"match\";\n    * | r := \"no\";\n  }")
        # 1 more pipe + head
        lines.append("| p91:=91")
        lines.append("| head(1)")
        query = "\n".join(lines)

        top_level = _count_top_level_pipes(query)
        api_count = top_level + 1
        # 90 simple + 1 format + 1 case + 1 p91 + 1 head = 94 top-level pipes
        # API count = 95, under 100 limit
        assert top_level == 94
        assert api_count == 95

        # API count 95 == soft limit, so a WARNING is expected (not ERROR)
        workflow = {
            "actions": {
                "CRA": {
                    "id": "123",
                    "inline_configuration": {"config": {"search_query": query}},
                }
            }
        }
        errors = self.rule.validate(workflow, ValidationContext(file_path="test.yaml"))
        assert len(errors) == 1
        assert errors[0].severity == ErrorSeverity.WARNING  # Warning, NOT error
        assert errors[0].code == "INLINE_QUERY_PIPE_WARNING"
