import os
import server
from aiohttp import web
import folder_paths
import nodes
from .utils.nodes import NODE_CLASS_MAPPINGS as MAIN_NODE_CLASS_MAPPINGS
from .utils.nodes import NODE_DISPLAY_NAME_MAPPINGS as MAIN_NODE_DISPLAY_NAME_MAPPINGS
from .utils.helper_nodes import HELPER_NODE_CLASS_MAPPINGS
from .utils.helper_nodes import HELPER_NODE_DISPLAY_NAME_MAPPINGS

# Combine main nodes and helper nodes
NODE_CLASS_MAPPINGS = {**MAIN_NODE_CLASS_MAPPINGS, **HELPER_NODE_CLASS_MAPPINGS}
NODE_DISPLAY_NAME_MAPPINGS = {**MAIN_NODE_DISPLAY_NAME_MAPPINGS, **HELPER_NODE_DISPLAY_NAME_MAPPINGS}

WEB_DIRECTORY = "./web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
