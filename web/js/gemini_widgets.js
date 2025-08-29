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
                this.createVideoPreview();
                
                return result;
            };
            
            // Method to create video preview
            nodeType.prototype.createVideoPreview = function() {
                // We'll inject the video preview HTML directly into the node's DOM
                this.videoPreviewContainer = null;
                this.videoElement = null;
                this.startSlider = null;
                this.endSlider = null;
                this.duration = 0;
                this.startTime = 0;
                this.endTime = 0;
            };
            
            // Method to show video preview inline
            nodeType.prototype.showVideoPreview = function() {
                if (!this.uploadedVideoFile || !this.uploadedVideoSubfolder) {
                    return;
                }
                
                // Remove existing preview if any
                if (this.videoPreviewContainer) {
                    this.videoPreviewContainer.remove();
                }
                
                // Create video preview HTML
                const videoUrl = `/view?filename=${this.uploadedVideoFile}&subfolder=${this.uploadedVideoSubfolder}&type=input&t=${Date.now()}`;
                
                // Create container
                this.videoPreviewContainer = document.createElement('div');
                this.videoPreviewContainer.style.cssText = `
                    background: #1e1e1e;
                    border: 1px solid #444;
                    border-radius: 6px;
                    padding: 15px;
                    margin: 10px 0;
                    width: 100%;
                    box-sizing: border-box;
                `;
                
                this.videoPreviewContainer.innerHTML = `
                    <div style="color: #fff; font-weight: bold; margin-bottom: 10px; font-size: 14px;">
                        🎬 Video Timeline Controls
                    </div>
                    <video 
                        id="video-${this.id}"
                        controls 
                        preload="metadata" 
                        style="width: 100%; max-height: 200px; border-radius: 4px; background: #000; margin-bottom: 15px;"
                    >
                        <source src="${videoUrl}" type="video/mp4">
                        Your browser does not support video playback.
                    </video>
                    
                    <div id="time-display-${this.id}" style="color: #ccc; font-size: 12px; margin-bottom: 10px; text-align: center;">
                        Loading video...
                    </div>
                    
                    <div style="margin-bottom: 10px;">
                        <label style="color: #ccc; font-size: 12px; display: block; margin-bottom: 5px;">Start Time:</label>
                        <input type="range" id="start-slider-${this.id}" min="0" max="100" value="0" 
                               style="width: 100%; margin-bottom: 10px; accent-color: #4CAF50;">
                    </div>
                    
                    <div style="margin-bottom: 15px;">
                        <label style="color: #ccc; font-size: 12px; display: block; margin-bottom: 5px;">End Time:</label>
                        <input type="range" id="end-slider-${this.id}" min="0" max="100" value="100" 
                               style="width: 100%; margin-bottom: 10px; accent-color: #FF9800;">
                    </div>
                    
                    <div style="display: flex; gap: 5px; margin-bottom: 10px; flex-wrap: wrap;">
                        <button onclick="window.setVideoRange(${this.id}, 0, 5)" style="background: #444; border: 1px solid #666; color: #ccc; padding: 4px 8px; border-radius: 3px; cursor: pointer; font-size: 11px;">First 5s</button>
                        <button onclick="window.setVideoRange(${this.id}, 0, 10)" style="background: #444; border: 1px solid #666; color: #ccc; padding: 4px 8px; border-radius: 3px; cursor: pointer; font-size: 11px;">First 10s</button>
                        <button onclick="window.setVideoRange(${this.id}, 0, 30)" style="background: #444; border: 1px solid #666; color: #ccc; padding: 4px 8px; border-radius: 3px; cursor: pointer; font-size: 11px;">First 30s</button>
                        <button onclick="window.resetVideoRange(${this.id})" style="background: #444; border: 1px solid #666; color: #ccc; padding: 4px 8px; border-radius: 3px; cursor: pointer; font-size: 11px;">Full Video</button>
                    </div>
                    
                    <div style="display: flex; gap: 5px; justify-content: center;">
                        <button onclick="window.playVideoSelection(${this.id})" style="background: #2196F3; border: none; color: white; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 12px;">▶️ Play Selection</button>
                    </div>
                `;
                
                // Find the node element and append preview
                const nodeElement = document.querySelector(`[data-node-id="${this.id}"]`);
                if (nodeElement) {
                    nodeElement.appendChild(this.videoPreviewContainer);
                } else {
                    // Fallback: append to document body with positioning
                    document.body.appendChild(this.videoPreviewContainer);
                    this.videoPreviewContainer.style.position = 'fixed';
                    this.videoPreviewContainer.style.top = '100px';
                    this.videoPreviewContainer.style.left = '100px';
                    this.videoPreviewContainer.style.zIndex = '10000';
                    this.videoPreviewContainer.style.maxWidth = '400px';
                }
                
                // Set up event listeners
                this.setupVideoControls();
            };
            
            // Setup video controls
            nodeType.prototype.setupVideoControls = function() {
                this.videoElement = document.getElementById(`video-${this.id}`);
                this.startSlider = document.getElementById(`start-slider-${this.id}`);
                this.endSlider = document.getElementById(`end-slider-${this.id}`);
                this.timeDisplay = document.getElementById(`time-display-${this.id}`);
                
                if (!this.videoElement || !this.startSlider || !this.endSlider) {
                    console.error("Could not find video controls");
                    return;
                }
                
                // Video loaded event
                this.videoElement.addEventListener('loadedmetadata', () => {
                    this.duration = this.videoElement.duration;
                    this.endTime = this.duration;
                    this.updateTimeDisplay();
                    console.log(`Video loaded: ${this.duration}s duration`);
                });
                
                // Start slider change
                this.startSlider.addEventListener('input', (e) => {
                    const newStart = (e.target.value / 100) * this.duration;
                    this.startTime = Math.min(newStart, this.endTime - 0.1);
                    this.updateTimeDisplay();
                    this.updateNodeParams();
                });
                
                // End slider change
                this.endSlider.addEventListener('input', (e) => {
                    const newEnd = (e.target.value / 100) * this.duration;
                    this.endTime = Math.max(newEnd, this.startTime + 0.1);
                    this.updateTimeDisplay();
                    this.updateNodeParams();
                });
                
                // Video time update
                this.videoElement.addEventListener('timeupdate', () => {
                    if (this.videoElement.currentTime >= this.endTime) {
                        this.videoElement.pause();
                        this.videoElement.currentTime = this.endTime;
                    }
                });
            };
            
            // Update time display
            nodeType.prototype.updateTimeDisplay = function() {
                if (!this.timeDisplay) return;
                
                const formatTime = (seconds) => {
                    const mins = Math.floor(seconds / 60);
                    const secs = Math.floor(seconds % 60);
                    return `${mins}:${secs.toString().padStart(2, '0')}`;
                };
                
                const duration = this.endTime - this.startTime;
                this.timeDisplay.innerHTML = `
                    <strong>Selection:</strong> ${formatTime(this.startTime)} → ${formatTime(this.endTime)} 
                    <span style="color: #4CAF50;">(${formatTime(duration)} duration)</span><br>
                    <strong>Total Video:</strong> ${formatTime(this.duration)}
                `;
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
        
        if (node.startSlider) {
            node.startSlider.value = (node.startTime / node.duration) * 100;
        }
        if (node.endSlider) {
            node.endSlider.value = (node.endTime / node.duration) * 100;
        }
        
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
        
        if (node.startSlider) {
            node.startSlider.value = 0;
        }
        if (node.endSlider) {
            node.endSlider.value = 100;
        }
        
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