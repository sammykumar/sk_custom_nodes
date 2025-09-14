import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";

console.log("Loading gemini_widgets.js extension");

// Register custom widget for the Gemini Video Describe node
app.registerExtension({
    name: "sk_custom_nodes.gemini_widgets",

    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        // Handle GeminiUtilOptions node
        if (nodeData.name === "GeminiUtilOptions") {
            console.log("Registering GeminiUtilOptions node");

            // This node doesn't need special widgets - it just provides configuration
            // The existing ComfyUI widgets are sufficient for this node
        }

        // Handle FilenameGenerator node
        else if (nodeData.name === "FilenameGenerator") {
            console.log("Registering FilenameGenerator node");

            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                const result = onNodeCreated?.apply(this, arguments);

                // Add a preview widget to show the generated filename
                this.addWidget(
                    "text",
                    "filename_preview",
                    "",
                    (value) => {
                        // This is a read-only preview widget
                    },
                    { multiline: true }
                );

                // Function to update the filename preview
                this.updateFilenamePreview = function () {
                    try {
                        // For scheduler, check if it's connected via input first
                        let scheduler = "scheduler_input";
                        const schedulerInput = this.inputs?.find(
                            (input) => input.name === "scheduler"
                        );
                        if (schedulerInput && schedulerInput.link) {
                            scheduler = "scheduler_connected";
                        } else {
                            // Fallback to widget if no connection (shouldn't happen with SAMPLER type, but for safety)
                            const schedulerWidget = this.widgets.find(
                                (w) => w.name === "scheduler"
                            );
                            if (schedulerWidget) {
                                scheduler = schedulerWidget.value || "scheduler_input";
                            }
                        }

                        const shift = this.widgets.find((w) => w.name === "shift")?.value || 12.0;
                        const total_steps =
                            this.widgets.find((w) => w.name === "total_steps")?.value || 40;
                        const shift_step =
                            this.widgets.find((w) => w.name === "shift_step")?.value || 25;
                        const high_cfg =
                            this.widgets.find((w) => w.name === "high_cfg")?.value || 3.0;
                        const low_cfg =
                            this.widgets.find((w) => w.name === "low_cfg")?.value || 4.0;
                        const base_filename =
                            this.widgets.find((w) => w.name === "base_filename")?.value || "base";
                        const subdirectory_prefix =
                            this.widgets.find((w) => w.name === "subdirectory_prefix")?.value || "";
                        const add_date_subdirectory =
                            this.widgets.find((w) => w.name === "add_date_subdirectory")?.value !==
                            false;

                        // Format float values to replace decimal points with underscores
                        const shift_str = shift.toFixed(2).replace(".", "_");
                        const high_cfg_str = high_cfg.toFixed(2).replace(".", "_");
                        const low_cfg_str = low_cfg.toFixed(2).replace(".", "_");

                        // Clean scheduler string to ensure it's filename-safe
                        const scheduler_clean = scheduler
                            .toString()
                            .trim()
                            .replace(/\s/g, "_")
                            .toLowerCase();

                        // Clean base filename to ensure it's filename-safe
                        const base_clean = base_filename.toString().trim().replace(/\s/g, "_");

                        // Generate the filename components
                        const filename_parts = [
                            base_clean,
                            "scheduler",
                            scheduler_clean,
                            "shift",
                            shift_str,
                            "total_steps",
                            total_steps.toString(),
                            "shift_step",
                            shift_step.toString(),
                            "highCFG",
                            high_cfg_str,
                            "lowCFG",
                            low_cfg_str,
                        ];

                        // Join all parts with underscores
                        let filename = filename_parts.join("_");

                        // Build directory structure with optional subdirectory prefix and date
                        const directory_parts = [];

                        // Add subdirectory prefix if provided
                        if (subdirectory_prefix && subdirectory_prefix.trim()) {
                            const prefix_clean = subdirectory_prefix.trim().replace(/\s/g, "_");
                            directory_parts.push(prefix_clean);
                        }

                        // Add date subdirectory if requested
                        if (add_date_subdirectory) {
                            const current_date = new Date().toISOString().split("T")[0]; // YYYY-MM-DD format
                            directory_parts.push(current_date);
                        }

                        // Combine directory parts with filename
                        let full_path;
                        if (directory_parts.length > 0) {
                            full_path = directory_parts.join("/") + "/" + filename;
                        } else {
                            full_path = filename;
                        }

                        // Update the preview widget
                        const previewWidget = this.widgets.find(
                            (w) => w.name === "filename_preview"
                        );
                        if (previewWidget) {
                            previewWidget.value = `Preview:\n${full_path}`;
                        }
                    } catch (error) {
                        console.log("Error updating filename preview:", error);
                        const previewWidget = this.widgets.find(
                            (w) => w.name === "filename_preview"
                        );
                        if (previewWidget) {
                            previewWidget.value = "Preview:\nError generating filename";
                        }
                    }
                };

                // Set up listeners for all input widgets to update the preview
                const inputWidgetNames = [
                    "shift",
                    "total_steps",
                    "shift_step",
                    "high_cfg",
                    "low_cfg",
                    "base_filename",
                    "subdirectory_prefix",
                    "add_date_subdirectory",
                ];

                for (const widgetName of inputWidgetNames) {
                    const widget = this.widgets.find((w) => w.name === widgetName);
                    if (widget) {
                        const originalCallback = widget.callback;
                        widget.callback = (...args) => {
                            if (originalCallback) {
                                originalCallback.apply(widget, args);
                            }
                            // Update preview after a small delay to ensure the value is set
                            setTimeout(() => this.updateFilenamePreview(), 10);
                        };
                    }
                }

                // Listen for input connections/disconnections to update preview
                const originalOnConnectionsChange = this.onConnectionsChange;
                this.onConnectionsChange = function (type, slotIndex, connected, linkInfo, ioSlot) {
                    if (originalOnConnectionsChange) {
                        originalOnConnectionsChange.call(
                            this,
                            type,
                            slotIndex,
                            connected,
                            linkInfo,
                            ioSlot
                        );
                    }
                    // Update preview when scheduler input changes
                    if (type === 1 && ioSlot && ioSlot.name === "scheduler") {
                        // type 1 = input
                        setTimeout(() => this.updateFilenamePreview(), 10);
                    }
                };

                // Initial preview update
                setTimeout(() => this.updateFilenamePreview(), 100);

                return result;
            };
        }

        // Handle GeminiUtilMediaDescribe node
        else if (nodeData.name === "GeminiUtilMediaDescribe") {
            console.log("Registering GeminiUtilMediaDescribe node with dynamic media widgets");

            // Add custom widget after the node is created
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                const result = onNodeCreated?.apply(this, arguments);

                // Hide the optional input widgets that shouldn't be directly visible
                // These will be managed by our dynamic widget system
                this.hideOptionalInputWidgets = function () {
                    const widgetsToHide = [
                        "media_path",
                        "uploaded_image_file",
                        "uploaded_video_file",
                        "seed",
                    ];

                    for (const widgetName of widgetsToHide) {
                        const widget = this.widgets.find((w) => w.name === widgetName);
                        if (widget) {
                            // Hide the widget by setting its type to 'hidden'
                            widget.type = "hidden";
                            widget.computeSize = () => [0, -4]; // Make it take no space
                            console.log(`[WIDGET] Hidden optional input widget: ${widgetName}`);
                        }
                    }
                };

                // Hide the optional input widgets immediately
                this.hideOptionalInputWidgets();

                // Find the media_source widget
                this.mediaSourceWidget = this.widgets.find((w) => w.name === "media_source");

                // Find the media_type widget
                this.mediaTypeWidget = this.widgets.find((w) => w.name === "media_type");

                // Method to clear all media state (images, videos, previews, file data)
                this.clearAllMediaState = function () {
                    console.log("[DEBUG] clearAllMediaState called");
                    console.log("[DEBUG] _pendingFileRestore exists:", !!this._pendingFileRestore);

                    // Clear video state and preview
                    this.clearVideoPreview();
                    this.uploadedVideoFile = null;
                    this.uploadedVideoSubfolder = null;

                    // Clear image state
                    this.uploadedImageFile = null;
                    this.uploadedImageSubfolder = null;

                    // Reset widget values to defaults (only upload-related widgets)
                    // FIXED: Only clear if widgets exist and we're not in restoration mode
                    if (this.videoInfoWidget && !this._pendingFileRestore) {
                        console.log("[DEBUG] Clearing videoInfoWidget");
                        this.videoInfoWidget.value = "No video selected";
                    } else if (this.videoInfoWidget && this._pendingFileRestore) {
                        console.log(
                            "[DEBUG] Skipping videoInfoWidget clear due to pending restore"
                        );
                    }

                    if (this.imageInfoWidget && !this._pendingFileRestore) {
                        console.log("[DEBUG] Clearing imageInfoWidget");
                        this.imageInfoWidget.value = "No image selected";
                    } else if (this.imageInfoWidget && this._pendingFileRestore) {
                        console.log(
                            "[DEBUG] Skipping imageInfoWidget clear due to pending restore"
                        );
                    }

                    // Don't clear media_path as it's not related to upload state
                    // if (this.mediaPathWidget) {
                    //     this.mediaPathWidget.value = "";
                    // }

                    // Clear hidden widgets that store file paths for Python node
                    if (this.videoFileWidget && !this._pendingFileRestore) {
                        console.log("[DEBUG] Clearing videoFileWidget");
                        this.videoFileWidget.value = "";
                    } else if (this.videoFileWidget && this._pendingFileRestore) {
                        console.log(
                            "[DEBUG] Skipping videoFileWidget clear due to pending restore"
                        );
                    }

                    if (this.imageFileWidget && !this._pendingFileRestore) {
                        console.log("[DEBUG] Clearing imageFileWidget");
                        this.imageFileWidget.value = "";
                    } else if (this.imageFileWidget && this._pendingFileRestore) {
                        console.log(
                            "[DEBUG] Skipping imageFileWidget clear due to pending restore"
                        );
                    }

                    // Also clear the original input widgets if not restoring
                    if (!this._pendingFileRestore) {
                        const originalUploadedImageWidget = this.widgets.find(
                            (w) => w.name === "uploaded_image_file"
                        );
                        const originalUploadedVideoWidget = this.widgets.find(
                            (w) => w.name === "uploaded_video_file"
                        );

                        if (originalUploadedImageWidget) {
                            console.log("[DEBUG] Clearing uploaded_image_file widget");
                            originalUploadedImageWidget.value = "";
                        }
                        if (originalUploadedVideoWidget) {
                            console.log("[DEBUG] Clearing uploaded_video_file widget");
                            originalUploadedVideoWidget.value = "";
                        }
                    } else {
                        console.log(
                            "[DEBUG] Skipping original widget clear due to pending restore"
                        );
                    }

                    console.log("[DEBUG] clearAllMediaState completed");
                };

                // Function to safely remove a widget
                this.removeWidgetSafely = function (widget) {
                    if (widget) {
                        const index = this.widgets.indexOf(widget);
                        if (index !== -1) {
                            this.widgets.splice(index, 1);
                        }
                    }
                };

                // Function to update widgets based on media_source and media_type
                this.updateMediaWidgets = function () {
                    const mediaSource = this.mediaSourceWidget?.value || "Upload Media";
                    const mediaType = this.mediaTypeWidget?.value || "image";

                    console.log(
                        `[STATE] Updating widgets: mediaSource=${mediaSource}, mediaType=${mediaType}`
                    );
                    console.log("[DEBUG] _pendingFileRestore exists:", !!this._pendingFileRestore);

                    // Find the original input widgets that we want to control
                    const originalMediaPathWidget = this.widgets.find(
                        (w) => w.name === "media_path"
                    );
                    const originalUploadedImageWidget = this.widgets.find(
                        (w) => w.name === "uploaded_image_file"
                    );
                    const originalUploadedVideoWidget = this.widgets.find(
                        (w) => w.name === "uploaded_video_file"
                    );
                    const originalSeedWidget = this.widgets.find((w) => w.name === "seed");

                    console.log("[DEBUG] Found widgets:");
                    console.log("  originalMediaPathWidget:", !!originalMediaPathWidget);
                    console.log(
                        "  originalUploadedImageWidget:",
                        !!originalUploadedImageWidget,
                        originalUploadedImageWidget?.value
                    );
                    console.log(
                        "  originalUploadedVideoWidget:",
                        !!originalUploadedVideoWidget,
                        originalUploadedVideoWidget?.value
                    );
                    console.log("  originalSeedWidget:", !!originalSeedWidget);

                    // Clear all previous media state when switching configurations
                    console.log("[STATE] About to call clearAllMediaState");
                    this.clearAllMediaState();

                    // Remove all upload-related widgets first to ensure clean state
                    console.log("[STATE] Removing existing widgets...");
                    this.removeWidgetSafely(this.imageUploadWidget);
                    this.removeWidgetSafely(this.imageInfoWidget);
                    this.removeWidgetSafely(this.videoUploadWidget);
                    this.removeWidgetSafely(this.videoInfoWidget);
                    // Don't remove the original media_path widget, just manage its visibility
                    // this.removeWidgetSafely(this.mediaPathWidget);

                    // Reset widget references
                    console.log("[STATE] Resetting widget references");
                    this.imageUploadWidget = null;
                    this.imageInfoWidget = null;
                    this.videoUploadWidget = null;
                    this.videoInfoWidget = null;
                    // this.mediaPathWidget = null;

                    // Manage visibility of original input widgets
                    if (mediaSource === "Randomize Media from Path") {
                        console.log("[STATE] Showing media path widget");

                        // Show the original media_path widget
                        if (originalMediaPathWidget) {
                            originalMediaPathWidget.type = "text";
                            originalMediaPathWidget.computeSize =
                                originalMediaPathWidget.constructor.prototype.computeSize;
                            this.mediaPathWidget = originalMediaPathWidget; // Reference the original
                        }

                        // Show the seed widget for randomization
                        if (originalSeedWidget) {
                            originalSeedWidget.type = "number";
                            originalSeedWidget.computeSize =
                                originalSeedWidget.constructor.prototype.computeSize;
                            console.log("[STATE] Showing seed widget for randomization");
                        }

                        // Note: Seed randomization is handled by ComfyUI's built-in controls

                        // Hide upload file widgets
                        if (originalUploadedImageWidget) {
                            originalUploadedImageWidget.type = "hidden";
                            originalUploadedImageWidget.computeSize = () => [0, -4];
                        }
                        if (originalUploadedVideoWidget) {
                            originalUploadedVideoWidget.type = "hidden";
                            originalUploadedVideoWidget.computeSize = () => [0, -4];
                        }
                    } else {
                        // Upload Media mode - Show appropriate upload widgets based on media_type
                        console.log("[STATE] Upload Media mode - hiding media_path widget");

                        // Hide the original media_path widget
                        if (originalMediaPathWidget) {
                            originalMediaPathWidget.type = "hidden";
                            originalMediaPathWidget.computeSize = () => [0, -4];
                        }

                        // Hide the seed widget when not randomizing
                        if (originalSeedWidget) {
                            originalSeedWidget.type = "hidden";
                            originalSeedWidget.computeSize = () => [0, -4];
                            console.log("[STATE] Hiding seed widget for upload mode");
                        }

                        if (mediaType === "image") {
                            console.log("[STATE] Creating image upload widgets");

                            // Hide the video upload widget, show image upload widget reference
                            if (originalUploadedVideoWidget) {
                                originalUploadedVideoWidget.type = "hidden";
                                originalUploadedVideoWidget.computeSize = () => [0, -4];
                            }
                            if (originalUploadedImageWidget) {
                                originalUploadedImageWidget.type = "hidden"; // Keep hidden, we'll use a custom widget
                                originalUploadedImageWidget.computeSize = () => [0, -4];
                            }

                            // Add image upload widgets
                            this.imageUploadWidget = this.addWidget(
                                "button",
                                "📁 Choose Image to Upload",
                                "upload_image",
                                () => {
                                    this.onImageUploadButtonPressed();
                                }
                            );
                            this.imageUploadWidget.serialize = false;

                            // Add a widget to display the selected image info
                            this.imageInfoWidget = this.addWidget(
                                "text",
                                "image_file",
                                "No image selected",
                                () => {},
                                {}
                            );
                            this.imageInfoWidget.serialize = false;
                        } else if (mediaType === "video") {
                            console.log("[STATE] Creating video upload widgets");

                            // Hide the image upload widget, show video upload widget reference
                            if (originalUploadedImageWidget) {
                                originalUploadedImageWidget.type = "hidden";
                                originalUploadedImageWidget.computeSize = () => [0, -4];
                            }
                            if (originalUploadedVideoWidget) {
                                originalUploadedVideoWidget.type = "hidden"; // Keep hidden, we'll use a custom widget
                                originalUploadedVideoWidget.computeSize = () => [0, -4];
                            }

                            // Add video upload widgets
                            this.videoUploadWidget = this.addWidget(
                                "button",
                                "📁 Choose Video to Upload",
                                "upload_video",
                                () => {
                                    this.onVideoUploadButtonPressed();
                                }
                            );
                            this.videoUploadWidget.serialize = false;

                            // Add a widget to display the selected video info
                            this.videoInfoWidget = this.addWidget(
                                "text",
                                "video_file",
                                "No video selected",
                                () => {},
                                {}
                            );
                            this.videoInfoWidget.serialize = false;
                        }
                    }

                    console.log(
                        `[STATE] Widget update complete. Total widgets: ${
                            this.widgets?.length || 0
                        }`
                    );

                    // Force node to recalculate size
                    this.setSize(this.computeSize());
                };

                // Initial setup
                this.updateMediaWidgets();

                // Hook into media_source widget changes
                if (this.mediaSourceWidget) {
                    const originalSourceCallback = this.mediaSourceWidget.callback;
                    this.mediaSourceWidget.callback = (value) => {
                        if (originalSourceCallback)
                            originalSourceCallback.call(this.mediaSourceWidget, value);
                        this.updateMediaWidgets();
                    };
                }

                // Hook into media_type widget changes
                if (this.mediaTypeWidget) {
                    const originalTypeCallback = this.mediaTypeWidget.callback;
                    this.mediaTypeWidget.callback = (value) => {
                        if (originalTypeCallback)
                            originalTypeCallback.call(this.mediaTypeWidget, value);
                        this.updateMediaWidgets();
                    };
                }

                return result;
            };

            // Add onSerialize method to save UI state
            const onSerialize = nodeType.prototype.onSerialize;
            nodeType.prototype.onSerialize = function (o) {
                const result = onSerialize?.apply(this, arguments);

                console.log("[DEBUG] onSerialize called - collecting state data");
                console.log("[DEBUG] uploadedVideoFile:", this.uploadedVideoFile);
                console.log("[DEBUG] uploadedVideoSubfolder:", this.uploadedVideoSubfolder);
                console.log("[DEBUG] videoInfoWidget value:", this.videoInfoWidget?.value);
                console.log("[DEBUG] uploadedImageFile:", this.uploadedImageFile);
                console.log("[DEBUG] uploadedImageSubfolder:", this.uploadedImageSubfolder);
                console.log("[DEBUG] imageInfoWidget value:", this.imageInfoWidget?.value);

                // Save current widget state for persistence
                o.widgets_values = o.widgets_values || [];
                o.ui_state = {
                    media_source: this.mediaSourceWidget?.value || "Upload Media",
                    media_type: this.mediaTypeWidget?.value || "image",
                    // Add uploaded file persistence
                    uploaded_file_info: {
                        image: {
                            file: this.uploadedImageFile,
                            subfolder: this.uploadedImageSubfolder,
                            display: this.imageInfoWidget?.value,
                        },
                        video: {
                            file: this.uploadedVideoFile,
                            subfolder: this.uploadedVideoSubfolder,
                            display: this.videoInfoWidget?.value,
                        },
                    },
                };

                console.log("[SERIALIZE] Saving UI state:", JSON.stringify(o.ui_state, null, 2));

                // Also check the actual widget values in widgets_values array
                console.log("[DEBUG] widgets_values array:", o.widgets_values);

                // Check if any widgets have video file info
                if (this.widgets) {
                    const videoWidget = this.widgets.find((w) => w.name === "uploaded_video_file");
                    const imageWidget = this.widgets.find((w) => w.name === "uploaded_image_file");
                    console.log("[DEBUG] uploaded_video_file widget value:", videoWidget?.value);
                    console.log("[DEBUG] uploaded_image_file widget value:", imageWidget?.value);
                }

                return result;
            };

            // Add onConfigure method to restore UI state
            const onConfigure = nodeType.prototype.onConfigure;
            nodeType.prototype.onConfigure = function (o) {
                const result = onConfigure?.apply(this, arguments);

                console.log("[DEBUG] onConfigure called with data:", o);
                console.log("[DEBUG] ui_state found:", !!o.ui_state);
                console.log("[DEBUG] widgets_values found:", !!o.widgets_values);

                // Restore UI state after widgets are created
                if (o.ui_state) {
                    console.log(
                        "[CONFIGURE] Restoring UI state:",
                        JSON.stringify(o.ui_state, null, 2)
                    );

                    // Set widget values if they exist
                    if (this.mediaSourceWidget && o.ui_state.media_source) {
                        console.log(
                            "[DEBUG] Setting mediaSourceWidget to:",
                            o.ui_state.media_source
                        );
                        this.mediaSourceWidget.value = o.ui_state.media_source;
                    }
                    if (this.mediaTypeWidget && o.ui_state.media_type) {
                        console.log("[DEBUG] Setting mediaTypeWidget to:", o.ui_state.media_type);
                        this.mediaTypeWidget.value = o.ui_state.media_type;
                    }

                    // Store upload file info for later restoration (after updateMediaWidgets clears state)
                    this._pendingFileRestore = o.ui_state.uploaded_file_info;
                    console.log(
                        "[DEBUG] Stored _pendingFileRestore:",
                        JSON.stringify(this._pendingFileRestore, null, 2)
                    );

                    // Update UI to match restored state
                    setTimeout(() => {
                        console.log("[DEBUG] First timeout - calling updateMediaWidgets");
                        this.updateMediaWidgets();

                        // FIXED: Restore uploaded file information after updateMediaWidgets has run
                        // Need a second timeout to ensure widgets are fully created
                        setTimeout(() => {
                            console.log("[DEBUG] Second timeout - starting file restoration");
                            console.log(
                                "[DEBUG] _pendingFileRestore still exists:",
                                !!this._pendingFileRestore
                            );

                            if (this._pendingFileRestore) {
                                const fileInfo = this._pendingFileRestore;
                                console.log(
                                    "[DEBUG] Processing fileInfo:",
                                    JSON.stringify(fileInfo, null, 2)
                                );

                                // Debug: List all current widgets
                                console.log(
                                    "[DEBUG] Current widgets:",
                                    this.widgets.map((w) => ({
                                        name: w.name,
                                        type: w.type,
                                        value: w.value,
                                    }))
                                );

                                // Restore image upload state
                                if (fileInfo.image?.file) {
                                    console.log("[DEBUG] Restoring image state:", fileInfo.image);
                                    this.uploadedImageFile = fileInfo.image.file;
                                    this.uploadedImageSubfolder = fileInfo.image.subfolder;
                                    if (this.imageInfoWidget && fileInfo.image.display) {
                                        this.imageInfoWidget.value = fileInfo.image.display;
                                        console.log(
                                            "[DEBUG] Updated imageInfoWidget:",
                                            this.imageInfoWidget.value
                                        );
                                    }

                                    // Update the hidden widget with file path
                                    const originalUploadedImageWidget = this.widgets.find(
                                        (w) => w.name === "uploaded_image_file"
                                    );
                                    if (originalUploadedImageWidget) {
                                        originalUploadedImageWidget.value = `${this.uploadedImageSubfolder}/${this.uploadedImageFile}`;
                                        console.log(
                                            `[CONFIGURE] Restored image file: ${originalUploadedImageWidget.value}`
                                        );
                                    } else {
                                        console.log(
                                            "[DEBUG] WARNING: uploaded_image_file widget not found!"
                                        );
                                    }
                                }

                                // FIXED: Restore video upload state with proper widget handling
                                if (fileInfo.video?.file) {
                                    console.log("[DEBUG] Restoring video state:", fileInfo.video);
                                    this.uploadedVideoFile = fileInfo.video.file;
                                    this.uploadedVideoSubfolder = fileInfo.video.subfolder;

                                    console.log(
                                        "[DEBUG] Set uploadedVideoFile:",
                                        this.uploadedVideoFile
                                    );
                                    console.log(
                                        "[DEBUG] Set uploadedVideoSubfolder:",
                                        this.uploadedVideoSubfolder
                                    );

                                    // Ensure video info widget exists and update it
                                    if (this.videoInfoWidget) {
                                        if (fileInfo.video.display) {
                                            this.videoInfoWidget.value = fileInfo.video.display;
                                        } else {
                                            // Fallback display if display info is missing
                                            this.videoInfoWidget.value = `${this.uploadedVideoFile} (restored)`;
                                        }
                                        console.log(
                                            `[CONFIGURE] Restored video info widget: ${this.videoInfoWidget.value}`
                                        );
                                    } else {
                                        console.log("[DEBUG] WARNING: videoInfoWidget not found!");
                                    }

                                    // Update the hidden widget with file path
                                    const originalUploadedVideoWidget = this.widgets.find(
                                        (w) => w.name === "uploaded_video_file"
                                    );
                                    if (originalUploadedVideoWidget) {
                                        const filePath = `${this.uploadedVideoSubfolder}/${this.uploadedVideoFile}`;
                                        originalUploadedVideoWidget.value = filePath;
                                        console.log(
                                            `[CONFIGURE] Restored video file widget: ${originalUploadedVideoWidget.value}`
                                        );
                                    } else {
                                        console.log(
                                            "[DEBUG] WARNING: uploaded_video_file widget not found!"
                                        );
                                    }

                                    // Also ensure the videoFileWidget is updated if it exists
                                    if (this.videoFileWidget) {
                                        this.videoFileWidget.value = `${this.uploadedVideoSubfolder}/${this.uploadedVideoFile}`;
                                        console.log(
                                            `[CONFIGURE] Updated videoFileWidget: ${this.videoFileWidget.value}`
                                        );
                                    } else {
                                        console.log(
                                            "[DEBUG] videoFileWidget not found (this might be OK)"
                                        );
                                    }
                                } else {
                                    console.log("[DEBUG] No video file info to restore");
                                }

                                // Clean up temporary storage
                                delete this._pendingFileRestore;
                                console.log("[DEBUG] Cleaned up _pendingFileRestore");
                            } else {
                                console.log(
                                    "[DEBUG] No _pendingFileRestore found in second timeout"
                                );
                            }

                            console.log("[CONFIGURE] File state restoration complete");
                        }, 50); // Small delay to ensure widget creation is complete

                        console.log("[CONFIGURE] UI state restored and widgets updated");
                    }, 0);
                } else {
                    console.log("[CONFIGURE] No UI state found, using defaults");
                    // Ensure initial state is applied even without saved state
                    setTimeout(() => {
                        this.updateMediaWidgets();
                    }, 0);
                }

                return result;
            };

            // Add onExecuted method to update the final_string widget
            const onExecutedMedia = nodeType.prototype.onExecuted;
            nodeType.prototype.onExecuted = function (message) {
                const result = onExecutedMedia?.apply(this, arguments);
                return result;
            };

            // Method to clear current media type state only
            nodeType.prototype.clearCurrentMediaState = function () {
                const mediaType = this.mediaTypeWidget?.value || "image";

                if (mediaType === "video") {
                    // Clear video state
                    this.clearVideoPreview();
                    this.uploadedVideoFile = null;
                    this.uploadedVideoSubfolder = null;

                    if (this.videoInfoWidget) {
                        this.videoInfoWidget.value = "No video selected";
                    }
                    if (this.videoFileWidget) {
                        this.videoFileWidget.value = "";
                    }
                } else if (mediaType === "image") {
                    // Clear image state
                    this.uploadedImageFile = null;
                    this.uploadedImageSubfolder = null;

                    if (this.imageInfoWidget) {
                        this.imageInfoWidget.value = "No image selected";
                    }
                    if (this.imageFileWidget) {
                        this.imageFileWidget.value = "";
                    }
                }
            };

            // Add image upload handler
            nodeType.prototype.onImageUploadButtonPressed = function () {
                console.log("Image upload button pressed!");

                // Clear current image state before starting new upload
                this.clearCurrentMediaState();

                // Create file input element
                const fileInput = document.createElement("input");
                fileInput.type = "file";
                fileInput.accept = "image/*";
                fileInput.style.display = "none";

                fileInput.onchange = async (event) => {
                    const file = event.target.files[0];
                    if (!file) {
                        return;
                    }

                    // Validate file type
                    if (!file.type.startsWith("image/")) {
                        app.ui.dialog.show("Please select a valid image file.");
                        return;
                    }

                    // Show loading state
                    this.imageInfoWidget.value = "Uploading image...";

                    try {
                        // Upload the image file
                        const formData = new FormData();
                        formData.append("image", file);
                        formData.append("subfolder", "gemini_images");
                        formData.append("type", "input");

                        const uploadResponse = await fetch("/upload/image", {
                            method: "POST",
                            body: formData,
                        });

                        if (!uploadResponse.ok) {
                            throw new Error(`Upload failed: ${uploadResponse.statusText}`);
                        }

                        const uploadResult = await uploadResponse.json();

                        // Update the image info widget
                        this.imageInfoWidget.value = `${file.name} (${(
                            file.size /
                            1024 /
                            1024
                        ).toFixed(2)} MB)`;

                        // Store image info for processing
                        this.uploadedImageFile = uploadResult.name;
                        this.uploadedImageSubfolder = uploadResult.subfolder || "gemini_images";

                        // Use the original uploaded_image_file widget to store the file path
                        const originalUploadedImageWidget = this.widgets.find(
                            (w) => w.name === "uploaded_image_file"
                        );
                        if (originalUploadedImageWidget) {
                            originalUploadedImageWidget.value = `${this.uploadedImageSubfolder}/${this.uploadedImageFile}`;
                            console.log(
                                `[UPLOAD] Updated original uploaded_image_file widget: ${originalUploadedImageWidget.value}`
                            );
                        } else {
                            // Fallback: create a hidden widget if the original doesn't exist
                            if (!this.imageFileWidget) {
                                this.imageFileWidget = this.addWidget(
                                    "text",
                                    "uploaded_image_file",
                                    "",
                                    () => {},
                                    {}
                                );
                                this.imageFileWidget.serialize = true;
                                this.imageFileWidget.type = "hidden";
                            }
                            this.imageFileWidget.value = `${this.uploadedImageSubfolder}/${this.uploadedImageFile}`;
                        }

                        // Show success notification
                        app.extensionManager?.toast?.add({
                            severity: "success",
                            summary: "Image Upload",
                            detail: `Successfully uploaded ${file.name}`,
                            life: 3000,
                        });

                        console.log("Image uploaded:", uploadResult);
                    } catch (error) {
                        console.error("Upload error:", error);

                        // Clear everything on error
                        this.imageInfoWidget.value = "Upload failed";
                        this.uploadedImageFile = null;
                        this.uploadedImageSubfolder = null;

                        if (this.imageFileWidget) {
                            this.imageFileWidget.value = "";
                        }

                        app.ui.dialog.show(`Upload failed: ${error.message}`);
                    }

                    // Clean up
                    document.body.removeChild(fileInput);
                };

                // Trigger file selection
                document.body.appendChild(fileInput);
                fileInput.click();
            };

            // Add video upload handler (reuse from existing video node)
            nodeType.prototype.onVideoUploadButtonPressed = function () {
                console.log("Video upload button pressed!");

                // Clear current video state before starting new upload
                this.clearCurrentMediaState();

                // Create file input element
                const fileInput = document.createElement("input");
                fileInput.type = "file";
                fileInput.accept = "video/*";
                fileInput.style.display = "none";

                fileInput.onchange = async (event) => {
                    const file = event.target.files[0];
                    if (!file) {
                        // User cancelled, keep cleared state
                        return;
                    }

                    // Validate file type
                    if (!file.type.startsWith("video/")) {
                        app.ui.dialog.show("Please select a valid video file.");
                        return;
                    }

                    // Show loading state
                    this.videoInfoWidget.value = "Uploading video...";

                    try {
                        // Upload the video file
                        const formData = new FormData();
                        formData.append("image", file);
                        formData.append("subfolder", "gemini_videos");
                        formData.append("type", "input");

                        const uploadResponse = await fetch("/upload/image", {
                            method: "POST",
                            body: formData,
                        });

                        if (!uploadResponse.ok) {
                            throw new Error(`Upload failed: ${uploadResponse.statusText}`);
                        }

                        const uploadResult = await uploadResponse.json();

                        console.log("[DEBUG] Video upload successful, result:", uploadResult);

                        // Update the video info widget
                        this.videoInfoWidget.value = `${file.name} (${(
                            file.size /
                            1024 /
                            1024
                        ).toFixed(2)} MB)`;

                        // Store video info for processing
                        this.uploadedVideoFile = uploadResult.name;
                        this.uploadedVideoSubfolder = uploadResult.subfolder || "gemini_videos";

                        console.log("[DEBUG] Set uploadedVideoFile to:", this.uploadedVideoFile);
                        console.log(
                            "[DEBUG] Set uploadedVideoSubfolder to:",
                            this.uploadedVideoSubfolder
                        );
                        console.log("[DEBUG] Set videoInfoWidget to:", this.videoInfoWidget.value);

                        // Use the original uploaded_video_file widget to store the file path
                        const originalUploadedVideoWidget = this.widgets.find(
                            (w) => w.name === "uploaded_video_file"
                        );
                        if (originalUploadedVideoWidget) {
                            originalUploadedVideoWidget.value = `${this.uploadedVideoSubfolder}/${this.uploadedVideoFile}`;
                            console.log(
                                `[UPLOAD] Updated original uploaded_video_file widget: ${originalUploadedVideoWidget.value}`
                            );
                        } else {
                            console.log(
                                "[DEBUG] WARNING: uploaded_video_file widget not found during upload!"
                            );
                            // Fallback: create a hidden widget if the original doesn't exist
                            if (!this.videoFileWidget) {
                                this.videoFileWidget = this.addWidget(
                                    "text",
                                    "uploaded_video_file",
                                    "",
                                    () => {},
                                    {}
                                );
                                this.videoFileWidget.serialize = true;
                                this.videoFileWidget.type = "hidden";
                                console.log("[DEBUG] Created fallback videoFileWidget");
                            }
                            this.videoFileWidget.value = `${this.uploadedVideoSubfolder}/${this.uploadedVideoFile}`;
                            console.log(
                                "[DEBUG] Updated fallback videoFileWidget:",
                                this.videoFileWidget.value
                            );
                        }

                        // Debug: Show all widget states after upload
                        console.log("[DEBUG] All widgets after upload:");
                        this.widgets.forEach((w) => {
                            console.log(`  ${w.name}: ${w.value} (type: ${w.type})`);
                        });

                        // Show success notification
                        app.extensionManager?.toast?.add({
                            severity: "success",
                            summary: "Video Upload",
                            detail: `Successfully uploaded ${file.name}`,
                            life: 3000,
                        });

                        console.log("Video uploaded:", uploadResult);
                    } catch (error) {
                        console.error("Upload error:", error);

                        // Clear everything on error
                        this.clearVideoPreview();
                        this.videoInfoWidget.value = "Upload failed";
                        this.uploadedVideoFile = null;
                        this.uploadedVideoSubfolder = null;

                        if (this.videoFileWidget) {
                            this.videoFileWidget.value = "";
                        }

                        app.ui.dialog.show(`Upload failed: ${error.message}`);
                    }

                    // Clean up
                    document.body.removeChild(fileInput);
                };

                // Trigger file selection
                document.body.appendChild(fileInput);
                fileInput.click();
            };

            // Add video preview clearing method (minimal version for media node)
            nodeType.prototype.clearVideoPreview = function () {
                // For the media node, we don't have complex video preview
                // This is just a placeholder method
                console.log("Video preview cleared for media node");
            };
        }
    },

    // Hook to handle workflow loading
    loadedGraphNode(node, app) {
        if (node.comfyClass === "GeminiUtilMediaDescribe") {
            console.log("[LOADED] loadedGraphNode called for GeminiUtilMediaDescribe");

            // Check if this node has saved UI state with uploaded file data
            const hasSavedVideoData = node.ui_state?.uploaded_file_info?.video?.file;
            const hasSavedImageData = node.ui_state?.uploaded_file_info?.image?.file;

            console.log(
                "[LOADED] hasSavedVideoData:",
                !!hasSavedVideoData,
                "hasSavedImageData:",
                !!hasSavedImageData
            );
            console.log("[LOADED] Saved video file:", hasSavedVideoData);
            console.log("[LOADED] Saved image file:", hasSavedImageData);

            // Only call updateMediaWidgets if we don't have any saved uploaded file data
            // If we have saved data, onConfigure will handle the restoration
            if (!hasSavedVideoData && !hasSavedImageData && node.updateMediaWidgets) {
                console.log(
                    "[LOADED] No saved uploaded file data found, applying default UI state"
                );
                setTimeout(() => {
                    node.updateMediaWidgets();
                    console.log("[LOADED] Applied default UI state for loaded workflow node");
                }, 100); // Small delay to ensure all widgets are properly initialized
            } else {
                console.log(
                    "[LOADED] Saved uploaded file data found, skipping updateMediaWidgets to preserve onConfigure restoration"
                );
            }
        }
    },
});
