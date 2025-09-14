import { app } from "../../../scripts/app.js";

console.log("Loading wan_unified_ksampler_widgets.js extension");

// Register custom widget for the WAN Video Unified KSampler node
app.registerExtension({
    name: "sk_custom_nodes.wan_unified_ksampler_widgets",

    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        // Handle WanVideoUnifiedKSampler node
        if (nodeData.name === "WanVideoUnifiedKSampler") {
            console.log("Registering WanVideoUnifiedKSampler node");

            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                const result = onNodeCreated?.apply(this, arguments);

                // Add a preview widget to show the sigma switching information
                this.addWidget(
                    "text",
                    "sigma_info_preview",
                    "Sigma switching info will appear here",
                    (value) => {
                        // This is a read-only preview widget
                    },
                    { multiline: true }
                );

                // Function to update the sigma info preview
                this.updateSigmaPreview = function () {
                    try {
                        const steps = this.widgets.find((w) => w.name === "steps")?.value || 30;
                        const boundary = this.widgets.find((w) => w.name === "boundary")?.value || 0.875;
                        const cfg_high_noise = this.widgets.find((w) => w.name === "cfg_high_noise")?.value || 4.0;
                        const cfg_low_noise = this.widgets.find((w) => w.name === "cfg_low_noise")?.value || 3.0;
                        const scheduler = this.widgets.find((w) => w.name === "scheduler")?.value || "unipc";

                        // Approximate calculation of switch step (simplified)
                        const switch_step = Math.floor(steps * (1 - boundary));

                        // Create preview text
                        const preview = `📊 WAN Video Unified KSampler Preview:
┌─ Model Switch Configuration ─┐
│ Total Steps: ${steps}
│ Switch at Step: ${switch_step} (${Math.round((switch_step / steps) * 100)}%)
│ Sigma Boundary: ${boundary}
├─ Model CFG Settings ─────────┤
│ High Noise CFG: ${cfg_high_noise}
│ Low Noise CFG: ${cfg_low_noise}
├─ Scheduler ──────────────────┤
│ Algorithm: ${scheduler}
└───────────────────────────────┘

🔀 Switch Point: σ < ${boundary}
📈 Graph will show sigma curve with red line at switch point`;

                        // Update the preview widget
                        const previewWidget = this.widgets.find((w) => w.name === "sigma_info_preview");
                        if (previewWidget) {
                            previewWidget.value = preview;
                        }

                        // Request UI update
                        if (this.onResize) {
                            this.onResize(this.size);
                        }

                        console.log(
                            `[WAN Unified KSampler] Updated preview: ${steps} steps, switch at ${switch_step}, boundary ${boundary}`
                        );
                    } catch (error) {
                        console.error("[WAN Unified KSampler] Error updating sigma preview:", error);
                        const previewWidget = this.widgets.find((w) => w.name === "sigma_info_preview");
                        if (previewWidget) {
                            previewWidget.value = "Error calculating sigma info";
                        }
                    }
                };

                // Set up event listeners for parameter changes
                const paramWidgets = ["steps", "boundary", "cfg_high_noise", "cfg_low_noise", "scheduler"];
                paramWidgets.forEach((paramName) => {
                    const widget = this.widgets.find((w) => w.name === paramName);
                    if (widget) {
                        const originalCallback = widget.callback;
                        widget.callback = (value) => {
                            if (originalCallback) {
                                originalCallback(value);
                            }
                            // Update preview when parameter changes
                            setTimeout(() => {
                                this.updateSigmaPreview();
                            }, 10);
                        };
                    }
                });

                // Initial update
                setTimeout(() => {
                    this.updateSigmaPreview();
                }, 100);

                // Add model type helper text
                this.addWidget(
                    "text",
                    "model_type_hint",
                    "💡 Tip: Use boundary 0.875 for Text2Image, 0.9 for Image2Video",
                    (value) => {
                        // Read-only helper widget
                    },
                    { multiline: false }
                );

                console.log(
                    `[STATE] WAN Unified KSampler widgets initialized. Total widgets: ${
                        this.widgets?.length || 0
                    }`
                );

                return result;
            };

            // Override the compute size to account for additional widgets
            const originalComputeSize = nodeType.prototype.computeSize;
            nodeType.prototype.computeSize = function (out) {
                const size = originalComputeSize ? originalComputeSize.apply(this, arguments) : [200, 100];
                
                // Add extra height for preview widgets
                const previewWidget = this.widgets?.find((w) => w.name === "sigma_info_preview");
                if (previewWidget && previewWidget.value) {
                    const lines = previewWidget.value.split('\n').length;
                    size[1] += Math.max(lines * 15, 100); // Additional height for preview text
                }
                
                return size;
            };

            console.log("WanVideoUnifiedKSampler widget registration complete");
        }
    },
});