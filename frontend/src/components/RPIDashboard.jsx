import React from 'react';

export default function RPIDashboard({
  rpiValue,
  thetaRoute,
  isRouted,
  uCalib,
  severity,
  unfaithfulness,
  w1,
  w2,
  w3
}) {
  const radius = 64;
  const strokeWidth = 7;
  const arcLength = Math.PI * radius;
  const clampedRPI = Math.min(1.0, Math.max(0.0, rpiValue));
  const strokeDashoffset = arcLength * (1 - clampedRPI);
  const parts = [
    { label: '0.35 × uncertainty', value: 0.35 * Number(uCalib || 0), color: '#38bdf8' },
    { label: '0.35 × severity', value: 0.35 * Number(severity || 0), color: '#fbbf24' },
    { label: '0.30 × unfaithfulness', value: 0.30 * Number(unfaithfulness || 0), color: '#fb7185' }
  ];

  const thetaAngle = Math.PI * (1 - thetaRoute);
  const tickInner = radius - 8;
  const tickOuter = radius + 6;
  const tickX0 = 100 + tickInner * Math.cos(thetaAngle);
  const tickY0 = 82 - tickInner * Math.sin(thetaAngle);
  const tickX1 = 100 + tickOuter * Math.cos(thetaAngle);
  const tickY1 = 82 - tickOuter * Math.sin(thetaAngle);

  return (
    <div className="bg-[#1a1c21] border border-[#2c303a] rounded-md p-4 flex flex-col justify-between">
      {/* Header */}
      <div className="flex items-center justify-between pb-2.5 border-b border-[#2c303a]">
        <div>
          <h2 className="text-xs font-medium text-[#e6e8ec]">
            Routing decision engine
          </h2>
          <span className="text-[11px] text-[#8c92a0]">
            Tri-factor Review-Priority Index (RPI)
          </span>
        </div>
        <span className="text-[11px] text-[#8c92a0]">
          Threshold: <span className="font-mono text-[#e6e8ec]">{Number(thetaRoute).toFixed(3)}</span>
        </span>
      </div>

      {/* Primary Decision Banner */}
      <div className="my-2.5">
        {isRouted ? (
          <div className="py-2.5 px-3 rounded bg-red-950/40 border border-red-500/60 text-red-300 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-red-500" />
              <span className="text-xs font-semibold">
                Routed to operator review
              </span>
            </div>
            <span className="text-[11px] font-mono text-red-400">
              RPI ({Number(rpiValue).toFixed(3)}) &gt; {Number(thetaRoute).toFixed(3)}
            </span>
          </div>
        ) : (
          <div className="py-2.5 px-3 rounded bg-emerald-950/40 border border-emerald-500/60 text-emerald-300 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-500" />
              <span className="text-xs font-semibold">
                Autonomous pass (line action)
              </span>
            </div>
            <span className="text-[11px] font-mono text-emerald-400">
              RPI ({Number(rpiValue).toFixed(3)}) ≤ {Number(thetaRoute).toFixed(3)}
            </span>
          </div>
        )}
      </div>

      {/* SVG Arc Gauge */}
      <div className="relative flex flex-col items-center justify-center py-1">
        <svg viewBox="0 0 200 100" className="w-48 h-24">
          <defs>
            <linearGradient id="rpiGrad" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#10b981" />
              <stop offset="50%" stopColor="#f59e0b" />
              <stop offset="100%" stopColor="#ef4444" />
            </linearGradient>
          </defs>

          {/* Background Track */}
          <path
            d="M 36 82 A 64 64 0 0 1 164 82"
            fill="none"
            stroke="#2c303a"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
          />

          {/* Active Level */}
          <path
            d="M 36 82 A 64 64 0 0 1 164 82"
            fill="none"
            stroke="url(#rpiGrad)"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={arcLength}
            strokeDashoffset={strokeDashoffset}
            className="transition-all duration-150"
          />

          {/* Threshold Tick */}
          <line
            x1={tickX0}
            y1={tickY0}
            x2={tickX1}
            y2={tickY1}
            stroke="#ffffff"
            strokeWidth="2"
            strokeLinecap="round"
          />
        </svg>

        {/* Digital Readout */}
        <div className="-mt-7 text-center">
          <span className="text-2xl font-bold font-mono tracking-tight text-[#e6e8ec]">
            {Number(rpiValue).toFixed(3)}
          </span>
          <div className="text-[11px] text-[#8c92a0]">
            Calculated priority score
          </div>
        </div>
      </div>

      {/* Tri-Factor Component Breakdowns */}
      <div className="space-y-2 pt-2.5 border-t border-[#2c303a] text-xs">
        <div className="relative">
          <div className="flex h-3 rounded overflow-hidden bg-[#121316]">
            {parts.map(part => <div key={part.label} style={{ width: `${part.value * 100}%`, backgroundColor: part.color }} />)}
          </div>
          <div className="absolute top-[-3px] h-5 border-l-2 border-white" style={{ left: `${Number(thetaRoute || 0) * 100}%` }} />
          <div className="flex justify-between text-[10px] text-[#8c92a0] mt-1"><span>Weighted RPI components</span><span>threshold</span></div>
          <div className="flex flex-wrap gap-x-3 gap-y-1 mt-1">
            {parts.map(part => <span key={part.label} className="text-[10px] text-[#8c92a0]"><i className="inline-block w-2 h-2 rounded-sm mr-1" style={{ backgroundColor: part.color }} />{part.label}</span>)}
          </div>
        </div>
        {/* Uncertainty */}
        <div>
          <div className="flex justify-between text-[11px] mb-1">
            <span className="text-[#8c92a0]">
              Uncertainty <span className="font-mono text-[#e6e8ec]">U(x)</span>
            </span>
            <span className="text-[#e6e8ec]">
              <span className="font-mono font-medium">{Number(uCalib).toFixed(3)}</span>{' '}
              <span className="text-[#8c92a0] text-[10px]">(w₁ = {Number(w1).toFixed(2)})</span>
            </span>
          </div>
          <div className="w-full bg-[#121316] h-1.5 rounded overflow-hidden">
            <div
              className="bg-sky-400 h-full transition-all"
              style={{ width: `${Math.min(100, (Number(uCalib) || 0) * 100)}%` }}
            />
          </div>
        </div>

        {/* Severity */}
        <div>
          <div className="flex justify-between text-[11px] mb-1">
            <span className="text-[#8c92a0]">
              Defect severity <span className="font-mono text-[#e6e8ec]">S(c)</span>
            </span>
            <span className="text-[#e6e8ec]">
              <span className="font-mono font-medium">{Number(severity).toFixed(3)}</span>{' '}
              <span className="text-[#8c92a0] text-[10px]">(w₂ = {Number(w2).toFixed(2)})</span>
            </span>
          </div>
          <div className="w-full bg-[#121316] h-1.5 rounded overflow-hidden">
            <div
              className="bg-amber-400 h-full transition-all"
              style={{ width: `${Math.min(100, (Number(severity) || 0) * 100)}%` }}
            />
          </div>
        </div>

        {/* Unfaithfulness */}
        <div>
          <div className="flex justify-between text-[11px] mb-1">
            <span className="text-[#8c92a0]">
              Unfaithfulness <span className="font-mono text-[#e6e8ec]">1 - F_exp</span> <span className="text-[10px]">(offline: uses truth box)</span>
            </span>
            <span className="text-[#e6e8ec]">
              <span className="font-mono font-medium">{Number(unfaithfulness).toFixed(3)}</span>{' '}
              <span className="text-[#8c92a0] text-[10px]">(w₃ = {Number(w3).toFixed(2)})</span>
            </span>
          </div>
          <div className="w-full bg-[#121316] h-1.5 rounded overflow-hidden">
            <div
              className="bg-red-400 h-full transition-all"
              style={{ width: `${Math.min(100, (Number(unfaithfulness) || 0) * 100)}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
