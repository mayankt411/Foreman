import React from 'react';
import { RotateCcw } from 'lucide-react';

export default function SidebarControls({
  w1, setW1,
  w2, setW2,
  w3, setW3,
  thetaRoute, setThetaRoute,
  defaultThetaRoute,
  currentTemperature, setCurrentTemperature,
  selectedCategory, setSelectedCategory,
  playbackSpeed, setPlaybackSpeed
}) {
  const categories = [
    { id: 'all', label: 'All frames' },
    { id: 'dry_joint', label: 'Dry joint' },
    { id: 'incorrect_installation', label: 'Incorrect install' },
    { id: 'pcb_damage', label: 'PCB damage' },
    { id: 'short_circuit', label: 'Short circuit' },
    { id: 'normal', label: 'Nominal' }
  ];

  const handleReset = () => {
    setW1(0.35);
    setW2(0.35);
    setW3(0.30);
    setThetaRoute(defaultThetaRoute);
  };

  return (
    <div className="w-full bg-[#1a1c21] border border-[#2c303a] rounded-md p-4 flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between pb-2 border-b border-[#2c303a]">
        <div>
          <h2 className="text-xs font-medium text-[#e6e8ec]">
            Inspection controls
          </h2>
          <span className="text-[11px] text-[#8c92a0]">
            Filter & routing parameters
          </span>
        </div>
        <button
          onClick={handleReset}
          title="Reset to paper defaults"
          className="p-1 text-[#8c92a0] hover:text-[#e6e8ec] hover:bg-[#22252c] rounded transition-colors"
        >
          <RotateCcw className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Defect Class Filter */}
      <div className="space-y-1.5">
        <div className="text-[11px] text-[#8c92a0]">
          Filter defect class
        </div>
        <div className="grid grid-cols-2 gap-1.5">
          {categories.map((cat) => (
            <button
              key={cat.id}
              onClick={() => setSelectedCategory(cat.id)}
              className={`py-1 px-2 rounded text-xs text-left truncate transition-colors ${
                selectedCategory === cat.id
                  ? 'bg-[#e6e8ec] text-[#121316] font-medium'
                  : 'bg-[#121316] text-[#8c92a0] border border-[#2c303a] hover:text-[#e6e8ec] hover:border-[#3f4452]'
              }`}
            >
              {cat.label}
            </button>
          ))}
        </div>
      </div>

      {/* RPI Formula & Weights */}
      <div className="space-y-3 pt-2.5 border-t border-[#2c303a]">
        <div className="text-[11px] text-[#8c92a0]">
          Routing weights (RPI)
        </div>

        {/* w1 */}
        <div className="space-y-1">
          <div className="flex justify-between text-xs">
            <span className="text-[#8c92a0]">w₁ Uncertainty</span>
            <span className="font-mono text-[#e6e8ec] font-medium">
              {w1.toFixed(2)}
            </span>
          </div>
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={w1}
            onChange={(e) => setW1(Number(e.target.value))}
            className="w-full accent-[#8c92a0] h-1 bg-[#2c303a] rounded cursor-pointer"
          />
        </div>

        {/* w2 */}
        <div className="space-y-1">
          <div className="flex justify-between text-xs">
            <span className="text-[#8c92a0]">w₂ Severity</span>
            <span className="font-mono text-[#e6e8ec] font-medium">
              {w2.toFixed(2)}
            </span>
          </div>
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={w2}
            onChange={(e) => setW2(Number(e.target.value))}
            className="w-full accent-[#8c92a0] h-1 bg-[#2c303a] rounded cursor-pointer"
          />
        </div>

        {/* w3 */}
        <div className="space-y-1">
          <div className="flex justify-between text-xs">
            <span className="text-[#8c92a0]">w₃ Faithfulness (offline)</span>
            <span className="font-mono text-[#e6e8ec] font-medium">
              {w3.toFixed(2)}
            </span>
          </div>
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={w3}
            onChange={(e) => setW3(Number(e.target.value))}
            className="w-full accent-[#8c92a0] h-1 bg-[#2c303a] rounded cursor-pointer"
          />
        </div>

        {/* Routing Threshold */}
        <div className="space-y-1 pt-2 border-t border-[#2c303a]">
          <div className="flex justify-between text-xs">
            <span className="text-[#8c92a0]">Routing threshold</span>
            <span className="font-mono text-[#e6e8ec] font-semibold">
              {thetaRoute.toFixed(3)}
            </span>
          </div>
          <input
            type="range"
            min="0.10"
            max="0.90"
            step="0.01"
            value={thetaRoute}
            onChange={(e) => setThetaRoute(Number(e.target.value))}
            className="w-full accent-[#8c92a0] h-1 bg-[#2c303a] rounded cursor-pointer"
          />
        </div>
      </div>

      {/* Stream Playback Speed */}
      <div className="space-y-1.5 pt-2.5 border-t border-[#2c303a]">
        <div className="flex justify-between text-[11px] text-[#8c92a0]">
          <span>Live calibration temperature</span>
          <span className="font-mono text-[#e6e8ec]">{Number(currentTemperature).toFixed(3)}</span>
        </div>
        <input
          type="range"
          min="0.1"
          max="10"
          step="0.001"
          value={currentTemperature}
          onChange={(e) => setCurrentTemperature(Number(e.target.value))}
          className="w-full accent-[#8c92a0] h-1 bg-[#2c303a] rounded cursor-pointer"
        />
      </div>

      {/* Stream Playback Speed */}
      <div className="space-y-1.5 pt-2.5 border-t border-[#2c303a]">
        <div className="text-[11px] text-[#8c92a0]">
          Stream speed
        </div>
        <div className="grid grid-cols-4 gap-1">
          {[0.5, 1.0, 2.0, 5.0].map((spd) => (
            <button
              key={spd}
              onClick={() => setPlaybackSpeed(spd)}
              className={`py-1 rounded text-xs transition-colors text-center ${
                playbackSpeed === spd
                  ? 'bg-[#e6e8ec] text-[#121316] font-medium'
                  : 'bg-[#121316] text-[#8c92a0] border border-[#2c303a] hover:text-[#e6e8ec]'
              }`}
            >
              {spd}×
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}