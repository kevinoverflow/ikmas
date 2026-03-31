#!/usr/bin/env bash
set -e

PYTHON_BIN="python3.11"

VENV_DIR=".venv"
REQ_FILE="requirements.txt"
REQ_HASH_FILE="$VENV_DIR/.requirements.hash"
APP_PATH="app/ui/streamlit_app.py"

# --- Check if python3.11 exists ---
if ! command -v $PYTHON_BIN &> /dev/null; then
  echo "❌ $PYTHON_BIN not found. Please install it with:"
  echo "   brew install python@3.11"
  exit 1
fi

# --- Create venv if missing ---
if [ ! -d "$VENV_DIR" ]; then
  echo "🔧 Creating virtual environment with Python 3.11..."
  $PYTHON_BIN -m venv "$VENV_DIR"
fi

# --- Activate venv ---
source "$VENV_DIR/bin/activate"

# --- Install requirements only if changed ---
if [ -f "$REQ_FILE" ]; then
  CURRENT_HASH=$(sha256sum "$REQ_FILE" | awk '{print $1}')
  STORED_HASH=""

  if [ -f "$REQ_HASH_FILE" ]; then
    STORED_HASH=$(cat "$REQ_HASH_FILE")
  fi

  if [ "$CURRENT_HASH" != "$STORED_HASH" ]; then
    echo "📦 Installing / updating dependencies..."
    pip install --upgrade pip setuptools wheel
    pip install -r "$REQ_FILE"
    echo "$CURRENT_HASH" > "$REQ_HASH_FILE"
  else
    echo "✅ Requirements already installed."
  fi
else
  echo "⚠️  requirements.txt not found. Skipping dependency install."
fi

# --- Check SCADS_API_KEY ---
if [ -z "${SCADS_API_KEY:-}" ]; then
  echo "🔑 SCADS_API_KEY is not set."
  read -rp "Please enter your SCADS_API_KEY: " SCADS_API_KEY
  export SCADS_API_KEY
fi

# --- Run app ---
echo "🚀 Starting Streamlit app..."
export PYTHONPATH=.
streamlit run "$APP_PATH"