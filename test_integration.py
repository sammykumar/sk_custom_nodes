#!/usr/bin/env python3

import os
import sys

def test_structure():
    """Test VHS-SK directory structure and file existence"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    vhs_sk_dir = os.path.join(base_dir, "VHS-SK")
    
    print("=== VHS-SK Structure Test ===")
    print(f"Base directory: {base_dir}")
    print(f"VHS-SK directory: {vhs_sk_dir}")
    
    if not os.path.exists(vhs_sk_dir):
        print("❌ VHS-SK directory not found!")
        return False
        
    # Check core files
    core_files = [
        "__init__.py",
        "nodes.py", 
        "utils.py",
        "logger.py",
        "server.py",
        "image_latent_nodes.py",
        "load_video_nodes.py", 
        "load_images_nodes.py",
        "batched_nodes.py",
        "README.md"
    ]
    
    missing_files = []
    for file in core_files:
        file_path = os.path.join(vhs_sk_dir, file)
        if os.path.exists(file_path):
            print(f"✅ {file}")
        else:
            print(f"❌ {file}")
            missing_files.append(file)
    
    # Check directories
    directories = [
        "video_formats",
        "web/js"
    ]
    
    for directory in directories:
        dir_path = os.path.join(vhs_sk_dir, directory) 
        if os.path.exists(dir_path):
            files = os.listdir(dir_path)
            print(f"✅ {directory}/ ({len(files)} files)")
            for file in files:
                print(f"   - {file}")
        else:
            print(f"❌ {directory}/")
            missing_files.append(directory)
    
    # Check video formats
    format_files = [
        "video_formats/webm.json",
        "video_formats/mp4.json"
    ]
    
    for format_file in format_files:
        format_path = os.path.join(vhs_sk_dir, format_file)
        if os.path.exists(format_path):
            print(f"✅ {format_file}")
        else:
            print(f"❌ {format_file}")
            missing_files.append(format_file)
    
    # Check web files  
    web_files = [
        "web/js/VHS.core.js",
        "web/js/vhs-sk.js"
    ]
    
    for web_file in web_files:
        web_path = os.path.join(vhs_sk_dir, web_file)
        if os.path.exists(web_path):
            print(f"✅ {web_file}")
        else:
            print(f"❌ {web_file}")
            missing_files.append(web_file)
    
    if missing_files:
        print(f"\n❌ Missing {len(missing_files)} files/directories:")
        for missing in missing_files:
            print(f"   - {missing}")
        return False
    else:
        print(f"\n✅ All VHS-SK files present and accounted for!")
        return True

def test_node_definitions():
    """Test that node definitions are accessible without importing ComfyUI"""
    print("\n=== Node Definitions Test ===")
    
    # Count expected nodes from our codebase
    vhs_sk_dir = os.path.join(os.path.dirname(__file__), "VHS-SK")
    nodes_file = os.path.join(vhs_sk_dir, "nodes.py")
    
    if not os.path.exists(nodes_file):
        print("❌ nodes.py not found")
        return False
        
    try:
        with open(nodes_file, 'r') as f:
            content = f.read()
            
        # Count NODE_CLASS_MAPPINGS entries
        if 'NODE_CLASS_MAPPINGS = {' in content:
            # Extract the dictionary content
            start_idx = content.find('NODE_CLASS_MAPPINGS = {')
            brace_count = 0
            in_dict = False
            node_count = 0
            
            for i, char in enumerate(content[start_idx:], start_idx):
                if char == '{':
                    brace_count += 1
                    in_dict = True
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        break
                elif in_dict and char == '"' and content[i:].startswith('"VHS_'):
                    node_count += 1
            
            print(f"✅ Found {node_count} VHS node definitions in NODE_CLASS_MAPPINGS")
            
            # List some key nodes
            key_nodes = [
                "VHS_VideoCombine", "VHS_LoadVideo", "VHS_LoadVideoPath", 
                "VHS_LoadImages", "VHS_LoadImagesPath", "VHS_LoadAudio",
                "VHS_SplitLatents", "VHS_MergeImages", "VHS_VAEEncodeBatched"
            ]
            
            found_nodes = []
            for node in key_nodes:
                if f'"{node}":' in content:
                    found_nodes.append(node)
                    
            print(f"✅ Key nodes found: {len(found_nodes)}/{len(key_nodes)}")
            for node in found_nodes[:5]:  # Show first 5
                print(f"   - {node}")
            if len(found_nodes) > 5:
                print(f"   ... and {len(found_nodes) - 5} more")
                
            return True
        else:
            print("❌ NODE_CLASS_MAPPINGS not found in nodes.py")
            return False
            
    except Exception as e:
        print(f"❌ Error reading nodes.py: {e}")
        return False

def main():
    structure_ok = test_structure()
    nodes_ok = test_node_definitions()
    
    print(f"\n=== Final Results ===")
    print(f"Structure test: {'✅ PASSED' if structure_ok else '❌ FAILED'}")
    print(f"Node definitions test: {'✅ PASSED' if nodes_ok else '❌ FAILED'}")
    
    overall_success = structure_ok and nodes_ok
    print(f"Overall: {'✅ VHS-SK INTEGRATION READY' if overall_success else '❌ INTEGRATION INCOMPLETE'}")
    
    return 0 if overall_success else 1

if __name__ == "__main__":
    sys.exit(main())