import React, { useState, useEffect, useMemo, useCallback } from 'react';
import TopHUD from './components/TopHUD';
import SidebarControls from './components/SidebarControls';
import LiveInspectionFeed from './components/LiveInspectionFeed';
import RPIDashboard from './components/RPIDashboard';
import OperatorConsole from './components/OperatorConsole';
import TableBenchmark from './components/TableBenchmark';
import CalibrationPanel from './components/CalibrationPanel';

export default function App() {
  const [predictions, setPredictions] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [health, setHealth] = useState(null);
  const [currentIndex, setCurrentIndex] = useState(0);

  // Hyperparameters
  const [w1, setW1] = useState(0.35);
  const [w2, setW2] = useState(0.35);
  const [w3, setW3] = useState(0.30);
  const [thetaRoute, setThetaRoute] = useState(0);

  const [selectedCategory, setSelectedCategory] = useState('all');
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1.0);
  const [activeTab, setActiveTab] = useState('console');

  const [currentTemperature, setCurrentTemperature] = useState(1.0);
  const [operatorLogs, setOperatorLogs] = useState([]);
  const [selectedLabel, setSelectedLabel] = useState('dry_joint');
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [feedbackError, setFeedbackError] = useState(null);
  const [recomputeError, setRecomputeError] = useState(null);
  const [onlyRouted, setOnlyRouted] = useState(false);
  const appendFeedbackLog = (log) => setOperatorLogs(prev => [...prev, {
    ...log,
    action: log.action === 'accept' ? 'accept' : `overrule (${log.override_label})`
  }]);

  useEffect(() => {
    const fetchJson = (url) => fetch(url).then(response => {
      if (!response.ok) throw new Error(`${url} returned ${response.status}`);
      return response.json();
    });

    Promise.all([
      fetchJson('/api/metrics'),
      fetchJson('/api/predictions'),
      fetchJson('/api/feedback/history'),
      fetchJson('/api/health')
    ]).then(([mData, pData, historyData, healthData]) => {
      setMetrics(mData);
      setPredictions(pData);
      if (mData?.fitted_temperature !== undefined) {
        setCurrentTemperature(mData.fitted_temperature);
      }
      if (mData?.rpi_threshold !== undefined) {
        setThetaRoute(mData.rpi_threshold);
      }
      setOperatorLogs(historyData.map(log => ({
        ...log,
        action: log.action === 'accept'
          ? 'accept'
          : `overrule (${log.override_label})`
      })));
      setHealth(healthData);
      setLoading(false);
    }).catch(err => {
      setLoadError(err.message);
      setLoading(false);
    });
  }, []);

  const filteredPreds = useMemo(() => {
    if (!predictions.length) return [];
    const categoryFiltered = selectedCategory === 'all'
      ? predictions
      : predictions.filter(p => p.predicted_label === selectedCategory || p.ground_truth_label === selectedCategory);
    return categoryFiltered
      .filter(frame => !onlyRouted || frame.routed_to_operator)
      .sort((a, b) => Number(b.rpi_score || 0) - Number(a.rpi_score || 0));
  }, [predictions, selectedCategory, onlyRouted]);

  const safeIndex = Math.min(currentIndex, Math.max(0, filteredPreds.length - 1));
  const currentFrame = filteredPreds[safeIndex] || null;
  const displayedFrame = currentFrame ? { ...currentFrame, rpi_threshold: thetaRoute } : null;

  useEffect(() => {
    if (loading || !metrics) return undefined;
    const timer = setTimeout(async () => {
      try {
        const response = await fetch(`/api/recompute?temperature=${encodeURIComponent(currentTemperature)}`);
        if (!response.ok) throw new Error(`recompute returned ${response.status}`);
        const data = await response.json();
        setThetaRoute(data.rpi_threshold);
        setPredictions(previous => previous.map(frame => {
          const update = data.frames.find(item => item.index === frame.index);
          return update ? { ...frame, ...update } : frame;
        }));
        setMetrics(previous => ({ ...previous, percent_routed_to_operator: (data.routed_count / Math.max(1, predictions.length)) * 100 }));
        setRecomputeError(null);
      } catch {
        setRecomputeError('live recalibration unavailable');
      }
    }, 200);
    return () => clearTimeout(timer);
  }, [currentTemperature, loading]);

  useEffect(() => {
    if (!isPlaying || filteredPreds.length === 0) return;
    const intervalMs = 1000 / playbackSpeed;
    const timer = setInterval(() => {
      setCurrentIndex(prev => (prev + 1) % filteredPreds.length);
    }, intervalMs);
    return () => clearInterval(timer);
  }, [isPlaying, playbackSpeed, filteredPreds.length]);

  const u_norm = Number(currentFrame?.u_calib ?? 0);
  const s_norm = Number(currentFrame?.severity_score ?? 0);
  const f_score = Number(currentFrame?.faithfulness_score ?? 0);
  const unfaith_norm = Math.max(0.0, 1.0 - f_score);

  const wSum = (w1 + w2 + w3) || 1.0;
  const w1_n = w1 / wSum;
  const w2_n = w2 / wSum;
  const w3_n = w3 / wSum;

  const liveRPI = Number(currentFrame?.rpi_score ?? ((w1_n * u_norm) + (w2_n * s_norm) + (w3_n * unfaith_norm)));
  const isRouted = Boolean(currentFrame?.routed_to_operator ?? liveRPI > thetaRoute);

  const feedbackFrameIndex = currentFrame?.index ?? safeIndex;
  const handleQueueSelect = useCallback((index) => {
    const position = filteredPreds.findIndex(frame => frame.index === index);
    if (position >= 0) setCurrentIndex(position);
  }, [filteredPreds]);

  const handleAccept = useCallback(async () => {
    if (!currentFrame) return;
    setFeedbackError(null);
    try {
      const response = await fetch('/api/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ frame_index: feedbackFrameIndex, action: 'accept', override_label: '' })
      });
      if (!response.ok) throw new Error(`feedback returned ${response.status}`);
      const data = await response.json();
      setCurrentTemperature(data.new_temperature);
      appendFeedbackLog(data.log);
    } catch {
      setFeedbackError('feedback not saved');
    }
  }, [currentFrame, feedbackFrameIndex]);

  const handleOverrule = useCallback(async (overrideLabel) => {
    if (!currentFrame) return;
    setFeedbackError(null);
    try {
      const response = await fetch('/api/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ frame_index: feedbackFrameIndex, action: 'overrule', override_label: overrideLabel })
      });
      if (!response.ok) throw new Error(`feedback returned ${response.status}`);
      const data = await response.json();
      setCurrentTemperature(data.new_temperature);
      appendFeedbackLog(data.log);
    } catch {
      setFeedbackError('feedback not saved');
    }
  }, [currentFrame, feedbackFrameIndex]);

  const handleUndo = useCallback(async () => {
    setFeedbackError(null);
    try {
      const response = await fetch('/api/feedback/undo', { method: 'POST' });
      if (!response.ok) throw new Error(`undo returned ${response.status}`);
      const data = await response.json();
      setCurrentTemperature(data.new_temperature);
      if (data.success) setOperatorLogs(prev => prev.slice(0, -1));
    } catch {
      setFeedbackError('feedback not saved');
    }
  }, []);

  // Keyboard Navigation
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.repeat || ['INPUT', 'SELECT', 'TEXTAREA'].includes(e.target.tagName)) return;
      if (e.key === 'ArrowLeft') {
        setCurrentIndex(prev => Math.max(0, prev - 1));
      } else if (e.key === 'ArrowRight') {
        setCurrentIndex(prev => Math.min((filteredPreds.length || 1) - 1, prev + 1));
      } else if (e.key === ' ') {
        e.preventDefault();
        setIsPlaying(p => !p);
      } else if (e.key === 'a' || e.key === 'A') {
        handleAccept();
      } else if (e.key === 'o' || e.key === 'O') {
        handleOverrule(selectedLabel);
      } else if (e.key === 'u' || e.key === 'U') {
        handleUndo();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [filteredPreds.length, handleAccept, handleOverrule, handleUndo, selectedLabel]);

  if (loading) {
    return <div className="min-h-screen bg-[#121316] text-[#e6e8ec] p-8 flex items-center justify-center">
      <div className="bg-[#1a1c21] border border-[#2c303a] rounded-md p-6 text-sm">Loading inspection data...</div>
    </div>;
  }

  if (loadError) {
    return <div className="min-h-screen bg-[#121316] text-[#e6e8ec] p-8 flex items-center justify-center">
      <div className="bg-[#1a1c21] border border-red-900 rounded-md p-6 text-sm">
        <p className="text-red-400 mb-3">{loadError}</p>
        <button onClick={() => window.location.reload()} className="border border-[#2c303a] rounded px-3 py-1">Retry</button>
      </div>
    </div>;
  }

  return (
    <div className="min-h-screen bg-[#121316] text-[#e6e8ec] p-4 md:p-6 lg:p-7 max-w-[1560px] mx-auto font-sans">
      {/* Station Header */}
      <header className="flex flex-col md:flex-row items-start md:items-center justify-between gap-3 mb-5 pb-3.5 border-b border-[#2c303a]">
        <div>
          <h1 className="text-base font-semibold text-[#e6e8ec]">
            XiVLM-Loop
          </h1>
          <p className="text-xs text-[#8c92a0] mt-0.5">
            PCB defect inspection with Grad-CAM heatmaps, calibrated confidence and operator feedback
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="flex items-center gap-3 w-full md:w-auto justify-end">
          <div className="flex items-center bg-[#1a1c21] border border-[#2c303a] rounded p-0.5 text-xs">
            <button
              onClick={() => setActiveTab('console')}
              className={`py-1.5 px-3.5 rounded transition-colors ${
                activeTab === 'console'
                  ? 'bg-[#22252c] text-[#e6e8ec] font-medium'
                  : 'text-[#8c92a0] hover:text-[#e6e8ec]'
              }`}
            >
              Inspection console
            </button>
            <button
              onClick={() => setActiveTab('benchmarks')}
              className={`py-1.5 px-3.5 rounded transition-colors ${
                activeTab === 'benchmarks'
                  ? 'bg-[#22252c] text-[#e6e8ec] font-medium'
                  : 'text-[#8c92a0] hover:text-[#e6e8ec]'
              }`}
            >
              Benchmark results & ECE
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      {activeTab === 'console' ? (
        <div className="space-y-4">
          {/* Main Inspection Area: Hero Viewport (7 cols) + Right Controls/Decision Column (5 cols) */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
            {/* Left Hero Column: Camera Viewport (7 cols) */}
            <div className="lg:col-span-7">
              <LiveInspectionFeed
                currentFrame={displayedFrame}
                frameIndex={safeIndex}
                totalFrames={filteredPreds.length}
                onPrev={() => setCurrentIndex(prev => Math.max(0, prev - 1))}
                onNext={() => setCurrentIndex(prev => Math.min((filteredPreds.length || 189) - 1, prev + 1))}
                onSelectFrame={handleQueueSelect}
                isPlaying={isPlaying}
                onTogglePlay={() => setIsPlaying(p => !p)}
                onlyRouted={onlyRouted}
                onOnlyRouted={() => setOnlyRouted(value => !value)}
                queueFrames={filteredPreds}
                onSelectQueue={handleQueueSelect}
              />
            </div>

            {/* Right Decision & Action Column (5 cols) */}
            <div className="lg:col-span-5 flex flex-col gap-4">
              <RPIDashboard
                rpiValue={liveRPI}
                thetaRoute={thetaRoute}
                isRouted={isRouted}
                uCalib={u_norm}
                severity={s_norm}
                unfaithfulness={unfaith_norm}
                w1={w1_n}
                w2={w2_n}
                w3={w3_n}
              />

              <OperatorConsole
                currentFrame={currentFrame}
                frameIndex={safeIndex}
                currentTemperature={currentTemperature}
                operatorLogs={operatorLogs}
                selectedLabel={selectedLabel}
                setSelectedLabel={setSelectedLabel}
                onAccept={handleAccept}
                onOverrule={handleOverrule}
                onUndo={handleUndo}
                feedbackError={feedbackError}
              />

              <SidebarControls
                w1={w1}
                setW1={setW1}
                w2={w2}
                setW2={setW2}
                w3={w3}
                setW3={setW3}
                thetaRoute={thetaRoute}
                setThetaRoute={setThetaRoute}
                defaultThetaRoute={metrics.rpi_threshold}
                currentTemperature={currentTemperature}
                setCurrentTemperature={setCurrentTemperature}
                selectedCategory={selectedCategory}
                setSelectedCategory={setSelectedCategory}
                playbackSpeed={playbackSpeed}
                setPlaybackSpeed={setPlaybackSpeed}
              />
            </div>
          </div>

          {/* Secondary Telemetry Strip (Table 4.3 Metrics) */}
          <TopHUD
            metrics={metrics} 
            currentTemperature={currentTemperature} 
          />
          {recomputeError && <div className="text-[11px] text-red-400">{recomputeError}</div>}
        </div>
      ) : (
        <div className="space-y-4">
          {/* Top Contained Metric Strip */}
          <TopHUD 
            metrics={metrics} 
            currentTemperature={currentTemperature} 
          />

          {/* Full-Width 2-Column Benchmark Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <TableBenchmark metrics={metrics} />
            <CalibrationPanel metrics={metrics} />
          </div>
        </div>
      )}

      {/* Industrial Footer */}
      <footer className="mt-8 pt-3 border-t border-[#2c303a] flex flex-col md:flex-row items-center justify-between text-xs text-[#8c92a0] gap-2">
        <span>XiVLM-Loop · {health?.model || health?.system || 'model status unavailable'} · latency measured on CPU incl. Grad-CAM ({Math.round(metrics.latency_mean_ms)} ms)</span>
        <div className="flex items-center gap-4 text-[11px]">
          <span>Shortcuts: [← / →] Seek · [Space] Stream · [A] Accept · [O] Overrule · [U] Undo</span>
          <span className="font-mono text-[#e6e8ec]">CPU latency: {Math.round(metrics.latency_mean_ms)} ms (p95: {Math.round(metrics.latency_p95_ms)} ms)</span>
        </div>
      </footer>
    </div>
  );
}