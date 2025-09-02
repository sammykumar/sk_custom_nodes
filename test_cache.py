#!/usr/bin/env python3
"""
Test script to validate Gemini media description caching functionality.

This script tests the caching behavior with different combinations of:
- Media identifiers (file paths, tensor hashes)
- Description modes
- Model settings

It validates that:
1. Cache hits work correctly for identical inputs
2. Cache misses work correctly for different inputs
3. Cache keys are unique for different combinations
"""

import os
import sys
import tempfile
import numpy as np

# Add the parent directory to path to import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.cache import get_cache, get_file_media_identifier, get_tensor_media_identifier


def test_cache_functionality():
    """Test basic cache get/set functionality."""
    print("=== Testing Basic Cache Functionality ===")
    
    cache = get_cache()
    
    # Test cache set and get
    media_id = "test_video.mp4:mtime:123456:size:1000000"
    description_mode = "Describe without clothing"
    model = "models/gemini-2.5-flash"
    description = "A woman dancing gracefully in a studio setting."
    
    # Store in cache
    cache.set(media_id, description_mode, model, description)
    print(f"✓ Stored cache entry")
    
    # Retrieve from cache
    result = cache.get(media_id, description_mode, model)
    assert result is not None, "Cache should return a result"
    assert result['description'] == description, "Description should match"
    print(f"✓ Retrieved cache entry successfully")
    
    # Test cache miss
    result_miss = cache.get(media_id, "Different mode", model)
    assert result_miss is None, "Cache should miss for different description mode"
    print(f"✓ Cache miss works correctly for different description mode")
    
    print("Basic cache functionality: PASSED\n")


def test_media_identifiers():
    """Test media identifier generation for files and tensors."""
    print("=== Testing Media Identifiers ===")
    
    # Test file identifier
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
        temp_file.write(b"fake video data")
        temp_path = temp_file.name
    
    try:
        file_id1 = get_file_media_identifier(temp_path)
        file_id2 = get_file_media_identifier(temp_path)
        assert file_id1 == file_id2, "File identifiers should be consistent"
        print(f"✓ File identifier consistent: {file_id1[:50]}...")
        
        # Test that different files have different identifiers
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file2:
            temp_file2.write(b"different fake video data")
            temp_path2 = temp_file2.name
        
        try:
            file_id3 = get_file_media_identifier(temp_path2)
            assert file_id1 != file_id3, "Different files should have different identifiers"
            print(f"✓ Different files have different identifiers")
        finally:
            os.unlink(temp_path2)
            
    finally:
        os.unlink(temp_path)
    
    # Test tensor identifier  
    tensor1 = np.random.rand(3, 224, 224)
    tensor2 = np.random.rand(3, 224, 224)
    
    tensor_id1 = get_tensor_media_identifier(tensor1)
    tensor_id1_again = get_tensor_media_identifier(tensor1)
    tensor_id2 = get_tensor_media_identifier(tensor2)
    
    assert tensor_id1 == tensor_id1_again, "Tensor identifiers should be consistent"
    assert tensor_id1 != tensor_id2, "Different tensors should have different identifiers"
    print(f"✓ Tensor identifier consistent: {tensor_id1[:50]}...")
    print(f"✓ Different tensors have different identifiers")
    
    print("Media identifiers: PASSED\n")


def test_description_mode_isolation():
    """Test that different description modes create separate cache entries."""
    print("=== Testing Description Mode Isolation ===")
    
    cache = get_cache()
    media_id = "test_media_isolation"
    model = "models/gemini-2.5-flash"
    
    modes_and_descriptions = [
        ("Describe without clothing", "A woman with flowing hair, graceful posture, and elegant gestures."),
        ("Describe with clothing", "A woman wearing a flowing blue dress, with flowing hair and elegant gestures."),
        ("Describe without clothing (No bokeh)", "A woman with flowing hair, sharp focus throughout the frame."),
        ("Describe with clothing (No bokeh)", "A woman in a blue dress, everything in sharp focus.")
    ]
    
    # Store all mode combinations
    for mode, desc in modes_and_descriptions:
        cache.set(media_id, mode, model, desc)
        print(f"✓ Stored cache entry for '{mode}'")
    
    # Verify all can be retrieved independently
    for mode, expected_desc in modes_and_descriptions:
        result = cache.get(media_id, mode, model)
        assert result is not None, f"Should find cache entry for {mode}"
        assert result['description'] == expected_desc, f"Description should match for {mode}"
        print(f"✓ Retrieved correct description for '{mode}'")
    
    print("Description mode isolation: PASSED\n")


def test_model_isolation():
    """Test that different models create separate cache entries."""
    print("=== Testing Model Isolation ===")
    
    cache = get_cache()
    media_id = "test_model_isolation"
    description_mode = "Describe without clothing"
    
    models_and_descriptions = [
        ("models/gemini-2.5-flash", "Fast model description"),
        ("models/gemini-2.5-flash-lite", "Lite model description"),
        ("models/gemini-2.5-pro", "Pro model description")
    ]
    
    # Store all model combinations
    for model, desc in models_and_descriptions:
        cache.set(media_id, description_mode, model, desc)
        print(f"✓ Stored cache entry for '{model}'")
    
    # Verify all can be retrieved independently
    for model, expected_desc in models_and_descriptions:
        result = cache.get(media_id, description_mode, model)
        assert result is not None, f"Should find cache entry for {model}"
        assert result['description'] == expected_desc, f"Description should match for {model}"
        print(f"✓ Retrieved correct description for '{model}'")
    
    print("Model isolation: PASSED\n")


def test_cache_persistence():
    """Test that cache entries are persisted to disk."""
    print("=== Testing Cache Persistence ===")
    
    cache = get_cache()
    initial_info = cache.get_cache_info()
    
    # Add a new entry
    media_id = "test_persistence"
    description_mode = "Describe without clothing"
    model = "models/gemini-2.5-flash"
    description = "Persistence test description"
    
    cache.set(media_id, description_mode, model, description)
    
    # Check that cache info shows increase
    after_info = cache.get_cache_info()
    assert after_info['entries'] > initial_info['entries'], "Cache entries should increase"
    assert after_info['total_size'] > initial_info['total_size'], "Cache size should increase"
    print(f"✓ Cache entries increased from {initial_info['entries']} to {after_info['entries']}")
    
    # Create a new cache instance and verify entry is still there
    new_cache = get_cache()
    result = new_cache.get(media_id, description_mode, model)
    assert result is not None, "Cache entry should persist across instances"
    assert result['description'] == description, "Persisted description should match"
    print(f"✓ Cache entry persisted across cache instances")
    
    print("Cache persistence: PASSED\n")


def main():
    """Run all cache tests."""
    print("Starting Gemini Cache Tests...\n")
    
    try:
        test_cache_functionality()
        test_media_identifiers()
        test_description_mode_isolation()
        test_model_isolation()
        test_cache_persistence()
        
        print("=== ALL TESTS PASSED ===")
        print("✓ Cache functionality is working correctly")
        print("✓ Media identifiers are generated properly")
        print("✓ Description modes are properly isolated")
        print("✓ Model settings are properly isolated")
        print("✓ Cache entries persist to disk")
        
        # Show final cache stats
        cache = get_cache()
        final_info = cache.get_cache_info()
        print(f"\nFinal cache statistics:")
        print(f"• Cache directory: {final_info['cache_dir']}")
        print(f"• Total entries: {final_info['entries']}")
        print(f"• Total size: {final_info['total_size_mb']} MB")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())