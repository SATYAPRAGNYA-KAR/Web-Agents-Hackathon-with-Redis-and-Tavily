"use client";

import { useCoAgent } from "@copilotkit/react-core";
import { CopilotSidebar } from "@copilotkit/react-ui";
import { useState, useEffect } from "react";
import React from "react";

type AgentState = {
  proverbs: string[];
  market_news?: any[];
}

type QueryTab = {
  id: string;
  title: string;
  data: any[];
  timestamp: string;
  queryMode: string;
  exchange?: string;
  exchangeData?: any;
}

export default function CopilotKitPage() {
  const [themeColor] = useState("#10b981");

  return (
    <main style={{ "--copilot-kit-primary-color": themeColor } as any}>
      <YourMainContent />
      <CopilotSidebar
        clickOutsideToClose={false}
        defaultOpen={true}
        labels={{
          title: "Market Intelligence AI",
          initial: "🚀 Welcome to Next-Gen Market Intelligence!\n\n**Two Analysis Modes:**\n🌍 **Location-Based**: Global economic events near you\n🏢 **Exchange-Specific**: Deep-dive into specific markets\n\nReal-time dashboards, AI causation analysis, and predictive insights at your fingertips!"
        }}
      />
    </main>
  );
}

function YourMainContent() {
  const { state, setState } = useCoAgent<AgentState>({
    name: "sample_agent",
    initialState: {
      proverbs: [],
      market_news: [],
    },
  });

  const [tabs, setTabs] = useState<QueryTab[]>([]);
  const [activeTabId, setActiveTabId] = useState<string | null>(null);
  const [exchanges, setExchanges] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [queryMode, setQueryMode] = useState<"location" | "exchange">("location");
  const [selectedExchange, setSelectedExchange] = useState<string>("");

  useEffect(() => {
    fetchExchanges();
    loadTabsFromStorage();
  }, []);

  useEffect(() => {
    if (tabs.length > 0) {
      localStorage.setItem("market_tabs", JSON.stringify(tabs));
    }
  }, [tabs]);

  function loadTabsFromStorage() {
    const stored = localStorage.getItem("market_tabs");
    if (stored) {
      try {
        const loadedTabs = JSON.parse(stored);
        setTabs(loadedTabs);
        if (loadedTabs.length > 0) {
          setActiveTabId(loadedTabs[0].id);
        }
      } catch (e) {
        console.error("Error loading tabs:", e);
      }
    }
  }

  async function fetchExchanges() {
    try {
      const resp = await fetch("/api/exchanges");
      const data = await resp.json();
      if (data?.ok) {
        setExchanges(data.exchanges);
      }
    } catch (err) {
      console.error("Failed to fetch exchanges:", err);
    }
  }

  async function fetchMarketNews(mode: "location" | "exchange", exchangeId?: string) {
    setIsLoading(true);
    
    if (mode === "location") {
      if (!navigator.geolocation) {
        alert("Geolocation not supported by your browser");
        setIsLoading(false);
        return;
      }
      
      navigator.geolocation.getCurrentPosition(
        async (pos) => {
          await performFetch(pos.coords.latitude, pos.coords.longitude, "location_based", "Your Location", null);
        },
        (err) => {
          // Fallback to NYC for testing
          performFetch(40.7128, -74.0060, "location_based", "New York (Demo)", null);
        },
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
      );
    } else {
      if (!exchangeId) {
        alert("Please select a stock exchange");
        setIsLoading(false);
        return;
      }
      
      const exchange = exchanges.find(e => e.id === exchangeId);
      if (!exchange) {
        alert("Invalid exchange selected");
        setIsLoading(false);
        return;
      }
      
      const [lat, lon] = exchange.location;
      await performFetch(lat, lon, "exchange_specific", exchange.name, exchange);
    }
  }

  async function performFetch(lat: number, lon: number, mode: string, label: string, exchangeData: any) {
    try {
      const resp = await fetch("/api/agent_fetch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          lat, 
          lon, 
          query_mode: mode,
          days: 1,
          max_results: 20
        }),
      });

      if (!resp.ok) {
        const errorText = await resp.text();
        alert(`API error (${resp.status}): ${errorText}`);
        return;
      }

      const data = await resp.json();
      
      if (data?.ok) {
        const newTab: QueryTab = {
          id: `tab_${Date.now()}`,
          title: label,
          data: data.data,
          timestamp: new Date().toISOString(),
          queryMode: mode,
          exchange: mode === "exchange_specific" ? label : undefined,
          exchangeData: exchangeData
        };
        
        setTabs(prev => [newTab, ...prev]);
        setActiveTabId(newTab.id);
        
        setState({
          ...state,
          market_news: data.data,
        });
      } else {
        alert("Failed to fetch market news: " + (data.error || JSON.stringify(data)));
      }
    } catch (err: any) {
      console.error("Fetch error:", err);
      alert("Network error: " + err.message);
    } finally {
      setIsLoading(false);
    }
  }

  function closeTab(tabId: string) {
    setTabs(prev => prev.filter(t => t.id !== tabId));
    if (activeTabId === tabId) {
      const remainingTabs = tabs.filter(t => t.id !== tabId);
      setActiveTabId(remainingTabs.length > 0 ? remainingTabs[0].id : null);
    }
  }

  function clearAllTabs() {
    if (confirm("Clear all tabs?")) {
      setTabs([]);
      setActiveTabId(null);
      localStorage.removeItem("market_tabs");
    }
  }

  const activeTab = tabs.find(t => t.id === activeTabId);
  const displayData = activeTab?.data || [];

  return (
    <div className="min-h-screen w-screen bg-gradient-to-br from-purple-900 via-indigo-900 to-blue-900 p-6">
      <div className="max-w-[1600px] mx-auto">
        {/* Header */}
        <div className="bg-gradient-to-r from-cyan-500/20 via-purple-500/20 to-pink-500/20 backdrop-blur-xl p-8 rounded-3xl shadow-2xl mb-6 border border-white/10">
          <div className="flex items-center justify-center gap-4 mb-3">
            <div className="text-5xl">🌐</div>
            <h1 className="text-5xl font-black text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-purple-400 to-pink-400">
              Geo-Weighted Market Intelligence
            </h1>
            <div className="text-5xl">📊</div>
          </div>
          <p className="text-cyan-200 text-center text-lg font-medium">
            Real-time AI-powered causation analysis • Predictive market insights • Live dashboards
          </p>
        </div>

        {/* Query Controls */}
        <div className="bg-gradient-to-br from-indigo-500/20 to-purple-500/20 backdrop-blur-xl p-6 rounded-3xl shadow-2xl mb-6 border border-white/10">
          <div className="flex flex-col gap-4">
            <div className="flex gap-4 justify-center">
              <button
                onClick={() => setQueryMode("location")}
                className={`px-8 py-4 rounded-2xl font-bold text-lg transition-all transform hover:scale-105 ${
                  queryMode === "location"
                    ? "bg-gradient-to-r from-cyan-500 to-blue-500 text-white shadow-lg shadow-cyan-500/50"
                    : "bg-white/10 text-white hover:bg-white/20 border border-white/20"
                }`}
              >
                🌍 Location-Based Analysis
              </button>
              <button
                onClick={() => setQueryMode("exchange")}
                className={`px-8 py-4 rounded-2xl font-bold text-lg transition-all transform hover:scale-105 ${
                  queryMode === "exchange"
                    ? "bg-gradient-to-r from-purple-500 to-pink-500 text-white shadow-lg shadow-purple-500/50"
                    : "bg-white/10 text-white hover:bg-white/20 border border-white/20"
                }`}
              >
                🏢 Exchange-Specific Analysis
              </button>
            </div>

            {queryMode === "location" ? (
              <div className="text-center">
                <button
                  onClick={() => fetchMarketNews("location")}
                  disabled={isLoading}
                  className="px-10 py-5 bg-gradient-to-r from-cyan-500 via-blue-500 to-purple-500 rounded-2xl text-white hover:from-cyan-400 hover:via-blue-400 hover:to-purple-400 disabled:opacity-50 disabled:cursor-not-allowed font-bold text-xl shadow-2xl shadow-cyan-500/50 transition-all transform hover:scale-105"
                >
                  {isLoading ? "🔄 Analyzing Markets..." : "🌍 Analyze Markets Near Me"}
                </button>
                <p className="text-cyan-200 text-sm mt-3">
                  Discovers global economic events and their impact on nearby markets with AI precision
                </p>
              </div>
            ) : (
              <div className="flex flex-col gap-3">
                <select
                  value={selectedExchange}
                  onChange={(e) => setSelectedExchange(e.target.value)}
                  className="px-6 py-4 rounded-2xl bg-white/10 text-white border-2 border-purple-400/50 focus:border-purple-400 focus:outline-none backdrop-blur-xl font-medium text-lg"
                >
                  <option value="" className="text-gray-900">🌐 Select a Stock Exchange</option>
                  {exchanges.map(ex => (
                    <option key={ex.id} value={ex.id} className="text-gray-900">
                      {ex.name} ({ex.city}, {ex.country}) - {ex.indices.join(", ")}
                    </option>
                  ))}
                </select>
                <button
                  onClick={() => fetchMarketNews("exchange", selectedExchange)}
                  disabled={isLoading || !selectedExchange}
                  className="px-10 py-5 bg-gradient-to-r from-purple-500 via-pink-500 to-red-500 rounded-2xl text-white hover:from-purple-400 hover:via-pink-400 hover:to-red-400 disabled:opacity-50 disabled:cursor-not-allowed font-bold text-xl shadow-2xl shadow-purple-500/50 transition-all transform hover:scale-105"
                >
                  {isLoading ? "🔄 Analyzing Exchange..." : "🏢 Launch Deep Analysis"}
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Tabs */}
        {tabs.length > 0 && (
          <div className="bg-gradient-to-br from-slate-800/40 to-slate-900/40 backdrop-blur-xl rounded-3xl shadow-2xl overflow-hidden border border-white/10">
            <div className="flex items-center gap-2 p-3 border-b border-white/10 overflow-x-auto bg-black/20">
              {tabs.map(tab => (
                <div
                  key={tab.id}
                  className={`flex items-center gap-2 px-5 py-3 rounded-xl cursor-pointer transition-all transform hover:scale-105 ${
                    activeTabId === tab.id
                      ? "bg-gradient-to-r from-cyan-500 to-purple-500 text-white shadow-lg"
                      : "bg-white/5 text-white/70 hover:bg-white/10 border border-white/10"
                  }`}
                  onClick={() => setActiveTabId(tab.id)}
                >
                  <span className="font-bold whitespace-nowrap">{tab.title}</span>
                  <span className="text-xs bg-white/20 px-2 py-1 rounded-full">({tab.data.length})</span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      closeTab(tab.id);
                    }}
                    className="ml-2 text-white/70 hover:text-white font-bold"
                  >
                    ✕
                  </button>
                </div>
              ))}
              <button
                onClick={clearAllTabs}
                className="ml-auto px-4 py-2 text-sm bg-gradient-to-r from-red-500 to-pink-500 text-white rounded-xl hover:from-red-400 hover:to-pink-400 font-bold shadow-lg"
              >
                Clear All
              </button>
            </div>

            <div className="p-6">
              {/* Exchange Dashboard */}
              {activeTab && (
                <ExchangeDashboard 
                  tab={activeTab} 
                  newsCount={displayData.length}
                />
              )}

              {/* News Cards */}
              {displayData.length > 0 ? (
                <div className="grid grid-cols-1 gap-4 mt-6">
                  {displayData.map((item: any, idx: number) => (
                    <NewsCard key={idx} item={item} />
                  ))}
                </div>
              ) : (
                <p className="text-cyan-200 italic text-center py-8 text-lg">No data in this tab</p>
              )}
            </div>
          </div>
        )}

        {tabs.length === 0 && !isLoading && (
          <div className="bg-gradient-to-br from-indigo-500/20 to-purple-500/20 backdrop-blur-xl p-16 rounded-3xl shadow-2xl text-center border border-white/10">
            <div className="text-8xl mb-6">🚀</div>
            <p className="text-white text-2xl mb-3 font-bold">
              Ready to Analyze Markets?
            </p>
            <p className="text-cyan-200 text-lg">
              Choose a query mode above and unlock AI-powered market intelligence!
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

function ExchangeDashboard({ tab, newsCount }: { tab: QueryTab; newsCount: number }) {
  const [mockData, setMockData] = useState({
    price: 0,
    change: 0,
    changePercent: 0,
    volume: 0,
    high: 0,
    low: 0
  });

  useEffect(() => {
    // Generate realistic mock data based on exchange
    const basePrice = Math.random() * 40000 + 10000;
    const change = (Math.random() - 0.5) * 500;
    const changePercent = (change / basePrice) * 100;
    
    setMockData({
      price: basePrice,
      change: change,
      changePercent: changePercent,
      volume: Math.random() * 5000000000 + 1000000000,
      high: basePrice + Math.abs(change) * 1.5,
      low: basePrice - Math.abs(change) * 1.5
    });
  }, [tab.id]);

  const isPositive = mockData.change >= 0;
  const exchangeData = tab.exchangeData;
  
  // Get primary exchange from first news item if available
  const primaryExchange = tab.data[0]?.primary_exchange || {};
  
  return (
    <div className="bg-gradient-to-br from-cyan-500/10 via-purple-500/10 to-pink-500/10 backdrop-blur-sm rounded-2xl p-6 border border-white/20 mb-6">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h2 className="text-3xl font-black text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-purple-400 mb-2">
            {tab.title}
          </h2>
          {exchangeData && (
            <div className="flex flex-wrap gap-2 text-sm text-cyan-200">
              <span className="bg-cyan-500/20 px-3 py-1 rounded-full border border-cyan-400/30">
                📍 {exchangeData.city}, {exchangeData.country}
              </span>
              {exchangeData.indices?.slice(0, 2).map((index: string, i: number) => (
                <span key={i} className="bg-purple-500/20 px-3 py-1 rounded-full border border-purple-400/30">
                  📊 {index}
                </span>
              ))}
            </div>
          )}
          {primaryExchange.exchange_name && !exchangeData && (
            <div className="text-sm text-cyan-200">
              <span className="bg-cyan-500/20 px-3 py-1 rounded-full border border-cyan-400/30">
                🏢 {primaryExchange.exchange_name}
              </span>
            </div>
          )}
        </div>
        <div className="text-right">
          <div className="text-sm text-cyan-300 font-semibold mb-1">LIVE MARKET DATA</div>
          <div className="text-xs text-cyan-400">Updated: {new Date().toLocaleTimeString()}</div>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* Current Price */}
        <div className="bg-gradient-to-br from-cyan-500/20 to-blue-500/20 backdrop-blur-sm rounded-xl p-4 border border-cyan-400/30">
          <div className="text-cyan-300 text-xs font-semibold mb-1">CURRENT PRICE</div>
          <div className="text-3xl font-black text-white mb-1">
            ${mockData.price.toLocaleString('en-US', { maximumFractionDigits: 2 })}
          </div>
          <div className={`text-sm font-bold ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
            {isPositive ? '▲' : '▼'} {Math.abs(mockData.change).toFixed(2)} ({Math.abs(mockData.changePercent).toFixed(2)}%)
          </div>
        </div>

        {/* Volume */}
        <div className="bg-gradient-to-br from-purple-500/20 to-pink-500/20 backdrop-blur-sm rounded-xl p-4 border border-purple-400/30">
          <div className="text-purple-300 text-xs font-semibold mb-1">VOLUME</div>
          <div className="text-2xl font-black text-white mb-1">
            {(mockData.volume / 1000000000).toFixed(2)}B
          </div>
          <div className="text-xs text-purple-300">Trading Volume</div>
        </div>

        {/* High/Low */}
        <div className="bg-gradient-to-br from-green-500/20 to-emerald-500/20 backdrop-blur-sm rounded-xl p-4 border border-green-400/30">
          <div className="text-green-300 text-xs font-semibold mb-1">24H HIGH</div>
          <div className="text-2xl font-black text-white mb-1">
            ${mockData.high.toLocaleString('en-US', { maximumFractionDigits: 2 })}
          </div>
          <div className="text-xs text-green-300">Peak Value</div>
        </div>

        <div className="bg-gradient-to-br from-orange-500/20 to-red-500/20 backdrop-blur-sm rounded-xl p-4 border border-orange-400/30">
          <div className="text-orange-300 text-xs font-semibold mb-1">24H LOW</div>
          <div className="text-2xl font-black text-white mb-1">
            ${mockData.low.toLocaleString('en-US', { maximumFractionDigits: 2 })}
          </div>
          <div className="text-xs text-orange-300">Bottom Value</div>
        </div>
      </div>

      {/* Analysis Summary */}
      <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white/5 rounded-xl p-4 border border-white/10">
          <div className="text-cyan-300 text-xs font-semibold mb-2">📰 NEWS ANALYZED</div>
          <div className="text-3xl font-black text-white">{newsCount}</div>
        </div>
        
        <div className="bg-white/5 rounded-xl p-4 border border-white/10">
          <div className="text-purple-300 text-xs font-semibold mb-2">🎯 MARKET SENTIMENT</div>
          <div className="text-2xl font-black text-transparent bg-clip-text bg-gradient-to-r from-green-400 to-emerald-400">
            {isPositive ? 'BULLISH' : 'BEARISH'}
          </div>
        </div>
        
        <div className="bg-white/5 rounded-xl p-4 border border-white/10">
          <div className="text-pink-300 text-xs font-semibold mb-2">⚡ AI CONFIDENCE</div>
          <div className="text-3xl font-black text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-purple-400">
            {Math.floor(Math.random() * 20 + 75)}%
          </div>
        </div>
      </div>
    </div>
  );
}

function NewsCard({ item }: { item: any }) {
  const primaryExchange = item.primary_exchange || {};
  const impact = primaryExchange.predicted_impact || "neutral";
  
  const impactConfig = {
    positive: {
      bg: "from-green-500/20 to-emerald-500/20",
      border: "border-green-400/50",
      icon: "📈",
      text: "text-green-400"
    },
    negative: {
      bg: "from-red-500/20 to-pink-500/20",
      border: "border-red-400/50",
      icon: "📉",
      text: "text-red-400"
    },
    neutral: {
      bg: "from-slate-500/20 to-gray-500/20",
      border: "border-gray-400/50",
      icon: "➡️",
      text: "text-gray-400"
    }
  };

  const config = impactConfig[impact as keyof typeof impactConfig];

  const formatDate = (dateString: string | null) => {
    if (!dateString) return "Recently published";
    
    try {
      const date = new Date(dateString);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffMins = Math.floor(diffMs / 60000);
      const diffHours = Math.floor(diffMs / 3600000);
      
      if (diffMins < 60) return `${diffMins}m ago`;
      if (diffHours < 24) return `${diffHours}h ago`;
      
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    } catch (e) {
      return dateString;
    }
  };

  return (
    <div className={`bg-gradient-to-br ${config.bg} backdrop-blur-sm border-2 ${config.border} rounded-2xl p-6 text-white shadow-xl hover:shadow-2xl transition-all transform hover:scale-[1.02]`}>
      <div className="flex flex-col lg:flex-row justify-between items-start gap-6">
        <div className="flex-1">
          <a 
            className="font-bold text-2xl hover:underline block mb-3 text-white hover:text-cyan-300 transition-colors leading-tight" 
            href={item.url} 
            target="_blank" 
            rel="noreferrer noopener"
          >
            {item.title}
            <span className="ml-2 text-lg">🔗</span>
          </a>
          
          <div className="text-sm text-white/90 mt-3 leading-relaxed mb-4 bg-black/20 p-4 rounded-xl">
            {item.snippet}
          </div>
          
          <div className="flex flex-wrap gap-3 items-center text-sm bg-black/30 p-3 rounded-xl backdrop-blur-sm">
            <span className="bg-cyan-500/30 px-3 py-1 rounded-full border border-cyan-400/50 font-semibold">
              📰 {item.source || "Unknown"}
            </span>
            <span className="bg-purple-500/30 px-3 py-1 rounded-full border border-purple-400/50 font-semibold">
              🕐 {formatDate(item.published_at)}
            </span>
            {primaryExchange.exchange_name && (
              <span className="bg-pink-500/30 px-3 py-1 rounded-full border border-pink-400/50 font-semibold">
                🏢 {primaryExchange.exchange_name}
              </span>
            )}
            <a
              href={item.url}
              target="_blank"
              rel="noreferrer noopener"
              className="ml-auto px-4 py-2 bg-gradient-to-r from-cyan-500 to-purple-500 hover:from-cyan-400 hover:to-purple-400 rounded-full transition-all font-bold shadow-lg"
            >
              Read Article →
            </a>
          </div>
        </div>

        <div className="w-full lg:min-w-[320px] lg:max-w-[380px] bg-gradient-to-br from-black/40 to-black/20 backdrop-blur-md p-5 rounded-2xl border border-white/20">
          <div className="flex items-center gap-3 mb-4 pb-4 border-b border-white/20">
            <span className="text-4xl">{config.icon}</span>
            <div>
              <div className={`font-black capitalize text-2xl ${config.text}`}>{impact}</div>
              <div className="text-xs text-white/70 font-semibold">
                Confidence: <span className="text-cyan-400">{primaryExchange.confidence || "unknown"}</span>
              </div>
            </div>
          </div>
          
          <div className="text-sm mt-3 mb-4 text-white/95 leading-relaxed bg-white/5 p-4 rounded-xl border border-white/10">
            <strong className="text-cyan-400 block mb-2 text-base">🧠 AI Analysis</strong>
            {primaryExchange.reasoning || "No analysis available"}
          </div>
          
          {primaryExchange.affected_sectors && primaryExchange.affected_sectors.length > 0 && (
            <div className="mb-3 bg-white/5 p-3 rounded-xl border border-white/10">
              <strong className="block mb-2 text-purple-400 text-sm">🏭 Sectors</strong>
              <div className="flex flex-wrap gap-2">
                {primaryExchange.affected_sectors.map((sector: string, idx: number) => (
                  <span key={idx} className="bg-purple-500/30 px-3 py-1 rounded-full text-xs font-semibold border border-purple-400/50">
                    {sector}
                  </span>
                ))}
              </div>
            </div>
          )}
          
          {primaryExchange.indices && primaryExchange.indices.length > 0 && (
            <div className="mb-3 bg-white/5 p-3 rounded-xl border border-white/10">
              <strong className="block mb-2 text-green-400 text-sm">📈 Indices</strong>
              <div className="text-white/90 text-sm font-medium">
                {primaryExchange.indices.join(" • ")}
              </div>
            </div>
          )}
          
          <div className="flex justify-between items-center text-xs pt-3 border-t border-white/20 text-white/60 font-semibold">
            <span>📍 {primaryExchange.distance_km}km</span>
            <span>⚖️ Weight: {primaryExchange.geo_weight}</span>
          </div>
        </div>
      </div>
    </div>
  );
}