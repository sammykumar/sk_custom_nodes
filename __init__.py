from .utils.nodes import NODE_CLASS_MAPPINGS as MAIN_NODE_CLASS_MAPPINGS
from .utils.nodes import NODE_DISPLAY_NAME_MAPPINGS as MAIN_NODE_DISPLAY_NAME_MAPPINGS
from .utils.helper_nodes import HELPER_NODE_CLASS_MAPPINGS
from .utils.helper_nodes import HELPER_NODE_DISPLAY_NAME_MAPPINGS

# Import VHS-SK nodes  
try:
    import importlib.util
    import os
    vhs_sk_path = os.path.join(os.path.dirname(__file__), "VHS-SK", "__init__.py")
    spec = importlib.util.spec_from_file_location("VHS_SK", vhs_sk_path)
    vhs_sk_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(vhs_sk_module)
    VHS_NODE_CLASS_MAPPINGS = vhs_sk_module.VHS_NODE_CLASS_MAPPINGS
    VHS_NODE_DISPLAY_NAME_MAPPINGS = vhs_sk_module.VHS_NODE_DISPLAY_NAME_MAPPINGS
except Exception as e:
    print(f"Warning: Could not import VHS-SK nodes: {e}")
    VHS_NODE_CLASS_MAPPINGS = {}
    VHS_NODE_DISPLAY_NAME_MAPPINGS = {}

# Combine main nodes, helper nodes, and VHS-SK nodes
NODE_CLASS_MAPPINGS = {
    **MAIN_NODE_CLASS_MAPPINGS, 
    **HELPER_NODE_CLASS_MAPPINGS,
    **VHS_NODE_CLASS_MAPPINGS
}
NODE_DISPLAY_NAME_MAPPINGS = {
    **MAIN_NODE_DISPLAY_NAME_MAPPINGS, 
    **HELPER_NODE_DISPLAY_NAME_MAPPINGS,
    **VHS_NODE_DISPLAY_NAME_MAPPINGS
}

WEB_DIRECTORY = "./web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
