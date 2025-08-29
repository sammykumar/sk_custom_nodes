import React, { useState, useRef, useEffect, useCallback } from 'react'
import './VideoTrimmer.css'

interface VideoTrimmerProps {
  videoUrl: string
  onTrimChange?: (startTime: number, endTime: number) => void
  initialStartTime?: number
  initialEndTime?: number
}

interface TrimRange {
  start: number
  end: number
}

export const VideoTrimmer: React.FC<VideoTrimmerProps> = ({
  videoUrl,
  onTrimChange,
  initialStartTime = 0,
  initialEndTime = 0
}) => {
  const videoRef = useRef<HTMLVideoElement>(null)
  const timelineRef = useRef<HTMLDivElement>(null)
  const [duration, setDuration] = useState(0)
  const [currentTime, setCurrentTime] = useState(0)
  const [trimRange, setTrimRange] = useState<TrimRange>({ start: initialStartTime, end: initialEndTime })
  const [isDragging, setIsDragging] = useState<'start' | 'end' | null>(null)
  const [isPlaying, setIsPlaying] = useState(false)

  useEffect(() => {
    if (initialEndTime > 0) {
      setTrimRange({ start: initialStartTime, end: initialEndTime })
    }
  }, [initialStartTime, initialEndTime])

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    const ms = Math.floor((seconds % 1) * 100)
    return `${mins}:${secs.toString().padStart(2, '0')}.${ms.toString().padStart(2, '0')}`
  }

  const handleLoadedMetadata = () => {
    if (videoRef.current) {
      const videoDuration = videoRef.current.duration
      setDuration(videoDuration)
      if (trimRange.end === 0) {
        setTrimRange({ start: 0, end: videoDuration })
      }
    }
  }

  const handleTimeUpdate = () => {
    if (videoRef.current) {
      const time = videoRef.current.currentTime
      setCurrentTime(time)
      
      // Stop playback at trim end
      if (time >= trimRange.end) {
        videoRef.current.pause()
        videoRef.current.currentTime = trimRange.end
        setIsPlaying(false)
      }
    }
  }

  const handlePlay = () => {
    if (videoRef.current) {
      // Start from trim start if current time is outside trim range
      if (videoRef.current.currentTime < trimRange.start || videoRef.current.currentTime > trimRange.end) {
        videoRef.current.currentTime = trimRange.start
      }
      videoRef.current.play()
      setIsPlaying(true)
    }
  }

  const handlePause = () => {
    if (videoRef.current) {
      videoRef.current.pause()
      setIsPlaying(false)
    }
  }

  const getTimeFromPosition = (clientX: number): number => {
    if (!timelineRef.current) return 0
    const rect = timelineRef.current.getBoundingClientRect()
    const position = (clientX - rect.left) / rect.width
    return Math.max(0, Math.min(duration, position * duration))
  }

  const handleMouseDown = (event: React.MouseEvent, handle: 'start' | 'end') => {
    event.preventDefault()
    setIsDragging(handle)
  }

  const handleMouseMove = useCallback((event: MouseEvent) => {
    if (!isDragging || !timelineRef.current) return

    const newTime = getTimeFromPosition(event.clientX)
    
    if (isDragging === 'start') {
      const newStart = Math.min(newTime, trimRange.end - 0.1) // Minimum 0.1s clip
      const newRange = { start: newStart, end: trimRange.end }
      setTrimRange(newRange)
      onTrimChange?.(newRange.start, newRange.end)
      
      // Restart video from new start
      if (videoRef.current) {
        videoRef.current.currentTime = newStart
        if (isPlaying) {
          videoRef.current.play()
        }
      }
    } else if (isDragging === 'end') {
      const newEnd = Math.max(newTime, trimRange.start + 0.1) // Minimum 0.1s clip
      const newRange = { start: trimRange.start, end: newEnd }
      setTrimRange(newRange)
      onTrimChange?.(newRange.start, newRange.end)
      
      // Restart video from start
      if (videoRef.current) {
        videoRef.current.currentTime = trimRange.start
        if (isPlaying) {
          videoRef.current.play()
        }
      }
    }
  }, [isDragging, trimRange, onTrimChange, isPlaying])

  const handleMouseUp = useCallback(() => {
    setIsDragging(null)
  }, [])

  useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove)
      document.addEventListener('mouseup', handleMouseUp)
      return () => {
        document.removeEventListener('mousemove', handleMouseMove)
        document.removeEventListener('mouseup', handleMouseUp)
      }
    }
  }, [isDragging, handleMouseMove, handleMouseUp])

  const startPercentage = duration > 0 ? (trimRange.start / duration) * 100 : 0
  const endPercentage = duration > 0 ? (trimRange.end / duration) * 100 : 100
  const currentPercentage = duration > 0 ? (currentTime / duration) * 100 : 0

  return (
    <div className="video-trimmer">
      <div className="video-container">
        <video
          ref={videoRef}
          src={videoUrl}
          onLoadedMetadata={handleLoadedMetadata}
          onTimeUpdate={handleTimeUpdate}
          onPlay={() => setIsPlaying(true)}
          onPause={() => setIsPlaying(false)}
          controls={false}
          className="trim-video"
        />
        <div className="video-overlay">
          <button
            className="play-button"
            onClick={isPlaying ? handlePause : handlePlay}
          >
            {isPlaying ? '⏸️' : '▶️'}
          </button>
        </div>
      </div>
      
      <div className="timeline-container">
        <div className="timeline" ref={timelineRef}>
          {/* Background timeline */}
          <div className="timeline-track"></div>
          
          {/* Trimmed area */}
          <div
            className="timeline-selection"
            style={{
              left: `${startPercentage}%`,
              width: `${endPercentage - startPercentage}%`
            }}
          ></div>
          
          {/* Current time indicator */}
          <div
            className="timeline-current"
            style={{ left: `${currentPercentage}%` }}
          ></div>
          
          {/* Start handle */}
          <div
            className="timeline-handle timeline-handle-start"
            style={{ left: `${startPercentage}%` }}
            onMouseDown={(e) => handleMouseDown(e, 'start')}
          >
            <div className="handle-bracket handle-bracket-left">⟨</div>
          </div>
          
          {/* End handle */}
          <div
            className="timeline-handle timeline-handle-end"
            style={{ left: `${endPercentage}%` }}
            onMouseDown={(e) => handleMouseDown(e, 'end')}
          >
            <div className="handle-bracket handle-bracket-right">⟩</div>
          </div>
        </div>
        
        <div className="time-display">
          <span>{formatTime(trimRange.start)}</span>
          <span>Duration: {formatTime(trimRange.end - trimRange.start)}</span>
          <span>{formatTime(trimRange.end)}</span>
        </div>
      </div>
    </div>
  )
}