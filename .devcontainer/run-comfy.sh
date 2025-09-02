#!/bin/bash
set -e

echo "🚀 Starting ComfyUI with SK Custom Nodes..."

# Change to ComfyUI directory
cd /opt/ComfyUI

# Ensure our custom node is symlinked
if [ ! -L "custom_nodes/sk_custom_nodes" ]; then
    echo "🔗 Creating symlink to repository..."
    ln -sf /workspaces/repo custom_nodes/sk_custom_nodes
fi

# Set environment variables for better development experience
export PYTHONPATH="/workspaces/repo:$PYTHONPATH"

echo "📍 ComfyUI will be available at: http://localhost:8188"
echo "🎮 Custom nodes loaded from: /workspaces/repo"
echo ""
echo "🛑 To stop ComfyUI, press Ctrl+C"
echo ""

# Start ComfyUI with appropriate settings for development
python main.py \
    --listen 0.0.0.0 \
    --port 8188 \
    --enable-cors-header \
    --output-directory /workspaces/repo/output \
    --input-directory /workspaces/repo/input