#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/../backend"
BUILD_DIR="$SCRIPT_DIR/build"

echo "🏗️  Packaging Lambda functions..."

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

python3 -m venv "$BUILD_DIR/venv"
source "$BUILD_DIR/venv/bin/activate"

pip install --upgrade pip
pip install -r "$BACKEND_DIR/requirements.txt"

echo "📦 Packaging claims service..."
CLAIMS_DIR="$BUILD_DIR/claims"
mkdir -p "$CLAIMS_DIR"

cp -r "$BACKEND_DIR/claims" "$CLAIMS_DIR/"
cp -r "$BACKEND_DIR/notify" "$CLAIMS_DIR/"  # Both services need access to each other

pip install -r "$BACKEND_DIR/requirements.txt" --target "$CLAIMS_DIR"

cd "$CLAIMS_DIR"
zip -r "../claims_lambda.zip" . -x "*.pyc" "*/__pycache__/*" "*/tests/*"
cd - > /dev/null

echo "📦 Packaging notify service..."
NOTIFY_DIR="$BUILD_DIR/notify"
mkdir -p "$NOTIFY_DIR"

cp -r "$BACKEND_DIR/claims" "$NOTIFY_DIR/"  # Both services need access to each other
cp -r "$BACKEND_DIR/notify" "$NOTIFY_DIR/"

pip install -r "$BACKEND_DIR/requirements.txt" --target "$NOTIFY_DIR"

cd "$NOTIFY_DIR"
zip -r "../notify_lambda.zip" . -x "*.pyc" "*/__pycache__/*" "*/tests/*"
cd - > /dev/null

deactivate

echo "✅ Lambda packages created:"
echo "   - $BUILD_DIR/claims_lambda.zip"
echo "   - $BUILD_DIR/notify_lambda.zip"
