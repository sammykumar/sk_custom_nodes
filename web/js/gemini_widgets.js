import { app } from '../../../scripts/app.js'
import { api } from '../../../scripts/api.js'

console.log("Loading gemini_widgets.js extension - SIMPLE INLINE PREVIEW VERSION");

// Register custom widget for the Gemini Video Describe node
app.registerExtension({
    name: "sk_custom_nodes.gemini_widgets",
    
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "GeminiUtilVideoDescribe") {
            console.log("Registering GeminiUtilVideoDescribe node with inline video preview");
            
            // Add custom widget after the node is created
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                const result = onNodeCreated?.apply(this, arguments);
                
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
            
            // Method to show video preview as DOM widget (VHS approach)
            nodeType.prototype.showVideoPreview = function() {
                if (!this.uploadedVideoFile || !this.uploadedVideoSubfolder) {
                    return;
                }
                
                // Remove existing video widget if any
                if (this.videoWidget) {
                    const widgetIndex = this.widgets.indexOf(this.videoWidget);
                    if (widgetIndex !== -1) {
                        this.widgets.splice(widgetIndex, 1);
                    }
                }
                
                // Create video preview HTML
                const videoUrl = `/view?filename=${this.uploadedVideoFile}&subfolder=${this.uploadedVideoSubfolder}&type=input&t=${Date.now()}`;
                
                // Create container element
                const element = document.createElement("div");
                const previewNode = this;
                
                // Create a DOM widget using ComfyUI's built-in method (same as VHS)
                this.videoWidget = this.addDOMWidget("videopreview", "preview", element, {
                    serialize: false,
                    hideOnZoom: false,
                    getValue() {
                        return element.value;
                    },
                    setValue(v) {
                        element.value = v;
                    }
                });
                
                // Add drag support
                this.allowDragFromWidget(this.videoWidget);
                
                // Set up compute size for proper layout
                this.videoWidget.computeSize = function(width) {
                    if (this.aspectRatio && !this.parentEl.hidden) {
                        let height = (previewNode.size[0] - 20) / this.aspectRatio + 80; // Extra space for controls
                        if (!(height > 0)) {
                            height = 0;
                        }
                        this.computedHeight = height + 10;
                        return [width, height];
                    }
                    return [width, 350]; // Default height when no video loaded
                };
                
                // Add event listeners for canvas interaction
                element.addEventListener('contextmenu', (e) => {
                    e.preventDefault();
                    return app.canvas._mousedown_callback(e);
                }, true);
                
                element.addEventListener('pointerdown', (e) => {
                    e.preventDefault();
                    return app.canvas._mousedown_callback(e);
                }, true);
                
                element.addEventListener('mousewheel', (e) => {
                    e.preventDefault();
                    return app.canvas._mousewheel_callback(e);
                }, true);
                
                element.addEventListener('pointermove', (e) => {
                    e.preventDefault();
                    return app.canvas._mousemove_callback(e);
                }, true);
                
                element.addEventListener('pointerup', (e) => {
                    e.preventDefault();
                    return app.canvas._mouseup_callback(e);
                }, true);
                
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
                        style="width: 100%;"
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
            nodeType.prototype.allowDragFromWidget = function(widget) {
                widget.onPointerDown = function(pointer, node) {
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
            nodeType.prototype.setupVideoControls = function() {
                this.videoElement = document.getElementById(`video-${this.id}`);
                this.timeDisplay = document.getElementById(`time-display-${this.id}`);
                
                // Check for missing elements
                if (!this.videoElement || !this.timeDisplay) {
                    console.error("Could not find video elements for node:", this.id);
                    return;
                }
                
                // Video loaded event
                this.videoElement.addEventListener('loadedmetadata', () => {
                    this.duration = this.videoElement.duration;
                    this.endTime = this.duration;
                    this.startTime = 0;
                    
                    // Update widget aspect ratio for proper sizing
                    if (this.videoWidget) {
                        this.videoWidget.aspectRatio = this.videoElement.videoWidth / this.videoElement.videoHeight;
                        this.setSize(this.computeSize());
                    }
                    
                    this.timeDisplay.textContent = `Duration: ${this.duration.toFixed(1)}s`;
                    console.log(`Video loaded: ${this.duration}s duration`);
                });
                
                // Video error event
                this.videoElement.addEventListener('error', () => {
                    console.error("Video failed to load");
                    if (this.videoWidget && this.videoWidget.parentEl) {
                        this.videoWidget.parentEl.hidden = true;
                        this.setSize(this.computeSize());
                    }
                });
                
                // Video time update
                this.videoElement.addEventListener('timeupdate', () => {
                    if (this.videoElement.currentTime >= this.endTime) {
                        this.videoElement.pause();
                        this.videoElement.currentTime = this.endTime;
                    }
                    
                    // Update time display during playback
                    const current = this.videoElement.currentTime;
                    const total = this.duration || this.videoElement.duration;
                    this.timeDisplay.textContent = `${current.toFixed(1)}s / ${total.toFixed(1)}s`;
                });
            };
            
            // Update node parameters
            nodeType.prototype.updateNodeParams = function() {
                const startTimeWidget = this.widgets.find(w => w.name === 'start_time');
                const maxDurationWidget = this.widgets.find(w => w.name === 'max_duration');
                
                if (startTimeWidget) {
                    startTimeWidget.value = this.startTime;
                }
                
                if (maxDurationWidget) {
                    const duration = this.endTime - this.startTime;
                    maxDurationWidget.value = duration;
                }
            };
            
            // Add the upload button press handler
            nodeType.prototype.onUploadButtonPressed = function() {
                console.log("Upload button pressed!");
                
                // Create file input element
                const fileInput = document.createElement("input");
                fileInput.type = "file";
                fileInput.accept = "video/*";
                fileInput.style.display = "none";
                
                fileInput.onchange = async (event) => {
                    const file = event.target.files[0];
                    if (!file) return;
                    
                    // Validate file type
                    if (!file.type.startsWith('video/')) {
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
                            body: formData
                        });
                        
                        if (!uploadResponse.ok) {
                            throw new Error(`Upload failed: ${uploadResponse.statusText}`);
                        }
                        
                        const uploadResult = await uploadResponse.json();
                        
                        // Update the video info widget
                        this.videoInfoWidget.value = `${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`;
                        
                        // Store video info for processing
                        this.uploadedVideoFile = uploadResult.name;
                        this.uploadedVideoSubfolder = uploadResult.subfolder || "gemini_videos";
                        
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
                            severity: 'success',
                            summary: 'Video Upload',
                            detail: `Successfully uploaded ${file.name}`,
                            life: 3000
                        });
                        
                        console.log("Video uploaded:", uploadResult);
                        
                    } catch (error) {
                        console.error("Upload error:", error);
                        this.videoInfoWidget.value = "Upload failed";
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
    }
});

// Global helper functions for video controls
window.setVideoRange = function(nodeId, start, duration) {
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

window.resetVideoRange = function(nodeId) {
    const node = app.graph.getNodeById(nodeId);
    if (node && node.duration) {
        node.startTime = 0;
        node.endTime = node.duration;
        
        node.updateTimeDisplay();
        node.updateNodeParams();
    }
};

window.playVideoSelection = function(nodeId) {
    const node = app.graph.getNodeById(nodeId);
    if (node && node.videoElement) {
        node.videoElement.currentTime = node.startTime;
        node.videoElement.play();
    }
};