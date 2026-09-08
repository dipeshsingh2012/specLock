"""
Unit tests for Conventional Commits validator script (scripts/check_commit_msg.py).
Validates Conventional Commits v1.0.0 specification rules and CLI hook entrypoint.
"""

import sys
from pathlib import Path

# Add project root to sys.path so scripts can be imported cleanly
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.check_commit_msg import (
    ALLOWED_TYPES,
    ALLOWED_SCOPES,
    MAX_HEADER_LENGTH,
    validate_commit_message,
    format_error_report,
    main,
)


def test_allowed_types_and_scopes_presence():
    """Verify expected Conventional Commit types and SpecLock scopes are defined."""
    expected_types = {"feat", "fix", "docs", "style", "refactor", "perf", "test", "build", "ci", "chore", "revert"}
    assert expected_types.issubset(ALLOWED_TYPES)

    expected_scopes = {"api", "graph", "ranker", "catalog", "config", "deps", "tests", "docs", "readme", "ci", "build"}
    assert expected_scopes.issubset(ALLOWED_SCOPES)
    assert MAX_HEADER_LENGTH == 100


def test_valid_commit_messages_with_and_without_scope():
    """Verify valid conventional commit headers across all types and scopes pass validation."""
    valid_samples = [
        "feat(api): add stage 2 neural ranking endpoint",
        "fix(graph): resolve voltage constraint filtering bug",
        "docs(readme): update quickstart and openapi documentation",
        "docs: update license and architecture notes",
        "style(catalog): format json spec values consistently",
        "refactor(ranker): extract cosine similarity scoring helper",
        "perf(graph): optimize candidate pruning bitmask traversal",
        "test(tests): add test coverage for conventional commits",
        "build(deps): bump sentence-transformers dependency",
        "ci(ci): configure commitlint verification workflow",
        "ci: configure automated test suite action",
        "chore: clean temporary cache directories",
        "revert(api): revert commit abc1234",
    ]

    for sample in valid_samples:
        is_valid, errors = validate_commit_message(sample)
        assert is_valid is True, f"Expected '{sample}' to be valid, got errors: {errors}"
        assert len(errors) == 0


def test_valid_breaking_change_notations():
    """Verify breaking change marker '!' and BREAKING CHANGE footers are recognized as valid."""
    breaking_samples = [
        "feat(api)!: migrate endpoint parameters to query models",
        "fix(graph)!: change primary spec key representation",
        "feat!: redesign recommendation pipeline structure",
        (
            "feat(api): migrate recommendation endpoint\n\n"
            "Migrates legacy path parameter to query parameter.\n\n"
            "BREAKING CHANGE: machine_id is now required as query parameter."
        ),
    ]

    for sample in breaking_samples:
        is_valid, errors = validate_commit_message(sample)
        assert is_valid is True, f"Expected breaking change sample to be valid, got errors: {errors}"
        assert len(errors) == 0


def test_valid_multiline_commit_with_body_and_footer():
    """Verify commits with multi-line body and issue references pass validation."""
    message = (
        "feat(ranker): implement dense embedding cache\n\n"
        "Pre-computes and caches 384-dimensional dense embeddings for\n"
        "all catalog machines and accessories during lifespan startup.\n\n"
        "Closes #42\n"
    )
    is_valid, errors = validate_commit_message(message)
    assert is_valid is True
    assert len(errors) == 0


def test_invalid_commit_type():
    """Verify commit headers with unsupported types fail validation."""
    invalid_types = [
        "update(api): update endpoints",
        "add(catalog): add new accessory",
        "change: change some code",
        "bugfix(graph): fix traversal bug",
        "feature(ranker): add ranker",
    ]

    for sample in invalid_types:
        is_valid, errors = validate_commit_message(sample)
        assert is_valid is False
        assert any("Invalid commit type" in err for err in errors)


def test_invalid_commit_scope():
    """Verify commit headers with unregistered scopes fail validation."""
    sample = "feat(unknown_scope): add cool new feature"
    is_valid, errors = validate_commit_message(sample)
    assert is_valid is False
    assert any("Invalid scope 'unknown_scope'" in err for err in errors)


def test_subject_validation_rules():
    """Verify subject uppercase, trailing period, and empty subject rules."""
    # Uppercase start
    is_valid_upper, errors_upper = validate_commit_message("feat(api): Add new neural endpoint")
    assert is_valid_upper is False
    assert any("must start with a lowercase letter" in err for err in errors_upper)

    # Trailing period
    is_valid_period, errors_period = validate_commit_message("fix(graph): resolve voltage check.")
    assert is_valid_period is False
    assert any("must not end with a period" in err for err in errors_period)

    # Malformed / empty subject
    is_valid_empty, errors_empty = validate_commit_message("feat(api): ")
    assert is_valid_empty is False
    assert any("does not match Conventional Commits format" in err or "empty" in err for err in errors_empty)


def test_empty_and_comment_only_messages():
    """Verify empty messages or messages containing only comments are rejected."""
    empty_samples = [
        "",
        "   \n  \t ",
        "# Just a git commit comment\n# Another comment",
    ]

    for sample in empty_samples:
        is_valid, errors = validate_commit_message(sample)
        assert is_valid is False
        assert any("cannot be empty" in err for err in errors)


def test_header_exceeds_max_length():
    """Verify headers exceeding MAX_HEADER_LENGTH trigger descriptive error."""
    long_subject = "a" * 90
    long_header = f"feat(api): {long_subject}"
    assert len(long_header) > MAX_HEADER_LENGTH

    is_valid, errors = validate_commit_message(long_header)
    assert is_valid is False
    assert any(f"exceeds maximum length of {MAX_HEADER_LENGTH}" in err for err in errors)


def test_missing_blank_line_between_header_and_body():
    """Verify omission of blank line between header and body triggers error."""
    bad_multiline = (
        "feat(api): add new query parameter\n"
        "Missing the required blank line before this body description.\n"
    )
    is_valid, errors = validate_commit_message(bad_multiline)
    assert is_valid is False
    assert any("blank line must separate" in err for err in errors)


def test_format_error_report():
    """Verify format_error_report produces colorized, descriptive output."""
    errors = ["Invalid commit type 'badtype'.", "Commit description/subject must not end with a period ('.')."]
    report = format_error_report(errors, "badtype: some message.")

    assert "Invalid commit message!" in report
    assert "badtype" in report
    assert "Allowed Types:" in report
    assert "Allowed Scopes:" in report
    assert "Examples:" in report


def test_cli_main_execution(tmp_path: Path):
    """Verify main() CLI handles missing args, missing files, valid files, and invalid files."""
    # 1. No arguments provided
    assert main([]) == 1

    # 2. Non-existent file path
    non_existent = tmp_path / "non_existent.txt"
    assert main([str(non_existent)]) == 1

    # 3. Valid commit message file
    valid_file = tmp_path / "valid_commit.txt"
    valid_file.write_text("feat(graph): add inverted candidate pruning index\n", encoding="utf-8")
    assert main([str(valid_file)]) == 0

    # 4. Invalid commit message file
    invalid_file = tmp_path / "invalid_commit.txt"
    invalid_file.write_text("Random non-conventional commit message\n", encoding="utf-8")
    assert main([str(invalid_file)]) == 1
