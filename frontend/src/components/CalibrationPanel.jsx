import React, { useState } from 'react';

export default function CalibrationPanel({ metrics }) {
  const [split, setSplit] = useState('oof');
  const result = metrics?.[split] || {};
  const ci = metrics?.ci95?.[split] || {};
  const plotNames = split === 'oof'
    ? ['reliability_oof', 'confusion_oof']
    : ['reliability_test', 'confusion_test'];
  const metric = (name, digits = 3) => Number(result[name] || 0).toFixed(digits);
  const interval = name => {
    const values = ci[name] || [0, 0];
    return `[${Number(values[0]).toFixed(3)}, ${Number(values[1]).toFixed(3)}]`;
  };
  return (
    <div className="bg-[#1a1c21] border border-[#2c303a] rounded-md p-4">
      <div className="flex items-center justify-between border-b border-[#2c303a] pb-2.5">
        <div><h2 className="text-xs font-medium">Calibration</h2><p className="text-[11px] text-[#8c92a0]">OOF and locked test diagnostics</p></div>
        <div className="flex gap-1">{['oof', 'test'].map(value => <button key={value} onClick={() => setSplit(value)} className={`px-2 py-1 rounded text-[11px] ${split === value ? 'bg-[#e6e8ec] text-[#121316]' : 'bg-[#121316] text-[#8c92a0]'}`}>{value.toUpperCase()}</button>)}</div>
      </div>
      <div className="grid grid-cols-2 gap-3 mt-3">{plotNames.map(name => <img key={name} src={`/api/plots/${name}`} alt={`${name} calibration plot`} className="w-full bg-[#121316] rounded border border-[#2c303a]" />)}</div>
      <div className="grid grid-cols-3 gap-2 mt-3 text-[11px]">
        <div className="bg-[#121316] rounded p-2">Accuracy <strong>{metric('accuracy')}</strong><span className="block text-[#8c92a0]">{interval('accuracy')}</span></div>
        <div className="bg-[#121316] rounded p-2">F1 macro <strong>{metric('f1_macro')}</strong><span className="block text-[#8c92a0]">{interval('f1_macro')}</span></div>
        <div className="bg-[#121316] rounded p-2">ECE (%) <strong>{metric('ece', 2)}</strong><span className="block text-[#8c92a0]">{interval('ece')}</span></div>
      </div>
      <p className="text-[11px] text-[#8c92a0] mt-3">Test split has 36 images. Wide intervals. pcb_damage has 5 images.</p>
    </div>
  );
}
