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
                    
                    <!-- Video Scrubber Timeline -->
                    <div style="margin-bottom: 15px;">
                        <div style="color: #ccc; font-size: 10px; margin-bottom: 8px;">Timeline Scrubber:</div>
                        <div id="scrubber-container-${this.id}" style="position: relative; height: 40px; background: #333; border-radius: 4px; margin-bottom: 8px; cursor: pointer; z-index: 100; pointer-events: auto;">
                            <!-- Timeline track -->
                            <div id="timeline-track-${this.id}" style="position: absolute; top: 15px; left: 8px; right: 8px; height: 4px; background: #555; border-radius: 2px;"></div>
                            
                            <!-- Selected range -->
                            <div id="selected-range-${this.id}" style="position: absolute; top: 15px; height: 4px; background: linear-gradient(90deg, #4CAF50, #FF9800); border-radius: 2px; pointer-events: none;"></div>
                            
                            <!-- Start handle -->
                            <div id="start-handle-${this.id}" style="position: absolute; top: 8px; width: 12px; height: 18px; background: #4CAF50; border-radius: 2px; cursor: ew-resize; border: 1px solid #fff; box-shadow: 0 2px 4px rgba(0,0,0,0.3); z-index: 1000; pointer-events: auto;"></div>
                            
                            <!-- End handle -->
                            <div id="end-handle-${this.id}" style="position: absolute; top: 8px; width: 12px; height: 18px; background: #FF9800; border-radius: 2px; cursor: ew-resize; border: 1px solid #fff; box-shadow: 0 2px 4px rgba(0,0,0,0.3); z-index: 1000; pointer-events: auto;"></div>
                            
                            <!-- Time labels -->
                            <div id="start-time-label-${this.id}" style="position: absolute; top: 28px; font-size: 10px; color: #4CAF50; transform: translateX(-50%);"></div>
                            <div id="end-time-label-${this.id}" style="position: absolute; top: 28px; font-size: 10px; color: #FF9800; transform: translateX(-50%);"></div>
                        </div>
                    </div>
                    
                    <div style="display: flex; gap: 3px; margin-bottom: 8px; flex-wrap: wrap;">
                        <button onclick="window.setVideoRange(${this.id}, 0, 5)" style="background: #444; border: 1px solid #666; color: #ccc; padding: 2px 6px; border-radius: 3px; cursor: pointer; font-size: 10px;">5s</button>
                        <button onclick="window.setVideoRange(${this.id}, 0, 10)" style="background: #444; border: 1px solid #666; color: #ccc; padding: 2px 6px; border-radius: 3px; cursor: pointer; font-size: 10px;">10s</button>
                        <button onclick="window.setVideoRange(${this.id}, 0, 30)" style="background: #444; border: 1px solid #666; color: #ccc; padding: 2px 6px; border-radius: 3px; cursor: pointer; font-size: 10px;">30s</button>
                        <button onclick="window.resetVideoRange(${this.id})" style="background: #444; border: 1px solid #666; color: #ccc; padding: 2px 6px; border-radius: 3px; cursor: pointer; font-size: 10px;">Full</button>
                    </div>
                    
                    <div style="display: flex; gap: 5px; justify-content: center;">
                        <button onclick="window.playVideoSelection(${this.id})" style="background: #2196F3; border: none; color: white; padding: 4px 8px; border-radius: 4px; cursor: pointer; font-size: 11px;">▶️ Play</button>
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
                    // Debug logging
                    console.log("🔍 allowDragFromWidget - onPointerDown called");
                    console.log("🔍 scrubberInteractionActive:", window.scrubberInteractionActive);
                    
                    // Check global flag first
                    if (window.scrubberInteractionActive) {
                        console.log("🚫 Blocking node drag - scrubber interaction active");
                        return false;
                    }
                    
                    console.log("✅ Allowing node drag");
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
                
                // Scrubber elements
                this.scrubberContainer = document.getElementById(`scrubber-container-${this.id}`);
                this.timelineTrack = document.getElementById(`timeline-track-${this.id}`);
                this.selectedRange = document.getElementById(`selected-range-${this.id}`);
                this.startHandle = document.getElementById(`start-handle-${this.id}`);
                this.endHandle = document.getElementById(`end-handle-${this.id}`);
                this.startTimeLabel = document.getElementById(`start-time-label-${this.id}`);
                this.endTimeLabel = document.getElementById(`end-time-label-${this.id}`);
                
                // Check for missing elements with detailed logging
                const missingElements = [];
                if (!this.videoElement) missingElements.push(`video-${this.id}`);
                if (!this.scrubberContainer) missingElements.push(`scrubber-container-${this.id}`);
                if (!this.timeDisplay) missingElements.push(`time-display-${this.id}`);
                if (!this.timelineTrack) missingElements.push(`timeline-track-${this.id}`);
                if (!this.selectedRange) missingElements.push(`selected-range-${this.id}`);
                if (!this.startHandle) missingElements.push(`start-handle-${this.id}`);
                if (!this.endHandle) missingElements.push(`end-handle-${this.id}`);
                
                if (missingElements.length > 0) {
                    console.error("Could not find video control elements:", missingElements);
                    console.error("Node ID:", this.id);
                    return;
                }
                
                // Video loaded event
                this.videoElement.addEventListener('loadedmetadata', () => {
                    this.duration = this.videoElement.duration;
                    this.endTime = this.duration;
                    this.updateScrubber();
                    this.updateTimeDisplay();
                    
                    // Update widget aspect ratio for proper sizing
                    if (this.videoWidget) {
                        this.videoWidget.aspectRatio = this.videoElement.videoWidth / this.videoElement.videoHeight;
                        this.setSize(this.computeSize());
                    }
                    
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
                });
                
                // Set up scrubber interactions
                this.setupScrubberInteractions();
            };
            
            // Setup scrubber drag interactions
            nodeType.prototype.setupScrubberInteractions = function() {
                let isDragging = false;
                let dragTarget = null;
                let dragStartX = 0;
                let dragStartTime = 0;
                
                // Global flag to prevent node dragging when scrubber is active
                window.scrubberInteractionActive = false;
                
                const getTimeFromPosition = (x) => {
                    const rect = this.timelineTrack.getBoundingClientRect();
                    const relativeX = Math.max(0, Math.min(rect.width, x - rect.left));
                    return (relativeX / rect.width) * this.duration;
                };
                
                const getPositionFromTime = (time) => {
                    const rect = this.timelineTrack.getBoundingClientRect();
                    return (time / this.duration) * rect.width;
                };
                
                // Handle mouse down on handles with capture to intercept early
                this.startHandle.addEventListener('mousedown', (e) => {
                    console.log("🎯 Start handle mousedown event triggered");
                    console.log("🎯 Event target:", e.target);
                    console.log("🎯 Event target id:", e.target.id);
                    
                    // Set global flag to prevent node dragging
                    window.scrubberInteractionActive = true;
                    
                    e.preventDefault();
                    e.stopPropagation();
                    e.stopImmediatePropagation();
                    isDragging = true;
                    dragTarget = 'start';
                    dragStartX = e.clientX;
                    dragStartTime = this.startTime;
                    document.body.style.cursor = 'ew-resize';
                    
                    console.log("🎯 Start handle drag initiated");
                    return false;
                }, true); // Use capture phase
                
                this.endHandle.addEventListener('mousedown', (e) => {
                    console.log("🎯 End handle mousedown event triggered");
                    console.log("🎯 Event target:", e.target);
                    console.log("🎯 Event target id:", e.target.id);
                    
                    // Set global flag to prevent node dragging
                    window.scrubberInteractionActive = true;
                    
                    e.preventDefault();
                    e.stopPropagation();
                    e.stopImmediatePropagation();
                    isDragging = true;
                    dragTarget = 'end';
                    dragStartX = e.clientX;
                    dragStartTime = this.endTime;
                    document.body.style.cursor = 'ew-resize';
                    
                    console.log("🎯 End handle drag initiated");
                    return false;
                }, true); // Use capture phase
                
                // Handle clicking on timeline to move nearest handle
                this.scrubberContainer.addEventListener('mousedown', (e) => {
                    if (isDragging || e.target === this.startHandle || e.target === this.endHandle) return;
                    
                    e.preventDefault();
                    e.stopPropagation();
                    e.stopImmediatePropagation();
                    
                    const clickTime = getTimeFromPosition(e.clientX);
                    const startDistance = Math.abs(clickTime - this.startTime);
                    const endDistance = Math.abs(clickTime - this.endTime);
                    
                    // Move the closest handle to click position
                    if (startDistance < endDistance) {
                        this.startTime = Math.max(0, Math.min(clickTime, this.endTime - 0.1));
                    } else {
                        this.endTime = Math.min(this.duration, Math.max(clickTime, this.startTime + 0.1));
                    }
                    
                    this.updateScrubber();
                    this.updateTimeDisplay();
                    this.updateNodeParams();
                    
                    return false;
                });
                
                // Global mouse move and up handlers
                document.addEventListener('mousemove', (e) => {
                    if (!isDragging) return;
                    
                    console.log("🎯 Mouse move during drag, target:", dragTarget);
                    const newTime = getTimeFromPosition(e.clientX);
                    
                    if (dragTarget === 'start') {
                        this.startTime = Math.max(0, Math.min(newTime, this.endTime - 0.1));
                    } else if (dragTarget === 'end') {
                        this.endTime = Math.min(this.duration, Math.max(newTime, this.startTime + 0.1));
                    }
                    
                    this.updateScrubber();
                    this.updateTimeDisplay();
                    this.updateNodeParams();
                });
                
                document.addEventListener('mouseup', () => {
                    if (isDragging) {
                        console.log("🎯 Mouse up - ending drag");
                        isDragging = false;
                        dragTarget = null;
                        document.body.style.cursor = '';
                    }
                    // Always clear the global flag on mouseup
                    window.scrubberInteractionActive = false;
                });
            };
            
            // Update scrubber visual positions
            nodeType.prototype.updateScrubber = function() {
                if (!this.duration || !this.timelineTrack) return;
                
                const trackRect = this.timelineTrack.getBoundingClientRect();
                const containerRect = this.scrubberContainer.getBoundingClientRect();
                const trackWidth = trackRect.width;
                const trackLeft = trackRect.left - containerRect.left;
                
                // Calculate positions
                const startPos = (this.startTime / this.duration) * trackWidth + trackLeft;
                const endPos = (this.endTime / this.duration) * trackWidth + trackLeft;
                
                // Position handles
                this.startHandle.style.left = `${startPos - 6}px`;
                this.endHandle.style.left = `${endPos - 6}px`;
                
                // Position selected range
                this.selectedRange.style.left = `${startPos}px`;
                this.selectedRange.style.width = `${endPos - startPos}px`;
                
                // Position time labels
                this.startTimeLabel.style.left = `${startPos}px`;
                this.endTimeLabel.style.left = `${endPos}px`;
                
                // Update label text
                const formatTime = (seconds) => {
                    const mins = Math.floor(seconds / 60);
                    const secs = Math.floor(seconds % 60);
                    return `${mins}:${secs.toString().padStart(2, '0')}`;
                };
                
                this.startTimeLabel.textContent = formatTime(this.startTime);
                this.endTimeLabel.textContent = formatTime(this.endTime);
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
                
                // Update scrubber if it exists
                if (this.updateScrubber) {
                    this.updateScrubber();
                }
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