# VHS-SK - Video Helper Suite customized for SK Custom Nodes
# Forked from ComfyUI-VideoHelperSuite by Kosinkadink
# https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite

"""
Video Helper Suite SK - Enhanced video processing nodes for ComfyUI
"""

from .nodes import NODE_CLASS_MAPPINGS as VHS_NODE_CLASS_MAPPINGS
from .nodes import NODE_DISPLAY_NAME_MAPPINGS as VHS_NODE_DISPLAY_NAME_MAPPINGS

# Export for integration with SK Custom Nodes
__all__ = ["VHS_NODE_CLASS_MAPPINGS", "VHS_NODE_DISPLAY_NAME_MAPPINGS"]