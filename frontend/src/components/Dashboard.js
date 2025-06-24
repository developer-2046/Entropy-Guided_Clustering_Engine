import React, { useState, useEffect, useRef } from 'react';
import config from '../config';

const MarketEntropyDashboard = () => {
  const [regimeData, setRegimeData] = useState(null);
  const [historicalData, setHistoricalData] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [alerts, setAlerts] = useState([]);
  
  // Use polling instead of WebSocket for Netlify
  useEffect(() => {
    const fetchRegimeData = async () => {
      try {
        // Fetch current regime
        const response = await fetch(`${config.apiUrl}/api/v1/regime/current`);
        const data = await response.json();
        
        setRegimeData(data);
        setHistoricalData(prev => [...prev.slice(-100), data]);
        setIsConnected(true);
        
        // Add alerts for high stress
        if (data.stress_level === 'HIGH' || data.stress_level === 'CRITICAL') {
          setAlerts(prev => [...prev, {
            id: Date.now(),
            message: `🚨 ${data.stress_level} Market Stress Detected`,
            entropy: data.entropy_score,
            timestamp: new Date().toLocaleTimeString()
          }]);
        }
        
      } catch (error) {
        console.error('Failed to fetch regime data:', error);
        setIsConnected(false);
      }
    };
    
    // Initial fetch
    fetchRegimeData();
    
    // Poll every 5 seconds
    const interval = setInterval(fetchRegimeData, 5000);
    
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-gray-900 text-white">
      {/* Header */}
      <header className="border-b border-blue-500/30 bg-black/20 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
                MarketEntropy
              </div>
              <div className="text-sm text-gray-400">Real-time Market Regime Detection</div>
            </div>
            
            <div className="flex items-center space-x-4">
              <ConnectionStatus isConnected={isConnected} />
              <CurrentTime />
            </div>
          </div>
        </div>
      </header>

      {/* Main Dashboard */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Platform indicator */}
        <div className="mb-4 p-4 bg-black/20 rounded-lg text-sm text-green-400 text-center">
          🚀 Running on Netlify Functions | Live Polling Mode
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Column */}
          <div className="lg:col-span-1 space-y-6">
            <RegimeStatusCard regimeData={regimeData} />
            <AlertsPanel alerts={alerts} setAlerts={setAlerts} />
          </div>
          
          {/* Middle Column */}
          <div className="lg:col-span-1">
            <CorrelationHeatmap regimeData={regimeData} />
          </div>
          
          {/* Right Column */}
          <div className="lg:col-span-1">
            <NetworkVisualization regimeData={regimeData} />
          </div>
        </div>
        
        {/* Bottom Row */}
        <div className="mt-8">
          <EntropyTimeline historicalData={historicalData} />
        </div>
      </main>
    </div>
  );
};

// Connection Status Component
const ConnectionStatus = ({ isConnected }) => (
  <div className="flex items-center space-x-2">
    <div className={`w-3 h-3 rounded-full ${isConnected ? 'bg-green-400 animate-pulse' : 'bg-red-400'}`} />
    <span className="text-sm text-gray-300">
      {isConnected ? 'Live Polling' : 'Disconnected'}
    </span>
  </div>
);

// Current Time Component
const CurrentTime = () => {
  const [time, setTime] = useState(new Date());
  
  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);
  
  return (
    <div className="text-sm text-gray-300">
      {time.toLocaleTimeString()}
    </div>
  );
};

// Regime Status Card (same as before)
const RegimeStatusCard = ({ regimeData }) => {
  const getRegimeName = (id) => {
    const names = ['Stable', 'Volatile', 'Crisis', 'Recovery'];
    return names[id] || 'Unknown';
  };
  
  const getStressColor = (level) => {
    switch (level) {
      case 'LOW': return 'text-green-400';
      case 'MEDIUM': return 'text-yellow-400';
      case 'HIGH': return 'text-orange-400';
      case 'CRITICAL': return 'text-red-400';
      default: return 'text-gray-400';
    }
  };

  return (
    <div className="bg-black/30 backdrop-blur-sm border border-blue-500/30 rounded-lg p-6">
      <h3 className="text-lg font-semibold mb-4 text-blue-300">Current Market Regime</h3>
      
      {regimeData ? (
        <div className="space-y-4">
          <div className="text-center">
            <div className="text-3xl font-bold text-white mb-2">
              {getRegimeName(regimeData.regime_id)}
            </div>
            <div className="text-sm text-gray-400">
              Confidence: {(regimeData.probability * 100).toFixed(1)}%
            </div>
            <div className="text-xs text-blue-400 mt-1">
              Mode: {regimeData.model_status}
            </div>
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <div className="text-center">
              <div className="text-xl font-bold text-blue-400">
                {regimeData.entropy_score?.toFixed(3)}
              </div>
              <div className="text-xs text-gray-400">Entropy Score</div>
            </div>
            
            <div className="text-center">
              <div className={`text-xl font-bold ${getStressColor(regimeData.market_stress_level)}`}>
                {regimeData.market_stress_level}
              </div>
              <div className="text-xs text-gray-400">Stress Level</div>
            </div>
          </div>
          
          {/* Regime Probability Bars */}
          <div className="space-y-2">
            <div className="text-sm text-gray-400 mb-2">Regime Probabilities:</div>
            {[0, 1, 2, 3].map(id => (
              <div key={id} className="flex items-center space-x-2">
                <div className="w-16 text-xs text-gray-400">{getRegimeName(id)}</div>
                <div className="flex-1 bg-gray-700 rounded-full h-2">
                  <div 
                    className={`h-2 rounded-full transition-all duration-500 ${
                      id === regimeData.regime_id ? 'bg-blue-400' : 'bg-gray-500'
                    }`}
                    style={{ 
                      width: id === regimeData.regime_id ? 
                        `${regimeData.probability * 100}%` : '10%' 
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="text-center text-gray-400">
          <div className="animate-pulse">Loading regime data...</div>
        </div>
      )}
    </div>
  );
};

// Include all your other components (AlertsPanel, CorrelationHeatmap, etc.)
// ... (copy from previous version)

const AlertsPanel = ({ alerts, setAlerts }) => {
  const clearAlert = (id) => {
    setAlerts(prev => prev.filter(alert => alert.id !== id));
  };

  return (
    <div className="bg-black/30 backdrop-blur-sm border border-blue-500/30 rounded-lg p-6">
      <h3 className="text-lg font-semibold mb-4 text-blue-300">Market Alerts</h3>
      
      <div className="space-y-2 max-h-64 overflow-y-auto">
        {alerts.length > 0 ? (
          alerts.slice(-5).reverse().map(alert => (
            <div key={alert.id} className="bg-red-900/30 border border-red-500/50 rounded p-3">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="text-sm font-medium text-red-300">
                    {alert.message}
                  </div>
                  <div className="text-xs text-gray-400 mt-1">
                    Entropy: {alert.entropy.toFixed(3)} • {alert.timestamp}
                  </div>
                </div>
                <button 
                  onClick={() => clearAlert(alert.id)}
                  className="text-gray-400 hover:text-white ml-2"
                >
                  ×
                </button>
              </div>
            </div>
          ))
        ) : (
          <div className="text-center text-gray-400 py-8">
            No alerts
          </div>
        )}
      </div>
    </div>
  );
};

const CorrelationHeatmap = ({ regimeData }) => {
  // Simple placeholder - you can add your full visualization here
  return (
    <div className="bg-black/30 backdrop-blur-sm border border-blue-500/30 rounded-lg p-6">
      <h3 className="text-lg font-semibold mb-4 text-blue-300">Correlation Matrix</h3>
      <div className="h-64 flex items-center justify-center text-gray-400">
        <div className="text-center">
          <div className="text-2xl mb-2">📊</div>
          <div>Live correlation visualization</div>
          <div className="text-sm mt-2">
            Regime: {regimeData ? ['Stable', 'Volatile', 'Crisis', 'Recovery'][regimeData.regime_id] : 'Loading...'}
          </div>
        </div>
      </div>
    </div>
  );
};

const NetworkVisualization = ({ regimeData }) => {
  return (
    <div className="bg-black/30 backdrop-blur-sm border border-blue-500/30 rounded-lg p-6">
      <h3 className="text-lg font-semibold mb-4 text-blue-300">Network Graph</h3>
      <div className="h-64 flex items-center justify-center text-gray-400">
        <div className="text-center">
          <div className="text-2xl mb-2">🌐</div>
          <div>Market network visualization</div>
          <div className="text-sm mt-2">
            Stress: {regimeData?.market_stress_level || 'Loading...'}
          </div>
        </div>
      </div>
    </div>
  );
};

const EntropyTimeline = ({ historicalData }) => {
  if (!historicalData || historicalData.length === 0) {
    return (
      <div className="bg-black/30 backdrop-blur-sm border border-blue-500/30 rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-4 text-blue-300">Entropy Timeline</h3>
        <div className="h-32 flex items-center justify-center text-gray-400">
          <div className="animate-pulse">Collecting historical data...</div>
        </div>
      </div>
    );
  }

  const maxEntropy = Math.max(...historicalData.map(d => d.entropy_score));
  const minEntropy = Math.min(...historicalData.map(d => d.entropy_score));

  return (
    <div className="bg-black/30 backdrop-blur-sm border border-blue-500/30 rounded-lg p-6">
      <h3 className="text-lg font-semibold mb-4 text-blue-300">Entropy Timeline</h3>
      
      <div className="h-32 flex items-end space-x-1 overflow-x-auto">
        {historicalData.slice(-50).map((data, i) => {
          const height = ((data.entropy_score - minEntropy) / (maxEntropy - minEntropy)) * 100;
          const color = data.stress_level === 'CRITICAL' ? 'bg-red-400' :
                       data.stress_level === 'HIGH' ? 'bg-orange-400' :
                       data.stress_level === 'MEDIUM' ? 'bg-yellow-400' :
                       'bg-blue-400';
          
          return (
            <div
              key={i}
              className={`w-2 ${color} opacity-80 transition-all duration-300 hover:opacity-100`}
              style={{ height: `${Math.max(5, height)}%` }}
              title={`Entropy: ${data.entropy_score.toFixed(3)} | Stress: ${data.stress_level}`}
            />
          );
        })}
      </div>
      
      <div className="flex justify-between text-xs text-gray-400 mt-2">
        <span>Min: {minEntropy.toFixed(2)}</span>
        <span>Points: {historicalData.length}</span>
        <span>Latest: {historicalData[historicalData.length - 1]?.entropy_score.toFixed(3)}</span>
        <span>Max: {maxEntropy.toFixed(2)}</span>
      </div>
    </div>
  );
};

export default MarketEntropyDashboard;
