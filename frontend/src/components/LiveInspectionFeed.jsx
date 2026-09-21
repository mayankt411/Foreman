import React, { useRef, useState } from 'react';
import { Play, Pause, ChevronLeft, ChevronRight, Crosshair } from 'lucide-react';

export default function LiveInspectionFeed({
  currentFrame, frameIndex, totalFrames, onPrev, onNext, onSelectFrame,
  isPlaying, onTogglePlay, onOnlyRouted, onlyRouted, queueFrames, onSelectQueue
}) {
  const [mousePos, setMousePos] = useState(null);
  const [heatmapOn, setHeatmapOn] = useState(true);
  const [opacity, setOpacity] = useState(60);
  const [boxesOn, setBoxesOn] = useState(true);
  const [viewMode, setViewMode] = useState('defect');
  const imgContainerRef = useRef(null);
  if (!currentFrame) return <div className="bg-[#1a1c21] border border-[#2c303a] rounded-md p-6 text-center text-[#8c92a0] text-sm">No inspection frames available.</div>;

  const width = currentFrame.width || 640;
  const height = currentFrame.height || 480;
  const isDefect = currentFrame.predicted_label !== 'normal';
  const calibratedPct = (Number(currentFrame.calibrated_confidence || currentFrame.raw_confidence) * 100).toFixed(1);
  let bboxes = Array.isArray(currentFrame.bboxes) ? currentFrame.bboxes : [];
  if (typeof currentFrame.bboxes === 'string') {
    try { bboxes = JSON.parse(currentFrame.bboxes); } catch { bboxes = []; }
  }
  const showHeatmap = heatmapOn && currentFrame.has_heatmap && viewMode === 'attention';
  const showBoxes = boxesOn && viewMode === 'defect';
  const queue = queueFrames || [];

  const handleMouseMove = (event) => {
    if (!imgContainerRef.current) return;
    const rect = imgContainerRef.current.getBoundingClientRect();
    setMousePos({
      x: Math.round(((event.clientX - rect.left) / rect.width) * width),
      y: Math.round(((event.clientY - rect.top) / rect.height) * height)
    });
  };

  return (
    <div className="bg-[#1a1c21] border border-[#2c303a] rounded-md p-4">
      <div className={`mb-3 rounded border px-3 py-2 flex justify-between items-center ${currentFrame.routed_to_operator ? 'bg-amber-950/40 border-amber-500/60 text-amber-300' : 'bg-emerald-950/40 border-emerald-500/60 text-emerald-300'}`}>
        <span className="font-semibold text-xs">{currentFrame.routed_to_operator ? 'REVIEW' : 'PASS'}</span>
        <span className="font-mono text-[11px]">RPI {Number(currentFrame.rpi_score || 0).toFixed(3)} / threshold {Number(currentFrame.rpi_threshold || 0).toFixed(3)}</span>
      </div>
      <div className="flex items-center justify-between pb-2.5 border-b border-[#2c303a]">
        <div><h2 className="text-xs font-medium text-[#e6e8ec]">Optical inspection feed</h2><span className="text-[11px] text-[#8c92a0]">Channel 01 · High-resolution surface mount</span></div>
        <span className="text-xs text-[#8c92a0]">Frame <span className="font-mono text-[#e6e8ec]">{frameIndex + 1}</span> of <span className="font-mono text-[#e6e8ec]">{totalFrames}</span></span>
      </div>
      <div ref={imgContainerRef} onMouseMove={handleMouseMove} onMouseLeave={() => setMousePos(null)} className="relative mt-3 rounded overflow-hidden bg-[#121316] border border-[#2c303a] aspect-[4/3] select-none flex items-center justify-center">
        <img src={currentFrame.image_url || `/api/image/${currentFrame.index ?? frameIndex}`} alt={`PCB inspection frame ${frameIndex}`} className="w-full h-full object-cover" />
        {showHeatmap && <img src={currentFrame.heatmap_url} alt="" className="absolute inset-0 w-full h-full object-cover pointer-events-none" style={{ opacity: opacity / 100 }} />}
        <svg className="absolute inset-0 w-full h-full pointer-events-none" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
          {showBoxes && bboxes.map((box, index) => {
            const [x, y, w, h] = box;
            return <rect key={index} x={x} y={y} width={w} height={h} fill="rgba(239,68,68,.12)" stroke="#ef4444" strokeWidth="2" strokeDasharray="5 3" />;
          })}
        </svg>
        <div className="absolute top-2 right-2 px-2 py-0.5 rounded bg-[#1a1c21]/90 border border-[#2c303a] text-xs">{isDefect ? `Defect detected (${calibratedPct}%)` : `Nominal (${calibratedPct}%)`}</div>
        <div className="absolute bottom-2 left-2 text-[11px] text-[#8c92a0] bg-[#121316]/90 px-2 py-0.5 rounded border border-[#2c303a] font-mono">{mousePos ? `X: ${mousePos.x} Y: ${mousePos.y}` : `${width} × ${height} px`}</div>
      </div>
      {currentFrame.has_heatmap && <div className="mt-3 p-2 bg-[#121316] border border-[#2c303a] rounded space-y-2 text-[11px]">
        <div className="flex flex-wrap gap-2">
          <button onClick={() => setHeatmapOn(value => !value)} className="border border-[#2c303a] rounded px-2 py-1">{heatmapOn ? 'Heatmap on' : 'Heatmap off'}</button>
          <label className="flex items-center gap-2">Opacity <input type="range" min="0" max="100" value={opacity} onChange={event => setOpacity(Number(event.target.value))} /> {opacity}%</label>
          <button onClick={() => setBoxesOn(value => !value)} className="border border-[#2c303a] rounded px-2 py-1">{boxesOn ? 'Boxes on' : 'Boxes off'}</button>
          <button onClick={() => setViewMode('defect')} className={`border rounded px-2 py-1 ${viewMode === 'defect' ? 'border-amber-400 text-amber-300' : 'border-[#2c303a]'}`}>Defect zone</button>
          <button onClick={() => setViewMode('attention')} className={`border rounded px-2 py-1 ${viewMode === 'attention' ? 'border-amber-400 text-amber-300' : 'border-[#2c303a]'}`}>Model attention</button>
        </div>
        <div className="flex items-center gap-2"><span>high</span><div className="h-2 flex-1 rounded" style={{ background: 'linear-gradient(to right, #ef4444, #f97316, #fde047, #22c55e)' }} /><span>low attention</span></div>
      </div>}
      <div className="mt-3 p-2.5 bg-[#121316] border border-[#2c303a] rounded"><div className="text-[11px] text-[#8c92a0] mb-1">Model explanation</div><p className="text-xs text-[#e6e8ec] leading-relaxed">{currentFrame.rationale || 'No explanation generated for this frame.'}</p></div>
      <div className="mt-3 pt-2.5 border-t border-[#2c303a] space-y-2">
        <div className="flex items-center justify-between gap-2">
          <button onClick={onPrev} disabled={frameIndex <= 0} className="px-2.5 py-1 rounded bg-[#22252c] text-xs disabled:opacity-30"><ChevronLeft className="w-3.5 h-3.5 inline" /> Previous</button>
          <button onClick={onTogglePlay} className="px-3 py-1 rounded bg-[#22252c] text-xs">{isPlaying ? <><Pause className="w-3.5 h-3.5 inline" /> Pause</> : <><Play className="w-3.5 h-3.5 inline" /> Play</>}</button>
          <button onClick={onNext} disabled={frameIndex >= totalFrames - 1} className="px-2.5 py-1 rounded bg-[#22252c] text-xs disabled:opacity-30">Next <ChevronRight className="w-3.5 h-3.5 inline" /></button>
        </div>
        <input type="range" min="0" max={totalFrames - 1} value={frameIndex} onChange={event => onSelectFrame(Number(event.target.value))} className="w-full accent-[#8c92a0]" />
        <label className="flex items-center gap-2 text-[11px] text-[#8c92a0]"><input type="checkbox" checked={onlyRouted} onChange={onOnlyRouted} /> Only routed</label>
        <div className="max-h-28 overflow-y-auto space-y-1">{queue.slice(0, 8).map(frame => <button key={frame.index} onClick={() => onSelectQueue(frame.index)} className={`w-full text-left px-2 py-1 rounded text-[11px] ${frame.index === currentFrame.index ? 'bg-[#2c303a]' : 'bg-[#121316]'}`}>#{frame.index + 1} · RPI {Number(frame.rpi_score || 0).toFixed(3)} · {frame.predicted_label}</button>)}</div>
      </div>
    </div>
  );
}
