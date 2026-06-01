# Agent E QA / Distribution Report

Date: 2026-05-31

## Scope

Phase 8 focused on GitHub/Windows distribution readiness and documentation cleanup for Desktop 0.99 beta.

## Completed

- Updated `.gitignore` to ignore local virtual environments, generated telemetry data, primary user DB, logs, backups, and packaging output.
- Kept `data/demo/fh6_demo.db` commit-ready as a demo/sample database artifact.
- Updated `setup_windows.bat` to create `.venv`, install `requirements.txt`, and initialize SQLite with legacy migration plus demo seed.
- Updated `start_desktop.bat` to launch PySide6 Desktop from `.venv`, with a local developer fallback to `.venv312` when `.venv` cannot load Qt.
- Cleaned `README.md`, `PROJECT_STATUS.md`, `NEXT_STEPS.md`, and `AGENTS.md` for the 0.99 beta state.
- Confirmed end-user setup docs no longer point users to `.venv312`; only `start_desktop.bat` has an intentional local developer fallback.

## Static Checks

```text
README.md / PROJECT_STATUS.md / NEXT_STEPS.md / setup_windows.bat:
no .venv312 references

start_desktop.bat:
contains an intentional `.venv312` local developer fallback because the current `.venv` in this workspace cannot load `PySide6.QtWidgets`.

AGENTS.md / README.md / PROJECT_STATUS.md / NEXT_STEPS.md / ARCHITECTURE.md:
no '?' mojibake matches in the checked files
```

## Git Limitation

`git` is not installed/available in the current shell environment, and this workspace does not contain a `.git` directory. Because of that, the following checks still need to be run in a real Git checkout:

```powershell
git status --ignored
git check-ignore -v reports/desktop_0_99_beta_plan.md
git check-ignore -v data/demo/fh6_demo.db
git check-ignore -v data/fh6_tuning_sim.db
```

## Remaining Distribution Work

- Run a full Windows 10/11 clone test:
  - `git clone`
  - `setup_windows.bat`
  - `start_desktop.bat`
  - complete one real recording workflow
- Decide whether the demo database should be committed as `data/demo/fh6_demo.db` or regenerated only by setup.
