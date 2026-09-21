# Install the Wharton Growth Scorer on Windows

## What you need

- Windows 10 or 11
- Python 3.11 or 3.12 from [python.org](https://www.python.org/downloads/)
- An internet connection when installing and when downloading market data

During Python installation, select **Add Python to PATH**.

## Fast installation

### One-line PowerShell installation

Paste this complete line into PowerShell. No GitHub account or Git installation is required:

```powershell
irm https://raw.githubusercontent.com/kianjindal2010/wharton-growth-scorer/main/bootstrap.ps1 | iex
```

Then type:

```powershell
wharton predict
```

The same command can be used later to download updates and reinstall the model.

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

The program asks for the exact Yahoo Finance ticker, country, scoring date, and scorecard. Select `auto` for detailed industry detection. It then creates an Excel report, JSON result, frozen snapshot, and local history database, including timestamp-filtered Yahoo Finance news factors when eligible articles are available.

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
- **Insufficient Data:** review the Warnings sheet. The program applies neutral scores to unavailable fields and lowers confidence automatically.
- **No historical news:** Yahoo Finance usually provides only recent headlines. The scorer correctly leaves historical news neutral rather than using present-day stories in an earlier run.
- **Network error:** retry later and confirm that Yahoo Finance is reachable.

## Model boundaries

The scorer does not check WInS eligibility. Submit only securities the team has already confirmed as eligible. The tool also does not select bonds, cash, ETFs, position sizes, or the defensive sleeve.
