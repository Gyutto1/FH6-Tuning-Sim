# Known Issues (Current)

1. Local environment variance:
   - `.venv` may fail `PySide6.QtWidgets` load in this workspace.
   - `start_desktop.bat` includes `.venv312` fallback.

2. Historical encoding artifacts:
   - Some old files contain legacy encoding noise; function behavior is unaffected.

3. Git shell availability:
   - Some local shells may not provide `git`, impacting local git validation commands.

4. Manual validation still required:
   - Windows + FH6 Data Out runtime path should be validated before 1.0 hardening.
