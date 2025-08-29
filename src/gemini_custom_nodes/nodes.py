from inspect import cleandoc
from google import genai
from google.genai import types
import torch
import numpy as np
import cv2
import tempfile
import os
import base64

class GeminiVideoDescribe:
    """
    A ComfyUI custom node for describing videos using Google's Gemini API.
    Takes IMAGE input from VideoHelperSuite nodes and converts back to video for analysis.
    """
    
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        """
        Return a dictionary which contains config for all input fields.
        Takes IMAGE input from VHS LoadVideoUpload node.
        """
        return {"required": {
                    "images": ("IMAGE",),
                    "frame_rate": ("FLOAT", {
                        "default": 24.0,
                        "min": 1.0,
                        "max": 60.0,
                        "step": 0.1,
                        "tooltip": "Frame rate for the temporary video file"
                    }),
                    "gemini_api_key": ("STRING", {
                        "multiline": False,
                        "default": "",
                        "tooltip": "Your Gemini API key"
                    }),
                    "gemini_model": (["models/gemini-2.5-flash", "models/gemini-2.5-flash-lite", "models/gemini-2.5-pro"], {
                        "default": "models/gemini-2.5-flash",
                        "tooltip": "Select the Gemini model to use"
                    }),
                    "system_prompt": ("STRING", {
                        "multiline": True,
                        "default": "You are an expert assistant specialized in analyzing and verbalizing input videos for cinematic-quality video transformation using the Wan 2.2 + VACE workflow.\nBefore writing, silently review all provided frames as a single clip and infer motion across time; reason stepwise over the entire sequence (start → middle → end). Do not use meta phrases (e.g., \"this video shows\").\nGenerate descriptions that adhere to the following structured layers and constraints, formatting each as a SEPARATE PARAGRAPH in this exact order:\n\n1. SUBJECT (First Paragraph)\nBegin with a gendered noun phrase (e.g., \"A woman…\", \"A man…\").\nInclude allowed visual traits: hairstyle and its texture or motion (no color or length), makeup, posture, gestures.\nStrictly exclude any reference to ethnicity, age, body type, tattoos, glasses, hair color, hair length, eye color, or height.\n\n2. SCENE (Second Paragraph)\nDescribe the visible environment clearly and vividly.\n\n3. MOVEMENT (Third Paragraph)\nIn this paragraph, describe body-part–specific movement and how it aligns with musical rhythm and beat structure. Begin with an overall summary: e.g., 'The subject initiates with a hip sway on the downbeat…'. Then narrate movement chronologically, using precise action verbs and transitions like 'then', 'as', and 'after', referencing the timeline (e.g., early/mid/late beat or second). Specify which body parts move, how they articulate (e.g., 'the right arm lifts upward, then sweeps outward; the torso tilts as the knees bend'), describe footwork, weight shifts, and alignment with music beats. Also include any camera movement (e.g., 'camera pans to follow the torso shift'). Avoid general labels—focus on locomotor and non‑locomotor gestures, repetition, rhythm, and choreography phrasing. Always include any buttock or breast movements that you see\n\n4. CINEMATIC AESTHETIC CONTROL (Fourth Paragraph)\nLighting (source/direction/quality/temperature), camera details (shot type, angle/height, movement), optics (lens feel, DOF, rack focus), and exposure/render cues as applicable.\n\n5. STYLIZATION & TONE (Fifth Paragraph)\nMood/genre descriptors (e.g., \"noir-inspired silhouette,\" \"cinematic realism,\" etc.).\n\nCRITICAL: Output exactly 5 paragraphs, one per category, separated by a blank line. Never mention prohibited attributes, even if visible.",
                        "tooltip": "System prompt to set the context for the AI"
                    }),
                    "user_prompt": ("STRING", {
                        "multiline": True,
                        "default": "Please analyze this video and provide a detailed description following the 5-paragraph structure outlined in the system prompt.",
                        "tooltip": "User prompt for the specific task"
                    }),
                }}
                
    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("description", "video_info", "gemini_status")
    FUNCTION = "describe_video"
    CATEGORY = "Gemini"
    
    def describe_video(self, images, frame_rate, gemini_api_key, gemini_model, system_prompt, user_prompt):
        """
        Convert ComfyUI IMAGE tensor to video and analyze with Gemini
        
        Args:
            images: IMAGE tensor from VideoHelperSuite (shape: [frames, height, width, channels])
            frame_rate: Frame rate for temporary video
            gemini_api_key: Your Gemini API key
            gemini_model: Gemini model to use
            system_prompt: System context for the AI
            user_prompt: User's specific request
        """
        try:
            # Convert ComfyUI IMAGE tensor to numpy array
            # ComfyUI images are in format [frames, height, width, channels] with values 0-1
            if isinstance(images, torch.Tensor):
                frames_np = images.cpu().numpy()
            else:
                frames_np = np.array(images)
            
            # Convert from 0-1 range to 0-255 and ensure uint8
            frames_np = (frames_np * 255).astype(np.uint8)
            
            # Create temporary video file
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
                temp_video_path = temp_file.name
            
            # Get video dimensions
            num_frames, height, width, channels = frames_np.shape
            
            # Initialize video writer
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            video_writer = cv2.VideoWriter(temp_video_path, fourcc, frame_rate, (width, height))
            
            if not video_writer.isOpened():
                raise RuntimeError("Failed to open video writer")
            
            # Write frames to video
            for i in range(num_frames):
                frame = frames_np[i]
                # Convert RGB to BGR for OpenCV
                if channels == 3:
                    frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                else:
                    frame_bgr = frame[:, :, :3]  # Drop alpha if present
                    frame_bgr = cv2.cvtColor(frame_bgr, cv2.COLOR_RGB2BGR)
                
                video_writer.write(frame_bgr)
            
            video_writer.release()
            
            # Read the temporary video file and encode to base64
            with open(temp_video_path, 'rb') as video_file:
                video_data = video_file.read()
            
            # Clean up temporary file
            os.unlink(temp_video_path)
            
            # Initialize the Gemini client
            client = genai.Client(api_key=gemini_api_key)
            
            # Create the content structure for video analysis
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_bytes(
                            mime_type="video/mp4",
                            data=video_data,
                        ),
                    ],
                ),
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=f"{system_prompt}\n\n{user_prompt}"),
                    ],
                ),
            ]
            
            # Configure generation with thinking enabled
            generate_content_config = types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(
                    thinking_budget=-1,
                ),
            )
            
            # Generate the video description
            response = client.models.generate_content(
                model=gemini_model,
                contents=contents,
                config=generate_content_config,
            )
            
            # Format the three separate outputs
            file_size = len(video_data) / 1024 / 1024  # Size in MB
            
            # 1. Description - Clean output from Gemini (for direct use as prompt)
            description = response.text.strip()
            
            # 2. Video Info - Technical details about the processed video
            video_info = f"""📹 Video Processing Info:
• Frames: {num_frames}
• Frame Rate: {frame_rate} FPS
• Resolution: {width}x{height}
• File Size: {file_size:.2f} MB
• Duration: {num_frames/frame_rate:.2f} seconds"""
            
            # 3. Gemini Status - API and model information
            gemini_status = f"""🤖 Gemini Analysis Status: ✅ Complete
• Model: {gemini_model}
• API Key: {'*' * (len(gemini_api_key) - 4) + gemini_api_key[-4:] if len(gemini_api_key) >= 4 else '****'}"""
            
            return (description, video_info, gemini_status)
            
        except Exception as e:
            # Handle errors gracefully with three separate outputs
            
            # 1. Description - Error message (still usable as text, though not ideal)
            description = f"Error: Video analysis failed - {str(e)}"
            
            # 2. Video Info - What we know about the input
            video_info = f"""📹 Video Processing Info:
• Frames: {num_frames if 'num_frames' in locals() else 'Unknown'}
• Frame Rate: {frame_rate} FPS
• Resolution: {width if 'width' in locals() else 'Unknown'}x{height if 'height' in locals() else 'Unknown'}
• Status: ❌ Processing Failed"""
            
            # 3. Gemini Status - Error details
            gemini_status = f"""🤖 Gemini Analysis Status: ❌ Failed
• Model: {gemini_model}
• API Key: {'*' * (len(gemini_api_key) - 4) + gemini_api_key[-4:] if len(gemini_api_key) >= 4 else '****'}
• Error: {str(e)[:100]}{'...' if len(str(e)) > 100 else ''}

Please check:
1. API key is valid and has quota
2. Image tensor is properly formatted
3. Internet connectivity
4. Model supports video analysis"""
            
            return (description, video_info, gemini_status)


# A dictionary that contains all nodes you want to export with their names
# NOTE: names should be globally unique
NODE_CLASS_MAPPINGS = {
    "GeminiVideoDescribe": GeminiVideoDescribe
}

# A dictionary that contains the friendly/humanly readable titles for the nodes
NODE_DISPLAY_NAME_MAPPINGS = {
    "GeminiVideoDescribe": "Gemini Video Describe"
}
