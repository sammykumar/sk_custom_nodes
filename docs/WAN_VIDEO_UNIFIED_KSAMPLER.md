# WAN Video Unified KSampler

## Overview

The WAN Video Unified KSampler is a custom ComfyUI node that combines the functionality of high noise and low noise WAN 2.2 models into a single, intelligent sampler. It automatically switches between the two models based on a configurable sigma threshold, eliminating the need for two separate KSampler nodes in WAN 2.2 workflows.

## Key Features

- **Automatic Model Switching**: Seamlessly transitions from high noise to low noise model at the optimal sigma point
- **Sigma Visualization**: Displays a real-time graph showing the sigma curve with the exact switching point
- **WanVideoWrapper Compatibility**: Designed specifically for WanVideoWrapper input types (not native ComfyUI types)
- **Configurable Parameters**: Separate CFG settings for each model and adjustable boundary threshold
- **Interactive Preview**: JavaScript widget shows switching information and parameter preview

## Parameters

### Required Inputs

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model_high_noise` | WANVIDEOMODEL | - | WAN Video high noise model for early denoising steps |
| `model_low_noise` | WANVIDEOMODEL | - | WAN Video low noise model for final denoising steps |
| `image_embeds` | WANVIDIMAGE_EMBEDS | - | Image embeddings for video generation |
| `text_embeds` | WANVIDEOTEXTEMBEDS | - | Text embeddings for conditioning |
| `steps` | INT | 30 | Total number of denoising steps |
| `cfg_high_noise` | FLOAT | 4.0 | CFG scale for the high noise model |
| `cfg_low_noise` | FLOAT | 3.0 | CFG scale for the low noise model |
| `boundary` | FLOAT | 0.875 | Sigma threshold for model switching |
| `shift` | FLOAT | 5.0 | Sigma shift parameter |
| `seed` | INT | 0 | Random seed for generation |
| `scheduler` | STRING | "unipc" | Scheduler algorithm |

### Optional Inputs

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `samples` | LATENT | None | Initial latents for image-to-video workflows |
| `denoise_strength` | FLOAT | 1.0 | Denoising strength (1.0 = full denoising) |

## Boundary Values

The `boundary` parameter controls when the model switches from high noise to low noise:

- **0.875**: Recommended for Text-to-Video (T2V) workflows
- **0.9**: Recommended for Image-to-Video (I2V) workflows
- **Custom**: Any value between 0.0-1.0 for fine-tuning

## Outputs

| Output | Type | Description |
|--------|------|-------------|
| `samples` | LATENT | Generated video latents |
| `switch_info` | STRING | Information about the model switch point and parameters |

## Sigma Graph Visualization

The node automatically generates and displays a sigma schedule graph showing:
- **Blue curve**: Sigma values across all steps
- **Red vertical line**: Exact point where model switching occurs
- **Annotations**: Sigma value at the switch point
- **Dark theme**: Consistent with ComfyUI's interface

## JavaScript Widget Features

The accompanying JavaScript widget provides:
- **Real-time preview** of switching parameters
- **Visual summary** of model configuration
- **Parameter change detection** with automatic updates
- **Helpful hints** for boundary value selection
- **Responsive sizing** based on content

## Usage Examples

### Basic Text-to-Video
```
WAN Video Unified KSampler:
├─ model_high_noise: WAN_2_2_high_noise.safetensors
├─ model_low_noise: WAN_2_2_low_noise.safetensors  
├─ boundary: 0.875 (T2V recommended)
├─ cfg_high_noise: 4.0
├─ cfg_low_noise: 3.0
└─ steps: 30
```

### Image-to-Video with Custom Settings
```
WAN Video Unified KSampler:
├─ model_high_noise: WAN_2_2_high_noise.safetensors
├─ model_low_noise: WAN_2_2_low_noise.safetensors
├─ boundary: 0.9 (I2V recommended)
├─ cfg_high_noise: 3.5
├─ cfg_low_noise: 2.8
├─ samples: [initial_image_latents]
└─ steps: 25
```

## Technical Implementation

The node uses the switching logic from [WanMoeKSampler](https://github.com/stduhpf/ComfyUI-WanMoeKSampler) but adapted for WanVideoWrapper compatibility:

1. **Sigma Calculation**: Computes the exact step where sigma drops below the boundary
2. **Model Switching**: Runs high noise model until switch point, then low noise model
3. **Graph Generation**: Uses matplotlib to create sigma visualization
4. **ComfyUI Integration**: Sends graph via PromptServer for display

## Compatibility

- **Compatible with**: WanVideoWrapper nodes and input types
- **Incompatible with**: Native ComfyUI model types (use WanMoeKSampler instead)
- **Requirements**: matplotlib, torch (optional for advanced sigma calculation)

## Installation

The node is automatically available when SK Custom Nodes is installed. Ensure matplotlib is installed:

```bash
pip install matplotlib
```

## Troubleshooting

### Common Issues

1. **"Cannot generate sigma plot"**: matplotlib not installed
   - Solution: `pip install matplotlib`

2. **Model incompatibility**: Using wrong model types
   - Solution: Ensure models are WANVIDEOMODEL type from WanVideoWrapper

3. **Switch point seems wrong**: Boundary value needs adjustment
   - Solution: Use 0.875 for T2V, 0.9 for I2V, or experiment with custom values

### Debug Information

The node outputs detailed information to the console:
- Switch step calculation
- Sigma values at switch point
- Model switching confirmation
- Error messages with context

## Integration with Existing Workflows

The WAN Video Unified KSampler replaces the need for:
- Two separate WanVideoSampler nodes
- Manual step counting for model switching
- Complex workflow routing between models

Simply connect your WAN models, embeddings, and parameters to get automatic model switching with visual feedback.