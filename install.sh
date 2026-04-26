#!/bin/bash
# ClawMemory Installation Script
# One-command setup for ClawMemory on OpenClaw

set -e

echo "======================================================================"
echo "ClawMemory - Semantic Memory Installation"
echo "======================================================================"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not installed"
    exit 1
fi

echo "Python version: $(python3 --version)"

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
echo "Installation directory: $SCRIPT_DIR"

# Install dependencies
echo ""
echo "Step 1: Installing Python dependencies..."
echo "  - sentence-transformers (embeddings)"
echo "  - numpy (vector operations)"

pip install sentence-transformers numpy --quiet

if [ $? -eq 0 ]; then
    echo "✓ Dependencies installed"
else
    echo "✗ Failed to install dependencies"
    exit 1
fi

# Optional: sqlite-vec (not strictly required with numpy fallback)
echo ""
echo "Step 2: Installing optional sqlite-vec (for advanced vector ops)..."
pip install sqlite-vec --quiet 2>/dev/null || echo "  (sqlite-vec skipped - numpy provides fallback)"

# Import existing memories
echo ""
echo "Step 3: Importing existing OpenClaw memories..."

WORKSPACE_PATH="/root/.openclaw/workspace"
if [ -d "$WORKSPACE_PATH" ]; then
    python3 "$SCRIPT_DIR/clawmemory.py" import-existing "$WORKSPACE_PATH"
    if [ $? -eq 0 ]; then
        echo "✓ Memories imported"
    else
        echo "  (No existing memories to import, or import failed - that's OK)"
    fi
else
    echo "  (Workspace not found at $WORKSPACE_PATH)"
fi

# Run demo
echo ""
echo "Step 4: Running demo..."
echo ""

if python3 "$SCRIPT_DIR/demo.py"; then
    echo ""
    echo "======================================================================"
    echo "Installation Complete!"
    echo "======================================================================"
    echo ""
    echo "Next steps:"
    echo ""
    echo "1. Use the CLI:"
    echo "   python3 $SCRIPT_DIR/clawmemory.py search 'your query'"
    echo "   python3 $SCRIPT_DIR/clawmemory.py add 'new memory'"
    echo "   python3 $SCRIPT_DIR/clawmemory.py list"
    echo ""
    echo "2. Integrate with OpenClaw:"
    echo "   from openclaw_bridge import OpenClawBridge"
    echo "   bridge = OpenClawBridge()"
    echo "   memories = bridge.search_relevant_memories(context, top_k=5)"
    echo ""
    echo "3. Read the skill documentation:"
    echo "   cat $SCRIPT_DIR/skill/SKILL.md"
    echo ""
else
    echo ""
    echo "======================================================================"
    echo "Installation Failed"
    echo "======================================================================"
    echo "The demo did not run successfully. Check the output above for errors."
    exit 1
fi
