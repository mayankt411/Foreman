import React, { useState, useRef } from 'react';
import { Play, Pause, ChevronLeft, ChevronRight, Crosshair } from 'lucide-react';

export default function LiveInspectionFeed({
  currentFrame,
  frameIndex,
  totalFrames,
  onPrev,
  onNext,
  onSelectFrame,
  isPlaying,
  onTogglePlay
}) {
  const [mousePos, setMousePos] = useState(null);
  const imgContainerRef = useRef(null);

  if (!currentFrame) {
    return (
      <div className="bg-[#1a1c21] border border-[#2c303a] rounded-md p-6 text-center text-[#8c92a0] text-sm">
        Initializing optical inspection feed...
      </div>
    );
  }

  const isDefect = currentFrame.predicted_label !== 'normal';
  const confidencePct = (Number(currentFrame.raw_confidence) * 100).toFixed(1);
  const calibratedPct = (Number(currentFrame.calibrated_confidence || currentFrame.raw_confidence) * 100).toFixed(1);

  // Parse bounding boxes if present
  let bboxes = [];
  try {
    if (Array.isArray(currentFrame.bboxes)) {
      bboxes = currentFrame.bboxes;
    } else if (typeof currentFrame.bboxes === 'string') {
      bboxes = JSON.parse(currentFrame.bboxes);
    }
  } catch (e) {
    bboxes = [];
  }

  const handleMouseMove = (e) => {
    if (!imgContainerRef.current) return;
    const rect = imgContainerRef.current.getBoundingClientRect();
    const x = Math.round(((e.clientX - rect.left) / rect.width) * (currentFrame.width || 640));
    const y = Math.round(((e.clientY - rect.top) / rect.height) * (currentFrame.height || 480));
    setMousePos({ x, y });
  };

  const handleMouseLeave = () => {
    setMousePos(null);
  };

  return (
    <div className="bg-[#1a1c21] border border-[#2c303a] rounded-md p-4 flex flex-col justify-between">
      {/* Header */}
      <div className="flex items-center justify-between pb-2.5 border-b border-[#2c303a]">
        <div>
          <h2 className="text-xs font-medium text-[#e6e8ec]">
            Optical inspection feed
          </h2>
          <span className="text-[11px] text-[#8c92a0]">
            Channel 01 · High-resolution surface mount
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-[#8c92a0]">
            Frame <span className="font-mono text-[#e6e8ec]">{frameIndex + 1}</span> of <span className="font-mono text-[#e6e8ec]">{totalFrames}</span>
          </span>
        </div>
      </div>

      {/* Main Visual Display */}
      <div
        ref={imgContainerRef}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
        className="relative mt-3 rounded overflow-hidden bg-[#121316] border border-[#2c303a] aspect-[4/3] select-none flex items-center justify-center"
      >
        <img
          src={currentFrame.image_url || `/api/image/${currentFrame.index || frameIndex}`}
          alt={`PCB inspection frame ${frameIndex}`}
          className="w-full h-full object-cover"
          onError={(e) => {
            e.target.style.display = 'none';
          }}
        />

        {/* Fallback pattern if image is missing */}
        <div className="absolute inset-0 -z-10 flex flex-col items-center justify-center text-[#8c92a0] bg-[#121316]">
          <Crosshair className="w-6 h-6 stroke-1 text-[#2c303a] mb-1" />
          <span className="text-xs">No sensor signal</span>
        </div>

        {/* SVG Bounding Boxes Overlay */}
        <svg
          className="absolute inset-0 w-full h-full pointer-events-none"
          viewBox={`0 0 ${currentFrame.width || 640} ${currentFrame.height || 480}`}
          preserveAspectRatio="none"
        >
          {/* Render Ground Truth / Detected Boxes */}
          {bboxes.map((box, bIdx) => {
            const [bx, by, bw, bh] = box;
            return (
              <g key={bIdx}>
                {/* Bounding Box Rect */}
                <rect
                  x={bx}
                  y={by}
                  width={bw}
                  height={bh}
                  fill="rgba(239, 68, 68, 0.12)"
                  stroke="#ef4444"
                  strokeWidth="1.5"
                  strokeDasharray="4 2"
                />
                {/* Corner reticles */}
                <path
                  d={`M ${bx} ${by + 8} L ${bx} ${by} L ${bx + 8} ${by}`}
                  fill="none"
                  stroke="#ef4444"
                  strokeWidth="2"
                />
                <path
                  d={`M ${bx + bw - 8} ${by} L ${bx + bw} ${by} L ${bx + bw} ${by + 8}`}
                  fill="none"
                  stroke="#ef4444"
                  strokeWidth="2"
                />
                <path
                  d={`M ${bx} ${by + bh - 8} L ${bx} ${by + bh} L ${bx + 8} ${by + bh}`}
                  fill="none"
                  stroke="#ef4444"
                  strokeWidth="2"
                />
                <path
                  d={`M ${bx + bw - 8} ${by + bh} L ${bx + bw} ${by + bh} L ${bx + bw} ${by + bh - 8}`}
                  fill="none"
                  stroke="#ef4444"
                  strokeWidth="2"
                />
                {/* Label Tag */}
                <rect
                  x={bx}
                  y={Math.max(0, by - 16)}
                  width={Math.min(160, bw + 20)}
                  height="16"
                  fill="#ef4444"
                />
                <text
                  x={bx + 4}
                  y={Math.max(11, by - 4)}
                  fill="#ffffff"
                  fontSize="10"
                  fontFamily="sans-serif"
                  fontWeight="600"
                >
                  {currentFrame.predicted_label} ({calibratedPct}%)
                </text>
              </g>
            );
          })}

          {/* If defect but no explicit bboxes array */}
          {isDefect && bboxes.length === 0 && (
            <g>
              <rect
                x="120"
                y="90"
                width="400"
                height="300"
                fill="rgba(239, 68, 68, 0.08)"
                stroke="#ef4444"
                strokeWidth="1.5"
              />
              <rect x="120" y="72" width="180" height="18" fill="#ef4444" />
              <text x="126" y="85" fill="#ffffff" fontSize="10" fontFamily="sans-serif" fontWeight="600">
                Defect: {currentFrame.predicted_label}
              </text>
            </g>
          )}
        </svg>

        {/* Top-Right Status Chip */}
        <div className="absolute top-2.5 right-2.5 flex items-center gap-1.5">
          {isDefect ? (
            <span className="px-2 py-0.5 rounded bg-[#1a1c21]/90 border border-red-500/50 text-red-400 text-xs font-medium">
              Defect detected ({calibratedPct}%)
            </span>
          ) : (
            <span className="px-2 py-0.5 rounded bg-[#1a1c21]/90 border border-emerald-500/50 text-emerald-400 text-xs font-medium">
              Nominal ({calibratedPct}%)
            </span>
          )}
        </div>

        {/* Bottom-Left Live Coordinate Readout */}
        <div className="absolute bottom-2 left-2 text-[11px] text-[#8c92a0] bg-[#121316]/90 px-2 py-0.5 rounded border border-[#2c303a] font-mono">
          {mousePos ? `X: ${mousePos.x}  Y: ${mousePos.y}` : `640 × 480 px`}
        </div>
      </div>

      {/* Diagnostic Rationale Box */}
      <div className="mt-3 p-2.5 bg-[#121316] border border-[#2c303a] rounded">
        <div className="text-[11px] text-[#8c92a0] mb-1 flex items-center justify-between">
          <span>Model explanation</span>
          <span className="text-[10px]">IPC-A-610 standards</span>
        </div>
        <p className="text-xs text-[#e6e8ec] leading-relaxed">
          {currentFrame.rationale || 'No explanation generated for this frame.'}
        </p>
      </div>

      {/* Playback & Frame Scrubber */}
      <div className="mt-3 pt-2.5 border-t border-[#2c303a] space-y-2">
        <div className="flex items-center justify-between gap-2">
          <button
            onClick={onPrev}
            disabled={frameIndex <= 0}
            className="px-2.5 py-1 rounded bg-[#22252c] hover:bg-[#2c303a] text-[#e6e8ec] disabled:opacity-30 text-xs flex items-center gap-1 transition-colors"
          >
            <ChevronLeft className="w-3.5 h-3.5" />
            <span>Previous</span>
          </button>

          <button
            onClick={onTogglePlay}
            className={`px-3 py-1 rounded text-xs font-medium flex items-center gap-1.5 transition-colors ${
              isPlaying
                ? 'bg-red-600/90 text-white hover:bg-red-600'
                : 'bg-[#22252c] text-[#e6e8ec] hover:bg-[#2c303a]'
            }`}
          >
            {isPlaying ? (
              <>
                <Pause className="w-3.5 h-3.5" />
                <span>Pause stream</span>
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5" />
                <span>Play stream</span>
              </>
            )}
          </button>

          <button
            onClick={onNext}
            disabled={frameIndex >= totalFrames - 1}
            className="px-2.5 py-1 rounded bg-[#22252c] hover:bg-[#2c303a] text-[#e6e8ec] disabled:opacity-30 text-xs flex items-center gap-1 transition-colors"
          >
            <span>Next</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Scrubber */}
        <input
          type="range"
          min="0"
          max={totalFrames - 1}
          value={frameIndex}
          onChange={(e) => onSelectFrame(Number(e.target.value))}
          className="w-full accent-[#8c92a0] h-1 bg-[#2c303a] rounded cursor-pointer"
        />
      </div>
    </div>
  );
}