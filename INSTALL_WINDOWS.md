# Install the Wharton Growth Scorer on Windows

## What you need

- Windows 10 or 11
- Python 3.11 or 3.12 from [python.org](https://www.python.org/downloads/)
- Git from [git-scm.com](https://git-scm.com/download/win)
- An internet connection when installing and when downloading market data

During Python installation, select **Add Python to PATH**.

## Fast installation

### One-line PowerShell installation

After the repository owner has added your GitHub account as a collaborator, paste this complete line into PowerShell:

```powershell
$d="$env:LOCALAPPDATA\WhartonGrowthScorer"; if (Test-Path "$d\.git") { git -C $d pull } else { git clone https://github.com/kianjindal2010/wharton-growth-scorer.git $d }; powershell -NoProfile -ExecutionPolicy Bypass -File "$d\install.ps1"; $env:Path="$env:LOCALAPPDATA\Programs\WhartonGrowthScorer\bin;$env:Path"
```

Then type:

```powershell
wharton predict
```

The same command can be used later to update and reinstall the model.

1. Open PowerShell.
2. Download the shared ZIP from Google Drive, extract it, and open PowerShell in the extracted `Wharton_Growth_Scorer_v0.4.0` folder.

   After the repository is published later, teammates may instead clone it and enter the folder:

```powershell
git clone https://github.com/kianjindal2010/wharton-growth-scorer.git
cd wharton-growth-scorer
```

3. Run the installer:

```powershell
.\install_windows.bat
```

4. Start the interactive scorer:

```powershell
.\run_wharton.bat
```

To use the shorter `wharton predict` command in the same PowerShell window, activate the environment first:

```powershell
.\.venv\Scripts\Activate.ps1
wharton predict
```

The program asks for the exact Yahoo Finance ticker, country, scoring date, scorecard, and an optional verified-override workbook. Select `auto` for the normal sector-aware workflow. It then creates an Excel report, JSON result, frozen snapshot, and local history database, including the timestamp-filtered Yahoo Finance news factors when eligible articles are available.

## Command line installation

If the installer cannot run, use these commands:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\wharton.exe predict
```

Python 3.11 can be substituted if Python 3.12 is unavailable.

## Updating the model

From the repository folder:

```powershell
git pull
.\.venv\Scripts\python.exe -m pip install -e .
```

## Common problems

- **Ticker not found:** verify the exact ticker on Yahoo Finance, including suffixes such as `.TW`, `.T`, `.L`, or `.NS`.
- **`py` is not recognized:** reinstall Python and enable the PATH option.
- **`wharton` is not recognized:** use `.\.venv\Scripts\wharton.exe predict` or run `run_wharton.bat`.
- **Insufficient Data:** add verified regulatory metrics using an override workbook. This is expected for many banks, insurers, and pre-profit biotechnology companies.
- **No historical news:** Yahoo Finance usually provides only recent headlines. The scorer correctly leaves historical news neutral rather than using present-day stories in an earlier run.
- **Network error:** retry later and confirm that Yahoo Finance is reachable.

## Model boundaries

The scorer does not check WInS eligibility. Submit only securities the team has already confirmed as eligible. The tool also does not select bonds, cash, ETFs, position sizes, or the defensive sleeve.
