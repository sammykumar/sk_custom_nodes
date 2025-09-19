import os
import itertools
import numpy as np
import torch
from PIL import Image, ImageOps
import cv2
import psutil
import subprocess
import re
import time

import folder_paths
from comfy.utils import common_upscale, ProgressBar
import nodes
from comfy.k_diffusion.utils import FolderOfImages
from .logger import logger
from .utils import BIGMAX, DIMMAX, calculate_file_hash, get_sorted_dir_files_from_directory,\
        lazy_get_audio, hash_path, validate_path, strip_path, try_download_video,  \
        is_url, imageOrLatent, ffmpeg_path, ENCODE_ARGS, floatOrInt


video_extensions = ['webm', 'mp4', 'mkv', 'gif', 'mov']

VHSLoadFormats = {
    'None': {},
    'AnimateDiff': {'target_rate': 8, 'dim': (8,0,512,512)},
    'Mochi': {'target_rate': 24, 'dim': (16,0,848,480), 'frames':(6,1)},
    'LTXV': {'target_rate': 24, 'dim': (32,0,768,512), 'frames':(8,1)},
    'Hunyuan': {'target_rate': 24, 'dim': (16,0,848,480), 'frames':(4,1)},
    'Cosmos': {'target_rate': 24, 'dim': (16,0,1280,704), 'frames':(8,1)},
    'Wan': {'target_rate': 16, 'dim': (8,0,832,480), 'frames':(4,1)},
}

# Compatibility with external plugins
if not hasattr(nodes, 'VHSLoadFormats'):
    nodes.VHSLoadFormats = {}

def get_load_formats():
    formats = {}
    formats.update(nodes.VHSLoadFormats)
    formats.update(VHSLoadFormats)
    return (list(formats.keys()),
            {'default': 'AnimateDiff', 'formats': formats})

def get_format(format):
    if format in VHSLoadFormats:
        return VHSLoadFormats[format]
    return nodes.VHSLoadFormats.get(format, {})

def is_gif(filename) -> bool:
    file_parts = filename.split('.')
    return len(file_parts) > 1 and file_parts[-1] == "gif"

def target_size(width, height, custom_width, custom_height, downscale_ratio=8) -> tuple[int, int]:
    if downscale_ratio is None:
        downscale_ratio = 8
    if custom_width == 0 and custom_height ==  0:
        pass
    elif custom_height == 0:
        height *= custom_width/width
        width = custom_width
    elif custom_width == 0:
        width *= custom_height/height
        height = custom_height
    else:
        width = custom_width
        height = custom_height
    width = int(width/downscale_ratio + 0.5) * downscale_ratio
    height = int(height/downscale_ratio + 0.5) * downscale_ratio
    return (width, height)

def cv_frame_generator(video, force_rate, frame_load_cap, skip_first_frames,
                       select_every_nth, meta_batch=None, unique_id=None):
    """OpenCV-based frame generator - simplified version for VHS-SK"""
    video_cap = cv2.VideoCapture(video)
    if not video_cap.isOpened() or not video_cap.grab():
        raise ValueError(f"{video} could not be loaded with cv.")

    # extract video metadata
    fps = video_cap.get(cv2.CAP_PROP_FPS)
    width = int(video_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(video_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(video_cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps

    if width <=0 or height <=0:
        _, frame = video_cap.retrieve()
        height, width, _ = frame.shape

    # simplified frame processing for VHS-SK
    frames_added = 0
    base_frame_time = 1 / fps
    target_frame_time = 1/force_rate if force_rate != 0 else base_frame_time
    
    yieldable_frames = min(frame_load_cap, int(total_frames)) if frame_load_cap > 0 else total_frames
    yield (width, height, fps, duration, total_frames, target_frame_time, yieldable_frames)
    
    pbar = ProgressBar(yieldable_frames)
    
    for i in range(total_frames):
        ret, frame = video_cap.read()
        if not ret:
            break
            
        if i < skip_first_frames:
            continue
            
        if (i - skip_first_frames) % select_every_nth != 0:
            continue
            
        # Convert BGR to RGB
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = np.array(frame, dtype=np.float32) / 255.0
        
        yield frame
        frames_added += 1
        pbar.update(1)
        
        if frame_load_cap > 0 and frames_added >= frame_load_cap:
            break
    
    video_cap.release()

def load_video(meta_batch=None, unique_id=None, memory_limit_mb=None, vae=None,
               generator=cv_frame_generator, format='None', **kwargs):
    """Load video function for VHS-SK - simplified version"""
    format_config = get_format(format)
    kwargs['video'] = strip_path(kwargs['video'])
    
    if vae is not None:
        downscale_ratio = getattr(vae, "downscale_ratio", 8)
    else:
        downscale_ratio = format_config.get('dim', (1,))[0]

    # Generate frames
    gen = generator(meta_batch=meta_batch, unique_id=unique_id, **kwargs)
    (width, height, fps, duration, total_frames, target_frame_time, yieldable_frames) = next(gen)

    # Collect frames
    frames = []
    for frame in gen:
        frames.append(frame)
    
    if len(frames) == 0:
        raise RuntimeError("No frames generated")

    # Convert to torch tensor
    images = torch.from_numpy(np.array(frames))
    
    # Audio handling (lazy loading)
    start_time = kwargs.get('start_time', kwargs.get('skip_first_frames', 0) * target_frame_time)
    audio = lazy_get_audio(kwargs['video'], start_time, len(images) * target_frame_time)
    
    # Video info for compatibility
    video_info = {
        "source_fps": fps,
        "source_frame_count": total_frames,
        "source_duration": duration,
        "source_width": width,
        "source_height": height,
        "loaded_fps": 1/target_frame_time,
        "loaded_frame_count": len(images),
        "loaded_duration": len(images) * target_frame_time,
        "loaded_width": width,
        "loaded_height": height,
    }
    
    if vae is not None:
        return ({"samples": images}, len(images), audio, video_info)
    else:
        return (images, len(images), audio, video_info)

# Load Video Upload Node
class LoadVideoUpload:
    @classmethod
    def INPUT_TYPES(s):
        input_dir = folder_paths.get_input_directory()
        files = []
        for f in os.listdir(input_dir):
            if os.path.isfile(os.path.join(input_dir, f)):
                file_parts = f.split('.')
                if len(file_parts) > 1 and (file_parts[-1].lower() in video_extensions):
                    files.append(f)
        return {"required": {
                    "video": (sorted(files),),
                    "force_rate": (floatOrInt, {"default": 0, "min": 0, "max": 60, "step": 1}),
                    "custom_width": ("INT", {"default": 0, "min": 0, "max": DIMMAX}),
                    "custom_height": ("INT", {"default": 0, "min": 0, "max": DIMMAX}),
                    "frame_load_cap": ("INT", {"default": 0, "min": 0, "max": BIGMAX, "step": 1}),
                    "skip_first_frames": ("INT", {"default": 0, "min": 0, "max": BIGMAX, "step": 1}),
                    "select_every_nth": ("INT", {"default": 1, "min": 1, "max": BIGMAX, "step": 1}),
                    },
                "optional": {
                    "format": get_load_formats(),
                },
                "hidden": {
                    "unique_id": "UNIQUE_ID"
                },
                }

    CATEGORY = "VHS-SK 🎥🎬"
    RETURN_TYPES = (imageOrLatent, "INT", "AUDIO", "VHS_VIDEOINFO")
    RETURN_NAMES = ("IMAGE", "frame_count", "audio", "video_info")
    FUNCTION = "load_video"

    def load_video(self, **kwargs):
        kwargs['video'] = folder_paths.get_annotated_filepath(strip_path(kwargs['video']))
        return load_video(**kwargs)

    @classmethod
    def IS_CHANGED(s, video, **kwargs):
        image_path = folder_paths.get_annotated_filepath(video)
        return calculate_file_hash(image_path)

    @classmethod
    def VALIDATE_INPUTS(s, video):
        if not folder_paths.exists_annotated_filepath(video):
            return "Invalid video file: {}".format(video)
        return True

# Load Video Path Node  
class LoadVideoPath:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "video": ("STRING", {"placeholder": "X://insert/path/here.mp4", "vhs_path_extensions": video_extensions}),
                "force_rate": (floatOrInt, {"default": 0, "min": 0, "max": 60, "step": 1}),
                "custom_width": ("INT", {"default": 0, "min": 0, "max": DIMMAX}),
                "custom_height": ("INT", {"default": 0, "min": 0, "max": DIMMAX}),
                "frame_load_cap": ("INT", {"default": 0, "min": 0, "max": BIGMAX, "step": 1}),
                "skip_first_frames": ("INT", {"default": 0, "min": 0, "max": BIGMAX, "step": 1}),
                "select_every_nth": ("INT", {"default": 1, "min": 1, "max": BIGMAX, "step": 1}),
            },
            "optional": {
                "format": get_load_formats(),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID"
            },
        }

    CATEGORY = "VHS-SK 🎥🎬"
    RETURN_TYPES = (imageOrLatent, "INT", "AUDIO", "VHS_VIDEOINFO")
    RETURN_NAMES = ("IMAGE", "frame_count", "audio", "video_info")
    FUNCTION = "load_video"

    def load_video(self, **kwargs):
        if kwargs['video'] is None or validate_path(kwargs['video']) != True:
            raise Exception("video is not a valid path: " + kwargs['video'])
        if is_url(kwargs['video']):
            kwargs['video'] = try_download_video(kwargs['video']) or kwargs['video']
        return load_video(**kwargs)

    @classmethod
    def IS_CHANGED(s, video, **kwargs):
        return hash_path(video)

    @classmethod
    def VALIDATE_INPUTS(s, video):
        return validate_path(video, allow_none=True)

# Basic Image Path Loading Node
class LoadImagePath:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "image": ("STRING", {"placeholder": "X://insert/path/here.png", "vhs_path_extensions": list(FolderOfImages.IMG_EXTENSIONS)}),
                "custom_width": ("INT", {"default": 0, "min": 0, "max": DIMMAX, "step": 8}),
                "custom_height": ("INT", {"default": 0, "min": 0, "max": DIMMAX, "step": 8}),
            },
        }

    CATEGORY = "VHS-SK 🎥🎬"
    RETURN_TYPES = ("IMAGE", "MASK")
    RETURN_NAMES = ("IMAGE", "mask")
    FUNCTION = "load_image"

    def load_image(self, **kwargs):
        if kwargs['image'] is None or validate_path(kwargs['image']) != True:
            raise Exception("image is not a valid path: " + kwargs['image'])
        
        # Load single image as video frame
        kwargs.update({'video': kwargs['image'], 'force_rate': 0, 'frame_load_cap': 1})
        kwargs.pop('image')
        
        image, _, _, _ = load_video(**kwargs)
        
        # Handle alpha channel if present
        if image.size(3) == 4:
            return (image[:,:,:,:3], 1-image[:,:,:,3])
        return (image, torch.zeros(image.size(0), 64, 64, device="cpu"))

    @classmethod
    def IS_CHANGED(s, image, **kwargs):
        return hash_path(image)

    @classmethod
    def VALIDATE_INPUTS(s, image):
        return validate_path(image, allow_none=True)