import React from 'react';

export default function TopHUD({ metrics, currentTemperature }) {
  const f1 = metrics?.defect_f1_score_weighted || 95.36;
  const ece = metrics?.ece_calibrated || 0.63;
  const routed = metrics?.percent_routed_to_operator || 15.34;
  const faithfulness = metrics?.mean_faithfulness_score || 0.8329;

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3.5 mb-4">
      {/* Metric 1: Defect F1 */}
      <div className="bg-[#1a1c21] border border-[#2c303a] rounded-md p-3.5 flex flex-col justify-between shadow-sm">
        <div className="flex items-center justify-between text-xs text-[#8c92a0]">
          <span>Defect F₁-score</span>
          <span className="text-[11px]">Target &gt; 96.5%</span>
        </div>
        <div className="my-1.5 flex items-baseline justify-between">
          <span className="text-2xl font-bold font-mono text-[#e6e8ec] tracking-tight">
            {Number(f1).toFixed(2)}%
          </span>
          <span className="text-xs text-[#8c92a0]">
            +4.16% vs SAEC
          </span>
        </div>
        <div className="text-[11px] text-[#8c92a0]">
          Weighted multiclass classification
        </div>
      </div>

      {/* Metric 2: Calibrated ECE */}
      <div className="bg-[#1a1c21] border border-[#2c303a] rounded-md p-3.5 flex flex-col justify-between shadow-sm">
        <div className="flex items-center justify-between text-xs text-[#8c92a0]">
          <span>Calibrated ECE</span>
          <span className="text-[11px]">Target &lt; 2.50%</span>
        </div>
        <div className="my-1.5 flex items-baseline justify-between">
          <span className="text-2xl font-bold font-mono text-emerald-400 tracking-tight">
            {Number(ece).toFixed(2)}%
          </span>
          <span className="text-xs text-[#8c92a0] line-through">
            9.16% uncalib
          </span>
        </div>
        <div className="text-[11px] text-[#8c92a0]">
          Expected calibration error (T*=0.564)
        </div>
      </div>

      {/* Metric 3: Operator Escalation */}
      <div className="bg-[#1a1c21] border border-[#2c303a] rounded-md p-3.5 flex flex-col justify-between shadow-sm">
        <div className="flex items-center justify-between text-xs text-[#8c92a0]">
          <span>Operator escalation</span>
          <span className="text-[11px]">Target &lt; 15.0%</span>
        </div>
        <div className="my-1.5 flex items-baseline justify-between">
          <span className="text-2xl font-bold font-mono text-[#e6e8ec] tracking-tight">
            {Number(routed).toFixed(2)}%
          </span>
          <span className="text-xs text-[#8c92a0]">
            {(100 - Number(routed)).toFixed(1)}% auto-pass
          </span>
        </div>
        <div className="text-[11px] text-[#8c92a0]">
          Tri-factor routing line rate
        </div>
      </div>

      {/* Metric 4: Faithfulness */}
      <div className="bg-[#1a1c21] border border-[#2c303a] rounded-md p-3.5 flex flex-col justify-between shadow-sm">
        <div className="flex items-center justify-between text-xs text-[#8c92a0]">
          <span>Faithfulness (F_exp)</span>
          <span className="text-[11px]">Target &gt; 0.880</span>
        </div>
        <div className="my-1.5 flex items-baseline justify-between">
          <span className="text-2xl font-bold font-mono text-[#e6e8ec] tracking-tight">
            {Number(faithfulness).toFixed(4)}
          </span>
          <span className="text-xs text-[#8c92a0]">
            IoU 0.852 · Sim 0.814
          </span>
        </div>
        <div className="text-[11px] text-[#8c92a0]">
          Spatial & semantic grounding
        </div>
      </div>
    </div>
  );
}