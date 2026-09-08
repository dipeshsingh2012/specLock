#!/usr/bin/env python3
"""
Conventional Commits v1.0.0 Validator for SpecLock.
Enforces commit message formatting across local git hooks and CI pipelines:
  <type>(<optional scope>)[!]: <description>

  [optional body]

  [optional footer(s)]
"""

import re
import sys
from pathlib import Path
from typing import List, Optional, Set, Tuple

# Conventional Commits v1.0.0 standard types
ALLOWED_TYPES: Set[str] = {
    "feat",
    "fix",
    "docs",
    "style",
    "refactor",
    "perf",
    "test",
    "build",
    "ci",
    "chore",
    "revert",
}

# Domain-specific scopes tailored to SpecLock architecture
ALLOWED_SCOPES: Set[str] = {
    "api",
    "graph",
    "ranker",
    "catalog",
    "config",
    "deps",
    "tests",
    "docs",
    "readme",
    "ci",
    "build",
}

HEADER_PATTERN = re.compile(
    r"^(?P<type>[a-zA-Z0-9_-]+)(?:\((?P<scope>[a-zA-Z0-9_/-]+)\))?(?P<breaking>!)?: (?P<subject>.+)$"
)

MAX_HEADER_LENGTH = 100


def validate_commit_message(
    message: str,
    allowed_types: Optional[Set[str]] = None,
    allowed_scopes: Optional[Set[str]] = None,
) -> Tuple[bool, List[str]]:
    """
    Validates a commit message against Conventional Commits v1.0.0 rules.
    Returns (is_valid, list_of_error_reasons).
    """
    types = allowed_types if allowed_types is not None else ALLOWED_TYPES
    scopes = allowed_scopes if allowed_scopes is not None else ALLOWED_SCOPES
    errors: List[str] = []

    # Strip trailing whitespace and ignore comment lines starting with #
    lines = [line for line in message.strip().splitlines() if not line.strip().startswith("#")]

    if not lines or not any(line.strip() for line in lines):
        return False, ["Commit message cannot be empty."]

    header = lines[0].strip()

    if len(header) > MAX_HEADER_LENGTH:
        errors.append(
            f"Commit header exceeds maximum length of {MAX_HEADER_LENGTH} characters (current: {len(header)})."
        )

    match = HEADER_PATTERN.match(header)
    if not match:
        errors.append(
            "Commit header does not match Conventional Commits format: '<type>(<scope>): <description>' or '<type>: <description>'."
        )
        return False, errors

    commit_type = match.group("type").strip()
    commit_scope = match.group("scope")
    subject = match.group("subject").strip()

    # 1. Type validation
    if commit_type not in types:
        errors.append(
            f"Invalid commit type '{commit_type}'. Allowed types are: {', '.join(sorted(types))}."
        )

    # 2. Scope validation (optional)
    if commit_scope is not None:
        commit_scope = commit_scope.strip()
        if commit_scope not in scopes:
            errors.append(
                f"Invalid scope '{commit_scope}'. Allowed scopes are: {', '.join(sorted(scopes))}."
            )

    # 3. Subject validation
    if not subject:
        errors.append("Commit description/subject cannot be empty.")
    else:
        if subject.endswith("."):
            errors.append("Commit description/subject must not end with a period ('.').")
        first_char = subject[0]
        if first_char.isalpha() and first_char.isupper():
            errors.append(
                f"Commit description/subject must start with a lowercase letter (got '{first_char}')."
            )

    # 4. Optional blank line between header and body
    if len(lines) > 1 and lines[1].strip() != "":
        errors.append("A blank line must separate the commit header from the body/footer.")

    return len(errors) == 0, errors


def format_error_report(errors: List[str], raw_message: str) -> str:
    """Formats an informative error report with guidance on valid convention."""
    header_preview = raw_message.splitlines()[0] if raw_message.strip() else "<empty>"
    error_list = "\n".join(f"  ✖ {err}" for err in errors)
    valid_types = ", ".join(sorted(ALLOWED_TYPES))
    valid_scopes = ", ".join(sorted(ALLOWED_SCOPES))

    return f"""\
\033[1;31m[Conventional Commits] Invalid commit message!\033[0m

\033[1mHeader:\033[0m
  {header_preview}

\033[1;31mErrors:\033[0m
{error_list}

\033[1;34mConventional Commit Format:\033[0m
  <type>(<scope>): <description>

  [optional body]

  [optional footer: BREAKING CHANGE: <explanation>]

\033[1;32mAllowed Types:\033[0m
  {valid_types}

\033[1;32mAllowed Scopes:\033[0m
  {valid_scopes}

\033[1;33mExamples:\033[0m
  feat(api): add neural ranking parameter to compatibility endpoint
  fix(graph): resolve voltage constraint mismatch for 240V models
  docs(readme): add Swagger UI testing guide
  feat(ranker)!: change default scoring weights
"""


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint for commit-msg hook or manual validation."""
    args = argv if argv is not None else sys.argv[1:]

    if not args:
        print("Usage: check_commit_msg.py <path_to_commit_msg_file>", file=sys.stderr)
        return 1

    commit_msg_path = Path(args[0])
    if not commit_msg_path.is_file():
        print(f"Error: Commit message file '{commit_msg_path}' not found.", file=sys.stderr)
        return 1

    content = commit_msg_path.read_text(encoding="utf-8")
    is_valid, errors = validate_commit_message(content)

    if not is_valid:
        print(format_error_report(errors, content), file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
