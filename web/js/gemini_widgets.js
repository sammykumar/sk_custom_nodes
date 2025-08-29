import { app } from '../../../scripts/app.js'
import { api } from '../../../scripts/api.js'

console.log("Loading gemini_widgets.js extension");

// Register custom widget for the Gemini Video Describe node
app.registerExtension({
    name: "sk_custom_nodes.gemini_widgets",
    
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "GeminiUtilVideoDescribe") {
            console.log("Registering GeminiUtilVideoDescribe node with upload button");
            
            // Add custom widget after the node is created
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                const result = onNodeCreated?.apply(this, arguments);
                
                // Add a video upload button widget
                const uploadButton = this.addWidget(
                    "button", 
                    "� Choose Video to Upload", 
                    "upload",
                    () => {
                        this.onUploadButtonPressed();
                    }
                );
                
                // Style the button
                uploadButton.serialize = false; // Don't save button state
                
                // Add a widget to display the selected video info
                this.videoInfoWidget = this.addWidget(
                    "text",
                    "video_file",
                    "No video selected",
                    () => {},
                    {}
                );
                this.videoInfoWidget.serialize = false;
                
                return result;
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
                            this.videoFileWidget.serialize = true; // This will be saved with the workflow
                            this.videoFileWidget.type = "hidden"; // Hide from UI
                        }
                        
                        // Store the file path in the hidden widget
                        this.videoFileWidget.value = `${this.uploadedVideoSubfolder}/${this.uploadedVideoFile}`;
                        
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