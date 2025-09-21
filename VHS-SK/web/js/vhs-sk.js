// VHS-SK - Simplified JavaScript widgets for video helper functionality
import { app } from '../../../scripts/app.js'

app.registerExtension({
    name: "VHS-SK.Core",
    beforeRegisterNodeDef(nodeType, nodeData, app) {
        if(nodeData?.name?.startsWith("VHS_")) {
            // Basic video preview support
            if (["VHS_VideoCombine", "VHS_LoadVideo", "VHS_LoadVideoPath"].includes(nodeData.name)) {
                const originalNodeCreated = nodeType.prototype.onNodeCreated;
                nodeType.prototype.onNodeCreated = function() {
                    const r = originalNodeCreated?.apply(this, arguments);
                    
                    // Add basic preview element
                    const previewDiv = document.createElement("div");
                    previewDiv.style.width = "100%";
                    previewDiv.style.height = "200px";
                    previewDiv.style.backgroundColor = "#222";
                    previewDiv.style.border = "1px solid #444";
                    previewDiv.style.borderRadius = "4px";
                    previewDiv.style.display = "flex";
                    previewDiv.style.alignItems = "center";
                    previewDiv.style.justifyContent = "center";
                    previewDiv.style.color = "#888";
                    previewDiv.textContent = "Video Preview (VHS-SK)";
                    
                    this.addDOMWidget("preview", "preview", previewDiv, {
                        serialize: false,
                        hideOnZoom: true,
                    });
                    
                    return r;
                };
            }
        }
    }
});