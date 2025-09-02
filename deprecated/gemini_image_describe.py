from google import genai
from google.genai import types
import numpy as np
from PIL import Image
import io

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
