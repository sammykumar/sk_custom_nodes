import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";

console.log("Loading gemini_widgets.js extension");

// Register custom widget for the Gemini Video Describe node
app.registerExtension({
    name: "sk_custom_nodes.gemini_widgets",

    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "GeminiUtilVideoDescribe") {
            console.log(
                "Registering GeminiUtilVideoDescribe node with inline video preview"
            );

            // Add custom widget after the node is created
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                const result = onNodeCreated?.apply(this, arguments);

                // Add a read-only final_string display widget
                this.finalStringWidget = this.addWidget(
                    "text",
                    "final_string",
                    "Populated Prompt (Will be generated automatically)",
                    () => {},
                    {
                        readonly: true,
                        multiline: true,
                        inputStyle: {
                            backgroundColor: "#1a1a1a",
                            border: "1px solid #444",
                            color: "#ccc",
                            padding: "8px",
                            borderRadius: "4px",
                            minHeight: "60px",
                            fontFamily: "monospace",
                            fontSize: "12px",
                        },
                    }
                );
                this.finalStringWidget.serialize = false;

                // Add a video upload button widget
                const uploadButton = this.addWidget(
                    "button",
                    "📁 Choose Video to Upload",
                    "upload",
                    () => {
                        this.onUploadButtonPressed();
                    }
                );
                uploadButton.serialize = false;

                // Add a widget to display the selected video info
                this.videoInfoWidget = this.addWidget(
                    "text",
                    "video_file",
                    "No video selected",
                    () => {},
                    {}
                );
                this.videoInfoWidget.serialize = false;

                // Create video preview container that will be attached to the node
                this.videoElement = null;
                this.timeDisplay = null;
                this.scrubberContainer = null;
                this.duration = 0;
                this.startTime = 0;
                this.endTime = 0;

                return result;
            };

            // Add onExecuted method to update the final_string widget
            const onExecuted = nodeType.prototype.onExecuted;
            nodeType.prototype.onExecuted = function (message) {
                const result = onExecuted?.apply(this, arguments);

                // Update final_string widget with the actual output
                if (message && message.output && this.finalStringWidget) {
                    // final_string is the 5th output (index 4) for GeminiUtilVideoDescribe
                    const finalStringOutput = message.output[4];
                    if (finalStringOutput && finalStringOutput.length > 0) {
                        this.finalStringWidget.value = finalStringOutput[0];
                        console.log(
                            "Updated final_string widget with:",
                            finalStringOutput[0]
                        );
                    }
                }

                return result;
            };

            // Method to clear previous video preview
            nodeType.prototype.clearVideoPreview = function () {
                // Stop and clear existing video element
                if (this.videoElement) {
                    this.videoElement.pause();
                    this.videoElement.src = "";
                    this.videoElement.load(); // Reset the video element
                    this.videoElement = null;
                }

                // Clear DOM references
                this.timeDisplay = null;
                this.scrubberContainer = null;

                // Remove existing video widget if any
                if (this.videoWidget) {
                    // Remove DOM element if it exists
                    if (
                        this.videoWidget.parentEl &&
                        this.videoWidget.parentEl.parentNode
                    ) {
                        this.videoWidget.parentEl.parentNode.removeChild(
                            this.videoWidget.parentEl
                        );
                    }

                    const widgetIndex = this.widgets.indexOf(this.videoWidget);
                    if (widgetIndex !== -1) {
                        this.widgets.splice(widgetIndex, 1);
                    }
                    this.videoWidget = null;
                }

                // Reset video properties
                this.duration = 0;
                this.startTime = 0;
                this.endTime = 0;
            };

            // Method to show video preview as DOM widget (VHS approach)
            nodeType.prototype.showVideoPreview = function () {
                if (!this.uploadedVideoFile || !this.uploadedVideoSubfolder) {
                    return;
                }

                // Clear any existing video preview first
                this.clearVideoPreview();

                // Create video preview HTML
                const videoUrl = `/view?filename=${
                    this.uploadedVideoFile
                }&subfolder=${
                    this.uploadedVideoSubfolder
                }&type=input&t=${Date.now()}`;

                // Create container element
                const element = document.createElement("div");
                const previewNode = this;

                // Create a DOM widget using ComfyUI's built-in method (same as VHS)
                this.videoWidget = this.addDOMWidget(
                    "videopreview",
                    "preview",
                    element,
                    {
                        serialize: false,
                        hideOnZoom: false,
                        getValue() {
                            return element.value;
                        },
                        setValue(v) {
                            element.value = v;
                        },
                    }
                );

                // Add drag support
                this.allowDragFromWidget(this.videoWidget);

                // Set up compute size for proper layout
                this.videoWidget.computeSize = function (width) {
                    // Always return a fixed height regardless of video aspect ratio
                    // This prevents the node from resizing when video is loaded
                    const fixedHeight = 350; // Fixed height for the widget container
                    return [width, fixedHeight];
                };

                // Add event listeners for canvas interaction
                element.addEventListener(
                    "contextmenu",
                    (e) => {
                        e.preventDefault();
                        return app.canvas._mousedown_callback(e);
                    },
                    true
                );

                element.addEventListener(
                    "pointerdown",
                    (e) => {
                        e.preventDefault();
                        return app.canvas._mousedown_callback(e);
                    },
                    true
                );

                element.addEventListener(
                    "mousewheel",
                    (e) => {
                        e.preventDefault();
                        return app.canvas._mousewheel_callback(e);
                    },
                    true
                );

                element.addEventListener(
                    "pointermove",
                    (e) => {
                        e.preventDefault();
                        return app.canvas._mousemove_callback(e);
                    },
                    true
                );

                element.addEventListener(
                    "pointerup",
                    (e) => {
                        e.preventDefault();
                        return app.canvas._mouseup_callback(e);
                    },
                    true
                );

                // Create parent container for the video widget
                this.videoWidget.parentEl = document.createElement("div");
                this.videoWidget.parentEl.className = "gemini_video_preview";
                this.videoWidget.parentEl.style.cssText = `
                    width: 100%;
                    padding: 10px;
                    box-sizing: border-box;
                `;

                // Add the HTML content
                this.videoWidget.parentEl.innerHTML = `
                    <video 
                        id="video-${this.id}"
                        loop
                        autoplay 
                        controls
                        style="
                            width: 100%;
                            background: #000;
                        "
                    >
                        <source src="${videoUrl}" type="video/mp4">
                        Your browser does not support video playback.
                    </video>
                    
                    <div id="time-display-${this.id}" style="color: #ccc; font-size: 12px; margin-bottom: 10px; text-align: center;">
                        Click play to preview video
                    </div>
                `;

                // Append to the main element
                element.appendChild(this.videoWidget.parentEl);

                // Set up video controls after DOM is ready
                setTimeout(() => {
                    this.setupVideoControls();
                }, 0);

                // Force node to recalculate size
                this.setSize(this.computeSize());
            };

            // Helper method for drag support (from VHS)
            nodeType.prototype.allowDragFromWidget = function (widget) {
                widget.onPointerDown = function (pointer, node) {
                    pointer.onDragStart = () => {
                        app.canvas.emitBeforeChange();
                        app.canvas.graph?.beforeChange();
                        app.canvas.processSelect(node, pointer.eDown, true);
                        app.canvas.isDragging = true;
                    };
                    pointer.onDragEnd = () => {
                        app.canvas.isDragging = false;
                        app.canvas.graph?.afterChange();
                        app.canvas.emitAfterChange();
                        app.canvas.dirty_canvas = true;
                        app.canvas.dirty_bgcanvas = true;
                    };
                    app.canvas.dirty_canvas = true;
                    return true;
                };
            };

            // Setup video controls
            nodeType.prototype.setupVideoControls = function () {
                this.videoElement = document.getElementById(`video-${this.id}`);
                this.timeDisplay = document.getElementById(
                    `time-display-${this.id}`
                );

                // Check for missing elements
                if (!this.videoElement || !this.timeDisplay) {
                    console.error(
                        "Could not find video elements for node:",
                        this.id
                    );
                    return;
                }

                // Video loaded event
                this.videoElement.addEventListener("loadedmetadata", () => {
                    this.duration = this.videoElement.duration;
                    this.endTime = this.duration;
                    this.startTime = 0;

                    // Don't update widget aspect ratio to prevent resizing
                    // The video will maintain its aspect ratio using CSS object-fit: contain

                    this.timeDisplay.textContent = `Duration: ${this.duration.toFixed(
                        1
                    )}s`;
                    console.log(`Video loaded: ${this.duration}s duration`);
                });

                // Video error event
                this.videoElement.addEventListener("error", () => {
                    console.error("Video failed to load");
                    if (this.videoWidget && this.videoWidget.parentEl) {
                        this.videoWidget.parentEl.hidden = true;
                        this.setSize(this.computeSize());
                    }
                });

                // Video time update
                this.videoElement.addEventListener("timeupdate", () => {
                    if (this.videoElement.currentTime >= this.endTime) {
                        this.videoElement.pause();
                        this.videoElement.currentTime = this.endTime;
                    }

                    // Update time display during playback
                    const current = this.videoElement.currentTime;
                    const total = this.duration || this.videoElement.duration;
                    this.timeDisplay.textContent = `${current.toFixed(
                        1
                    )}s / ${total.toFixed(1)}s`;
                });
            };

            // Update node parameters
            nodeType.prototype.updateNodeParams = function () {
                const startTimeWidget = this.widgets.find(
                    (w) => w.name === "start_time"
                );
                const maxDurationWidget = this.widgets.find(
                    (w) => w.name === "max_duration"
                );

                if (startTimeWidget) {
                    startTimeWidget.value = this.startTime;
                }

                if (maxDurationWidget) {
                    const duration = this.endTime - this.startTime;
                    maxDurationWidget.value = duration;
                }
            };

            // Add the upload button press handler
            nodeType.prototype.onUploadButtonPressed = function () {
                console.log("Upload button pressed!");

                // Clear any existing video preview immediately
                this.clearVideoPreview();

                // Reset video info widget
                this.videoInfoWidget.value = "No video selected";

                // Clear stored video file info
                this.uploadedVideoFile = null;
                this.uploadedVideoSubfolder = null;

                // Clear hidden widget if it exists
                if (this.videoFileWidget) {
                    this.videoFileWidget.value = "";
                }

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
                            throw new Error(
                                `Upload failed: ${uploadResponse.statusText}`
                            );
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
                        this.uploadedVideoSubfolder =
                            uploadResult.subfolder || "gemini_videos";

                        // Add a hidden widget to store the video file path for the Python node
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

                        // Store the file path in the hidden widget
                        this.videoFileWidget.value = `${this.uploadedVideoSubfolder}/${this.uploadedVideoFile}`;

                        // Show the video preview
                        this.showVideoPreview();

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
        }

        // Handle GeminiUtilImageDescribe node
        else if (nodeData.name === "GeminiUtilImageDescribe") {
            console.log(
                "Registering GeminiUtilImageDescribe node with final_string display"
            );

            // Add custom widget after the node is created
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                const result = onNodeCreated?.apply(this, arguments);

                // Add a read-only final_string display widget
                this.finalStringWidget = this.addWidget(
                    "text",
                    "final_string",
                    "Populated Prompt (Will be generated automatically)",
                    () => {},
                    {
                        readonly: true,
                        multiline: true,
                        inputStyle: {
                            backgroundColor: "#1a1a1a",
                            border: "1px solid #444",
                            color: "#ccc",
                            padding: "8px",
                            borderRadius: "4px",
                            minHeight: "60px",
                            fontFamily: "monospace",
                            fontSize: "12px",
                        },
                    }
                );
                this.finalStringWidget.serialize = false;

                return result;
            };

            // Add onExecuted method to update the final_string widget
            const onExecutedImage = nodeType.prototype.onExecuted;
            nodeType.prototype.onExecuted = function (message) {
                const result = onExecutedImage?.apply(this, arguments);

                // Update final_string widget with the actual output
                if (message && message.output && this.finalStringWidget) {
                    // final_string is the 3rd output (index 2) for GeminiUtilImageDescribe
                    const finalStringOutput = message.output[2];
                    if (finalStringOutput && finalStringOutput.length > 0) {
                        this.finalStringWidget.value = finalStringOutput[0];
                        console.log(
                            "Updated final_string widget with:",
                            finalStringOutput[0]
                        );
                    }
                }

                return result;
            };
        }
        // Handle GeminiUtilMediaDescribe node
        else if (nodeData.name === "GeminiUtilMediaDescribe") {
            console.log(
                "Registering GeminiUtilMediaDescribe node with dynamic media widgets"
            );

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
                    ];

                    for (const widgetName of widgetsToHide) {
                        const widget = this.widgets.find(
                            (w) => w.name === widgetName
                        );
                        if (widget) {
                            // Hide the widget by setting its type to 'hidden'
                            widget.type = "hidden";
                            widget.computeSize = () => [0, -4]; // Make it take no space
                            console.log(
                                `[WIDGET] Hidden optional input widget: ${widgetName}`
                            );
                        }
                    }
                };

                // Hide the optional input widgets immediately
                this.hideOptionalInputWidgets();

                // Find the media_source widget
                this.mediaSourceWidget = this.widgets.find(
                    (w) => w.name === "media_source"
                );

                // Find the media_type widget
                this.mediaTypeWidget = this.widgets.find(
                    (w) => w.name === "media_type"
                );

                // Add a read-only final_string display widget
                this.finalStringWidget = this.addWidget(
                    "text",
                    "final_string",
                    "Populated Prompt (Will be generated automatically)",
                    () => {},
                    {
                        readonly: true,
                        multiline: true,
                        inputStyle: {
                            backgroundColor: "#1a1a1a",
                            border: "1px solid #444",
                            color: "#ccc",
                            padding: "8px",
                            borderRadius: "4px",
                            minHeight: "60px",
                            fontFamily: "monospace",
                            fontSize: "12px",
                        },
                    }
                );
                this.finalStringWidget.serialize = false;

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
                    const mediaSource =
                        this.mediaSourceWidget?.value || "Upload Media";
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

                        // Hide upload file widgets
                        if (originalUploadedImageWidget) {
                            originalUploadedImageWidget.type = "hidden";
                            originalUploadedImageWidget.computeSize = () => [
                                0, -4,
                            ];
                        }
                        if (originalUploadedVideoWidget) {
                            originalUploadedVideoWidget.type = "hidden";
                            originalUploadedVideoWidget.computeSize = () => [
                                0, -4,
                            ];
                        }
                    } else {
                        // Upload Media mode - Show appropriate upload widgets based on media_type
                        console.log(
                            "[STATE] Upload Media mode - hiding media_path widget"
                        );

                        // Hide the original media_path widget
                        if (originalMediaPathWidget) {
                            originalMediaPathWidget.type = "hidden";
                            originalMediaPathWidget.computeSize = () => [0, -4];
                        }

                        if (mediaType === "image") {
                            console.log(
                                "[STATE] Creating image upload widgets"
                            );

                            // Hide the video upload widget, show image upload widget reference
                            if (originalUploadedVideoWidget) {
                                originalUploadedVideoWidget.type = "hidden";
                                originalUploadedVideoWidget.computeSize =
                                    () => [0, -4];
                            }
                            if (originalUploadedImageWidget) {
                                originalUploadedImageWidget.type = "hidden"; // Keep hidden, we'll use a custom widget
                                originalUploadedImageWidget.computeSize =
                                    () => [0, -4];
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
                            console.log(
                                "[STATE] Creating video upload widgets"
                            );

                            // Hide the image upload widget, show video upload widget reference
                            if (originalUploadedImageWidget) {
                                originalUploadedImageWidget.type = "hidden";
                                originalUploadedImageWidget.computeSize =
                                    () => [0, -4];
                            }
                            if (originalUploadedVideoWidget) {
                                originalUploadedVideoWidget.type = "hidden"; // Keep hidden, we'll use a custom widget
                                originalUploadedVideoWidget.computeSize =
                                    () => [0, -4];
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
                    const originalSourceCallback =
                        this.mediaSourceWidget.callback;
                    this.mediaSourceWidget.callback = (value) => {
                        if (originalSourceCallback)
                            originalSourceCallback.call(
                                this.mediaSourceWidget,
                                value
                            );
                        this.updateMediaWidgets();
                    };
                }

                // Hook into media_type widget changes
                if (this.mediaTypeWidget) {
                    const originalTypeCallback = this.mediaTypeWidget.callback;
                    this.mediaTypeWidget.callback = (value) => {
                        if (originalTypeCallback)
                            originalTypeCallback.call(
                                this.mediaTypeWidget,
                                value
                            );
                        this.updateMediaWidgets();
                    };
                }

                return result;
            };

            // Add onExecuted method to update the final_string widget
            const onExecutedMedia = nodeType.prototype.onExecuted;
            nodeType.prototype.onExecuted = function (message) {
                const result = onExecutedMedia?.apply(this, arguments);

                // Update final_string widget with the actual output
                if (message && message.output && this.finalStringWidget) {
                    // final_string is the 3rd output (index 2) for GeminiUtilMediaDescribe
                    const finalStringOutput = message.output[2];
                    if (finalStringOutput && finalStringOutput.length > 0) {
                        this.finalStringWidget.value = finalStringOutput[0];
                        console.log(
                            "Updated final_string widget with:",
                            finalStringOutput[0]
                        );
                    }
                }

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
                            throw new Error(
                                `Upload failed: ${uploadResponse.statusText}`
                            );
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
                        this.uploadedImageSubfolder =
                            uploadResult.subfolder || "gemini_images";

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
                            throw new Error(
                                `Upload failed: ${uploadResponse.statusText}`
                            );
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
                        this.uploadedVideoSubfolder =
                            uploadResult.subfolder || "gemini_videos";

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
});

// Global helper functions for video controls
window.setVideoRange = function (nodeId, start, duration) {
    const node = app.graph.getNodeById(nodeId);
    if (node && node.duration) {
        node.startTime = start;
        node.endTime = Math.min(start + duration, node.duration);

        node.updateTimeDisplay();
        node.updateNodeParams();

        if (node.videoElement) {
            node.videoElement.currentTime = node.startTime;
        }
    }
};

window.resetVideoRange = function (nodeId) {
    const node = app.graph.getNodeById(nodeId);
    if (node && node.duration) {
        node.startTime = 0;
        node.endTime = node.duration;

        node.updateTimeDisplay();
        node.updateNodeParams();
    }
};

window.playVideoSelection = function (nodeId) {
    const node = app.graph.getNodeById(nodeId);
    if (node && node.videoElement) {
        node.videoElement.currentTime = node.startTime;
        node.videoElement.play();
    }
};
