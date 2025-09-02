#!/bin/bash
set -e

echo "🚀 Setting up SK Custom Nodes development environment..."

# Create custom_nodes directory if it doesn't exist
mkdir -p /opt/ComfyUI/custom_nodes

# Create symlink to our repo in custom_nodes
if [ ! -L "/opt/ComfyUI/custom_nodes/sk_custom_nodes" ]; then
    echo "🔗 Creating symlink to repository in ComfyUI custom_nodes..."
    ln -sf /workspaces/repo /opt/ComfyUI/custom_nodes/sk_custom_nodes
fi

# Install Python development dependencies
echo "🐍 Installing Python development dependencies..."
pip install --user -e /workspaces/repo
pip install --user ruff black mypy pytest pre-commit coverage

# Install additional Python dependencies for video processing
echo "📹 Installing video processing dependencies..."
pip install --user opencv-python pillow

# Install JavaScript tooling
echo "🟨 Setting up JavaScript development environment..."
cd /workspaces/repo

# Create web/package.json if it doesn't exist
if [ ! -f "web/package.json" ]; then
    echo "📦 Creating web/package.json..."
    cat > web/package.json << 'EOF'
{
  "name": "sk-custom-nodes-web",
  "version": "0.0.1",
  "description": "Web extension for SK Custom Nodes",
  "scripts": {
    "dev": "echo 'JavaScript widgets - no build step required'",
    "build": "echo 'JavaScript widgets - no build step required'",
    "lint": "eslint js/**/*.js",
    "lint:fix": "eslint js/**/*.js --fix",
    "format": "prettier --write js/**/*.js css/**/*.css"
  },
  "devDependencies": {
    "eslint": "^9.0.0",
    "prettier": "^3.0.0"
  }
}
EOF
fi

# Install Node.js dependencies
cd web
npm install

# Install pre-commit hooks
echo "🪝 Setting up pre-commit hooks..."
cd /workspaces/repo
pre-commit install --install-hooks

# Verify FFmpeg is available (should be included in the Docker image)
echo "🎬 Verifying FFmpeg availability..."
if command -v ffmpeg &> /dev/null; then
    echo "✅ FFmpeg is available: $(ffmpeg -version | head -1)"
else
    echo "⚠️  FFmpeg not found - installing..."
    sudo apt-get update && sudo apt-get install -y ffmpeg
fi

# Test Python imports
echo "🧪 Testing Python imports..."
python -c "from utils.nodes import NODE_CLASS_MAPPINGS; print('✅ Python nodes loaded:', list(NODE_CLASS_MAPPINGS.keys()))"

# Make run script executable
chmod +x /workspaces/repo/.devcontainer/run-comfy.sh

echo "✅ Development environment setup complete!"
echo ""
echo "🎯 Next steps:"
echo "  • Run './devcontainer/run-comfy.sh' to start ComfyUI"
echo "  • ComfyUI will be available at http://localhost:8188"
echo "  • Your custom nodes will be automatically loaded"
echo ""
echo "🔧 Development commands:"
echo "  • 'ruff check .' - Run Python linting"
echo "  • 'pytest' - Run Python tests"
echo "  • 'cd web && npm run lint' - Run JavaScript linting"
echo "  • 'pre-commit run --all-files' - Run all pre-commit hooks"