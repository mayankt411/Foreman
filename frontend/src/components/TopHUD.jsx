import React from 'react';

const pct = (value, digits = 1) => (value === undefined || value === null ? 'n/a' : `${(Number(value) * 100).toFixed(digits)}%`);
const num = (value, digits = 2) => (value === undefined || value === null ? 'n/a' : Number(value).toFixed(digits));

function Card({ title, note, value, valueClass = 'text-[#e6e8ec]', side, foot }) {
  return (
    <div className="bg-[#1a1c21] border border-[#2c303a] rounded-md p-3.5 flex flex-col justify-between shadow-sm">
      <div className="flex items-center justify-between text-xs text-[#8c92a0]">
        <span>{title}</span>
        <span className="text-[11px]">{note}</span>
      </div>
      <div className="my-1.5 flex items-baseline justify-between">
        <span className={`text-2xl font-bold font-mono tracking-tight ${valueClass}`}>{value}</span>
        <span className="text-xs text-[#8c92a0]">{side}</span>
      </div>
      <div className="text-[11px] text-[#8c92a0]">{foot}</div>
    </div>
  );
}

export default function TopHUD({ metrics, currentTemperature }) {
  const oof = metrics?.oof || {};
  const test = metrics?.test || {};
  const routed = metrics?.percent_routed_to_operator;
  const temperature = currentTemperature ?? metrics?.fitted_temperature;

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3.5 mb-4">
      <Card
        title="Defect F1 (macro)"
        note="OOF n=153"
        value={num(oof.f1_macro, 3)}
        side={`Test ${num(test.f1_macro, 3)}`}
        foot="Held-out folds. Test split has 36 images"
      />
      <Card
        title="Calibrated ECE"
        note="OOF n=153"
        value={`${num(oof.ece)}%`}
        valueClass="text-emerald-400"
        side={`Test ${num(test.ece)}%`}
        foot={`Temperature T = ${num(temperature, 2)}`}
      />
      <Card
        title="Operator escalation"
        note="RPI top 15%"
        value={routed === undefined ? 'n/a' : `${num(routed)}%`}
        side={routed === undefined ? '' : `${(100 - Number(routed)).toFixed(1)}% auto-pass`}
        foot={`${metrics?.auto_passed_fn_leaks ?? 'n/a'} missed defects auto-passed`}
      />
      <Card
        title="Faithfulness (offline)"
        note="uses truth box"
        value={num(metrics?.mean_faithfulness_score, 3)}
        side="0.5 IoU + 0.5 heat-in-box"
        foot="Evaluation only. Needs the ground-truth box, not available in production"
      />
    </div>
  );
}
