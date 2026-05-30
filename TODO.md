# TODO — pymetal

## Open issues

- [ ] #2 Dependency Dashboard (Renovate bot meta-issue)

## Gaps

- [ ] No `opm-check` workflow — correct, as this is a library with no OVOS/OPM entry points.
- [ ] Lint relies on the shared ruff workflow only; no committed ruff config or
      `.pre-commit-config.yaml` (`pre_commit: false`). Add if local lint parity is wanted.
- [ ] No typecheck step despite a fully typed pydantic v2 model layer; consider mypy/pyright.
- [ ] Local scratch artifacts present but gitignored and untracked: `.coverage`,
      `pymetal.egg-info/`, `.idea/`, `.pytest_cache/`. No action needed unless they get
      committed.

Standard gh-automations CI is otherwise complete: build-tests, coverage, license_check,
lint, pip_audit, conventional-label, repo-health, release_workflow, publish_stable,
release-preview, plus a repo-specific `nightly-live` cassette-drift check.

## Code TODOs

None found.
