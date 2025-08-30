from google import genai
from google.genai import types
import cv2
import tempfile
import os
import subprocess

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
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("description", "video_info", "gemini_status", "trimmed_video_path")
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

    def describe_video(self, gemini_api_key, gemini_model, system_prompt, user_prompt, frame_rate=24.0, uploaded_video_file="", max_duration=0.0):
        """
        Process uploaded video file and analyze with Gemini

        Args:
            gemini_api_key: Your Gemini API key
            gemini_model: Gemini model to use
            system_prompt: System context for the AI
            user_prompt: User's specific request
            frame_rate: Frame rate for temporary video (legacy parameter, not used)
            uploaded_video_file: Path to uploaded video file
            max_duration: Maximum duration in seconds (0 = use full video)
        """
        try:
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

            # Format the four separate outputs

            # 1. Description - Clean output from Gemini (for direct use as prompt)
            description = response.text.strip()

            # 2. Video Info - Technical details about the processed video
            video_info = video_info_text

            # 3. Gemini Status - API and model information
            gemini_status = f"""🤖 Gemini Analysis Status: ✅ Complete
• Model: {gemini_model}
• API Key: {'*' * (len(gemini_api_key) - 4) + gemini_api_key[-4:] if len(gemini_api_key) >= 4 else '****'}"""

            # 4. Trimmed Video Path - Path to the processed video file
            trimmed_video_path = trimmed_video_output_path

            return (description, video_info, gemini_status, trimmed_video_path)

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

            return (description, video_info, gemini_status, trimmed_video_path)


# A dictionary that contains all nodes you want to export with their names
# NOTE: names should be globally unique
NODE_CLASS_MAPPINGS = {
    "GeminiUtilVideoDescribe": GeminiVideoDescribe
}

# A dictionary that contains the friendly/humanly readable titles for the nodes
NODE_DISPLAY_NAME_MAPPINGS = {
    "GeminiUtilVideoDescribe": "Gemini Util - Video Describe"
}
