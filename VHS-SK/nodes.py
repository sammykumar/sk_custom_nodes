# VHS-SK - Video Helper Suite forked for SK Custom Nodes
# Based on ComfyUI-VideoHelperSuite by Kosinkadink
# https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite

import os
import sys
import json
import subprocess
import numpy as np
import re
import datetime
from typing import List
import torch
from PIL import Image, ExifTags
from PIL.PngImagePlugin import PngInfo
from pathlib import Path
from string import Template
import itertools
import functools

import folder_paths
from .logger import logger
from .image_latent_nodes import *
from .load_video_nodes import LoadVideoUpload, LoadVideoPath, LoadImagePath
from .load_images_nodes import LoadImagesFromDirectoryUpload, LoadImagesFromDirectoryPath
from .batched_nodes import VAEEncodeBatched, VAEDecodeBatched
from .utils import ffmpeg_path, get_audio, hash_path, validate_path, requeue_workflow, \
        gifski_path, calculate_file_hash, strip_path, try_download_video, is_url, \
        imageOrLatent, BIGMAX, merge_filter_args, ENCODE_ARGS, floatOrInt, cached, \
        ContainsAll
from comfy.utils import ProgressBar

# Video format handling (simplified)
if 'VHS_video_formats' not in folder_paths.folder_names_and_paths:
    folder_paths.folder_names_and_paths["VHS_video_formats"] = ((),{".json"})
if len(folder_paths.folder_names_and_paths['VHS_video_formats'][1]) == 0:
    folder_paths.folder_names_and_paths["VHS_video_formats"][1].add(".json")
audio_extensions = ['mp3', 'mp4', 'wav', 'ogg']

# Simplified video format support
base_formats_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "video_formats")

@cached(5)
def get_video_formats():
    """Get available video formats"""
    formats = ["video/webm", "video/mp4", "image/gif"]
    format_widgets = {}
    return formats, format_widgets

def apply_format_widgets(format_name, kwargs):
    """Apply format-specific widgets"""
    # Simplified format support
    return {"extension": "webm", "main_pass": ["-c:v", "libvpx-vp9", "-crf", "23"]}

def tensor_to_int(tensor, bits):
    tensor = tensor.cpu().numpy() * (2**bits-1) + 0.5
    return np.clip(tensor, 0, (2**bits-1))

def tensor_to_bytes(tensor):
    return tensor_to_int(tensor, 8).astype(np.uint8)

class VideoCombine:
    """Video Combine node for VHS-SK"""
    @classmethod
    def INPUT_TYPES(s):
        ffmpeg_formats, format_widgets = get_video_formats()
        return {
            "required": {
                "images": (imageOrLatent,),
                "frame_rate": (
                    floatOrInt,
                    {"default": 8, "min": 1, "step": 1},
                ),
                "loop_count": ("INT", {"default": 0, "min": 0, "max": 100, "step": 1}),
                "filename_prefix": ("STRING", {"default": "VHS-SK"}),
                "format": (["image/gif", "video/webm", "video/mp4"],),
                "save_output": ("BOOLEAN", {"default": True}),
            },
            "optional": {
                "audio": ("AUDIO",),
            },
            "hidden": ContainsAll({
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
                "unique_id": "UNIQUE_ID"
            }),
        }

    RETURN_TYPES = ("VHS_FILENAMES",)
    RETURN_NAMES = ("Filenames",)
    OUTPUT_NODE = True
    CATEGORY = "VHS-SK 🎥🎬"
    FUNCTION = "combine_video"

    def combine_video(
        self,
        frame_rate: int,
        loop_count: int,
        images=None,
        filename_prefix="VHS-SK",
        format="video/webm",
        save_output=True,
        prompt=None,
        extra_pnginfo=None,
        audio=None,
        unique_id=None,
        **kwargs
    ):
        if images is None or len(images) == 0:
            return ((save_output, []),)

        # Handle latents vs images
        if isinstance(images, dict) and "samples" in images:
            # This is a latent, we need VAE to decode it
            raise ValueError("Latents not supported in simplified VHS-SK version")
        
        first_image = images[0]
        num_frames = len(images)
        
        # Setup output paths
        output_dir = (
            folder_paths.get_output_directory()
            if save_output
            else folder_paths.get_temp_directory()
        )
        
        (
            full_output_folder,
            filename,
            _,
            subfolder,
            _,
        ) = folder_paths.get_save_image_path(filename_prefix, output_dir)
        output_files = []

        # Create metadata
        metadata = PngInfo()
        video_metadata = {}
        if prompt is not None:
            metadata.add_text("prompt", json.dumps(prompt))
            video_metadata["prompt"] = json.dumps(prompt)
        if extra_pnginfo is not None:
            for x in extra_pnginfo:
                metadata.add_text(x, json.dumps(extra_pnginfo[x]))
                video_metadata[x] = extra_pnginfo[x]
        
        metadata.add_text("CreationTime", datetime.datetime.now().isoformat(" ")[:19])

        # Counter for file naming
        max_counter = 0
        matcher = re.compile(f"{re.escape(filename)}_(\\d+)\\D*\\..+", re.IGNORECASE)
        for existing_file in os.listdir(full_output_folder):
            match = matcher.fullmatch(existing_file)
            if match:
                file_counter = int(match.group(1))
                if file_counter > max_counter:
                    max_counter = file_counter
        counter = max_counter + 1

        # Save first frame as PNG to keep metadata
        first_image_file = f"{filename}_{counter:05}.png"
        file_path = os.path.join(full_output_folder, first_image_file)
        Image.fromarray(tensor_to_bytes(first_image)).save(
            file_path,
            pnginfo=metadata,
            compress_level=4,
        )
        output_files.append(file_path)

        # Handle different formats
        format_type, format_ext = format.split("/")
        if format_type == "image":
            # Create animated image (GIF)
            file = f"{filename}_{counter:05}.{format_ext}"
            file_path = os.path.join(full_output_folder, file)
            
            pbar = ProgressBar(num_frames)
            
            def frames_gen(images):
                for i in images:
                    pbar.update(1)
                    yield Image.fromarray(tensor_to_bytes(i))
            
            frames = frames_gen(images)
            next(frames).save(
                file_path,
                format=format_ext.upper(),
                save_all=True,
                append_images=frames,
                duration=round(1000 / frame_rate),
                loop=loop_count,
                compress_level=4,
            )
            output_files.append(file_path)
        
        else:
            # Create video using ffmpeg
            if ffmpeg_path is None:
                raise ProcessLookupError("ffmpeg is required for video outputs")
            
            file = f"{filename}_{counter:05}.{format_ext}"
            file_path = os.path.join(full_output_folder, file)
            
            dimensions = (first_image.shape[1], first_image.shape[0])
            has_alpha = first_image.shape[-1] == 4
            
            # Setup ffmpeg command
            if has_alpha:
                i_pix_fmt = 'rgba'
            else:
                i_pix_fmt = 'rgb24'
            
            args = [ffmpeg_path, "-v", "error", "-f", "rawvideo", "-pix_fmt", i_pix_fmt,
                    "-s", f"{dimensions[0]}x{dimensions[1]}", "-r", str(frame_rate), "-i", "-"]
            
            if format_ext == "webm":
                args += ["-c:v", "libvpx-vp9", "-crf", "23", "-pix_fmt", "yuv420p"]
            elif format_ext == "mp4":
                args += ["-c:v", "libx264", "-crf", "23", "-pix_fmt", "yuv420p"]
            
            args.append(file_path)
            
            # Convert images to bytes and feed to ffmpeg
            images_bytes = b''.join(tensor_to_bytes(img).tobytes() for img in images)
            
            try:
                result = subprocess.run(args, input=images_bytes, capture_output=True, check=True)
            except subprocess.CalledProcessError as e:
                raise Exception("An error occurred in the ffmpeg subprocess:\n" + e.stderr.decode(*ENCODE_ARGS))
            
            output_files.append(file_path)
        
        # Create preview info
        preview = {
            "filename": file,
            "subfolder": subfolder,
            "type": "output" if save_output else "temp",
            "format": format,
            "frame_rate": frame_rate,
            "workflow": first_image_file,
            "fullpath": output_files[-1],
        }
        
        return {"ui": {"gifs": [preview]}, "result": ((save_output, output_files),)}

# Audio loading nodes
class LoadAudio:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "audio_file": ("STRING", {"default": "input/", "vhs_path_extensions": ['wav','mp3','ogg','m4a','flac']}),
                },
            "optional" : {
                "seek_seconds": ("FLOAT", {"default": 0, "min": 0}),
                "duration": ("FLOAT" , {"default": 0, "min": 0, "max": 10000000, "step": 0.01}),
                          }
        }

    RETURN_TYPES = ("AUDIO", "FLOAT")
    RETURN_NAMES = ("audio", "duration")
    CATEGORY = "VHS-SK 🎥🎬"
    FUNCTION = "load_audio"
    
    def load_audio(self, audio_file, seek_seconds=0, duration=0):
        audio_file = strip_path(audio_file)
        if audio_file is None or validate_path(audio_file) != True:
            raise Exception("audio_file is not a valid path: " + audio_file)
        if is_url(audio_file):
            audio_file = try_download_video(audio_file) or audio_file
        
        audio = get_audio(audio_file, start_time=seek_seconds, duration=duration)
        loaded_duration = audio['waveform'].size(2)/audio['sample_rate']
        return (audio, loaded_duration)

    @classmethod
    def IS_CHANGED(s, audio_file, **kwargs):
        return hash_path(audio_file)

    @classmethod
    def VALIDATE_INPUTS(s, audio_file, **kwargs):
        return validate_path(audio_file, allow_none=True)

# Video info nodes
class VideoInfo:
    @classmethod
    def INPUT_TYPES(s):
        return {
                "required": {
                    "video_info": ("VHS_VIDEOINFO",),
                    }
                }

    CATEGORY = "VHS-SK 🎥🎬"
    RETURN_TYPES = ("FLOAT","INT", "FLOAT", "INT", "INT", "FLOAT","INT", "FLOAT", "INT", "INT")
    RETURN_NAMES = (
        "source_fps🟨",
        "source_frame_count🟨",
        "source_duration🟨",
        "source_width🟨",
        "source_height🟨",
        "loaded_fps🟦",
        "loaded_frame_count🟦",
        "loaded_duration🟦",
        "loaded_width🟦",
        "loaded_height🟦",
    )
    FUNCTION = "get_video_info"

    def get_video_info(self, video_info):
        keys = ["fps", "frame_count", "duration", "width", "height"]
        source_info = []
        loaded_info = []

        for key in keys:
            source_info.append(video_info[f"source_{key}"])
            loaded_info.append(video_info[f"loaded_{key}"])

        return (*source_info, *loaded_info)

# Simplified utility nodes
class SelectFilename:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {"filenames": ("VHS_FILENAMES",), "index": ("INT", {"default": -1, "step": 1, "min": -1})}}
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES =("Filename",)
    CATEGORY = "VHS-SK 🎥🎬"
    FUNCTION = "select_filename"

    def select_filename(self, filenames, index):
        return (filenames[1][index],)

# Node mappings for VHS-SK
NODE_CLASS_MAPPINGS = {
    "VHS_VideoCombine": VideoCombine,
    "VHS_LoadVideo": LoadVideoUpload,
    "VHS_LoadVideoPath": LoadVideoPath,
    "VHS_LoadImagePath": LoadImagePath,
    "VHS_LoadImages": LoadImagesFromDirectoryUpload,
    "VHS_LoadImagesPath": LoadImagesFromDirectoryPath,
    "VHS_LoadAudio": LoadAudio,
    "VHS_VideoInfo": VideoInfo,
    "VHS_SelectFilename": SelectFilename,
    # Batched Nodes
    "VHS_VAEEncodeBatched": VAEEncodeBatched,
    "VHS_VAEDecodeBatched": VAEDecodeBatched,
    # Latent and Image nodes
    "VHS_SplitLatents": SplitLatents,
    "VHS_SplitImages": SplitImages,
    "VHS_SplitMasks": SplitMasks,
    "VHS_MergeLatents": MergeLatents,
    "VHS_MergeImages": MergeImages,
    "VHS_MergeMasks": MergeMasks,
    "VHS_GetLatentCount": GetLatentCount,
    "VHS_GetImageCount": GetImageCount,
    "VHS_GetMaskCount": GetMaskCount,
    "VHS_DuplicateLatents": RepeatLatents,
    "VHS_DuplicateImages": RepeatImages,
    "VHS_DuplicateMasks": RepeatMasks,
    "VHS_SelectEveryNthLatent": SelectEveryNthLatent,
    "VHS_SelectEveryNthImage": SelectEveryNthImage,
    "VHS_SelectEveryNthMask": SelectEveryNthMask,
    "VHS_SelectLatents": SelectLatents,
    "VHS_SelectImages": SelectImages,
    "VHS_SelectMasks": SelectMasks,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "VHS_VideoCombine": "Video Combine 🎥🎬",
    "VHS_LoadVideo": "Load Video (Upload) 🎥🎬",
    "VHS_LoadVideoPath": "Load Video (Path) 🎥🎬",
    "VHS_LoadImagePath": "Load Image (Path) 🎥🎬",
    "VHS_LoadImages": "Load Images (Upload) 🎥🎬",
    "VHS_LoadImagesPath": "Load Images (Path) 🎥🎬",
    "VHS_LoadAudio": "Load Audio (Path) 🎥🎬",
    "VHS_VideoInfo": "Video Info 🎥🎬",
    "VHS_SelectFilename": "Select Filename 🎥🎬",
    # Batched Nodes
    "VHS_VAEEncodeBatched": "VAE Encode Batched 🎥🎬",
    "VHS_VAEDecodeBatched": "VAE Decode Batched 🎥🎬",
    # Latent and Image nodes
    "VHS_SplitLatents": "Split Latents 🎥🎬",
    "VHS_SplitImages": "Split Images 🎥🎬",
    "VHS_SplitMasks": "Split Masks 🎥🎬",
    "VHS_MergeLatents": "Merge Latents 🎥🎬",
    "VHS_MergeImages": "Merge Images 🎥🎬",
    "VHS_MergeMasks": "Merge Masks 🎥🎬",
    "VHS_GetLatentCount": "Get Latent Count 🎥🎬",
    "VHS_GetImageCount": "Get Image Count 🎥🎬",
    "VHS_GetMaskCount": "Get Mask Count 🎥🎬",
    "VHS_DuplicateLatents": "Repeat Latents 🎥🎬",
    "VHS_DuplicateImages": "Repeat Images 🎥🎬",
    "VHS_DuplicateMasks": "Repeat Masks 🎥🎬",
    "VHS_SelectEveryNthLatent": "Select Every Nth Latent 🎥🎬",
    "VHS_SelectEveryNthImage": "Select Every Nth Image 🎥🎬",
    "VHS_SelectEveryNthMask": "Select Every Nth Mask 🎥🎬",
    "VHS_SelectLatents": "Select Latents 🎥🎬",
    "VHS_SelectImages": "Select Images 🎥🎬",
    "VHS_SelectMasks": "Select Masks 🎥🎬",
}