# SK Custom Nodes - ComfyUI Extension Development Guide

**ALWAYS reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.**

## Project Overview

SK Custom Nodes is a ComfyUI extension that provides Python custom nodes and JavaScript widgets. The project includes:

-   Python custom nodes for Gemini AI video analysis
-   JavaScript widgets for enhanced ComfyUI interaction
-   ~~React/TypeScript UI extension with internationalization~~ **DISABLED FOR NOW**
-   GitHub Actions for automated building and publishing

**Note: The React UI component (`ui-react_backup/`) is currently disabled and not in active development.**

## Working Effectively

### Essential System Dependencies

Install these system dependencies first:

```bash
# FFmpeg is REQUIRED for video processing functionality
sudo apt-get update && sudo apt-get install -y ffmpeg

# Verify installation
ffmpeg -version  # Should show version 6.1.1 or newer
```

### Bootstrap React UI Development _(DISABLED)_

**⚠️ The React UI component is currently disabled and not in active development.**

```bash
# THESE COMMANDS ARE CURRENTLY DISABLED
# Navigate to React UI directory
# cd ui-react_backup/ui

# Install Node.js dependencies - takes ~40 seconds
# npm install  # NEVER CANCEL: Takes 40 seconds. Set timeout to 60+ seconds.

# Build React extension - takes ~5 seconds
# npm run build  # NEVER CANCEL: Takes 5 seconds. Set timeout to 30+ seconds.
```

### Bootstrap Python Development

```bash
# Install Python package and dependencies
pip3 install -e .  # Takes ~12 seconds for basic dependencies

# Install essential Python dependencies for full functionality
# NEVER CANCEL: Takes 2-3 minutes for torch/opencv. Set timeout to 300+ seconds.
pip3 install torch opencv-python

# Install development tools
pip3 install pytest mypy coverage ruff pre-commit

# Verify Python modules work
python3 -c "from utils.nodes import NODE_CLASS_MAPPINGS; print('Available nodes:', list(NODE_CLASS_MAPPINGS.keys()))"
# Should output: Available nodes: ['GeminiUtilVideoDescribe']
```

## Development Workflows

### React UI Development _(DISABLED)_

**⚠️ The React UI component is currently disabled and not in active development.**

```bash
# THESE COMMANDS ARE CURRENTLY DISABLED
# cd ui-react_backup/ui

# Development with auto-reload (watches for changes)
# npm run watch

# Build for production
# npm run build  # NEVER CANCEL: Takes 5 seconds. Set timeout to 30+ seconds.

# TypeScript type checking
# npm run typecheck
```

### Python Development

```bash
# Import and test Python nodes
python3 -c "from utils.nodes import NODE_CLASS_MAPPINGS; print(list(NODE_CLASS_MAPPINGS.keys()))"

# Run Python linting (fast, < 1 second)
ruff check .

# Fix auto-fixable linting issues
ruff check --fix .
```

## Testing

### Python Testing

```bash
# Run pytest (currently no tests exist)
pytest  # NEVER CANCEL: Takes < 30 seconds. Set timeout to 60+ seconds.
# Expected: "no tests ran" - this is normal, no tests exist yet

# When adding tests, create them in a tests/ directory
```

### React UI Testing _(DISABLED)_

**⚠️ The React UI component is currently disabled and not in active development.**

```bash
# THESE COMMANDS ARE CURRENTLY DISABLED
# cd ui-react_backup/ui

# This command WILL FAIL with ES module errors
# npm test
# Error: "Jest encountered an unexpected token" - this is a known issue

# To add working tests, fix jest.config.js ES module configuration first
```

## Linting and Code Quality

### Python Linting (Works)

```bash
# Fast linting check (< 1 second)
ruff check .

# Fix automatically fixable issues
ruff check --fix .

# Note: Some unused import warnings are expected and can be ignored
# The code functions correctly despite these warnings
```

### React UI Linting _(DISABLED)_

**⚠️ The React UI component is currently disabled and not in active development.**

```bash
# THESE COMMANDS ARE CURRENTLY DISABLED
# cd ui-react_backup/ui

# This will show configuration errors but runs
# npm run lint  # Shows ESLint TypeScript project configuration issues

# Auto-fix formatting issues
# npm run lint:fix

# Format code
# npm run format
```

## Build and Publish Workflow

### Local Build Process _(DISABLED)_

**⚠️ The React UI component is currently disabled and not in active development.**

```bash
# THESE COMMANDS ARE CURRENTLY DISABLED
# Complete build from scratch
# cd ui-react_backup/ui
# npm install  # 40 seconds
# npm run build  # 5 seconds

# Verify built files exist
# ls -la ../dist/example_ext/  # Should show main.js, main.css, etc.
```

### GitHub Actions Publishing

The repository includes automated publishing via `.github/workflows/react-build.yml`:

-   Triggers on `pyproject.toml` changes pushed to main branch
-   Requires `REGISTRY_ACCESS_TOKEN` secret in repository settings
-   Automatically builds React UI and publishes to ComfyUI Registry

## Validation Scenarios

### Always validate changes by running these verification steps:

#### Python Node Validation

```bash
# 1. Import test
python3 -c "from utils.nodes import NODE_CLASS_MAPPINGS; print('✓ Python imports work')"

# 2. Linting
ruff check .  # Accept unused import warnings as normal

# 3. Verify system dependencies
ffmpeg -version | head -1  # Should show FFmpeg version
```

#### React UI Validation _(DISABLED)_

**⚠️ The React UI component is currently disabled and not in active development.**

```bash
# THESE COMMANDS ARE CURRENTLY DISABLED
# cd ui-react_backup/ui

# 1. Build test
# npm run build  # Should complete in ~5 seconds

# 2. Verify outputs
# ls -la ../dist/example_ext/main.js  # Should exist
# ls -la ../dist/locales/  # Should contain en/ and zh/ directories

# 3. TypeScript check
# npm run typecheck  # Should pass without errors
```

#### Full Integration Test _(PARTIALLY DISABLED)_

**⚠️ React UI components are disabled, but JavaScript widgets remain active.**

```bash
# 1. Clean build (DISABLED - React components only)
# cd ui-react_backup/ui
# rm -rf ../dist/
# npm run build

# 2. Verify ComfyUI integration files
# ls -la ../dist/example_ext/  # React build outputs (DISABLED)
ls -la ../../web/js/  # JavaScript widgets (ACTIVE)
ls -la ../../__init__.py  # Python entry point (ACTIVE)
```

## Known Issues and Limitations

### Jest Testing Configuration

-   Jest tests fail due to ES module configuration issues
-   Example test exists in `src/__tests__/dummy.test.tsx` but won't run
-   Fix requires updating jest.config.js and jest.setup.js for ESM support

### ESLint Configuration

-   ESLint shows TypeScript project configuration warnings
-   Code builds and runs correctly despite these warnings
-   Focus on functional validation rather than linting perfection

### Python Import Warnings

-   Ruff reports unused imports in `__init__.py` files
-   These imports are intentional for ComfyUI integration
-   The warnings can be safely ignored

### System Dependencies

-   FFmpeg is required for video processing features
-   Without FFmpeg, video-related functionality will fail at runtime
-   Always verify FFmpeg is installed in your environment

## Common Tasks

### File Structure Overview

```
sk_custom_nodes/
├── .github/workflows/react-build.yml  # CI/CD automation
├── __init__.py                         # Python entry point
├── pyproject.toml                      # Project metadata & publishing config
├── utils/nodes.py                      # Main Python custom nodes
├── web/js/gemini_widgets.js           # JavaScript widgets
└── ui-react_backup/                   # React UI extension
    ├── ui/src/                        # React source code
    ├── ui/package.json                # Node.js dependencies
    └── dist/                          # Built React outputs
```

### Package Management

```bash
# React dependencies
cd ui-react_backup/ui
npm install  # Install from package.json

# Python dependencies
pip3 install -e .  # Install from pyproject.toml
pip3 install torch opencv-python  # Additional ML dependencies
```

### Environment Verification

```bash
# Verify tool versions
node --version    # Should be v20.19.4+
npm --version     # Should be 10.8.2+
python3 --version # Should be 3.12.3+
ffmpeg -version   # Should be 6.1.1+

# Verify dependencies
npm list --prefix ui-react_backup/ui  # Show React dependencies
pip3 list | grep -E "(torch|opencv|google-genai)"  # Show Python ML deps
```

## Timing Expectations

**NEVER CANCEL these operations - they may appear to hang but are working:**

-   `npm install`: 40 seconds (normal)
-   `npm run build`: 5 seconds (very fast)
-   `pip3 install torch opencv-python`: 2-3 minutes (downloads large binaries)
-   `npm run watch`: Runs continuously until stopped
-   `ruff check`: < 1 second (very fast)
-   `pytest`: < 30 seconds (but no tests exist currently)

Set appropriate timeouts: 60+ seconds for npm install, 300+ seconds for Python ML dependencies.

## Development Tips

-   Always run `npm run build` in `ui-react_backup/ui` after React changes
-   Python code changes take effect immediately (no build step required)
-   Use `npm run watch` during active React development for auto-rebuilding
-   Focus on functional testing since automated tests have configuration issues
-   FFmpeg must be available in PATH for video processing features to work
