## Run Full Automation Pipeline

Use the PowerShell launcher from the project root:

```powershell
.\run-pipeline.ps1
```

This script will:

1. Start BlueStacks.
2. Wait for adb device `127.0.0.1:5555`.
3. Run `src\motion.py` using `.venv\Scripts\python.exe`.

### Useful Options

```powershell
# If BlueStacks is installed in a custom location
.\run-pipeline.ps1 -BlueStacksPath "C:\Program Files\BlueStacks_nxt\HD-Player.exe"

# If BlueStacks is already open
.\run-pipeline.ps1 -SkipBlueStacks

# Validate command flow without launching BlueStacks or Python automation
.\run-pipeline.ps1 -DryRun -SkipBlueStacks
```
