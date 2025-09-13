#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DEPLOYMENT_DIR="$PROJECT_ROOT/deployment"
BACKEND_DIR="$PROJECT_ROOT/backend"

echo "🚀 Starting optimized Lambda packaging process..."

rm -rf "$DEPLOYMENT_DIR/build"
mkdir -p "$DEPLOYMENT_DIR/build"

package_lambda() {
    local service_name=$1
    local handler_file=$2
    
    echo "📦 Packaging $service_name Lambda function..."
    
    local build_dir="$DEPLOYMENT_DIR/build/$service_name"
    mkdir -p "$build_dir"
    
    echo "  Installing Python dependencies with optimizations..."
    pip install -r "$BACKEND_DIR/requirements.txt" -t "$build_dir" --quiet \
        --no-deps --no-cache-dir --disable-pip-version-check
    
    pip install fastapi==0.112.2 -t "$build_dir" --quiet --no-cache-dir
    pip install uvicorn==0.30.6 -t "$build_dir" --quiet --no-cache-dir --no-deps
    pip install motor==3.6.0 -t "$build_dir" --quiet --no-cache-dir
    pip install pydantic==2.8.2 -t "$build_dir" --quiet --no-cache-dir
    pip install python-dotenv==1.0.1 -t "$build_dir" --quiet --no-cache-dir
    pip install httpx==0.27.2 -t "$build_dir" --quiet --no-cache-dir
    pip install pywebpush==1.14.0 -t "$build_dir" --quiet --no-cache-dir
    pip install mangum==0.17.0 -t "$build_dir" --quiet --no-cache-dir
    
    echo "  Copying backend source code..."
    cp -r "$BACKEND_DIR/claims" "$build_dir/" 2>/dev/null || true
    cp -r "$BACKEND_DIR/notify" "$build_dir/" 2>/dev/null || true
    
    echo "  Copying Lambda handler..."
    cp "$DEPLOYMENT_DIR/lambda/$handler_file" "$build_dir/"
    
    echo "  Aggressive cleanup of unnecessary files..."
    rm -rf "$build_dir/backend" 2>/dev/null || true
    rm -rf "$build_dir/venv" 2>/dev/null || true
    rm -rf "$build_dir/.venv" 2>/dev/null || true
    
    find "$build_dir" -name "tests" -type d -exec rm -rf {} + 2>/dev/null || true
    find "$build_dir" -name "test_*" -delete 2>/dev/null || true
    find "$build_dir" -name "*_test.py" -delete 2>/dev/null || true
    find "$build_dir" -name "*.md" -delete 2>/dev/null || true
    find "$build_dir" -name "*.rst" -delete 2>/dev/null || true
    find "$build_dir" -name "*.txt" -delete 2>/dev/null || true
    
    find "$build_dir" -name "*.pyc" -delete
    find "$build_dir" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find "$build_dir" -name "*.egg-info" -type d -exec rm -rf {} + 2>/dev/null || true
    find "$build_dir" -name ".git*" -delete 2>/dev/null || true
    
    find "$build_dir" -name "*.cpython-38*" -delete 2>/dev/null || true
    find "$build_dir" -name "*.cpython-39*" -delete 2>/dev/null || true
    find "$build_dir" -name "*.cpython-310*" -delete 2>/dev/null || true
    find "$build_dir" -name "*.cpython-311*" -delete 2>/dev/null || true
    
    find "$build_dir" -name "*.whl" -delete 2>/dev/null || true
    find "$build_dir" -name "*.dist-info" -type d -exec rm -rf {} + 2>/dev/null || true
    
    echo "  Creating deployment package..."
    cd "$build_dir"
    zip -r "../${service_name}-lambda.zip" . -q -x "*.pyc" "*/__pycache__/*"
    cd - > /dev/null
    
    local zip_size=$(du -h "$DEPLOYMENT_DIR/build/${service_name}-lambda.zip" | cut -f1)
    echo "✅ $service_name Lambda package created: $DEPLOYMENT_DIR/build/${service_name}-lambda.zip ($zip_size)"
}

package_lambda "claims" "claims_handler.py"
package_lambda "notifications" "notifications_handler.py"

echo "🎉 Lambda packaging completed successfully!"
echo "📁 Deployment packages available in: $DEPLOYMENT_DIR/build/"
ls -la "$DEPLOYMENT_DIR/build/"*.zip
