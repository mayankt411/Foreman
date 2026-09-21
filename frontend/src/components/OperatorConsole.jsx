import { Check, X } from 'lucide-react';

export default function OperatorConsole({
  currentFrame,
  frameIndex,
  currentTemperature,
  operatorLogs,
  selectedLabel,
  setSelectedLabel,
  onAccept,
  onOverrule,
  onUndo,
  feedbackError
}) {
  if (!currentFrame) return null;

  const predLabel = currentFrame.predicted_label;
  const gtLabel = currentFrame.ground_truth_label;
  const calibConf = (Number(currentFrame.calibrated_confidence || currentFrame.raw_confidence) * 100).toFixed(1);

  return (
    <div className="bg-[#1a1c21] border border-[#2c303a] rounded-md p-4 flex flex-col justify-between">
      {/* Header */}
      <div className="flex items-center justify-between pb-2.5 border-b border-[#2c303a]">
        <div>
          <h2 className="text-xs font-medium text-[#e6e8ec]">
            Operator review station
          </h2>
          <span className="text-[11px] text-[#8c92a0]">
            Human-in-the-loop active feedback
          </span>
        </div>
        <span className="text-[11px] text-emerald-400 font-medium">
          Online recalibration
        </span>
      </div>

      {/* Model Diagnostic Readout */}
      <div className="my-2.5 p-2.5 bg-[#121316] border border-[#2c303a] rounded space-y-2 text-xs">
        <div className="flex items-center justify-between">
          <span className="text-[#8c92a0]">Model prediction</span>
          <span className="text-[#e6e8ec] font-medium">
            {predLabel} <span className="font-mono text-[#8c92a0]">({calibConf}%)</span>
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-[#8c92a0]">Ground truth</span>
          <span className="text-[#e6e8ec] font-medium">
            {gtLabel}
          </span>
        </div>
      </div>

      {/* Override Dropdown */}
      <div className="my-1.5">
        <label className="block text-[11px] text-[#8c92a0] mb-1">
          Correction class (for overrules)
        </label>
        <select
          value={selectedLabel}
          onChange={(e) => setSelectedLabel(e.target.value)}
          className="w-full bg-[#121316] border border-[#2c303a] rounded py-1 px-2 text-xs text-[#e6e8ec] focus:outline-none focus:border-[#8c92a0]"
        >
          <option value="dry_joint">Dry joint</option>
          <option value="incorrect_installation">Incorrect installation</option>
          <option value="pcb_damage">PCB damage</option>
          <option value="short_circuit">Short circuit</option>
          <option value="normal">Nominal (defect-free)</option>
        </select>
      </div>

      {/* Action Buttons */}
      <div className="grid grid-cols-2 gap-2 my-2.5">
        <button
          onClick={onAccept}
          className="py-1.5 px-3 rounded bg-emerald-700/80 hover:bg-emerald-700 text-white text-xs font-medium flex items-center justify-center gap-1.5 transition-colors"
        >
          <Check className="w-3.5 h-3.5" />
          <span>Accept call [A]</span>
        </button>
        <button
          onClick={() => onOverrule(selectedLabel)}
          className="py-1.5 px-3 rounded bg-red-700/80 hover:bg-red-700 text-white text-xs font-medium flex items-center justify-center gap-1.5 transition-colors"
        >
          <X className="w-3.5 h-3.5" />
          <span>Overrule [O]</span>
        </button>
      </div>
      {feedbackError && (
        <div className="text-[11px] text-red-400 text-center mb-2">{feedbackError}</div>
      )}
      <button
        onClick={onUndo}
        className="py-1 px-3 rounded border border-[#2c303a] text-[#8c92a0] hover:text-[#e6e8ec] hover:bg-[#22252c] text-xs transition-colors"
      >
        Undo [U]
      </button>

      {/* Operator Audit & Temperature Recalibration Log */}
      <div className="pt-2.5 border-t border-[#2c303a]">
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-[11px] text-[#8c92a0]">
            Recalibration telemetry
          </span>
          <span className="text-[11px] text-[#8c92a0]">
            T* = <span className="font-mono text-[#e6e8ec] font-semibold">{Number(currentTemperature).toFixed(3)}</span>
          </span>
        </div>

        <div className="max-h-20 overflow-y-auto space-y-1 pr-1 text-[11px]">
          {operatorLogs && operatorLogs.length > 0 ? (
            operatorLogs.slice(-3).reverse().map((log, i) => (
              <div
                key={i}
                className="bg-[#121316] border border-[#2c303a] px-2 py-1 rounded flex items-center justify-between"
              >
                <span className={log.action.includes('accept') ? 'text-emerald-400' : 'text-red-400'}>
                  Frame {log.frame_index + 1}: {log.action}
                </span>
                <span className="text-[#8c92a0] font-mono text-[10px]">{log.timestamp}</span>
              </div>
            ))
          ) : (
            <div className="text-[#8c92a0] text-[11px] italic py-1 text-center">
              Autonomous line flow. Zero overrules logged.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
