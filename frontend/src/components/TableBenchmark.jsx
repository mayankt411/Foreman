import React from 'react';

const num = (value, digits = 3) => (value === undefined || value === null ? 'n/a' : Number(value).toFixed(digits));
const span = (interval, digits = 3) => (Array.isArray(interval) ? `[${Number(interval[0]).toFixed(digits)}, ${Number(interval[1]).toFixed(digits)}]` : '');

export default function TableBenchmark({ metrics }) {
  const oof = metrics?.oof || {};
  const test = metrics?.test || {};
  const ci = metrics?.ci95 || {};
  const classes = metrics?.per_class_f1 || {};

  const rows = [
    { name: 'Accuracy', oof: num(oof.accuracy), test: num(test.accuracy), ci: span(ci.test?.accuracy) },
    { name: 'F1 macro', oof: num(oof.f1_macro), test: num(test.f1_macro), ci: span(ci.test?.f1_macro) },
    { name: 'F1 weighted', oof: num(oof.f1_weighted), test: num(test.f1_weighted), ci: span(ci.test?.f1_weighted) },
    { name: 'ECE calibrated (%)', oof: num(oof.ece, 2), test: num(test.ece, 2), ci: span(ci.test?.ece, 1) },
  ];

  return (
    <div className="bg-[#1a1c21] border border-[#2c303a] rounded-md p-4 flex flex-col justify-between h-full">
      <div>
        <div className="flex items-center justify-between pb-2.5 border-b border-[#2c303a] mb-3">
          <div>
            <h2 className="text-xs font-medium text-[#e6e8ec]">Measured results</h2>
            <p className="text-[11px] text-[#8c92a0]">
              {metrics?.model || 'model'} · {metrics?.eval_protocol || 'evaluation protocol unavailable'}
            </p>
          </div>
          <span className="text-xs font-mono text-[#8c92a0] bg-[#121316] px-2.5 py-0.5 rounded border border-[#2c303a]">
            N = {metrics?.total_samples ?? 'n/a'}
          </span>
        </div>
        <div className="overflow-x-auto mb-3">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-[#2c303a] text-[#8c92a0] text-[11px]">
                <th className="py-2 px-2.5 font-medium">Metric</th>
                <th className="py-2 px-2.5 font-medium">OOF (n={oof.n ?? 'n/a'})</th>
                <th className="py-2 px-2.5 font-medium">Test (n={test.n ?? 'n/a'})</th>
                <th className="py-2 px-2.5 font-medium">Test 95% CI</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#2c303a]">
              {rows.map(row => (
                <tr key={row.name}>
                  <td className="py-2 px-2.5 text-[#e6e8ec]">{row.name}</td>
                  <td className="py-2 px-2.5 font-mono text-[#e6e8ec]">{row.oof}</td>
                  <td className="py-2 px-2.5 font-mono text-[#e6e8ec] font-semibold">{row.test}</td>
                  <td className="py-2 px-2.5 font-mono text-[#8c92a0]">{row.ci}</td>
                </tr>
              ))}
              <tr>
                <td className="py-2 px-2.5 text-[#e6e8ec]">CPU latency incl. Grad-CAM</td>
                <td className="py-2 px-2.5 font-mono text-[#e6e8ec] font-semibold" colSpan={3}>
                  {num(metrics?.latency_mean_ms, 0)} ms mean, {num(metrics?.latency_p95_ms, 0)} ms p95 (Colab CPU, not edge hardware)
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <div className="pt-2.5 border-t border-[#2c303a]">
        <div className="text-xs text-[#8c92a0] mb-2 flex items-center justify-between">
          <span>Per-class F1 on locked test split</span>
          <span className="text-[10px]">{Object.keys(classes).length} classes</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
          {Object.entries(classes).map(([name, item]) => (
            <div key={name} className="bg-[#121316] border border-[#2c303a] p-2 rounded flex items-center justify-between">
              <div>
                <div className="text-[#e6e8ec] text-[11px] font-medium">{name.replace(/_/g, ' ')}</div>
                <div className="text-[10px] text-[#8c92a0] font-mono">
                  n = {item.support}{item.support < 5 ? ' (too small to trust)' : ''}
                </div>
              </div>
              <span className="text-[#e6e8ec] font-semibold font-mono">{num(item.f1, 2)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
