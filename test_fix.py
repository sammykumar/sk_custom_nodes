#!/usr/bin/env python3
"""
Test script to verify the video path fix
"""

from utils.nodes import GeminiMediaDescribe
import tempfile
import os

def test_video_path_fix():
    """Test that video path is preserved even on error"""

    # Create a mock video file path
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
        temp_path = temp_file.name
        # Write some dummy data to make it a valid file
        temp_file.write(b"fake video data")

    try:
        # Initialize the node
        node = GeminiMediaDescribe()

        # Call the _process_video method with invalid API key to trigger error
        result = node._process_video(
            gemini_api_key="invalid_key",
            gemini_model="models/gemini-2.5-flash",
            description_mode="Describe without clothing",
            prefix_text="",
            selected_media_path=temp_path,
            frame_rate=30.0,
            max_duration=5.0,
            media_info_text="Test video"
        )

        # Check that the result includes the video path even on error
        description, media_info, gemini_status, processed_media_path, final_string = result

        print("🧪 Testing video path preservation on error:")
        print(f"   Selected path: {temp_path}")
        print(f"   Returned path: {processed_media_path}")
        print(f"   Description starts with 'Error:': {description.startswith('Error:')}")
        print(f"   Path preserved: {processed_media_path == temp_path}")

        # The fix ensures that even on error, the path is preserved
        assert processed_media_path == temp_path, "❌ Video path should be preserved on error"
        assert description.startswith("Error:"), "❌ Should return error description"

        print("✅ Video path fix working correctly!")

    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            os.unlink(temp_path)

if __name__ == "__main__":
    test_video_path_fix()
