# VHS-SK - Video Helper Suite for SK Custom Nodes

VHS-SK is a customized fork of the [ComfyUI VideoHelperSuite](https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite) integrated into SK Custom Nodes, providing comprehensive video processing capabilities within ComfyUI.

## Features

### 🎥 Video Processing Nodes
- **Video Combine**: Create videos from image sequences with audio support
- **Load Video (Upload/Path)**: Load videos from uploads or file paths  
- **Load Images (Upload/Path)**: Load image sequences from directories
- **Load Audio**: Audio loading and processing capabilities

### 🎬 Image/Latent Manipulation
- **Split/Merge**: Split and merge latents, images, and masks
- **Select**: Select specific frames or ranges from sequences  
- **Repeat**: Duplicate latents, images, or masks
- **Count**: Get counts of latents, images, or masks
- **Batched VAE**: Efficient VAE encoding/decoding for large batches

### 📹 Video Formats
- **WebM**: VP9 codec with Opus audio
- **MP4**: H.264 codec with AAC audio  
- **GIF**: Animated image format support

### 🔧 Utility Nodes
- **Video Info**: Extract metadata from videos
- **Select Filename**: Choose specific files from outputs
- **Audio Processing**: Load and process audio files

## Installation

The VHS-SK nodes are automatically loaded as part of SK Custom Nodes. Required dependencies:

```bash
pip install torch torchvision numpy opencv-python pillow
```

For video processing, FFmpeg must be installed:
```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS  
brew install ffmpeg
```

## Node Categories

All VHS-SK nodes are organized under the **VHS-SK 🎥🎬** category in ComfyUI's node browser.

## Usage

### Basic Video Creation
1. Load images using **Load Images** nodes
2. Use **Video Combine** to create videos
3. Optionally add audio using **Load Audio**
4. Configure format (WebM, MP4, GIF) and frame rate

### Video Processing  
1. Use **Load Video** to import existing videos
2. Process frames with image manipulation nodes
3. Use **Video Info** to extract metadata
4. Combine processed frames back into videos

### Advanced Features
- **Batch processing** with VAE Encode/Decode Batched nodes
- **Frame selection** using Select Every Nth nodes  
- **Sequence manipulation** with Split/Merge operations

## Web Interface

VHS-SK includes enhanced web widgets for:
- Video preview and playback
- Path selection with autocomplete
- Format-specific options
- Progress tracking during processing

## File Structure

```
VHS-SK/
├── __init__.py              # Module initialization
├── nodes.py                 # Main video processing nodes
├── utils.py                 # Utility functions  
├── logger.py                # Logging system
├── server.py                # Web server endpoints
├── image_latent_nodes.py    # Image/latent manipulation
├── load_video_nodes.py      # Video loading functionality
├── load_images_nodes.py     # Image sequence loading
├── batched_nodes.py         # Batch processing nodes
├── video_formats/           # Video format definitions
│   ├── webm.json           # WebM format config
│   └── mp4.json            # MP4 format config
└── web/
    └── js/
        ├── VHS.core.js     # Main web functionality
        └── vhs-sk.js       # Simplified widgets
```

## Customization

### Adding Video Formats
Create new JSON files in `VHS-SK/video_formats/`:
```json
{
    "main_pass": ["-c:v", "libx264", "-crf", "23"],
    "audio_pass": ["-c:a", "aac"],
    "extension": "mp4"
}
```

### Custom Widgets
Extend the web interface by modifying `VHS-SK/web/js/vhs-sk.js`.

## Compatibility

- **ComfyUI**: Compatible with standard ComfyUI installations
- **SK Custom Nodes**: Integrated with existing SK nodes
- **Original VHS**: Can coexist with the original VideoHelperSuite (different node names)

## Credits

- Original VideoHelperSuite by [Kosinkadink](https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite)
- Adapted and integrated for SK Custom Nodes
- Maintains compatibility with ComfyUI ecosystem

## License

This project inherits the license from the original VideoHelperSuite.