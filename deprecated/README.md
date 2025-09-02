# Deprecated Nodes

This folder contains deprecated Gemini nodes that are no longer actively maintained but preserved for reference.

## Contents

-   **`gemini_video_describe.py`** - Standalone video analysis node (replaced by `GeminiMediaDescribe`)
-   **`gemini_image_describe.py`** - Standalone image analysis node (replaced by `GeminiMediaDescribe`)

## Why Deprecated?

These standalone nodes have been replaced by the unified `GeminiMediaDescribe` node in the main codebase, which provides:

-   Combined image and video analysis functionality
-   Media upload and randomization from directory paths
-   Better error handling and status reporting
-   More consistent API and interface

## Usage

These nodes are **not loaded** into ComfyUI and will not appear in the node menu. They are preserved here only for:

-   Reference purposes
-   Historical code review
-   Potential future extraction of specific functionality

## Migration

If you were using the old standalone nodes:

-   **`GeminiUtilVideoDescribe`** → Use `GeminiUtilMediaDescribe` with `media_type` set to "video"
-   **`GeminiUtilImageDescribe`** → Use `GeminiUtilMediaDescribe` with `media_type` set to "image"

The unified node provides all the same functionality plus additional features like directory randomization.
