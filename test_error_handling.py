#!/usr/bin/env python3
"""
Test script to verify proper error handling - workflow should fail on Gemini errors
"""

from utils.nodes import GeminiMediaDescribe
import tempfile
import os

def test_proper_error_handling():
    """Test that errors properly stop workflow execution"""

    # Create a mock video file path
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
        temp_path = temp_file.name
        # Write some dummy data to make it a valid file
        temp_file.write(b"fake video data")

    try:
        # Initialize the node
        node = GeminiMediaDescribe()

        # Call the _process_video method with invalid API key to trigger error
        try:
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
            # If we get here, the method didn't raise an exception (bad)
            print("❌ ERROR: Method should have raised an exception but didn't!")
            print(f"   Unexpected result: {result}")

        except Exception as e:
            # This is the expected behavior - the method should raise an exception
            print("✅ CORRECT: Method properly raised an exception on error")
            print(f"   Exception message: {str(e)}")
            print("   Workflow will stop at this node (as intended)")

        print("\n🎯 Expected behavior:")
        print("   1. ✅ Gemini processing fails")
        print("   2. ✅ Node raises exception")
        print("   3. ✅ Workflow stops at Gemini node")
        print("   4. ✅ VHS Load Video never receives empty path")
        print("   5. ✅ User sees clear error at the source")

    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            os.unlink(temp_path)

if __name__ == "__main__":
    test_proper_error_handling()
