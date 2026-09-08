# Contributing to SpecLock

Thank you for contributing to SpecLock! To maintain a clean, semantic commit history, automate changelog generation, and enable automated semver releases, this project strictly adheres to the [Conventional Commits v1.0.0](https://www.conventionalcommits.org/en/v1.0.0/) specification.

---

## 1. Commit Message Structure

Every commit message must follow this structure:

```
<type>(<optional scope>): <description>

[optional body]

[optional footer(s)]
```

### Quick Rules
1. **Header format**: `<type>(<scope>): <description>` or `<type>: <description>`.
2. **Subject case**: The description must start with a **lowercase** letter.
3. **No trailing punctuation**: Do not end the description with a period (`.`).
4. **Imperative mood**: Write in the present tense (e.g., "add stage 2 ranking", not "added" or "adds").
5. **Header length**: Keep the header $\le 72$ characters recommended (maximum 100 characters enforced).
6. **Separation**: If adding a body or footer, a **blank line** must separate the header from the body.

---

## 2. Commit Types

| Type | Purpose | Example |
| :--- | :--- | :--- |
| `feat` | Introduces a new feature or user-facing functionality | `feat(api): add neural ranking query parameter` |
| `fix` | Patches a bug or resolves an unexpected defect | `fix(graph): resolve voltage constraint filtering bug` |
| `docs` | Documentation changes only (README, docstrings, OpenAPI) | `docs(readme): add Swagger UI interactive testing guide` |
| `style` | Formatting, whitespace, or code style adjustments (no logic change) | `style(catalog): format json spec attributes consistently` |
| `refactor` | Code restructuring without adding features or fixing bugs | `refactor(ranker): extract cosine similarity calculation` |
| `perf` | Code changes improving execution speed, latency, or memory | `perf(graph): optimize candidate pruning traversal index` |
| `test` | Adding, refactoring, or updating tests | `test(tests): add test coverage for conventional commits` |
| `build` | Changes to build system, packaging, or external dependencies | `build(deps): bump sentence-transformers dependency` |
| `ci` | Changes to CI/CD workflows and automated pipeline scripts | `ci(ci): configure commitlint verification workflow` |
| `chore` | Routine maintenance, repository hygiene, or git hooks | `chore: update gitignore and cache paths` |
| `revert` | Reverts a previous commit | `revert(api): revert commit a1b2c3d` |

---

## 3. Allowed Scopes

Scopes provide domain context specific to the SpecLock architecture:

| Scope | Description |
| :--- | :--- |
| `api` | FastAPI application, endpoints, schemas, CORS, and OpenAPI docs |
| `graph` | NetworkX bipartite graph builder, filtering engine, and graph schemas |
| `ranker` | Dense embedding cache, sentence-transformers model, and composite scoring |
| `catalog` | Raw Breville hardware catalog data, specifications, and SKU definitions |
| `config` | Application settings, SLA thresholds, environment variables, and weights |
| `deps` | Third-party dependency updates (`pyproject.toml`) |
| `tests` | Pytest test suite, mock fixtures, conftest helpers |
| `docs` | General documentation, architecture diagrams, walkthroughs |
| `readme` | Project README.md updates |
| `ci` | GitHub Actions workflows and automation |
| `build` | Build scripts, packaging, and project metadata |

*(Note: Scopes are optional for general commits, e.g., `docs: update license notes`)*.

---

## 4. Breaking Changes

Breaking API or schema changes are indicated in one of two ways:

1. **Exclamation mark (`!`) before the colon**:
   ```
   feat(api)!: change response payload structure for Stage 2
   ```

2. **`BREAKING CHANGE:` footer**:
   ```
   feat(api): migrate machine parameter to query model

   Migrates the legacy machine path parameter to a structured query model.

   BREAKING CHANGE: `machine_id` is now passed via query parameter rather than path.
   ```

---

## 5. Examples

### ✅ Valid Commits
```
feat(api): add neural ranking parameter to compatibility endpoint
fix(graph): resolve voltage constraint mismatch for 240V models
docs(readme): add Swagger UI interactive testing guide
refactor(ranker): optimize embedding batch computation
test(tests): add edge case tests for universal accessories
chore(deps): update ruff linter to v0.3.0
feat(api)!: rename target_voltage to voltage_override
```

### ❌ Invalid Commits
```
Updated endpoints                       # Missing type, uppercase start
feat(api): Add new neural endpoint.     # Uppercase start, ends with period
fix(unknown_scope): fix bug             # 'unknown_scope' is not an allowed scope
change: change some code                # 'change' is not an allowed type
feat(api):add endpoint                  # Missing space after colon
```

---

## 6. Local Git Hook Installation

To automatically validate commit messages before they are committed:

### Method A: Native Git Hook (Recommended & Zero-Dependency)
Point Git's hook directory to the repository's `.githooks` folder:
```bash
git config core.hooksPath .githooks
```

### Method B: Pre-Commit Framework
Install `pre-commit` into your environment and install the hooks:
```bash
.venv/bin/pip install pre-commit commitizen
.venv/bin/pre-commit install --hook-type commit-msg
```

### Manual Verification
You can validate any commit message file manually using the included validator script:
```bash
python scripts/check_commit_msg.py /path/to/commit_msg_file
```
