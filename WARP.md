# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Quickstart (macOS, Python ≥3.6)
- Create venv and install:
  - python3 -m venv .venv && source .venv/bin/activate
  - pip install --upgrade pip
  - pip install -e .
  - pip install pytest
- Run locally (dev; no console entry point needed):
  - python lazyscan.py
- Installed console script (after editable install):
  - lazyscan --help
  - Note: setup.py declares console_scripts "lazyscan=lazyscan:main" but lazyscan.py in this snapshot does not define main(); prefer running python lazyscan.py during development.
- Build distributions:
  - Note: setup.py reads README_PYPI.md (missing). For local builds, either create README_PYPI.md (you can copy README.md) or edit setup.py to read README.md.
  - pip install build
  - python -m build
  - OR legacy: python setup.py sdist bdist_wheel

## Testing
- Run all tests: pytest -q
- Run a single test file: pytest tests/test_unity.py -q
- Run a single test: pytest tests/test_unity.py::test_prompt_unity_project_selection -q
- Tests use unittest.mock/pytest fixtures to avoid destructive actions (mock input, temp dirs). Suites live under tests/ and target helpers and selection logic.

## Lint/format
- No ruff/flake8/black configs detected in this repo. If desired, install and run locally; not part of project defaults.

## Architecture and flows (high level)
- CLI orchestration (lazyscan.py):
  - Interactive UX (TTY checks), progress animation (knight_rider_animation), human-readable size formatting, config IO, and orchestration per app.
- Unity:
  - helpers/unity_hub.read_unity_hub_projects parses Unity Hub projects-v1.json (supports schema variants) returning [{name, path}].
  - helpers/unity_cache_helpers.generate_unity_project_report sizes Library, Temp, obj, Logs (optionally Build via args.build_dir).
  - CLI flow: scan_unity_project_via_hub(args, clean=False) → prompt_unity_project_selection → per-project reports → optional delete.
- Unreal:
  - helpers/unreal_launcher.get_unreal_projects discovers projects (Epic Launcher manifests and .uproject scanning).
  - helpers/unreal_cache_helpers.generate_unreal_project_report sizes Intermediate, Saved/Logs, Saved/Crashes, DerivedDataCache (optionally Binaries).
  - CLI flow: handle_unreal_discovery() → report → interactive clear.
- Chrome (macOS only):
  - helpers/chrome_cache_helpers.scan_chrome_cache inspects profiles, classifies “safe” vs “unsafe” user data for selective cleaning.
- Generic macOS cache cleanup:
  - clean_macos_cache(paths, colors) scans common system/app cache patterns, computes sizes, presents an interactive summary, then purges with safety checks.

## CLI entry points and flags
- Core module: lazyscan.py; package __version__ = 0.5.0.
- setup.py wires console_scripts "lazyscan=lazyscan:main" but main() is not present here; run python lazyscan.py during development or implement main() if you need the entry point.
- Notable flows exposed in lazyscan.py:
  - Unity via Hub JSON: scan_unity_project_via_hub(args, clean=False)
  - Unreal: handle_unreal_discovery()
  - Chrome (macOS): handle_chrome_discovery()
  - Generic macOS caches: clean_macos_cache(paths, colors)
- Flags shown in README are illustrative; this snapshot lacks argparse wiring. You may import and call the functions directly or add argparse if needed.

## Key operational notes (from README and code)
- First-run disclaimer persistence:
  - Stored at ~/.config/lazyscan/preferences.ini under [disclaimer].
  - mark_disclaimer_acknowledged() writes; has_seen_disclaimer() checks to decide whether to show warnings.
- macOS focus:
  - Many cache paths are macOS-specific; Chrome flow is guarded by sys.platform == "darwin".
- Destructive operations:
  - Flows prompt before deletion; tests mock input to avoid actual removal.

## Caveats
- Building distributions fails unless README_PYPI.md exists (read by setup.py). Create it (copy README.md) or modify setup.py for local builds.
- Console script mismatch: setup.py declares "lazyscan=lazyscan:main" but main() is absent here; prefer python lazyscan.py in this repo snapshot.
- No CLAUDE/Cursor/Copilot policy files were found in this repo.

## Test suites and mocking (references)
- Selection parsing robustness: tests/test_selection_parser.py
- Unity Hub parsing (schema variants, Unicode paths): tests/test_unity_hub.py
- Unity cache report + edge cases: tests/test_unity_cache_helpers.py, tests/test_end_to_end_unity_reports.py
- Unreal discovery (manifests, .uproject) and cache reports: tests/test_unreal_launcher.py, tests/test_unreal_cache_helpers.py
- macOS cache cleaning path safety and non-interactive behavior: tests/test_lazyscan.py

## Handy commands (day-to-day)
- source .venv/bin/activate
- python lazyscan.py --unityhub-json /path/to/projects-v1.json
- python lazyscan.py          # Unity interactive selection via prompts
- python lazyscan.py --unreal
- python lazyscan.py --chrome # macOS only
- Note: if CLI flags aren’t wired in this snapshot, import and call the handler functions directly or add argparse wiring.
