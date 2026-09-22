#!/usr/bin/env bash
set -euo pipefail

INSTALL_ROOT="$HOME/.local/share/wharton-growth-scorer"
BIN_DIR="$HOME/.local/bin"
TEMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/wharton-growth-scorer.XXXXXX")"
ARCHIVE_PATH="$TEMP_ROOT/source.zip"
EXTRACT_ROOT="$TEMP_ROOT/extracted"
SOURCE_URL="https://github.com/kianjindal2010/wharton-growth-scorer/archive/refs/heads/main.zip"

cleanup() {
  rm -rf "$TEMP_ROOT"
}
trap cleanup EXIT

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 was not found. Install Python 3.11 or newer from https://python.org or with Homebrew: brew install python@3.12"
  exit 1
fi

python3 - <<'PY'
import sys
if sys.version_info < (3, 11):
    raise SystemExit("Python 3.11 or newer is required. Install it with: brew install python@3.12")
PY

if ! command -v curl >/dev/null 2>&1; then
  echo "curl was not found. Install the macOS command line tools with: xcode-select --install"
  exit 1
fi

mkdir -p "$INSTALL_ROOT" "$BIN_DIR" "$EXTRACT_ROOT"
echo "Downloading Wharton Growth Scorer..."
curl -fL "$SOURCE_URL" -o "$ARCHIVE_PATH"

if command -v ditto >/dev/null 2>&1; then
  ditto -x -k "$ARCHIVE_PATH" "$EXTRACT_ROOT"
else
  unzip -q "$ARCHIVE_PATH" -d "$EXTRACT_ROOT"
fi

SOURCE_ROOT="$(find "$EXTRACT_ROOT" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
if [[ -z "$SOURCE_ROOT" ]]; then
  echo "The downloaded repository archive was empty."
  exit 1
fi

cp -R "$SOURCE_ROOT"/. "$INSTALL_ROOT"/

if [[ ! -x "$INSTALL_ROOT/.venv/bin/python" ]]; then
  python3 -m venv "$INSTALL_ROOT/.venv"
fi

"$INSTALL_ROOT/.venv/bin/python" -m pip install --upgrade pip
"$INSTALL_ROOT/.venv/bin/python" -m pip install -e "$INSTALL_ROOT"

cat > "$BIN_DIR/wharton" <<EOF
#!/usr/bin/env bash
exec "$INSTALL_ROOT/.venv/bin/wharton" "\$@"
EOF
chmod +x "$BIN_DIR/wharton"

APP_DIR="$HOME/Applications/Wharton Growth Scorer.app"
DESKTOP_APP_LINK="$HOME/Desktop/Wharton Growth Scorer.app"
mkdir -p "$APP_DIR/Contents/MacOS"
cat > "$APP_DIR/Contents/Info.plist" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleName</key><string>Wharton Growth Scorer</string>
  <key>CFBundleDisplayName</key><string>Wharton Growth Scorer</string>
  <key>CFBundleIdentifier</key><string>org.wharton-growth-scorer.desktop</string>
  <key>CFBundleExecutable</key><string>Wharton Growth Scorer</string>
  <key>CFBundleVersion</key><string>0.9.1</string>
  <key>CFBundleShortVersionString</key><string>0.9.1</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>LSMinimumSystemVersion</key><string>11.0</string>
  <key>NSHighResolutionCapable</key><true/>
</dict></plist>
EOF
cat > "$APP_DIR/Contents/MacOS/Wharton Growth Scorer" <<EOF
#!/usr/bin/env bash
exec "$INSTALL_ROOT/.venv/bin/python" -m growth_scorer.app
EOF
chmod +x "$APP_DIR/Contents/MacOS/Wharton Growth Scorer"

if [[ -d "$HOME/Desktop" ]]; then
  if [[ -L "$DESKTOP_APP_LINK" ]]; then
    ln -sfn "$APP_DIR" "$DESKTOP_APP_LINK"
  elif [[ ! -e "$DESKTOP_APP_LINK" ]]; then
    ln -s "$APP_DIR" "$DESKTOP_APP_LINK"
  fi
fi

PATH_LINE='export PATH="$HOME/.local/bin:$PATH"'
for PROFILE in "$HOME/.zprofile" "$HOME/.bash_profile"; do
  touch "$PROFILE"
  if ! grep -Fqx "$PATH_LINE" "$PROFILE"; then
    printf '\n%s\n' "$PATH_LINE" >> "$PROFILE"
  fi
done

echo
echo "Installation complete."
echo "Open 'Wharton Growth Scorer' from Applications, Spotlight, or the Desktop shortcut."
echo "Advanced command-line access remains available with: wharton predict"
echo "Excel reports will be saved under: $HOME/Documents/Wharton Growth Scorer/output/scores"
open "$APP_DIR"
