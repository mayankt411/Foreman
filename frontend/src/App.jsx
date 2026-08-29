import React, { useState, useEffect, useMemo, useCallback } from 'react';
import TopHUD from './components/TopHUD';
import SidebarControls from './components/SidebarControls';
import LiveInspectionFeed from './components/LiveInspectionFeed';
import RPIDashboard from './components/RPIDashboard';
import OperatorConsole from './components/OperatorConsole';
import TableBenchmark from './components/TableBenchmark';
import ECERecoveryChart from './components/ECERecoveryChart';

export default function App() {
  const [predictions, setPredictions] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [currentIndex, setCurrentIndex] = useState(0);

  // Hyperparameters
  const [w1, setW1] = useState(0.35);
  const [w2, setW2] = useState(0.35);
  const [w3, setW3] = useState(0.30);
  const [thetaRoute, setThetaRoute] = useState(0.351);

  const [selectedCategory, setSelectedCategory] = useState('all');
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1.0);
  const [activeTab, setActiveTab] = useState('console');

  const [currentTemperature, setCurrentTemperature] = useState(0.564);
  const [operatorLogs, setOperatorLogs] = useState([]);

  useEffect(() => {
    Promise.all([
      fetch('/api/metrics').then(r => r.json()),
      fetch('/api/predictions').then(r => r.json())
    ]).then(([mData, pData]) => {
      setMetrics(mData);
      setPredictions(pData);
      if (mData && mData.fitted_temperature) {
        setCurrentTemperature(mData.fitted_temperature);
      }
    }).catch(err => console.error('Fetch error:', err));
  }, []);

  const filteredPreds = useMemo(() => {
    if (!predictions.length) return [];
    if (selectedCategory === 'all') return predictions;
    return predictions.filter(p => p.predicted_label === selectedCategory || p.ground_truth_label === selectedCategory);
  }, [predictions, selectedCategory]);

  const safeIndex = Math.min(currentIndex, Math.max(0, filteredPreds.length - 1));
  const currentFrame = filteredPreds[safeIndex] || predictions[0] || {
    predicted_label: 'normal',
    ground_truth_label: 'normal',
    raw_confidence: 0.928,
    u_calib: 0.011,
    severity_score: 0.050,
    faithfulness_score: 0.8329,
    rationale: 'Surface trace geometry conforms to IPC-A-610 standards.'
  };

  useEffect(() => {
    if (!isPlaying || filteredPreds.length === 0) return;
    const intervalMs = 1000 / playbackSpeed;
    const timer = setInterval(() => {
      setCurrentIndex(prev => (prev + 1) % filteredPreds.length);
    }, intervalMs);
    return () => clearInterval(timer);
  }, [isPlaying, playbackSpeed, filteredPreds.length]);

  const u_norm = Number(currentFrame.u_calib || 0.011);
  const s_norm = Number(currentFrame.severity_score || 0.050);
  const f_score = Number(currentFrame.faithfulness_score || 0.8329);
  const unfaith_norm = Math.max(0.0, 1.0 - f_score);

  const wSum = (w1 + w2 + w3) || 1.0;
  const w1_n = w1 / wSum;
  const w2_n = w2 / wSum;
  const w3_n = w3 / wSum;

  const liveRPI = (w1_n * u_norm) + (w2_n * s_norm) + (w3_n * unfaith_norm);
  const isRouted = liveRPI > thetaRoute;

  const handleAccept = useCallback(() => {
    const newT = Math.max(0.10, Number((currentTemperature - 0.02).toFixed(3)));
    setCurrentTemperature(newT);
    setOperatorLogs(prev => [...prev, {
      frame_index: safeIndex,
      action: 'accept',
      temperature: newT,
      timestamp: new Date().toLocaleTimeString()
    }]);
    fetch('/api/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ frame_index: safeIndex, action: 'accept', current_temperature: currentTemperature })
    }).catch(() => {});
  }, [currentTemperature, safeIndex]);

  const handleOverrule = useCallback((overrideLabel) => {
    const newT = Math.min(2.0, Number((currentTemperature + 0.04).toFixed(3)));
    setCurrentTemperature(newT);
    setOperatorLogs(prev => [...prev, {
      frame_index: safeIndex,
      action: `overrule (${overrideLabel})`,
      temperature: newT,
      timestamp: new Date().toLocaleTimeString()
    }]);
    fetch('/api/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ frame_index: safeIndex, action: 'overrule', override_label: overrideLabel, current_temperature: currentTemperature })
    }).catch(() => {});
  }, [currentTemperature, safeIndex]);

  // Keyboard Navigation
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
      if (e.key === 'ArrowLeft') {
        setCurrentIndex(prev => Math.max(0, prev - 1));
      } else if (e.key === 'ArrowRight') {
        setCurrentIndex(prev => Math.min((filteredPreds.length || 1) - 1, prev + 1));
      } else if (e.key === ' ') {
        e.preventDefault();
        setIsPlaying(p => !p);
      } else if (e.key === 'a' || e.key === 'A') {
        handleAccept();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [filteredPreds.length, handleAccept]);

  return (
    <div className="min-h-screen bg-[#121316] text-[#e6e8ec] p-4 md:p-6 lg:p-7 max-w-[1560px] mx-auto font-sans">
      {/* Station Header */}
      <header className="flex flex-col md:flex-row items-start md:items-center justify-between gap-3 mb-5 pb-3.5 border-b border-[#2c303a]">
        <div>
          <h1 className="text-base font-semibold text-[#e6e8ec]">
            XiVLM-Loop
          </h1>
          <p className="text-xs text-[#8c92a0] mt-0.5">
            Explainable vision-language inspection with active recalibration for edge manufacturing
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
                currentFrame={currentFrame}
                frameIndex={safeIndex}
                totalFrames={filteredPreds.length || 189}
                onPrev={() => setCurrentIndex(prev => Math.max(0, prev - 1))}
                onNext={() => setCurrentIndex(prev => Math.min((filteredPreds.length || 189) - 1, prev + 1))}
                onSelectFrame={(index) => setCurrentIndex(index)}
                isPlaying={isPlaying}
                onTogglePlay={() => setIsPlaying(p => !p)}
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
                onAccept={handleAccept}
                onOverrule={handleOverrule}
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
            <ECERecoveryChart 
              metrics={metrics} 
              operatorLogs={operatorLogs} 
              currentTemperature={currentTemperature} 
            />
          </div>
        </div>
      )}

      {/* Industrial Footer */}
      <footer className="mt-8 pt-3 border-t border-[#2c303a] flex flex-col md:flex-row items-center justify-between text-xs text-[#8c92a0] gap-2">
        <span>XiVLM-Loop Architecture · Autonomous Inspection & Active Recalibration</span>
        <div className="flex items-center gap-4 text-[11px]">
          <span>Shortcuts: [← / →] Seek · [Space] Stream · [A] Accept · [O] Overrule</span>
          <span className="font-mono text-[#e6e8ec]">Latency: 3.13 ms (p95: 5.54 ms)</span>
        </div>
      </footer>
    </div>
  );
}