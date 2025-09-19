#!/usr/bin/env python3

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_vhs_sk_import():
    try:
        # Test importing VHS-SK nodes directly
        import importlib.util
        
        vhs_sk_path = os.path.join(os.path.dirname(__file__), "VHS-SK", "nodes.py")
        print(f"Loading VHS-SK from: {vhs_sk_path}")
        
        if not os.path.exists(vhs_sk_path):
            print("VHS-SK nodes.py not found!")
            return False
            
        spec = importlib.util.spec_from_file_location("vhs_sk_nodes", vhs_sk_path)
        vhs_sk_nodes = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(vhs_sk_nodes)
        
        nodes = vhs_sk_nodes.NODE_CLASS_MAPPINGS
        print(f"Successfully loaded {len(nodes)} VHS-SK nodes:")
        for name in sorted(nodes.keys())[:10]:  # Show first 10
            print(f"  - {name}")
        if len(nodes) > 10:
            print(f"  ... and {len(nodes) - 10} more")
            
        return True
        
    except Exception as e:
        print(f"Error loading VHS-SK nodes: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_vhs_sk_import()
    print(f"Test {'PASSED' if success else 'FAILED'}")
    sys.exit(0 if success else 1)