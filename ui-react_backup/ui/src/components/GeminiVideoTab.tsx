import React, { useCallback, useEffect, useState } from 'react'

import './GeminiVideoTab.css'
import { VideoTrimmer } from './VideoTrimmer'

interface GeminiVideoNode {
  id: string | number
  type: string
  uploadedVideoFile?: string
  uploadedVideoSubfolder?: string
  startTime?: number
  endTime?: number
  duration?: number
}

export const GeminiVideoTab: React.FC = () => {
  const [geminiNodes, setGeminiNodes] = useState<GeminiVideoNode[]>([])
  const [selectedNode, setSelectedNode] = useState<GeminiVideoNode | null>(null)
  const [videoUrl, setVideoUrl] = useState<string>('')

  // Function to find Gemini Video Describe nodes
  const findGeminiNodes = useCallback((): GeminiVideoNode[] => {
    if (!window.app?.graph) return []

    const graphNodes = window.app.graph._nodes
    if (!graphNodes) return []

    return graphNodes
      .filter((node) => node.type === 'GeminiVideoDescribe')
      .map((node) => {
        const extNode = node as any // Type assertion to access custom properties
        return {
          id: node.id,
          type: node.type,
          uploadedVideoFile: extNode.uploadedVideoFile,
          uploadedVideoSubfolder: extNode.uploadedVideoSubfolder,
          startTime: extNode.startTime || 0,
          endTime: extNode.endTime || 0,
          duration: extNode.duration || 0
        }
      })
  }, [])

  // Update nodes list
  const updateNodes = useCallback(() => {
    const nodes = findGeminiNodes()
    setGeminiNodes(nodes)

    // If no node is selected but nodes exist, select the first one
    if (!selectedNode && nodes.length > 0) {
      setSelectedNode(nodes[0])
    }

    // If selected node no longer exists, clear selection
    if (selectedNode && !nodes.find((n) => n.id === selectedNode.id)) {
      setSelectedNode(null)
      setVideoUrl('')
    }
  }, [findGeminiNodes, selectedNode])

  // Update video URL when node selection changes
  useEffect(() => {
    if (
      selectedNode &&
      selectedNode.uploadedVideoFile &&
      selectedNode.uploadedVideoSubfolder
    ) {
      const url = `/view?filename=${selectedNode.uploadedVideoFile}&subfolder=${selectedNode.uploadedVideoSubfolder}&type=input&t=${Date.now()}`
      setVideoUrl(url)
    } else {
      setVideoUrl('')
    }
  }, [selectedNode])

  // Listen for graph changes
  useEffect(() => {
    if (!window.app?.api) return

    updateNodes() // Initial load

    const handleGraphChanged = () => {
      updateNodes()
    }

    window.app.api.addEventListener('graphChanged', handleGraphChanged)

    return () => {
      window.app?.api.removeEventListener('graphChanged', handleGraphChanged)
    }
  }, [updateNodes])

  // Handle trim changes
  const handleTrimChange = (startTime: number, endTime: number) => {
    if (!selectedNode || !window.app?.graph) return

    const graphNodes = window.app.graph._nodes
    const node = graphNodes.find((n) => n.id === selectedNode.id) as any

    if (node) {
      // Update the node's trim values
      node.startTime = startTime
      node.endTime = endTime

      // Update the node's widgets if they exist
      const startTimeWidget = node.widgets?.find(
        (w: any) => w.name === 'start_time'
      )
      const maxDurationWidget = node.widgets?.find(
        (w: any) => w.name === 'max_duration'
      )

      if (startTimeWidget) {
        startTimeWidget.value = startTime
      }

      if (maxDurationWidget) {
        const duration = endTime - startTime
        maxDurationWidget.value = duration
      }

      // Update time display if available
      if (typeof node.updateTimeDisplay === 'function') {
        node.updateTimeDisplay()
      }

      // Mark the graph as dirty to trigger updates
      window.app.graph.setDirtyCanvas(true, false)

      // Update local state
      setSelectedNode({
        ...selectedNode,
        startTime,
        endTime
      })
    }
  }

  const handleNodeSelect = (node: GeminiVideoNode) => {
    setSelectedNode(node)

    // Focus on the node in the graph
    if (window.app?.graph) {
      const graphNodes = window.app.graph._nodes
      const graphNode = graphNodes.find((n) => n.id === node.id)
      if (graphNode) {
        window.app.canvas.centerOnNode(graphNode)
      }
    }
  }

  return (
    <div className="gemini-video-tab">
      <div className="tab-header">
        <h3>Gemini Video Trimmer</h3>
        <p>Select a Gemini Video Describe node to trim its uploaded video</p>
      </div>

      {geminiNodes.length === 0 ? (
        <div className="no-nodes">
          <div className="empty-state">
            <h4>No Gemini Video Nodes Found</h4>
            <p>
              Add a "Gemini Video Describe" node to your workflow and upload a
              video to start trimming.
            </p>
          </div>
        </div>
      ) : (
        <div className="nodes-container">
          <div className="node-selector">
            <label>Select Node:</label>
            <select
              value={selectedNode?.id || ''}
              onChange={(e) => {
                const node = geminiNodes.find(
                  (n) => n.id.toString() === e.target.value
                )
                if (node) handleNodeSelect(node)
              }}
            >
              <option value="">Choose a node...</option>
              {geminiNodes.map((node) => (
                <option key={node.id} value={node.id}>
                  Node {node.id}{' '}
                  {node.uploadedVideoFile
                    ? `(${node.uploadedVideoFile})`
                    : '(No video)'}
                </option>
              ))}
            </select>
          </div>

          {selectedNode && videoUrl ? (
            <div className="video-section">
              <div className="video-info">
                <h4>Node {selectedNode.id}</h4>
                <p>File: {selectedNode.uploadedVideoFile}</p>
                {selectedNode.duration && selectedNode.duration > 0 && (
                  <p>Duration: {selectedNode.duration.toFixed(2)}s</p>
                )}
              </div>

              <VideoTrimmer
                videoUrl={videoUrl}
                onTrimChange={handleTrimChange}
                initialStartTime={selectedNode.startTime || 0}
                initialEndTime={
                  selectedNode.endTime || selectedNode.duration || 0
                }
              />
            </div>
          ) : selectedNode && !videoUrl ? (
            <div className="no-video">
              <h4>No Video Uploaded</h4>
              <p>
                This node doesn't have a video uploaded yet. Use the upload
                button on the node to select a video file.
              </p>
            </div>
          ) : null}
        </div>
      )}
    </div>
  )
}
