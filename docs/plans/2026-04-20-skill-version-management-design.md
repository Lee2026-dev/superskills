# Skill Version Management Design

Date: 2026-04-20  
Status: Approved for planning  
Owner: wenli

## 1. Goal and Scope

Build version management for installed third-party skills, where each installed skill directory is an independent Git repository.

In scope:
- Discover and display per-skill version status during `scan`.
- List available versions from Git tags.
- Upgrade a skill to a specific tag or latest SemVer tag.

Out of scope:
- Editing `SKILL.md` version field as the primary upgrade mechanism.
- Automatic Git commits.
- Rollback command in first release.
- Non-Git installation modes.

## 2. Sources and Assumptions

- Version source: Git tags.
- Supported version tag formats: `vX.Y.Z` and `X.Y.Z`.
- SemVer scope (v1): core `MAJOR.MINOR.PATCH` only.
  - No prerelease or build metadata parsing in v1.
- Installed skill assumption (v1): each skill is a standalone local Git repo.

## 3. Commands and UX

### 3.1 New Commands

- `skills-inventory list-versions <name> [--path <abs>]`
- `skills-inventory upgrade <name> [--path <abs>] (--to <tag> | --latest)`

### 3.2 Skill Target Resolution

Default target input is by `name`.

Resolution rules:
1. Scan configured roots and collect matching skill directories by name.
2. If unique match, use it.
3. If multiple matches and `--path` is absent, fail and print candidate paths.
4. If `--path` is provided, it must be absolute and must match `<name>` directory basename.

## 4. `scan` Version Visibility (Default Behavior)

`scan` must include version status by default in both terminal output and JSON.

New per-skill fields:
- `current_version`
- `latest_version`

Derivation rules:
- `current_version`: SemVer tag exactly pointing to current `HEAD`; otherwise `unknown`.
- `latest_version`: after `git fetch --tags`, highest SemVer tag among available tags.

Failure behavior per skill:
- Not a Git repo: keep skill entry; set both versions to `unknown`; append warning.
- Fetch tags fails: continue full scan; set `latest_version=unknown`; append warning.
- No valid SemVer tags: `latest_version=unknown`.
- HEAD not on SemVer tag: `current_version=unknown`.

## 5. `list-versions` Behavior

Flow:
1. Resolve target skill (name/path rules above).
2. Validate Git repo.
3. `git fetch --tags --prune --quiet`.
4. Read tags, filter valid SemVer tags.
5. Sort descending by semantic version.
6. Print list and mark current version when applicable.

Error handling:
- Non-Git directory: non-zero exit.
- Fetch failure: non-zero exit.
- No valid SemVer tags: non-zero exit.

## 6. `upgrade` Behavior

Flow:
1. Resolve target skill.
2. Validate Git repo.
3. Check clean working tree (`git status --porcelain` must be empty).
4. Fetch tags.
5. Resolve target:
   - `--to <tag>`: must exist and be valid SemVer tag.
   - `--latest`: choose highest SemVer tag.
6. If already at target tag, exit 0 with no-op message.
7. `git checkout <tag>` (detached HEAD).
8. Print from/to version and commit summary.

Safety rules:
- Dirty working tree: fail fast, no mutation.
- Any fetch/checkout failure: fail with explicit reason.

## 7. Data Model Changes

Extend skill record with:
- `current_version: str`
- `latest_version: str`

Recommended sentinel value:
- `unknown` for unresolved/unsupported state.

JSON schema version should be bumped (e.g., `1.1`) to indicate added fields.

## 8. Terminal Output Changes

`scan` skills table adds columns:
- `Current Version`
- `Latest Version`

Display `unknown` literally when unavailable.

## 9. Testing Strategy

Unit tests:
- SemVer parsing/normalization (`vX.Y.Z` and `X.Y.Z`).
- Version ordering logic.
- HEAD-to-tag resolution.

Integration tests (temp git repos):
- `scan` populates both versions for valid repo.
- `scan` continues on fetch failure and warns.
- non-Git skill yields `unknown` values.
- `upgrade --latest` checks out highest SemVer tag.
- `upgrade --to` checks out requested tag.
- Dirty working tree blocks upgrade.
- Ambiguous name without `--path` fails with candidates.

## 10. Acceptance Criteria (v1)

- `scan` output (terminal + JSON) includes `current_version` and `latest_version` for every skill.
- `list-versions` lists SemVer tags in descending order.
- `upgrade` supports `--to` and `--latest`.
- `upgrade` refuses dirty working trees.
- Name ambiguity requires `--path`.
- Per-skill fetch failure in `scan` does not abort whole run.

## 11. Deferred Items

- Rollback command.
- Batch upgrade policies.
- Non-Git skill source integration.
- Full SemVer prerelease/build metadata.
