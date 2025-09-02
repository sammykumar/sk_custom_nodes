from google import genai
from google.genai import types
import cv2
import tempfile
import os
import subprocess
import numpy as np
from PIL import Image
import io

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
        Takes IMAGE input from VHS LoadVideoUpload node OR allows direct video file upload.
        """
        return {
            "required": {
                "gemini_api_key": ("STRING", {
                    "multiline": False,
                    "default": "AIzaSyBZpbWUwPlNsqQl6al0VEquoEY4pCZsSjM",
                    "tooltip": "Your Gemini API key"
                }),
                "gemini_model": (["models/gemini-2.5-flash", "models/gemini-2.5-flash-lite", "models/gemini-2.5-pro"], {
                    "default": "models/gemini-2.5-flash",
                    "tooltip": "Select the Gemini model to use"
                }),
                "description_mode": (["Describe without clothing", "Describe with clothing", "Describe without clothing (No bokeh)", "Describe with clothing (No bokeh)"], {
                    "default": "Describe without clothing",
                    "tooltip": "Choose whether to include detailed clothing description and depth of field effects"
                }),
            },
            "optional": {
                "frame_rate": ("FLOAT", {
                    "default": 30,
                    "min": 1.0,
                    "max": 60.0,
                    "step": 0.1,
                    "tooltip": "Frame rate for the temporary video file (used when processing IMAGE input)"
                }),
                "uploaded_video_file": ("STRING", {
                    "default": "",
                    "tooltip": "Path to uploaded video file (managed by upload widget)"
                }),
                "max_duration": ("FLOAT", {
                    "default": 5.0,
                    "min": 0.0,
                    "max": 300.0,
                    "step": 0.1,
                    "tooltip": "Maximum duration in seconds (0 = use full video)"
                }),
                "prefix_text": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "tooltip": "Text to prepend to the generated description"
                }),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("description", "video_info", "gemini_status", "trimmed_video_path", "final_string")
    FUNCTION = "describe_video"
    CATEGORY = "Gemini"

    def _trim_video(self, input_path, output_path, duration):
        """
        Trim video to specified duration from the beginning using ffmpeg

        Args:
            input_path: Path to input video file
            output_path: Path to output trimmed video file
            duration: Duration in seconds from the beginning
        """

        try:
            # Use ffmpeg to trim the video from the beginning
            cmd = [
                'ffmpeg',
                '-i', input_path,
                '-t', str(duration),     # Duration from start
                '-c', 'copy',  # Copy streams without re-encoding for speed
                '-avoid_negative_ts', 'make_zero',
                '-y',  # Overwrite output file if it exists
                output_path
            ]

            subprocess.run(cmd, capture_output=True, text=True, check=True)
            return True

        except subprocess.CalledProcessError as e:
            print(f"FFmpeg error: {e.stderr}")
            # Fallback: try with re-encoding if copy fails
            try:
                cmd = [
                    'ffmpeg',
                    '-i', input_path,
                    '-t', str(duration),
                    '-c:v', 'libx264',
                    '-c:a', 'aac',
                    '-y',
                    output_path
                ]
                subprocess.run(cmd, capture_output=True, text=True, check=True)
                return True
            except subprocess.CalledProcessError as e2:
                print(f"FFmpeg re-encoding also failed: {e2.stderr}")
                return False
        except FileNotFoundError:
            print("FFmpeg not found. Please install ffmpeg to use duration trimming.")
            return False

    def describe_video(self, gemini_api_key, gemini_model, description_mode, frame_rate=24.0, uploaded_video_file="", max_duration=0.0, prefix_text=""):
        """
        Process uploaded video file and analyze with Gemini

        Args:
            gemini_api_key: Your Gemini API key
            gemini_model: Gemini model to use
            description_mode: Mode for description with options for clothing and depth of field
            frame_rate: Frame rate for temporary video (legacy parameter, not used)
            uploaded_video_file: Path to uploaded video file
            max_duration: Maximum duration in seconds (0 = use full video)
        """
        try:
            # Set the appropriate system prompt and user prompt based on description mode
            if description_mode == "Describe with clothing":
                system_prompt = """You are an expert assistant specialized in analyzing and verbalizing input videos for cinematic-quality video transformation using the Wan 2.2 + VACE workflow.
Before writing, silently review all provided frames as a single clip and infer motion across time; reason stepwise over the entire sequence (start → middle → end). Do not use meta phrases (e.g., "this video shows").
Generate descriptions that adhere to the following structured layers and constraints, formatting each as a SEPARATE PARAGRAPH in this exact order:

1. SUBJECT (First Paragraph)
Begin with a gendered noun phrase (e.g., "A woman…", "A man…").
Include allowed visual traits: hairstyle and its texture or motion (no color or length), makeup, posture, gestures.
Strictly exclude any reference to ethnicity, age, body type, tattoos, glasses, hair color, hair length, eye color, or height.

2. CLOTHING (Second Paragraph)
Describe all visible clothing and accessories. Be granular: specify garment type, color(s), material/texture, fit/silhouette, length, notable construction (seams, straps, waistbands), and condition. Include footwear if visible and note how fabrics respond to motion (stretching, swaying, tightening, wrinkling). Do not describe logos or brand names. Exclude tattoos, glasses, and other prohibited attributes.

3. SCENE (Third Paragraph)
Describe the visible environment clearly and vividly.

4. MOVEMENT (Fourth Paragraph)
In this paragraph, describe body-part–specific movement and how it aligns with musical rhythm and beat structure. Begin with an overall summary: e.g., 'The subject initiates with a hip sway on the downbeat…'. Then narrate movement chronologically, using precise action verbs and transitions like 'then', 'as', and 'after', referencing the timeline (e.g., early/mid/late beat or second). Specify which body parts move, how they articulate (e.g., 'the right arm lifts upward, then sweeps outward; the torso tilts as the knees bend'), describe footwork, weight shifts, and alignment with music beats. Also include any camera movement (e.g., 'camera pans to follow the torso shift'). Avoid general labels—focus on locomotor and non‑locomotor gestures, repetition, rhythm, and choreography phrasing. Always include any buttock or breast movements that you see

5. CINEMATIC AESTHETIC CONTROL (Fifth Paragraph)
Lighting (source/direction/quality/temperature), camera details (shot type, angle/height, movement), optics (lens feel, DOF, rack focus), and exposure/render cues as applicable.

6. STYLIZATION & TONE (Sixth Paragraph)
Mood/genre descriptors (e.g., "noir-inspired silhouette," "cinematic realism," etc.).

CRITICAL: Output exactly 6 paragraphs, one per category, separated by a blank line. Never mention prohibited attributes, even if visible."""
                user_prompt = "Please analyze this video and provide a detailed description following the 6-paragraph structure outlined in the system prompt."
            elif description_mode == "Describe with clothing (No bokeh)":
                system_prompt = """You are an expert assistant specialized in analyzing and verbalizing input videos for cinematic-quality video transformation using the Wan 2.2 + VACE workflow.
Before writing, silently review all provided frames as a single clip and infer motion across time; reason stepwise over the entire sequence (start → middle → end). Do not use meta phrases (e.g., "this video shows").
Generate descriptions that adhere to the following structured layers and constraints, formatting each as a SEPARATE PARAGRAPH in this exact order:

1. SUBJECT (First Paragraph)
Begin with a gendered noun phrase (e.g., "A woman…", "A man…").
Include allowed visual traits: hairstyle and its texture or motion (no color or length), makeup, posture, gestures.
Strictly exclude any reference to ethnicity, age, body type, tattoos, glasses, hair color, hair length, eye color, or height.

2. CLOTHING (Second Paragraph)
Describe all visible clothing and accessories. Be granular: specify garment type, color(s), material/texture, fit/silhouette, length, notable construction (seams, straps, waistbands), and condition. Include footwear if visible and note how fabrics respond to motion (stretching, swaying, tightening, wrinkling). Do not describe logos or brand names. Exclude tattoos, glasses, and other prohibited attributes.

3. SCENE (Third Paragraph)
Describe the visible environment clearly and vividly.

4. MOVEMENT (Fourth Paragraph)
In this paragraph, describe body-part–specific movement and how it aligns with musical rhythm and beat structure. Begin with an overall summary: e.g., 'The subject initiates with a hip sway on the downbeat…'. Then narrate movement chronologically, using precise action verbs and transitions like 'then', 'as', and 'after', referencing the timeline (e.g., early/mid/late beat or second). Specify which body parts move, how they articulate (e.g., 'the right arm lifts upward, then sweeps outward; the torso tilts as the knees bend'), describe footwork, weight shifts, and alignment with music beats. Also include any camera movement (e.g., 'camera pans to follow the torso shift'). Avoid general labels—focus on locomotor and non‑locomotor gestures, repetition, rhythm, and choreography phrasing. Always include any buttock or breast movements that you see

5. CINEMATIC AESTHETIC CONTROL (Fifth Paragraph)
Lighting (source/direction/quality/temperature), camera details (shot type, angle/height, movement), and exposure/render cues as applicable. Everything must be in sharp focus with no depth of field effects, bokeh, or blur. Do not mention optics, DOF, rack focus, or any depth-related visual effects.

6. STYLIZATION & TONE (Sixth Paragraph)
Mood/genre descriptors (e.g., "noir-inspired silhouette," "cinematic realism," etc.).

CRITICAL: Output exactly 6 paragraphs, one per category, separated by a blank line. Never mention prohibited attributes, even if visible. Never mention depth of field, bokeh, blur, optics, DOF, rack focus, or any depth-related visual effects."""
                user_prompt = "Please analyze this video and provide a detailed description following the 6-paragraph structure outlined in the system prompt."
            elif description_mode == "Describe without clothing (No bokeh)":
                system_prompt = """You are an expert assistant specialized in analyzing and verbalizing input videos for cinematic-quality video transformation using the Wan 2.2 + VACE workflow.
Before writing, silently review all provided frames as a single clip and infer motion across time; reason stepwise over the entire sequence (start → middle → end). Do not use meta phrases (e.g., "this video shows").
Generate descriptions that adhere to the following structured layers and constraints, formatting each as a SEPARATE PARAGRAPH in this exact order:

1. SUBJECT (First Paragraph)
Begin with a gendered noun phrase (e.g., "A woman…", "A man…").
Include allowed visual traits: hairstyle and its texture or motion (no color or length), makeup, posture, gestures.
Strictly exclude any reference to ethnicity, age, body type, tattoos, glasses, hair color, hair length, eye color, or height.

2. SCENE (Second Paragraph)
Describe the visible environment clearly and vividly.

3. MOVEMENT (Third Paragraph)
In this paragraph, describe body-part–specific movement and how it aligns with musical rhythm and beat structure. Begin with an overall summary: e.g., 'The subject initiates with a hip sway on the downbeat…'. Then narrate movement chronologically, using precise action verbs and transitions like 'then', 'as', and 'after', referencing the timeline (e.g., early/mid/late beat or second). Specify which body parts move, how they articulate (e.g., 'the right arm lifts upward, then sweeps outward; the torso tilts as the knees bend'), describe footwork, weight shifts, and alignment with music beats. Also include any camera movement (e.g., 'camera pans to follow the torso shift'). Avoid general labels—focus on locomotor and non‑locomotor gestures, repetition, rhythm, and choreography phrasing. Always include any buttock or breast movements that you see

4. CINEMATIC AESTHETIC CONTROL (Fourth Paragraph)
Lighting (source/direction/quality/temperature), camera details (shot type, angle/height, movement), and exposure/render cues as applicable. Everything must be in sharp focus with no depth of field effects, bokeh, or blur. Do not mention optics, DOF, rack focus, or any depth-related visual effects.

5. STYLIZATION & TONE (Fifth Paragraph)
Mood/genre descriptors (e.g., "noir-inspired silhouette," "cinematic realism," etc.).

CRITICAL: Output exactly 5 paragraphs, one per category, separated by a blank line. DO NOT describe clothing, accessories, or garments in any paragraph. Never mention prohibited attributes, even if visible. Never mention depth of field, bokeh, blur, optics, DOF, rack focus, or any depth-related visual effects."""
                user_prompt = "Please analyze this video and provide a detailed description following the 5-paragraph structure outlined in the system prompt."
            else:  # "Describe without clothing"
                system_prompt = """You are an expert assistant specialized in analyzing and verbalizing input videos for cinematic-quality video transformation using the Wan 2.2 + VACE workflow.
Before writing, silently review all provided frames as a single clip and infer motion across time; reason stepwise over the entire sequence (start → middle → end). Do not use meta phrases (e.g., "this video shows").
Generate descriptions that adhere to the following structured layers and constraints, formatting each as a SEPARATE PARAGRAPH in this exact order:

1. SUBJECT (First Paragraph)
Begin with a gendered noun phrase (e.g., "A woman…", "A man…").
Include allowed visual traits: hairstyle and its texture or motion (no color or length), makeup, posture, gestures.
Strictly exclude any reference to ethnicity, age, body type, tattoos, glasses, hair color, hair length, eye color, or height.

2. SCENE (Second Paragraph)
Describe the visible environment clearly and vividly.

3. MOVEMENT (Third Paragraph)
In this paragraph, describe body-part–specific movement and how it aligns with musical rhythm and beat structure. Begin with an overall summary: e.g., 'The subject initiates with a hip sway on the downbeat…'. Then narrate movement chronologically, using precise action verbs and transitions like 'then', 'as', and 'after', referencing the timeline (e.g., early/mid/late beat or second). Specify which body parts move, how they articulate (e.g., 'the right arm lifts upward, then sweeps outward; the torso tilts as the knees bend'), describe footwork, weight shifts, and alignment with music beats. Also include any camera movement (e.g., 'camera pans to follow the torso shift'). Avoid general labels—focus on locomotor and non‑locomotor gestures, repetition, rhythm, and choreography phrasing. Always include any buttock or breast movements that you see

4. CINEMATIC AESTHETIC CONTROL (Fourth Paragraph)
Lighting (source/direction/quality/temperature), camera details (shot type, angle/height, movement), optics (lens feel, DOF, rack focus), and exposure/render cues as applicable.

5. STYLIZATION & TONE (Fifth Paragraph)
Mood/genre descriptors (e.g., "noir-inspired silhouette," "cinematic realism," etc.).

CRITICAL: Output exactly 5 paragraphs, one per category, separated by a blank line. DO NOT describe clothing, accessories, or garments in any paragraph. Never mention prohibited attributes, even if visible."""
                user_prompt = "Please analyze this video and provide a detailed description following the 5-paragraph structure outlined in the system prompt."
            video_data = None
            video_info_text = ""
            trimmed_video_output_path = ""  # Track the output path for trimmed video

            # Check if we have an uploaded video file
            if uploaded_video_file and uploaded_video_file.strip():
                # Process uploaded video file
                try:
                    # ComfyUI stores uploaded files in the input directory
                    try:
                        import folder_paths
                        input_dir = folder_paths.get_input_directory()
                    except ImportError:
                        # Fallback if folder_paths is not available
                        input_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "input")

                    video_path = os.path.join(input_dir, uploaded_video_file)

                    if os.path.exists(video_path):
                        # Get original video info using OpenCV
                        cap = cv2.VideoCapture(video_path)
                        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                        fps = cap.get(cv2.CAP_PROP_FPS)
                        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        original_duration = frame_count / fps if fps > 0 else 0
                        cap.release()

                        # Determine the video file to use for analysis
                        final_video_path = video_path
                        actual_duration = original_duration
                        trimmed = False

                        # Calculate duration based on max_duration
                        if max_duration > 0:
                            actual_duration = min(max_duration, original_duration)

                        # Check if we need to trim the video (only duration limit)
                        if max_duration > 0 and actual_duration < original_duration:
                            # Create a temporary trimmed video file
                            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
                                trimmed_video_path = temp_file.name

                            # Attempt to trim the video
                            if self._trim_video(video_path, trimmed_video_path, actual_duration):
                                final_video_path = trimmed_video_path
                                trimmed = True
                                # Store the trimmed video path for output
                                trimmed_video_output_path = trimmed_video_path
                            else:
                                # If trimming fails, use original video but warn user
                                print(f"Warning: Could not trim video. Using original video for {actual_duration:.2f}s")
                                actual_duration = original_duration
                                trimmed_video_output_path = video_path
                        else:
                            # No trimming needed, use original video path
                            trimmed_video_output_path = video_path

                        # Read the final video file (original or trimmed)
                        with open(final_video_path, 'rb') as video_file:
                            video_data = video_file.read()

                        # Note: We do NOT clean up the trimmed video file since we want to output its path

                        file_size = len(video_data) / 1024 / 1024  # Size in MB

                        # Update video info to include trimming details
                        end_time = actual_duration  # Since we start from 0
                        trim_info = f" (trimmed: 0.0s → {end_time:.1f}s)" if trimmed else ""

                        video_info_text = f"""📹 Video Processing Info (Uploaded File):
• File: {os.path.basename(uploaded_video_file)}
• Original Duration: {original_duration:.2f} seconds
• Start Time: 0.0 seconds
• End Time: {end_time:.2f} seconds
• Processed Duration: {actual_duration:.2f} seconds{trim_info}
• Frames: {frame_count}
• Frame Rate: {fps:.2f} FPS
• Resolution: {width}x{height}
• File Size: {file_size:.2f} MB"""

                    else:
                        raise FileNotFoundError(f"Uploaded video file not found: {video_path}")

                except Exception as e:
                    raise RuntimeError(f"Failed to process uploaded video: {str(e)}")

            else:
                raise ValueError("No video input provided. Please upload a video file using the upload button.")

            if video_data is None:
                raise RuntimeError("Failed to process video data")

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

            # Debug: Check response object
            print(f"[DEBUG] Response object: {response}")
            print(f"[DEBUG] Response type: {type(response)}")
            print(f"[DEBUG] Response.text: {response.text}")
            print(f"[DEBUG] Response.text type: {type(response.text)}")

            # Check if response has other useful attributes
            if hasattr(response, 'candidates'):
                print(f"[DEBUG] Response.candidates: {response.candidates}")
            if hasattr(response, 'prompt_feedback'):
                print(f"[DEBUG] Response.prompt_feedback: {response.prompt_feedback}")
            if hasattr(response, '_content'):
                print(f"[DEBUG] Response._content: {response._content}")

            # Format the four separate outputs

            # 1. Description - Clean output from Gemini (for direct use as prompt)
            # Add safety check for None response.text
            if response.text is not None:
                description = response.text.strip()
            else:
                # Provide more detailed error information
                error_msg = "Error: Gemini returned empty response"
                if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                    error_msg += f" (Prompt feedback: {response.prompt_feedback})"
                if hasattr(response, 'candidates') and response.candidates:
                    error_msg += f" (Candidates available: {len(response.candidates)})"
                description = error_msg
                print("[ERROR] Gemini response.text is None")

            # 2. Video Info - Technical details about the processed video
            video_info = video_info_text

            # 3. Gemini Status - API and model information
            gemini_status = f"""🤖 Gemini Analysis Status: ✅ Complete
• Model: {gemini_model}
• API Key: {'*' * (len(gemini_api_key) - 4) + gemini_api_key[-4:] if len(gemini_api_key) >= 4 else '****'}"""

            # 4. Trimmed Video Path - Path to the processed video file
            trimmed_video_path = trimmed_video_output_path

            # 5. Final String - Concatenated prefix and description
            final_string = f"{prefix_text}{description}" if prefix_text else description

            return (description, video_info, gemini_status, trimmed_video_path, final_string)

        except Exception as e:
            # Handle errors gracefully with four separate outputs

            # 1. Description - Error message (still usable as text, though not ideal)
            description = f"Error: Video analysis failed - {str(e)}"

            # 2. Video Info - What we know about the input
            video_info = f"""📹 Video Processing Info:
• Status: ❌ Processing Failed
• Input Type: {'Uploaded File' if uploaded_video_file and uploaded_video_file.strip() else 'None'}
• Frame Rate: {frame_rate} FPS (legacy parameter)
• Max Duration: {max_duration if max_duration > 0 else 'Full Video'} seconds"""

            # 3. Gemini Status - Error details
            gemini_status = f"""🤖 Gemini Analysis Status: ❌ Failed
• Model: {gemini_model}
• API Key: {'*' * (len(gemini_api_key) - 4) + gemini_api_key[-4:] if len(gemini_api_key) >= 4 else '****'}
• Error: {str(e)[:100]}{'...' if len(str(e)) > 100 else ''}

Please check:
1. API key is valid and has quota
2. Video file is uploaded using the upload button
3. Internet connectivity
4. Model supports video analysis"""

            # 4. Trimmed Video Path - Empty on error
            trimmed_video_path = ""

            # 5. Final String - Concatenated prefix and error description
            final_string = f"{prefix_text}{description}" if prefix_text else description

            return (description, video_info, gemini_status, trimmed_video_path, final_string)


class GeminiImageDescribe:
    """
    A ComfyUI custom node for describing single images using Google's Gemini API.
    Takes IMAGE input tensor from ComfyUI nodes and analyzes with Gemini for text-to-image prompt generation.
    """

    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        """
        Return a dictionary which contains config for all input fields.
        Takes standard ComfyUI IMAGE tensor input.
        """
        return {
            "required": {
                "image": ("IMAGE", {
                    "tooltip": "Input image to analyze"
                }),
                "gemini_api_key": ("STRING", {
                    "multiline": False,
                    "default": "AIzaSyBZpbWUwPlNsqQl6al0VEquoEY4pCZsSjM",
                    "tooltip": "Your Gemini API key"
                }),
                "gemini_model": (["models/gemini-2.5-flash", "models/gemini-2.5-flash-lite", "models/gemini-2.5-pro"], {
                    "default": "models/gemini-2.5-flash",
                    "tooltip": "Select the Gemini model to use"
                }),
                "model_type": (["Text2Image", "ImageEdit"], {
                    "default": "Text2Image",
                    "tooltip": "Select the type of model workflow to use"
                }),
                "description_mode": (["Describe without clothing", "Describe with clothing", "Describe without clothing (No bokeh)", "Describe with clothing (No bokeh)"], {
                    "default": "Describe without clothing",
                    "tooltip": "Choose whether to include detailed clothing description and depth of field effects"
                }),
                "prefix_text": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "tooltip": "Text to prepend to the generated description"
                }),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("description", "gemini_status", "final_string")
    FUNCTION = "describe_image"
    CATEGORY = "Gemini"

    def describe_image(self, image, gemini_api_key, gemini_model, model_type, description_mode, prefix_text=""):
        """
        Process image tensor and analyze with Gemini

        Args:
            image: ComfyUI IMAGE tensor (batch_size, height, width, channels)
            gemini_api_key: Your Gemini API key
            gemini_model: Gemini model to use
            model_type: Type of model workflow ("Text2Image" or "ImageEdit")
            description_mode: Mode for description with options for clothing and depth of field
            prefix_text: Text to prepend to the generated description
        """
        try:
            # Set the appropriate system prompt and user prompt based on model_type and description_mode
            if model_type == "Text2Image":
                if description_mode == "Describe with clothing":
                    system_prompt = """Generate a Wan 2.2 optimized text to image prompt. You are an expert assistant specialized in analyzing and verbalizing input media for instagram-quality posts using the Wan 2.2 Text to Image workflow.
Before writing, silently review the provided media. Do not use meta phrases (e.g., "this picture shows").
Generate descriptions that adhere to the following structured layers and constraints, formatting each as a SEPARATE PARAGRAPH in this exact order:

SUBJECT (First Paragraph)
Begin with a gendered noun phrase (e.g., "A woman…", "A man…").
Include allowed visual traits: hairstyle and its texture or motion (no color or length), makeup, posture, gestures.
Strictly exclude any reference to ethnicity, age, body type, tattoos, glasses, hair color, hair length, eye color, or height.

CINEMATIC AESTHETIC CONTROL (Second Paragraph)
Lighting (source/direction/quality/temperature), camera details (shot type, angle/height, movement), optics (lens feel, DOF, rack focus), and exposure/render cues as applicable.

STYLIZATION & TONE (Third Paragraph)
Mood/genre descriptors (e.g., "noir-inspired silhouette," "cinematic realism," etc.).

CLOTHING (Fourth Paragraph)
Describe all visible clothing and accessories. Be granular: specify garment type, color(s), material/texture, fit/silhouette, length, notable construction (seams, straps, waistbands), and condition. Include footwear if visible and note how fabrics respond to motion (stretching, swaying, tightening, wrinkling). Do not describe logos or brand names. Exclude tattoos, glasses, and other prohibited attributes.

CRITICAL: Output exactly 4 paragraphs, one per category, separated by a blank line. Never mention prohibited attributes, even if visible."""
                    user_prompt = "Please analyze this image and provide a detailed description following the 4-paragraph structure outlined in the system prompt."
                elif description_mode == "Describe with clothing (No bokeh)":
                    system_prompt = """Generate a Wan 2.2 optimized text to image prompt. You are an expert assistant specialized in analyzing and verbalizing input media for instagram-quality posts using the Wan 2.2 Text to Image workflow.
Before writing, silently review the provided media. Do not use meta phrases (e.g., "this picture shows").
Generate descriptions that adhere to the following structured layers and constraints, formatting each as a SEPARATE PARAGRAPH in this exact order:

SUBJECT (First Paragraph)
Begin with a gendered noun phrase (e.g., "A woman…", "A man…").
Include allowed visual traits: hairstyle and its texture or motion (no color or length), makeup, posture, gestures.
Strictly exclude any reference to ethnicity, age, body type, tattoos, glasses, hair color, hair length, eye color, or height.

CINEMATIC AESTHETIC CONTROL (Second Paragraph)
Lighting (source/direction/quality/temperature), camera details (shot type, angle/height, movement), and exposure/render cues as applicable. Everything must be in sharp focus with no depth of field effects, bokeh, or blur. Do not mention optics, DOF, rack focus, or any depth-related visual effects.

STYLIZATION & TONE (Third Paragraph)
Mood/genre descriptors (e.g., "noir-inspired silhouette," "cinematic realism," etc.).

CLOTHING (Fourth Paragraph)
Describe all visible clothing and accessories. Be granular: specify garment type, color(s), material/texture, fit/silhouette, length, notable construction (seams, straps, waistbands), and condition. Include footwear if visible and note how fabrics respond to motion (stretching, swaying, tightening, wrinkling). Do not describe logos or brand names. Exclude tattoos, glasses, and other prohibited attributes.

CRITICAL: Output exactly 4 paragraphs, one per category, separated by a blank line. Never mention prohibited attributes, even if visible. Never mention depth of field, bokeh, blur, optics, DOF, rack focus, or any depth-related visual effects."""
                    user_prompt = "Please analyze this image and provide a detailed description following the 4-paragraph structure outlined in the system prompt."
                elif description_mode == "Describe without clothing (No bokeh)":
                    system_prompt = """Generate a Wan 2.2 optimized text to image prompt. You are an expert assistant specialized in analyzing and verbalizing input media for instagram-quality posts using the Wan 2.2 Text to Image workflow.
Before writing, silently review the provided media. Do not use meta phrases (e.g., "this picture shows").
Generate descriptions that adhere to the following structured layers and constraints, formatting each as a SEPARATE PARAGRAPH in this exact order:

SUBJECT (First Paragraph)
Begin with a gendered noun phrase (e.g., "A woman…", "A man…").
Include allowed visual traits: hairstyle and its texture or motion (no color or length), makeup, posture, gestures.
Strictly exclude any reference to ethnicity, age, body type, tattoos, glasses, hair color, hair length, eye color, or height.

CINEMATIC AESTHETIC CONTROL (Second Paragraph)
Lighting (source/direction/quality/temperature), camera details (shot type, angle/height, movement), and exposure/render cues as applicable. Everything must be in sharp focus with no depth of field effects, bokeh, or blur. Do not mention optics, DOF, rack focus, or any depth-related visual effects.

STYLIZATION & TONE (Third Paragraph)
Mood/genre descriptors (e.g., "noir-inspired silhouette," "cinematic realism," etc.).

CRITICAL: Output exactly 3 paragraphs, one per category, separated by a blank line. DO NOT describe clothing, accessories, or garments in any paragraph. Never mention prohibited attributes, even if visible. Never mention depth of field, bokeh, blur, optics, DOF, rack focus, or any depth-related visual effects."""
                    user_prompt = "Please analyze this image and provide a detailed description following the 3-paragraph structure outlined in the system prompt."
                else:  # "Describe without clothing"
                    system_prompt = """Generate a Wan 2.2 optimized text to image prompt. You are an expert assistant specialized in analyzing and verbalizing input media for instagram-quality posts using the Wan 2.2 Text to Image workflow.
Before writing, silently review the provided media. Do not use meta phrases (e.g., "this picture shows").
Generate descriptions that adhere to the following structured layers and constraints, formatting each as a SEPARATE PARAGRAPH in this exact order:

SUBJECT (First Paragraph)
Begin with a gendered noun phrase (e.g., "A woman…", "A man…").
Include allowed visual traits: hairstyle and its texture or motion (no color or length), makeup, posture, gestures.
Strictly exclude any reference to ethnicity, age, body type, tattoos, glasses, hair color, hair length, eye color, or height.

CINEMATIC AESTHETIC CONTROL (Second Paragraph)
Lighting (source/direction/quality/temperature), camera details (shot type, angle/height, movement), optics (lens feel, DOF, rack focus), and exposure/render cues as applicable.

STYLIZATION & TONE (Third Paragraph)
Mood/genre descriptors (e.g., "noir-inspired silhouette," "cinematic realism," etc.).

CRITICAL: Output exactly 3 paragraphs, one per category, separated by a blank line. DO NOT describe clothing, accessories, or garments in any paragraph. Never mention prohibited attributes, even if visible."""
                    user_prompt = "Please analyze this image and provide a detailed description following the 3-paragraph structure outlined in the system prompt."
            else:  # model_type == "ImageEdit"
                if description_mode == "Describe with clothing":
                    # ImageEdit with clothing prompt
                    system_prompt = """You are an expert assistant generating concise, single-sentence Qwen-Image-Edit instructions; always begin with "Make this person…", include vivid, focused scene details (e.g. bedroom props, lights, furniture or gym bench, textured wall, window views) early to anchor the setting, specify deep focus ("f/11 for deep focus—no bokeh or blur"), describe allowed traits like pose, posture, and outfit style (without age, ethnicity, tattoos, hair color, etc.), include clear torso and head orientation (e.g., "back facing the camera with torso turned 45° and head looking over her shoulder toward viewer"), reference cinematic aesthetic cues (lighting, framing, lens, shot type), anchor realism by stating skin shows subtle pores, light wrinkles, and realistic surface detail, end with "keep everything else unchanged," and include negative safeguards like "no distortion, no blur artifacts.\""""
                    user_prompt = "Please analyze this image and generate a single-sentence Qwen-Image-Edit instruction following the guidelines in the system prompt."
                elif description_mode == "Describe with clothing (No bokeh)":
                    # ImageEdit with clothing (No bokeh) prompt
                    system_prompt = """You are an expert assistant generating concise, single-sentence Qwen-Image-Edit instructions; always begin with "Make this person…", include vivid, focused scene details (e.g. bedroom props, lights, furniture or gym bench, textured wall, window views) early to anchor the setting, specify everything is in sharp focus with no depth of field effects, describe allowed traits like pose, posture, and outfit style (without age, ethnicity, tattoos, hair color, etc.), include clear torso and head orientation (e.g., "back facing the camera with torso turned 45° and head looking over her shoulder toward viewer"), reference cinematic aesthetic cues (lighting, framing, lens, shot type), anchor realism by stating skin shows subtle pores, light wrinkles, and realistic surface detail, end with "keep everything else unchanged," and include negative safeguards like "no distortion, no blur artifacts, no depth of field, no bokeh.\""""
                    user_prompt = "Please analyze this image and generate a single-sentence Qwen-Image-Edit instruction following the guidelines in the system prompt."
                elif description_mode == "Describe without clothing (No bokeh)":
                    # ImageEdit without clothing (No bokeh) prompt
                    system_prompt = """You are an expert assistant generating concise, single-sentence Qwen-Image-Edit instructions; always begin with "Make this person…", include vivid, focused scene details (e.g. bedroom props, lights, furniture or gym bench, textured wall, window views) early to anchor the setting, specify everything is in sharp focus with no depth of field effects, describe allowed traits like pose and posture only (avoid clothing, age, ethnicity, tattoos, hair color, etc.), include clear torso and head orientation (e.g., "back facing the camera with torso turned 45° and head looking over her shoulder toward viewer"), reference cinematic aesthetic cues (lighting, framing, lens, shot type), anchor realism by stating skin shows subtle pores, light wrinkles, and realistic surface detail, end with "keep everything else unchanged," and include negative safeguards like "no distortion, no blur artifacts, no depth of field, no bokeh.\""""
                    user_prompt = "Please analyze this image and generate a single-sentence Qwen-Image-Edit instruction following the guidelines in the system prompt."
                else:  # "Describe without clothing"
                    # ImageEdit without clothing prompt
                    system_prompt = """You are an expert assistant generating concise, single-sentence Qwen-Image-Edit instructions; always begin with "Make this person…", include vivid, focused scene details (e.g. bedroom props, lights, furniture or gym bench, textured wall, window views) early to anchor the setting, specify deep focus ("f/11 for deep focus—no bokeh or blur"), describe allowed traits like pose and posture only (avoid clothing, age, ethnicity, tattoos, hair color, etc.), include clear torso and head orientation (e.g., "back facing the camera with torso turned 45° and head looking over her shoulder toward viewer"), reference cinematic aesthetic cues (lighting, framing, lens, shot type), anchor realism by stating skin shows subtle pores, light wrinkles, and realistic surface detail, end with "keep everything else unchanged," and include negative safeguards like "no distortion, no blur artifacts.\""""
                    user_prompt = "Please analyze this image and generate a single-sentence Qwen-Image-Edit instruction following the guidelines in the system prompt."
            # Convert ComfyUI IMAGE tensor to image data
            # ComfyUI images are typically in format (batch_size, height, width, channels) with values 0-1

            # Convert PyTorch tensor to numpy array
            if hasattr(image, 'cpu'):
                # PyTorch tensor - convert to numpy
                image_np = image.cpu().numpy()
            else:
                # Already numpy array
                image_np = image

            # Take the first image from the batch if multiple images
            if len(image_np.shape) == 4:
                image_array = image_np[0]  # Take first image from batch
            else:
                image_array = image_np

            # Convert from 0-1 float to 0-255 uint8
            if image_array.dtype == np.float32 or image_array.dtype == np.float64:
                image_array = (image_array * 255).astype(np.uint8)

            # Convert numpy array to PIL Image
            if len(image_array.shape) == 3 and image_array.shape[2] == 3:
                # RGB image
                pil_image = Image.fromarray(image_array, 'RGB')
            elif len(image_array.shape) == 3 and image_array.shape[2] == 4:
                # RGBA image
                pil_image = Image.fromarray(image_array, 'RGBA')
            else:
                # Grayscale or other format, convert to RGB
                pil_image = Image.fromarray(image_array).convert('RGB')

            # Convert PIL image to bytes
            img_byte_arr = io.BytesIO()
            pil_image.save(img_byte_arr, format='JPEG')
            image_data = img_byte_arr.getvalue()

            # Initialize the Gemini client
            client = genai.Client(api_key=gemini_api_key)

            # Create the content structure for image analysis
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_bytes(
                            mime_type="image/jpeg",
                            data=image_data,
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

            # Generate the image description
            response = client.models.generate_content(
                model=gemini_model,
                contents=contents,
                config=generate_content_config,
            )

            # Debug: Check response object
            print(f"[DEBUG] Response object: {response}")
            print(f"[DEBUG] Response type: {type(response)}")
            print(f"[DEBUG] Response.text: {response.text}")
            print(f"[DEBUG] Response.text type: {type(response.text)}")

            # Check if response has other useful attributes
            if hasattr(response, 'candidates'):
                print(f"[DEBUG] Response.candidates: {response.candidates}")
            if hasattr(response, 'prompt_feedback'):
                print(f"[DEBUG] Response.prompt_feedback: {response.prompt_feedback}")
            if hasattr(response, '_content'):
                print(f"[DEBUG] Response._content: {response._content}")

            # Format the three outputs

            # 1. Description - Clean output from Gemini (for direct use as prompt)
            # Add safety check for None response.text
            if response.text is not None:
                description = response.text.strip()
            else:
                # Provide more detailed error information
                error_msg = "Error: Gemini returned empty response"
                if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                    error_msg += f" (Prompt feedback: {response.prompt_feedback})"
                if hasattr(response, 'candidates') and response.candidates:
                    error_msg += f" (Candidates available: {len(response.candidates)})"
                description = error_msg
                print("[ERROR] Gemini response.text is None")

            # 2. Gemini Status - API and model information
            gemini_status = f"""🤖 Gemini Analysis Status: ✅ Complete
• Model: {gemini_model}
• Model Type: {model_type}
• API Key: {'*' * (len(gemini_api_key) - 4) + gemini_api_key[-4:] if len(gemini_api_key) >= 4 else '****'}
• Input: Single Image ({pil_image.size[0]}x{pil_image.size[1]})"""

            # 3. Final String - Concatenated prefix and description
            final_string = f"{prefix_text}{description}" if prefix_text else description

            return (description, gemini_status, final_string)

        except Exception as e:
            # Handle errors gracefully with three outputs

            # 1. Description - Error message (still usable as text, though not ideal)
            description = f"Error: Image analysis failed - {str(e)}"

            # 2. Gemini Status - Error details
            gemini_status = f"""🤖 Gemini Analysis Status: ❌ Failed
• Model: {gemini_model}
• Model Type: {model_type}
• API Key: {'*' * (len(gemini_api_key) - 4) + gemini_api_key[-4:] if len(gemini_api_key) >= 4 else '****'}
• Error: {str(e)[:100]}{'...' if len(str(e)) > 100 else ''}

Please check:
1. API key is valid and has quota
2. Image input is connected properly
3. Internet connectivity
4. Model supports image analysis"""

            # 3. Final String - Concatenated prefix and error description
            final_string = f"{prefix_text}{description}" if prefix_text else description

            return (description, gemini_status, final_string)


class GeminiMediaDescribe:
    """
    A ComfyUI custom node for describing images or videos using Google's Gemini API.
    Supports both uploaded media and random selection from a directory path.
    """

    def __init__(self):
        pass

    def _trim_video(self, input_path, output_path, duration):
        """
        Trim video to specified duration from the beginning using ffmpeg

        Args:
            input_path: Path to input video file
            output_path: Path to output trimmed video file
            duration: Duration in seconds from the beginning
        """

        try:
            # Use ffmpeg to trim the video from the beginning
            cmd = [
                'ffmpeg',
                '-i', input_path,
                '-t', str(duration),     # Duration from start
                '-c', 'copy',  # Copy streams without re-encoding for speed
                '-avoid_negative_ts', 'make_zero',
                '-y',  # Overwrite output file if it exists
                output_path
            ]

            subprocess.run(cmd, capture_output=True, text=True, check=True)
            return True

        except subprocess.CalledProcessError as e:
            print(f"FFmpeg error: {e.stderr}")
            # Fallback: try with re-encoding if copy fails
            try:
                cmd = [
                    'ffmpeg',
                    '-i', input_path,
                    '-t', str(duration),
                    '-c:v', 'libx264',
                    '-c:a', 'aac',
                    '-y',
                    output_path
                ]
                subprocess.run(cmd, capture_output=True, text=True, check=True)
                return True
            except subprocess.CalledProcessError as e2:
                print(f"FFmpeg re-encoding also failed: {e2.stderr}")
                return False
        except FileNotFoundError:
            print("FFmpeg not found. Please install ffmpeg to use duration trimming.")
            return False

    def _process_image(self, gemini_api_key, gemini_model, model_type, description_mode, prefix_text, image, selected_media_path, media_info_text):
        """
        Process image using logic from GeminiImageDescribe
        """
        try:
            # Set the appropriate system prompt and user prompt based on model_type and description_mode
            if model_type == "Text2Image":
                if description_mode == "Describe with clothing":
                    system_prompt = """Generate a Wan 2.2 optimized text to image prompt. You are an expert assistant specialized in analyzing and verbalizing input media for instagram-quality posts using the Wan 2.2 Text to Image workflow.
Before writing, silently review the provided media. Do not use meta phrases (e.g., "this picture shows").
Generate descriptions that adhere to the following structured layers and constraints, formatting each as a SEPARATE PARAGRAPH in this exact order:

SUBJECT (First Paragraph)
Begin with a gendered noun phrase (e.g., "A woman…", "A man…").
Include allowed visual traits: hairstyle and its texture or motion (no color or length), makeup, posture, gestures.
Strictly exclude any reference to ethnicity, age, body type, tattoos, glasses, hair color, hair length, eye color, or height.

CINEMATIC AESTHETIC CONTROL (Second Paragraph)
Lighting (source/direction/quality/temperature), camera details (shot type, angle/height, movement), optics (lens feel, DOF, rack focus), and exposure/render cues as applicable.

STYLIZATION & TONE (Third Paragraph)
Mood/genre descriptors (e.g., "noir-inspired silhouette," "cinematic realism," etc.).

CLOTHING (Fourth Paragraph)
Describe all visible clothing and accessories. Be granular: specify garment type, color(s), material/texture, fit/silhouette, length, notable construction (seams, straps, waistbands), and condition. Include footwear if visible and note how fabrics respond to motion (stretching, swaying, tightening, wrinkling). Do not describe logos or brand names. Exclude tattoos, glasses, and other prohibited attributes.

CRITICAL: Output exactly 4 paragraphs, one per category, separated by a blank line. Never mention prohibited attributes, even if visible."""
                    user_prompt = "Please analyze this image and provide a detailed description following the 4-paragraph structure outlined in the system prompt."
                elif description_mode == "Describe with clothing (No bokeh)":
                    system_prompt = """Generate a Wan 2.2 optimized text to image prompt. You are an expert assistant specialized in analyzing and verbalizing input media for instagram-quality posts using the Wan 2.2 Text to Image workflow.
Before writing, silently review the provided media. Do not use meta phrases (e.g., "this picture shows").
Generate descriptions that adhere to the following structured layers and constraints, formatting each as a SEPARATE PARAGRAPH in this exact order:

SUBJECT (First Paragraph)
Begin with a gendered noun phrase (e.g., "A woman…", "A man…").
Include allowed visual traits: hairstyle and its texture or motion (no color or length), makeup, posture, gestures.
Strictly exclude any reference to ethnicity, age, body type, tattoos, glasses, hair color, hair length, eye color, or height.

CINEMATIC AESTHETIC CONTROL (Second Paragraph)
Lighting (source/direction/quality/temperature), camera details (shot type, angle/height, movement), and exposure/render cues as applicable. Everything must be in sharp focus with no depth of field effects, bokeh, or blur. Do not mention optics, DOF, rack focus, or any depth-related visual effects.

STYLIZATION & TONE (Third Paragraph)
Mood/genre descriptors (e.g., "noir-inspired silhouette," "cinematic realism," etc.).

CLOTHING (Fourth Paragraph)
Describe all visible clothing and accessories. Be granular: specify garment type, color(s), material/texture, fit/silhouette, length, notable construction (seams, straps, waistbands), and condition. Include footwear if visible and note how fabrics respond to motion (stretching, swaying, tightening, wrinkling). Do not describe logos or brand names. Exclude tattoos, glasses, and other prohibited attributes.

CRITICAL: Output exactly 4 paragraphs, one per category, separated by a blank line. Never mention prohibited attributes, even if visible. Never mention depth of field, bokeh, blur, optics, DOF, rack focus, or any depth-related visual effects."""
                    user_prompt = "Please analyze this image and provide a detailed description following the 4-paragraph structure outlined in the system prompt."
                elif description_mode == "Describe without clothing (No bokeh)":
                    system_prompt = """Generate a Wan 2.2 optimized text to image prompt. You are an expert assistant specialized in analyzing and verbalizing input media for instagram-quality posts using the Wan 2.2 Text to Image workflow.
Before writing, silently review the provided media. Do not use meta phrases (e.g., "this picture shows").
Generate descriptions that adhere to the following structured layers and constraints, formatting each as a SEPARATE PARAGRAPH in this exact order:

SUBJECT (First Paragraph)
Begin with a gendered noun phrase (e.g., "A woman…", "A man…").
Include allowed visual traits: hairstyle and its texture or motion (no color or length), makeup, posture, gestures.
Strictly exclude any reference to ethnicity, age, body type, tattoos, glasses, hair color, hair length, eye color, or height.

CINEMATIC AESTHETIC CONTROL (Second Paragraph)
Lighting (source/direction/quality/temperature), camera details (shot type, angle/height, movement), and exposure/render cues as applicable. Everything must be in sharp focus with no depth of field effects, bokeh, or blur. Do not mention optics, DOF, rack focus, or any depth-related visual effects.

STYLIZATION & TONE (Third Paragraph)
Mood/genre descriptors (e.g., "noir-inspired silhouette," "cinematic realism," etc.).

CRITICAL: Output exactly 3 paragraphs, one per category, separated by a blank line. DO NOT describe clothing, accessories, or garments in any paragraph. Never mention prohibited attributes, even if visible. Never mention depth of field, bokeh, blur, optics, DOF, rack focus, or any depth-related visual effects."""
                    user_prompt = "Please analyze this image and provide a detailed description following the 3-paragraph structure outlined in the system prompt."
                else:  # "Describe without clothing"
                    system_prompt = """Generate a Wan 2.2 optimized text to image prompt. You are an expert assistant specialized in analyzing and verbalizing input media for instagram-quality posts using the Wan 2.2 Text to Image workflow.
Before writing, silently review the provided media. Do not use meta phrases (e.g., "this picture shows").
Generate descriptions that adhere to the following structured layers and constraints, formatting each as a SEPARATE PARAGRAPH in this exact order:

SUBJECT (First Paragraph)
Begin with a gendered noun phrase (e.g., "A woman…", "A man…").
Include allowed visual traits: hairstyle and its texture or motion (no color or length), makeup, posture, gestures.
Strictly exclude any reference to ethnicity, age, body type, tattoos, glasses, hair color, hair length, eye color, or height.

CINEMATIC AESTHETIC CONTROL (Second Paragraph)
Lighting (source/direction/quality/temperature), camera details (shot type, angle/height, movement), optics (lens feel, DOF, rack focus), and exposure/render cues as applicable.

STYLIZATION & TONE (Third Paragraph)
Mood/genre descriptors (e.g., "noir-inspired silhouette," "cinematic realism," etc.).

CRITICAL: Output exactly 3 paragraphs, one per category, separated by a blank line. DO NOT describe clothing, accessories, or garments in any paragraph. Never mention prohibited attributes, even if visible."""
                    user_prompt = "Please analyze this image and provide a detailed description following the 3-paragraph structure outlined in the system prompt."
            else:  # model_type == "ImageEdit"
                if description_mode == "Describe with clothing":
                    system_prompt = """You are an expert assistant generating concise, single-sentence Qwen-Image-Edit instructions; always begin with "Make this person…", include vivid, focused scene details (e.g. bedroom props, lights, furniture or gym bench, textured wall, window views) early to anchor the setting, specify deep focus ("f/11 for deep focus—no bokeh or blur"), describe allowed traits like pose, posture, and outfit style (without age, ethnicity, tattoos, hair color, etc.), include clear torso and head orientation (e.g., "back facing the camera with torso turned 45° and head looking over her shoulder toward viewer"), reference cinematic aesthetic cues (lighting, framing, lens, shot type), anchor realism by stating skin shows subtle pores, light wrinkles, and realistic surface detail, end with "keep everything else unchanged," and include negative safeguards like "no distortion, no blur artifacts.\""""
                    user_prompt = "Please analyze this image and generate a single-sentence Qwen-Image-Edit instruction following the guidelines in the system prompt."
                elif description_mode == "Describe with clothing (No bokeh)":
                    system_prompt = """You are an expert assistant generating concise, single-sentence Qwen-Image-Edit instructions; always begin with "Make this person…", include vivid, focused scene details (e.g. bedroom props, lights, furniture or gym bench, textured wall, window views) early to anchor the setting, specify everything is in sharp focus with no depth of field effects, describe allowed traits like pose, posture, and outfit style (without age, ethnicity, tattoos, hair color, etc.), include clear torso and head orientation (e.g., "back facing the camera with torso turned 45° and head looking over her shoulder toward viewer"), reference cinematic aesthetic cues (lighting, framing, lens, shot type), anchor realism by stating skin shows subtle pores, light wrinkles, and realistic surface detail, end with "keep everything else unchanged," and include negative safeguards like "no distortion, no blur artifacts, no depth of field, no bokeh.\""""
                    user_prompt = "Please analyze this image and generate a single-sentence Qwen-Image-Edit instruction following the guidelines in the system prompt."
                elif description_mode == "Describe without clothing (No bokeh)":
                    system_prompt = """You are an expert assistant generating concise, single-sentence Qwen-Image-Edit instructions; always begin with "Make this person…", include vivid, focused scene details (e.g. bedroom props, lights, furniture or gym bench, textured wall, window views) early to anchor the setting, specify everything is in sharp focus with no depth of field effects, describe allowed traits like pose and posture only (avoid clothing, age, ethnicity, tattoos, hair color, etc.), include clear torso and head orientation (e.g., "back facing the camera with torso turned 45° and head looking over her shoulder toward viewer"), reference cinematic aesthetic cues (lighting, framing, lens, shot type), anchor realism by stating skin shows subtle pores, light wrinkles, and realistic surface detail, end with "keep everything else unchanged," and include negative safeguards like "no distortion, no blur artifacts, no depth of field, no bokeh.\""""
                    user_prompt = "Please analyze this image and generate a single-sentence Qwen-Image-Edit instruction following the guidelines in the system prompt."
                else:  # "Describe without clothing"
                    system_prompt = """You are an expert assistant generating concise, single-sentence Qwen-Image-Edit instructions; always begin with "Make this person…", include vivid, focused scene details (e.g. bedroom props, lights, furniture or gym bench, textured wall, window views) early to anchor the setting, specify deep focus ("f/11 for deep focus—no bokeh or blur"), describe allowed traits like pose and posture only (avoid clothing, age, ethnicity, tattoos, hair color, etc.), include clear torso and head orientation (e.g., "back facing the camera with torso turned 45° and head looking over her shoulder toward viewer"), reference cinematic aesthetic cues (lighting, framing, lens, shot type), anchor realism by stating skin shows subtle pores, light wrinkles, and realistic surface detail, end with "keep everything else unchanged," and include negative safeguards like "no distortion, no blur artifacts.\""""
                    user_prompt = "Please analyze this image and generate a single-sentence Qwen-Image-Edit instruction following the guidelines in the system prompt."

            # Convert image to bytes for Gemini
            if image is not None:
                # Convert ComfyUI IMAGE tensor to image data
                if hasattr(image, 'cpu'):
                    image_np = image.cpu().numpy()
                else:
                    image_np = image

                # Take the first image from the batch if multiple images
                if len(image_np.shape) == 4:
                    image_array = image_np[0]
                else:
                    image_array = image_np

                # Convert from 0-1 float to 0-255 uint8
                if image_array.dtype == np.float32 or image_array.dtype == np.float64:
                    image_array = (image_array * 255).astype(np.uint8)

                # Convert numpy array to PIL Image
                if len(image_array.shape) == 3 and image_array.shape[2] == 3:
                    pil_image = Image.fromarray(image_array, 'RGB')
                elif len(image_array.shape) == 3 and image_array.shape[2] == 4:
                    pil_image = Image.fromarray(image_array, 'RGBA')
                else:
                    pil_image = Image.fromarray(image_array).convert('RGB')

                # Convert PIL image to bytes
                img_byte_arr = io.BytesIO()
                pil_image.save(img_byte_arr, format='JPEG')
                image_data = img_byte_arr.getvalue()

                # Update media info
                media_info_text += f"\n• Resolution: {pil_image.size[0]}x{pil_image.size[1]}"
            elif selected_media_path:
                # Read image from file path
                pil_image = Image.open(selected_media_path)
                if pil_image.mode != 'RGB':
                    pil_image = pil_image.convert('RGB')

                # Convert PIL image to bytes
                img_byte_arr = io.BytesIO()
                pil_image.save(img_byte_arr, format='JPEG')
                image_data = img_byte_arr.getvalue()

                # Update media info
                file_size = os.path.getsize(selected_media_path) / 1024 / 1024  # Size in MB
                media_info_text += f"\n• Resolution: {pil_image.size[0]}x{pil_image.size[1]}\n• File Size: {file_size:.2f} MB"
            else:
                raise ValueError("No image data available for processing")

            # Initialize the Gemini client
            client = genai.Client(api_key=gemini_api_key)

            # Create the content structure for image analysis
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_bytes(
                            mime_type="image/jpeg",
                            data=image_data,
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

            # Generate the image description
            response = client.models.generate_content(
                model=gemini_model,
                contents=contents,
                config=generate_content_config,
            )

            # Process response
            if response.text is not None:
                description = response.text.strip()
            else:
                error_msg = "Error: Gemini returned empty response"
                if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                    error_msg += f" (Prompt feedback: {response.prompt_feedback})"
                if hasattr(response, 'candidates') and response.candidates:
                    error_msg += f" (Candidates available: {len(response.candidates)})"
                description = error_msg

            # Format outputs for image processing
            gemini_status = f"""🤖 Gemini Analysis Status: ✅ Complete
• Model: {gemini_model}
• Model Type: {model_type}
• API Key: {'*' * (len(gemini_api_key) - 4) + gemini_api_key[-4:] if len(gemini_api_key) >= 4 else '****'}
• Input: Image"""

            processed_media_path = selected_media_path if selected_media_path else ""
            final_string = f"{prefix_text}{description}" if prefix_text else description

            return (description, media_info_text, gemini_status, processed_media_path, final_string)

        except Exception as e:
            description = f"Error: Image analysis failed - {str(e)}"
            gemini_status = f"""🤖 Gemini Analysis Status: ❌ Failed
• Model: {gemini_model}
• Model Type: {model_type}
• API Key: {'*' * (len(gemini_api_key) - 4) + gemini_api_key[-4:] if len(gemini_api_key) >= 4 else '****'}
• Error: {str(e)[:100]}{'...' if len(str(e)) > 100 else ''}

Please check:
1. API key is valid and has quota
2. Image input is connected properly
3. Internet connectivity
4. Model supports image analysis"""
            processed_media_path = ""
            final_string = f"{prefix_text}{description}" if prefix_text else description
            return (description, media_info_text, gemini_status, processed_media_path, final_string)

    def _process_video(self, gemini_api_key, gemini_model, description_mode, prefix_text, selected_media_path, frame_rate, max_duration, media_info_text):
        """
        Process video using logic from GeminiVideoDescribe
        """
        try:
            # Set the appropriate system prompt and user prompt based on description_mode
            if description_mode == "Describe with clothing":
                system_prompt = """You are an expert assistant specialized in analyzing and verbalizing input videos for cinematic-quality video transformation using the Wan 2.2 + VACE workflow.
Before writing, silently review all provided frames as a single clip and infer motion across time; reason stepwise over the entire sequence (start → middle → end). Do not use meta phrases (e.g., "this video shows").
Generate descriptions that adhere to the following structured layers and constraints, formatting each as a SEPARATE PARAGRAPH in this exact order:

1. SUBJECT (First Paragraph)
Begin with a gendered noun phrase (e.g., "A woman…", "A man…").
Include allowed visual traits: hairstyle and its texture or motion (no color or length), makeup, posture, gestures.
Strictly exclude any reference to ethnicity, age, body type, tattoos, glasses, hair color, hair length, eye color, or height.

2. CLOTHING (Second Paragraph)
Describe all visible clothing and accessories. Be granular: specify garment type, color(s), material/texture, fit/silhouette, length, notable construction (seams, straps, waistbands), and condition. Include footwear if visible and note how fabrics respond to motion (stretching, swaying, tightening, wrinkling). Do not describe logos or brand names. Exclude tattoos, glasses, and other prohibited attributes.

3. SCENE (Third Paragraph)
Describe the visible environment clearly and vividly.

4. MOVEMENT (Fourth Paragraph)
In this paragraph, describe body-part–specific movement and how it aligns with musical rhythm and beat structure. Begin with an overall summary: e.g., 'The subject initiates with a hip sway on the downbeat…'. Then narrate movement chronologically, using precise action verbs and transitions like 'then', 'as', and 'after', referencing the timeline (e.g., early/mid/late beat or second). Specify which body parts move, how they articulate (e.g., 'the right arm lifts upward, then sweeps outward; the torso tilts as the knees bend'), describe footwork, weight shifts, and alignment with music beats. Also include any camera movement (e.g., 'camera pans to follow the torso shift'). Avoid general labels—focus on locomotor and non‑locomotor gestures, repetition, rhythm, and choreography phrasing. Always include any buttock or breast movements that you see

5. CINEMATIC AESTHETIC CONTROL (Fifth Paragraph)
Lighting (source/direction/quality/temperature), camera details (shot type, angle/height, movement), optics (lens feel, DOF, rack focus), and exposure/render cues as applicable.

6. STYLIZATION & TONE (Sixth Paragraph)
Mood/genre descriptors (e.g., "noir-inspired silhouette," "cinematic realism," etc.).

CRITICAL: Output exactly 6 paragraphs, one per category, separated by a blank line. Never mention prohibited attributes, even if visible."""
                user_prompt = "Please analyze this video and provide a detailed description following the 6-paragraph structure outlined in the system prompt."
            elif description_mode == "Describe with clothing (No bokeh)":
                system_prompt = """You are an expert assistant specialized in analyzing and verbalizing input videos for cinematic-quality video transformation using the Wan 2.2 + VACE workflow.
Before writing, silently review all provided frames as a single clip and infer motion across time; reason stepwise over the entire sequence (start → middle → end). Do not use meta phrases (e.g., "this video shows").
Generate descriptions that adhere to the following structured layers and constraints, formatting each as a SEPARATE PARAGRAPH in this exact order:

1. SUBJECT (First Paragraph)
Begin with a gendered noun phrase (e.g., "A woman…", "A man…").
Include allowed visual traits: hairstyle and its texture or motion (no color or length), makeup, posture, gestures.
Strictly exclude any reference to ethnicity, age, body type, tattoos, glasses, hair color, hair length, eye color, or height.

2. CLOTHING (Second Paragraph)
Describe all visible clothing and accessories. Be granular: specify garment type, color(s), material/texture, fit/silhouette, length, notable construction (seams, straps, waistbands), and condition. Include footwear if visible and note how fabrics respond to motion (stretching, swaying, tightening, wrinkling). Do not describe logos or brand names. Exclude tattoos, glasses, and other prohibited attributes.

3. SCENE (Third Paragraph)
Describe the visible environment clearly and vividly.

4. MOVEMENT (Fourth Paragraph)
In this paragraph, describe body-part–specific movement and how it aligns with musical rhythm and beat structure. Begin with an overall summary: e.g., 'The subject initiates with a hip sway on the downbeat…'. Then narrate movement chronologically, using precise action verbs and transitions like 'then', 'as', and 'after', referencing the timeline (e.g., early/mid/late beat or second). Specify which body parts move, how they articulate (e.g., 'the right arm lifts upward, then sweeps outward; the torso tilts as the knees bend'), describe footwork, weight shifts, and alignment with music beats. Also include any camera movement (e.g., 'camera pans to follow the torso shift'). Avoid general labels—focus on locomotor and non‑locomotor gestures, repetition, rhythm, and choreography phrasing. Always include any buttock or breast movements that you see

5. CINEMATIC AESTHETIC CONTROL (Fifth Paragraph)
Lighting (source/direction/quality/temperature), camera details (shot type, angle/height, movement), and exposure/render cues as applicable. Everything must be in sharp focus with no depth of field effects, bokeh, or blur. Do not mention optics, DOF, rack focus, or any depth-related visual effects.

6. STYLIZATION & TONE (Sixth Paragraph)
Mood/genre descriptors (e.g., "noir-inspired silhouette," "cinematic realism," etc.).

CRITICAL: Output exactly 6 paragraphs, one per category, separated by a blank line. Never mention prohibited attributes, even if visible. Never mention depth of field, bokeh, blur, optics, DOF, rack focus, or any depth-related visual effects."""
                user_prompt = "Please analyze this video and provide a detailed description following the 6-paragraph structure outlined in the system prompt."
            elif description_mode == "Describe without clothing (No bokeh)":
                system_prompt = """You are an expert assistant specialized in analyzing and verbalizing input videos for cinematic-quality video transformation using the Wan 2.2 + VACE workflow.
Before writing, silently review all provided frames as a single clip and infer motion across time; reason stepwise over the entire sequence (start → middle → end). Do not use meta phrases (e.g., "this video shows").
Generate descriptions that adhere to the following structured layers and constraints, formatting each as a SEPARATE PARAGRAPH in this exact order:

1. SUBJECT (First Paragraph)
Begin with a gendered noun phrase (e.g., "A woman…", "A man…").
Include allowed visual traits: hairstyle and its texture or motion (no color or length), makeup, posture, gestures.
Strictly exclude any reference to ethnicity, age, body type, tattoos, glasses, hair color, hair length, eye color, or height.

2. SCENE (Second Paragraph)
Describe the visible environment clearly and vividly.

3. MOVEMENT (Third Paragraph)
In this paragraph, describe body-part–specific movement and how it aligns with musical rhythm and beat structure. Begin with an overall summary: e.g., 'The subject initiates with a hip sway on the downbeat…'. Then narrate movement chronologically, using precise action verbs and transitions like 'then', 'as', and 'after', referencing the timeline (e.g., early/mid/late beat or second). Specify which body parts move, how they articulate (e.g., 'the right arm lifts upward, then sweeps outward; the torso tilts as the knees bend'), describe footwork, weight shifts, and alignment with music beats. Also include any camera movement (e.g., 'camera pans to follow the torso shift'). Avoid general labels—focus on locomotor and non‑locomotor gestures, repetition, rhythm, and choreography phrasing. Always include any buttock or breast movements that you see

4. CINEMATIC AESTHETIC CONTROL (Fourth Paragraph)
Lighting (source/direction/quality/temperature), camera details (shot type, angle/height, movement), and exposure/render cues as applicable. Everything must be in sharp focus with no depth of field effects, bokeh, or blur. Do not mention optics, DOF, rack focus, or any depth-related visual effects.

5. STYLIZATION & TONE (Fifth Paragraph)
Mood/genre descriptors (e.g., "noir-inspired silhouette," "cinematic realism," etc.).

CRITICAL: Output exactly 5 paragraphs, one per category, separated by a blank line. DO NOT describe clothing, accessories, or garments in any paragraph. Never mention prohibited attributes, even if visible. Never mention depth of field, bokeh, blur, optics, DOF, rack focus, or any depth-related visual effects."""
                user_prompt = "Please analyze this video and provide a detailed description following the 5-paragraph structure outlined in the system prompt."
            else:  # "Describe without clothing"
                system_prompt = """You are an expert assistant specialized in analyzing and verbalizing input videos for cinematic-quality video transformation using the Wan 2.2 + VACE workflow.
Before writing, silently review all provided frames as a single clip and infer motion across time; reason stepwise over the entire sequence (start → middle → end). Do not use meta phrases (e.g., "this video shows").
Generate descriptions that adhere to the following structured layers and constraints, formatting each as a SEPARATE PARAGRAPH in this exact order:

1. SUBJECT (First Paragraph)
Begin with a gendered noun phrase (e.g., "A woman…", "A man…").
Include allowed visual traits: hairstyle and its texture or motion (no color or length), makeup, posture, gestures.
Strictly exclude any reference to ethnicity, age, body type, tattoos, glasses, hair color, hair length, eye color, or height.

2. SCENE (Second Paragraph)
Describe the visible environment clearly and vividly.

3. MOVEMENT (Third Paragraph)
In this paragraph, describe body-part–specific movement and how it aligns with musical rhythm and beat structure. Begin with an overall summary: e.g., 'The subject initiates with a hip sway on the downbeat…'. Then narrate movement chronologically, using precise action verbs and transitions like 'then', 'as', and 'after', referencing the timeline (e.g., early/mid/late beat or second). Specify which body parts move, how they articulate (e.g., 'the right arm lifts upward, then sweeps outward; the torso tilts as the knees bend'), describe footwork, weight shifts, and alignment with music beats. Also include any camera movement (e.g., 'camera pans to follow the torso shift'). Avoid general labels—focus on locomotor and non‑locomotor gestures, repetition, rhythm, and choreography phrasing. Always include any buttock or breast movements that you see

4. CINEMATIC AESTHETIC CONTROL (Fourth Paragraph)
Lighting (source/direction/quality/temperature), camera details (shot type, angle/height, movement), optics (lens feel, DOF, rack focus), and exposure/render cues as applicable.

5. STYLIZATION & TONE (Fifth Paragraph)
Mood/genre descriptors (e.g., "noir-inspired silhouette," "cinematic realism," etc.).

CRITICAL: Output exactly 5 paragraphs, one per category, separated by a blank line. DO NOT describe clothing, accessories, or garments in any paragraph. Never mention prohibited attributes, even if visible."""
                user_prompt = "Please analyze this video and provide a detailed description following the 5-paragraph structure outlined in the system prompt."

            # Process video file
            if not selected_media_path or not os.path.exists(selected_media_path):
                raise ValueError(f"Video file not found: {selected_media_path}")

            # Get original video info using OpenCV
            cap = cv2.VideoCapture(selected_media_path)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            original_duration = frame_count / fps if fps > 0 else 0
            cap.release()

            # Determine the video file to use for analysis
            final_video_path = selected_media_path
            actual_duration = original_duration
            trimmed = False
            trimmed_video_output_path = selected_media_path

            # Calculate duration based on max_duration
            if max_duration > 0:
                actual_duration = min(max_duration, original_duration)

            # Check if we need to trim the video (only duration limit)
            if max_duration > 0 and actual_duration < original_duration:
                # Create a temporary trimmed video file
                with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
                    trimmed_video_path = temp_file.name

                # Attempt to trim the video
                if self._trim_video(selected_media_path, trimmed_video_path, actual_duration):
                    final_video_path = trimmed_video_path
                    trimmed = True
                    trimmed_video_output_path = trimmed_video_path
                else:
                    print(f"Warning: Could not trim video. Using original video for {actual_duration:.2f}s")
                    actual_duration = original_duration
                    trimmed_video_output_path = selected_media_path

            # Read the final video file (original or trimmed)
            with open(final_video_path, 'rb') as video_file:
                video_data = video_file.read()

            file_size = len(video_data) / 1024 / 1024  # Size in MB

            # Update video info to include trimming details
            end_time = actual_duration  # Since we start from 0
            trim_info = f" (trimmed: 0.0s → {end_time:.1f}s)" if trimmed else ""

            updated_media_info = f"""{media_info_text}
• Original Duration: {original_duration:.2f} seconds
• Start Time: 0.0 seconds
• End Time: {end_time:.2f} seconds
• Processed Duration: {actual_duration:.2f} seconds{trim_info}
• Frames: {frame_count}
• Frame Rate: {fps:.2f} FPS
• Resolution: {width}x{height}
• File Size: {file_size:.2f} MB"""

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

            # Process response
            if response.text is not None:
                description = response.text.strip()
            else:
                error_msg = "Error: Gemini returned empty response"
                if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                    error_msg += f" (Prompt feedback: {response.prompt_feedback})"
                if hasattr(response, 'candidates') and response.candidates:
                    error_msg += f" (Candidates available: {len(response.candidates)})"
                description = error_msg

            # Format outputs for video processing
            gemini_status = f"""🤖 Gemini Analysis Status: ✅ Complete
• Model: {gemini_model}
• API Key: {'*' * (len(gemini_api_key) - 4) + gemini_api_key[-4:] if len(gemini_api_key) >= 4 else '****'}
• Input: Video"""

            final_string = f"{prefix_text}{description}" if prefix_text else description

            return (description, updated_media_info, gemini_status, trimmed_video_output_path, final_string)

        except Exception as e:
            description = f"Error: Video analysis failed - {str(e)}"
            gemini_status = f"""🤖 Gemini Analysis Status: ❌ Failed
• Model: {gemini_model}
• API Key: {'*' * (len(gemini_api_key) - 4) + gemini_api_key[-4:] if len(gemini_api_key) >= 4 else '****'}
• Error: {str(e)[:100]}{'...' if len(str(e)) > 100 else ''}

Please check:
1. API key is valid and has quota
2. Video file exists and is accessible
3. Internet connectivity
4. Model supports video analysis"""
            processed_media_path = ""
            final_string = f"{prefix_text}{description}" if prefix_text else description
            return (description, media_info_text, gemini_status, processed_media_path, final_string)

    @classmethod
    def INPUT_TYPES(s):
        """
        Return a dictionary which contains config for all input fields.
        Supports both image and video inputs with upload or random selection from path.
        """
        return {
            "required": {
                "gemini_api_key": ("STRING", {
                    "multiline": False,
                    "default": "AIzaSyBZpbWUwPlNsqQl6al0VEquoEY4pCZsSjM",
                    "tooltip": "Your Gemini API key"
                }),
                "gemini_model": (["models/gemini-2.5-flash", "models/gemini-2.5-flash-lite", "models/gemini-2.5-pro"], {
                    "default": "models/gemini-2.5-flash",
                    "tooltip": "Select the Gemini model to use"
                }),
                "model_type": (["Text2Image", "ImageEdit"], {
                    "default": "Text2Image",
                    "tooltip": "Select the type of model workflow to use (only applies to images)"
                }),
                "description_mode": (["Describe without clothing", "Describe with clothing", "Describe without clothing (No bokeh)", "Describe with clothing (No bokeh)"], {
                    "default": "Describe without clothing",
                    "tooltip": "Choose whether to include detailed clothing description and depth of field effects"
                }),
                "prefix_text": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "tooltip": "Text to prepend to the generated description"
                }),
                "media_source": (["Upload Media", "Randomize Media from Path"], {
                    "default": "Upload Media",
                    "tooltip": "Choose whether to upload media or randomize from a directory path"
                }),
                "media_type": (["image", "video"], {
                    "default": "image",
                    "tooltip": "Select the type of media to analyze"
                }),
                "seed": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 0xFFFFFFFFFFFFFFFF,
                    "tooltip": "Seed for randomization when using 'Randomize Media from Path'. Use different seeds to force re-execution."
                }),
            },
            "optional": {
                "image": ("IMAGE", {
                    "tooltip": "Input image to analyze (used when media_source is Upload Media and media_type is image)"
                }),
                "media_path": ("STRING", {
                    "multiline": False,
                    "default": "",
                    "tooltip": "Directory path to randomly select media from (used when media_source is Randomize Media from Path)"
                }),
                "uploaded_image_file": ("STRING", {
                    "default": "",
                    "tooltip": "Path to uploaded image file (managed by upload widget)"
                }),
                "uploaded_video_file": ("STRING", {
                    "default": "",
                    "tooltip": "Path to uploaded video file (managed by upload widget)"
                }),
                "frame_rate": ("FLOAT", {
                    "default": 30,
                    "min": 1.0,
                    "max": 60.0,
                    "step": 0.1,
                    "tooltip": "Frame rate for the temporary video file (used when processing VIDEO input)"
                }),
                "max_duration": ("FLOAT", {
                    "default": 5.0,
                    "min": 0.0,
                    "max": 300.0,
                    "step": 0.1,
                    "tooltip": "Maximum duration in seconds (0 = use full video, only applies to videos)"
                }),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("description", "media_info", "gemini_status", "processed_media_path", "final_string")
    FUNCTION = "describe_media"
    CATEGORY = "Gemini"

    def describe_media(self, gemini_api_key, gemini_model, model_type, description_mode, prefix_text, media_source, media_type, seed, image=None, media_path="", uploaded_image_file="", uploaded_video_file="", frame_rate=24.0, max_duration=0.0):
        """
        Process media (image or video) and analyze with Gemini

        Args:
            gemini_api_key: Your Gemini API key
            gemini_model: Gemini model to use
            model_type: Type of model workflow ("Text2Image" or "ImageEdit") - only applies to images
            description_mode: Mode for description with options for clothing and depth of field
            prefix_text: Text to prepend to the generated description
            media_source: Source of media ("Upload Media" or "Randomize Media from Path")
            media_type: Type of media ("image" or "video")
            seed: Seed for randomization when using "Randomize Media from Path" (forces re-execution)
            image: ComfyUI IMAGE tensor (optional, used for uploaded images)
            media_path: Directory path to randomly select media from (optional)
            uploaded_image_file: Path to uploaded image file (optional)
            uploaded_video_file: Path to uploaded video file (optional)
            frame_rate: Frame rate for temporary video (legacy parameter, not used)
            max_duration: Maximum duration in seconds (0 = use full video, only applies to videos)
        """
        try:
            # Import required modules
            import os
            import random
            import glob

            # First, determine what media we're processing
            selected_media_path = None
            media_info_text = ""
            processed_media_path = ""

            if media_source == "Randomize Media from Path":
                if not media_path or not media_path.strip():
                    raise ValueError("Media path is required when using 'Randomize Media from Path'")

                # Validate path exists
                if not os.path.exists(media_path):
                    current_dir = os.getcwd()
                    parent_dir = os.path.dirname(media_path) if media_path else "N/A"
                    parent_exists = os.path.exists(parent_dir) if parent_dir else False

                    debug_info = f"""
Path Debug Info:
• Requested path: {media_path}
• Current working dir: {current_dir}
• Parent directory: {parent_dir}
• Parent exists: {parent_exists}
• Is absolute path: {os.path.isabs(media_path) if media_path else False}"""

                    raise ValueError(f"Media path does not exist: {media_path}{debug_info}")

                # Define supported file extensions
                if media_type == "image":
                    extensions = ["*.jpg", "*.jpeg", "*.png", "*.bmp", "*.gif", "*.tiff", "*.webp"]
                else:  # video
                    extensions = ["*.mp4", "*.avi", "*.mov", "*.mkv", "*.wmv", "*.flv", "*.webm"]

                # Find all matching files
                all_files = []
                for ext in extensions:
                    all_files.extend(glob.glob(os.path.join(media_path, ext)))
                    all_files.extend(glob.glob(os.path.join(media_path, ext.upper())))

                if not all_files:
                    try:
                        dir_contents = os.listdir(media_path)
                        total_files = len(dir_contents)
                        sample_files = dir_contents[:5]

                        debug_info = f"""
Directory scan results:
• Path: {media_path}
• Total items in directory: {total_files}
• Sample files: {sample_files}
• Looking for {media_type} files with extensions: {extensions}"""

                        raise ValueError(f"No {media_type} files found in path: {media_path}{debug_info}")
                    except PermissionError:
                        raise ValueError(f"Permission denied accessing path: {media_path}")
                    except Exception as scan_error:
                        raise ValueError(f"Error scanning path {media_path}: {str(scan_error)}")

                # Randomly select a file
                selected_media_path = random.choice(all_files)

                if media_type == "image":
                    # For random image, we'll read it as PIL and convert to bytes
                    media_info_text = f"📷 Image Processing Info (Random Selection):\n• File: {os.path.basename(selected_media_path)}\n• Source: Random from {media_path}"
                else:
                    # For random video, set up for video processing
                    media_info_text = f"📹 Video Processing Info (Random Selection):\n• File: {os.path.basename(selected_media_path)}\n• Source: Random from {media_path}"
            else:
                # Upload Media mode
                if media_type == "image":
                    if image is None and not uploaded_image_file:
                        raise ValueError("Image input is required when media_source is 'Upload Media' and media_type is 'image'")
                    if uploaded_image_file:
                        # Use uploaded image file
                        try:
                            import folder_paths
                            input_dir = folder_paths.get_input_directory()
                        except ImportError:
                            input_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "input")
                        selected_media_path = os.path.join(input_dir, uploaded_image_file)
                        media_info_text = f"📷 Image Processing Info (Uploaded File):\n• File: {uploaded_image_file}"
                    else:
                        # Use image tensor input
                        media_info_text = "📷 Image Processing Info (Tensor Input):\n• Source: ComfyUI IMAGE tensor"
                else:  # video
                    if not uploaded_video_file:
                        raise ValueError("Video upload is required when media_source is 'Upload Media' and media_type is 'video'")
                    try:
                        import folder_paths
                        input_dir = folder_paths.get_input_directory()
                    except ImportError:
                        input_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "input")
                    selected_media_path = os.path.join(input_dir, uploaded_video_file)
                    media_info_text = f"📹 Video Processing Info (Uploaded File):\n• File: {uploaded_video_file}"

            # Now process the media based on type
            if media_type == "image":
                # Process as image - delegate to image logic
                return self._process_image(
                    gemini_api_key, gemini_model, model_type, description_mode, prefix_text,
                    image, selected_media_path, media_info_text
                )
            else:
                # Process as video - delegate to video logic  
                return self._process_video(
                    gemini_api_key, gemini_model, description_mode, prefix_text,
                    selected_media_path, frame_rate, max_duration, media_info_text
                )

        except Exception as e:
            # Handle errors gracefully with five outputs
            description = f"Error: Media analysis failed - {str(e)}"
            media_info = f"""📱 Media Processing Info:
• Status: ❌ Processing Failed
• Media Source: {media_source}
• Media Type: {media_type}"""
            gemini_status = f"""🤖 Gemini Analysis Status: ❌ Failed
• Model: {gemini_model}
• Model Type: {model_type if media_type == 'image' else 'N/A (Video)'}
• API Key: {'*' * (len(gemini_api_key) - 4) + gemini_api_key[-4:] if len(gemini_api_key) >= 4 else '****'}
• Error: {str(e)[:100]}{'...' if len(str(e)) > 100 else ''}

Please check:
1. API key is valid and has quota
2. Media input is provided correctly
3. Directory path exists (if using Randomize Media from Path)
4. Internet connectivity
5. Model supports media analysis"""
            processed_media_path = ""
            final_string = f"{prefix_text}{description}" if prefix_text else description
            return (description, media_info, gemini_status, processed_media_path, final_string)


# A dictionary that contains all nodes you want to export with their names
# NOTE: names should be globally unique
NODE_CLASS_MAPPINGS = {
    "GeminiUtilVideoDescribe": GeminiVideoDescribe,
    "GeminiUtilImageDescribe": GeminiImageDescribe,
    "GeminiUtilMediaDescribe": GeminiMediaDescribe
}

# A dictionary that contains the friendly/humanly readable titles for the nodes
NODE_DISPLAY_NAME_MAPPINGS = {
    "GeminiUtilVideoDescribe": "Gemini Util - Video Describe",
    "GeminiUtilImageDescribe": "Gemini Util - Image Describe",
    "GeminiUtilMediaDescribe": "Gemini Util - Media Describe"
}
