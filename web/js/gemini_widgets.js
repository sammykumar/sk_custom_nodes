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
                    // Clear video state and preview
                    this.clearVideoPreview();
                    this.uploadedVideoFile = null;
                    this.uploadedVideoSubfolder = null;

                    // Clear image state
                    this.uploadedImageFile = null;
                    this.uploadedImageSubfolder = null;

                    // Reset widget values to defaults (only upload-related widgets)
                    if (this.videoInfoWidget) {
                        this.videoInfoWidget.value = "No video selected";
                    }
                    if (this.imageInfoWidget) {
                        this.imageInfoWidget.value = "No image selected";
                    }
                    // Don't clear media_path as it's not related to upload state
                    // if (this.mediaPathWidget) {
                    //     this.mediaPathWidget.value = "";
                    // }

                    // Clear hidden widgets that store file paths for Python node
                    if (this.videoFileWidget) {
                        this.videoFileWidget.value = "";
                    }
                    if (this.imageFileWidget) {
                        this.imageFileWidget.value = "";
                    }

                    // Also clear the original input widgets
                    const originalUploadedImageWidget = this.widgets.find(
                        (w) => w.name === "uploaded_image_file"
                    );
                    const originalUploadedVideoWidget = this.widgets.find(
                        (w) => w.name === "uploaded_video_file"
                    );

                    if (originalUploadedImageWidget) {
                        originalUploadedImageWidget.value = "";
                    }
                    if (originalUploadedVideoWidget) {
                        originalUploadedVideoWidget.value = "";
                    }
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

                    // Clear all previous media state when switching configurations
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
                            display: this.imageInfoWidget?.value
                        },
                        video: {
                            file: this.uploadedVideoFile,
                            subfolder: this.uploadedVideoSubfolder,
                            display: this.videoInfoWidget?.value
                        }
                    }
                };

                console.log("[SERIALIZE] Saving UI state:", o.ui_state);
                return result;
            };

            // Add onConfigure method to restore UI state
            const onConfigure = nodeType.prototype.onConfigure;
            nodeType.prototype.onConfigure = function (o) {
                const result = onConfigure?.apply(this, arguments);

                // Restore UI state after widgets are created
                if (o.ui_state) {
                    console.log("[CONFIGURE] Restoring UI state:", o.ui_state);

                    // Set widget values if they exist
                    if (this.mediaSourceWidget && o.ui_state.media_source) {
                        this.mediaSourceWidget.value = o.ui_state.media_source;
                    }
                    if (this.mediaTypeWidget && o.ui_state.media_type) {
                        this.mediaTypeWidget.value = o.ui_state.media_type;
                    }

                    // Store upload file info for later restoration (after updateMediaWidgets clears state)
                    this._pendingFileRestore = o.ui_state.uploaded_file_info;

                    // Update UI to match restored state
                    setTimeout(() => {
                        this.updateMediaWidgets();
                        
                        // Restore uploaded file information after updateMediaWidgets has run
                        if (this._pendingFileRestore) {
                            const fileInfo = this._pendingFileRestore;
                            
                            // Restore image upload state
                            if (fileInfo.image?.file) {
                                this.uploadedImageFile = fileInfo.image.file;
                                this.uploadedImageSubfolder = fileInfo.image.subfolder;
                                if (this.imageInfoWidget && fileInfo.image.display) {
                                    this.imageInfoWidget.value = fileInfo.image.display;
                                }
                                
                                // Update the hidden widget with file path
                                const originalUploadedImageWidget = this.widgets.find(
                                    (w) => w.name === "uploaded_image_file"
                                );
                                if (originalUploadedImageWidget) {
                                    originalUploadedImageWidget.value = `${this.uploadedImageSubfolder}/${this.uploadedImageFile}`;
                                    console.log(`[CONFIGURE] Restored image file: ${originalUploadedImageWidget.value}`);
                                }
                            }
                            
                            // Restore video upload state  
                            if (fileInfo.video?.file) {
                                this.uploadedVideoFile = fileInfo.video.file;
                                this.uploadedVideoSubfolder = fileInfo.video.subfolder;
                                if (this.videoInfoWidget && fileInfo.video.display) {
                                    this.videoInfoWidget.value = fileInfo.video.display;
                                }
                                
                                // Update the hidden widget with file path
                                const originalUploadedVideoWidget = this.widgets.find(
                                    (w) => w.name === "uploaded_video_file"
                                );
                                if (originalUploadedVideoWidget) {
                                    originalUploadedVideoWidget.value = `${this.uploadedVideoSubfolder}/${this.uploadedVideoFile}`;
                                    console.log(`[CONFIGURE] Restored video file: ${originalUploadedVideoWidget.value}`);
                                }
                            }
                            
                            // Clean up temporary storage
                            delete this._pendingFileRestore;
                        }
                        
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

                        // Update the video info widget
                        this.videoInfoWidget.value = `${file.name} (${(
                            file.size /
                            1024 /
                            1024
                        ).toFixed(2)} MB)`;

                        // Store video info for processing
                        this.uploadedVideoFile = uploadResult.name;
                        this.uploadedVideoSubfolder = uploadResult.subfolder || "gemini_videos";

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
                            }
                            this.videoFileWidget.value = `${this.uploadedVideoSubfolder}/${this.uploadedVideoFile}`;
                        }

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
            // Ensure UI state is applied when workflow is loaded
            if (node.updateMediaWidgets) {
                setTimeout(() => {
                    node.updateMediaWidgets();
                    console.log("[LOADED] Applied UI state for loaded workflow node");
                }, 100); // Small delay to ensure all widgets are properly initialized
            }
        }
    },
});
