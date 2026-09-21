# Install the Wharton Growth Scorer on macOS

## Requirements

- macOS with an internet connection
- Python 3.11 or newer

Check the installed version:

```bash
python3 --version
```

If necessary, install a current Python from [python.org](https://www.python.org/downloads/macos/) or with Homebrew:

```bash
brew install python@3.12
```

## One-line installation

Paste this complete line into Terminal:

```bash
curl -fsSL https://raw.githubusercontent.com/kianjindal2010/wharton-growth-scorer/main/bootstrap.sh | bash && export PATH="$HOME/.local/bin:$PATH"
```

The installer creates **Wharton Growth Scorer.app** in your user Applications folder, adds a Desktop alias, and opens it automatically. For future use, double-click the Desktop icon, open it from Finder → Applications, or search for it with Spotlight. No Terminal command is required.

The command-line interface remains available for advanced use:

```bash
wharton predict
```

In the frontend, choose **Single company** or **Batch comparison**, add the companies, select the information date, and click the run button. The result screen can open the generated Excel workbook or output folder directly.

For a batch, paste up to 100 already formatted Yahoo Finance tickers into one comma-separated list. Markets may be mixed, such as `MSFT,TCS.NS,2330.TW,000660.KS`; the application detects the country from each suffix.

The same installer command downloads updates and reinstalls the model later.

## Interactive inputs

Enter an exact Yahoo Finance ticker, the matching country code, an as-of date, and press Enter for automatic detailed scorecard selection.

```text
Stock ticker: 2330.TW
Country: TW
As-of date: 2026-09-20
Scorecard: press Enter
```

## Output

The generated workbook is saved under:

```text
~/Documents/Wharton Growth Scorer/output/scores/YYYY-MM-DD/
```

It contains Summary, Factor Breakdown, Raw Data, Source Log, and Warnings worksheets.

## Troubleshooting

- If `wharton` is not found, close and reopen Terminal or run `export PATH="$HOME/.local/bin:$PATH"`.
- If Python is too old, install Python 3.11 or newer and repeat the installer command.
- Apple Silicon and Intel Macs are both supported as long as the Python installation matches the computer architecture.
