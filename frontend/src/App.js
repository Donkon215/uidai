import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { MapContainer, TileLayer, useMap, useMapEvents } from 'react-leaflet';
import { LineChart, Line, BarChart, Bar, PieChart, Pie, Cell, AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend, RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis } from 'recharts';
import axios from 'axios';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

const API_BASE = 'http://localhost:8000/api';

// India boundary for filtering
const INDIA_BOUNDS = {
  min_lat: 6.5,
  max_lat: 35.5,
  min_lng: 68.0,
  max_lng: 97.5
};

// Check if point is within India
const isWithinIndia = (lat, lng) => {
  return lat >= INDIA_BOUNDS.min_lat && 
         lat <= INDIA_BOUNDS.max_lat && 
         lng >= INDIA_BOUNDS.min_lng && 
         lng <= INDIA_BOUNDS.max_lng;
};

// Sector configuration
const SECTORS = [
  { id: 'education', label: 'Education', icon: '📚', color: '#4361ee', metric: 'School_Dropout_Risk_Index' },
  { id: 'hunger', label: 'Ration/Hunger', icon: '🍚', color: '#e67e22', metric: 'Migrant_Hunger_Score' },
  { id: 'rural', label: 'Rural Dev', icon: '🏘️', color: '#f1c40f', metric: 'Village_Hollow_Out_Rate' },
  { id: 'electoral', label: 'Electoral', icon: '🗳️', color: '#e74c3c', metric: 'Electoral_Discrepancy_Index' },
  { id: 'labor', label: 'Labor', icon: '👷', color: '#2ecc71', metric: 'Skill_Gap_Migration_Flow' },
];

// User roles for chatbot
const USER_ROLES = [
  { id: 'police', label: 'Police Administration', icon: '👮' },
  { id: 'district_admin', label: 'District Administration', icon: '🏛️' },
  { id: 'state_govt', label: 'State Government', icon: '🏢' },
  { id: 'budget', label: 'Budget & Finance', icon: '💰' },
  { id: 'education', label: 'Education Department', icon: '🎓' },
  { id: 'health', label: 'Health Department', icon: '🏥' },
  { id: 'skill', label: 'Skill & Employment', icon: '🛠️' }
];

// Enhanced color interpolation for smooth heatmap
const getHeatmapRGB = (score) => {
  // Blue -> Cyan -> Green -> Yellow -> Orange -> Red gradient
  if (score >= 70) return { r: 231, g: 76, b: 60 };    // Critical Red
  if (score >= 55) return { r: 230, g: 126, b: 34 };   // Orange
  if (score >= 40) return { r: 241, g: 196, b: 15 };   // Yellow
  if (score >= 25) return { r: 46, g: 204, b: 113 };   // Green
  if (score >= 15) return { r: 26, g: 188, b: 156 };   // Teal
  return { r: 52, g: 152, b: 219 };                     // Blue
};

// Interpolate between two colors
const interpolateColor = (score) => {
  const stops = [
    { score: 0, r: 52, g: 152, b: 219 },    // Blue
    { score: 20, r: 26, g: 188, b: 156 },   // Teal
    { score: 35, r: 46, g: 204, b: 113 },   // Green
    { score: 50, r: 241, g: 196, b: 15 },   // Yellow
    { score: 65, r: 230, g: 126, b: 34 },   // Orange
    { score: 80, r: 231, g: 76, b: 60 },    // Red
    { score: 100, r: 192, g: 57, b: 43 }    // Dark Red
  ];
  
  for (let i = 0; i < stops.length - 1; i++) {
    if (score >= stops[i].score && score <= stops[i + 1].score) {
      const t = (score - stops[i].score) / (stops[i + 1].score - stops[i].score);
      return {
        r: Math.round(stops[i].r + t * (stops[i + 1].r - stops[i].r)),
        g: Math.round(stops[i].g + t * (stops[i + 1].g - stops[i].g)),
        b: Math.round(stops[i].b + t * (stops[i + 1].b - stops[i].b))
      };
    }
  }
  return stops[stops.length - 1];
};

// Canvas Heatmap Layer Component
function CanvasHeatmapLayer({ data, activeSector, onPincodeClick }) {
  const map = useMap();
  const canvasRef = useRef(null);
  const tooltipRef = useRef(null);
  const [hoveredPoint, setHoveredPoint] = useState(null);
  
  // Get metric value based on sector
  const getMetricValue = useCallback((item) => {
    if (activeSector === 'all') {
      return item.Governance_Risk_Score || 0;
    }
    const sector = SECTORS.find(s => s.id === activeSector);
    return sector ? (item[sector.metric] || 0) : 0;
  }, [activeSector]);

  // Render canvas
  const renderCanvas = useCallback(() => {
    if (!canvasRef.current || !data.length) return;
    
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const size = map.getSize();
    const zoom = map.getZoom();
    
    canvas.width = size.x;
    canvas.height = size.y;
    
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Calculate point size based on zoom level
    const baseRadius = zoom < 5 ? 8 : zoom < 7 ? 6 : zoom < 9 ? 4 : 3;
    const blurRadius = zoom < 5 ? 12 : zoom < 7 ? 8 : zoom < 9 ? 5 : 3;
    
    // Sort by risk score so higher risk points render on top
    const sortedData = [...data].sort((a, b) => getMetricValue(a) - getMetricValue(b));
    
    // Render each point
    sortedData.forEach(point => {
      if (!isWithinIndia(point.latitude, point.longitude)) return;
      
      const latLng = L.latLng(point.latitude, point.longitude);
      const pixel = map.latLngToContainerPoint(latLng);
      
      // Skip if outside visible area
      if (pixel.x < -50 || pixel.x > canvas.width + 50 || 
          pixel.y < -50 || pixel.y > canvas.height + 50) return;
      
      const score = getMetricValue(point);
      const color = interpolateColor(score);
      
      // Draw glow/blur effect for heatmap look
      const gradient = ctx.createRadialGradient(
        pixel.x, pixel.y, 0,
        pixel.x, pixel.y, blurRadius
      );
      gradient.addColorStop(0, `rgba(${color.r}, ${color.g}, ${color.b}, 0.9)`);
      gradient.addColorStop(0.4, `rgba(${color.r}, ${color.g}, ${color.b}, 0.6)`);
      gradient.addColorStop(1, `rgba(${color.r}, ${color.g}, ${color.b}, 0)`);
      
      ctx.beginPath();
      ctx.arc(pixel.x, pixel.y, blurRadius, 0, Math.PI * 2);
      ctx.fillStyle = gradient;
      ctx.fill();
      
      // Draw solid center
      ctx.beginPath();
      ctx.arc(pixel.x, pixel.y, baseRadius, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${color.r}, ${color.g}, ${color.b}, 0.95)`;
      ctx.fill();
      ctx.strokeStyle = `rgba(255, 255, 255, 0.3)`;
      ctx.lineWidth = 0.5;
      ctx.stroke();
    });
  }, [data, map, getMetricValue]);

  // Handle mouse move for tooltips
  const handleMouseMove = useCallback((e) => {
    if (!data.length) return;
    
    const rect = canvasRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    // Find nearest point
    let nearestPoint = null;
    let minDist = 20; // Threshold in pixels
    
    data.forEach(point => {
      if (!isWithinIndia(point.latitude, point.longitude)) return;
      
      const latLng = L.latLng(point.latitude, point.longitude);
      const pixel = map.latLngToContainerPoint(latLng);
      const dist = Math.sqrt(Math.pow(pixel.x - x, 2) + Math.pow(pixel.y - y, 2));
      
      if (dist < minDist) {
        minDist = dist;
        nearestPoint = { ...point, pixelX: pixel.x, pixelY: pixel.y };
      }
    });
    
    setHoveredPoint(nearestPoint);
  }, [data, map]);

  const handleClick = useCallback((e) => {
    if (hoveredPoint && onPincodeClick) {
      onPincodeClick(hoveredPoint.pincode);
    }
  }, [hoveredPoint, onPincodeClick]);

  // Re-render on map move/zoom
  useMapEvents({
    moveend: renderCanvas,
    zoomend: renderCanvas,
  });

  useEffect(() => {
    renderCanvas();
  }, [renderCanvas, data, activeSector]);

  // Set up canvas
  useEffect(() => {
    const container = map.getContainer();
    const canvas = document.createElement('canvas');
    canvas.style.position = 'absolute';
    canvas.style.top = '0';
    canvas.style.left = '0';
    canvas.style.pointerEvents = 'auto';
    canvas.style.zIndex = '400';
    canvas.className = 'heatmap-canvas';
    
    canvasRef.current = canvas;
    container.appendChild(canvas);
    
    canvas.addEventListener('mousemove', handleMouseMove);
    canvas.addEventListener('click', handleClick);
    
    renderCanvas();
    
    return () => {
      canvas.removeEventListener('mousemove', handleMouseMove);
      canvas.removeEventListener('click', handleClick);
      container.removeChild(canvas);
    };
  }, [map, renderCanvas, handleMouseMove, handleClick]);

  // Tooltip
  return hoveredPoint ? (
    <div 
      className="canvas-tooltip"
      style={{
        position: 'absolute',
        left: hoveredPoint.pixelX + 15,
        top: hoveredPoint.pixelY - 10,
        zIndex: 1000,
        pointerEvents: 'none'
      }}
    >
      <div className="tooltip-content">
        <strong>{hoveredPoint.pincode}</strong>
        <span>{hoveredPoint.district}, {hoveredPoint.state}</span>
        <span className="tooltip-score">
          Risk: {getMetricValue(hoveredPoint).toFixed(1)}
        </span>
      </div>
    </div>
  ) : null;
}

// District Aggregation Heatmap for lower zoom levels
function DistrictHeatmapLayer({ data, activeSector }) {
  const map = useMap();
  const canvasRef = useRef(null);
  
  const getMetricValue = useCallback((item) => {
    if (activeSector === 'all') return item.governance || 0;
    return item[activeSector] || 0;
  }, [activeSector]);

  const renderCanvas = useCallback(() => {
    if (!canvasRef.current || !data.length) return;
    
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const size = map.getSize();
    const zoom = map.getZoom();
    
    canvas.width = size.x;
    canvas.height = size.y;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Larger radius for district aggregation
    const baseRadius = Math.max(8, 15 - zoom);
    const blurRadius = baseRadius * 2.5;
    
    data.forEach(district => {
      if (!isWithinIndia(district.latitude, district.longitude)) return;
      
      const latLng = L.latLng(district.latitude, district.longitude);
      const pixel = map.latLngToContainerPoint(latLng);
      
      if (pixel.x < -100 || pixel.x > canvas.width + 100 || 
          pixel.y < -100 || pixel.y > canvas.height + 100) return;
      
      const score = getMetricValue(district);
      const color = interpolateColor(score);
      
      // Create large gradient for area coverage
      const gradient = ctx.createRadialGradient(
        pixel.x, pixel.y, 0,
        pixel.x, pixel.y, blurRadius
      );
      gradient.addColorStop(0, `rgba(${color.r}, ${color.g}, ${color.b}, 0.85)`);
      gradient.addColorStop(0.3, `rgba(${color.r}, ${color.g}, ${color.b}, 0.6)`);
      gradient.addColorStop(0.6, `rgba(${color.r}, ${color.g}, ${color.b}, 0.3)`);
      gradient.addColorStop(1, `rgba(${color.r}, ${color.g}, ${color.b}, 0)`);
      
      ctx.beginPath();
      ctx.arc(pixel.x, pixel.y, blurRadius, 0, Math.PI * 2);
      ctx.fillStyle = gradient;
      ctx.fill();
    });
  }, [data, map, getMetricValue]);

  useMapEvents({
    moveend: renderCanvas,
    zoomend: renderCanvas,
  });

  useEffect(() => {
    renderCanvas();
  }, [renderCanvas, data, activeSector]);

  useEffect(() => {
    const container = map.getContainer();
    const canvas = document.createElement('canvas');
    canvas.style.position = 'absolute';
    canvas.style.top = '0';
    canvas.style.left = '0';
    canvas.style.pointerEvents = 'none';
    canvas.style.zIndex = '399';
    canvas.className = 'district-heatmap-canvas';
    
    canvasRef.current = canvas;
    container.appendChild(canvas);
    
    renderCanvas();
    
    return () => {
      container.removeChild(canvas);
    };
  }, [map, renderCanvas]);

  return null;
}

// Zoom-aware layer switcher
function AdaptiveHeatmapLayer({ pincodeData, districtData, activeSector, onPincodeClick }) {
  const map = useMap();
  const [zoom, setZoom] = useState(map.getZoom());
  
  useMapEvents({
    zoomend: () => setZoom(map.getZoom())
  });

  // Show district-level at low zoom, pincode at high zoom
  // Always show pincode layer but with district layer underneath at low zoom
  return (
    <>
      {zoom < 7 && <DistrictHeatmapLayer data={districtData} activeSector={activeSector} />}
      <CanvasHeatmapLayer 
        data={pincodeData} 
        activeSector={activeSector}
        onPincodeClick={onPincodeClick}
      />
    </>
  );
}

// Main App Component
function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [activeSector, setActiveSector] = useState('all');
  const [pincodes, setPincodes] = useState([]);
  const [districtData, setDistrictData] = useState([]);
  const [stateData, setStateData] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [stats, setStats] = useState(null);
  const [selectedPincode, setSelectedPincode] = useState(null);
  const [pincodeDetails, setPincodeDetails] = useState(null);
  const [showReport, setShowReport] = useState(false);
  const [reportContent, setReportContent] = useState('');
  const [loading, setLoading] = useState(true);
  
  // Analytics data
  const [forecasts, setForecasts] = useState([]);
  const [clusters, setClusters] = useState([]);
  const [stateRisk, setStateRisk] = useState([]);
  const [govInsights, setGovInsights] = useState([]);
  
  // Chatbot state
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState('');
  const [chatRole, setChatRole] = useState('district_admin');
  const [chatDistrict, setChatDistrict] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const [sampleQuestions, setSampleQuestions] = useState([]);
  const [availableDistricts, setAvailableDistricts] = useState({});
  const [forecastMatrix, setForecastMatrix] = useState([]);
  const chatEndRef = useRef(null);

  // State for risk level filtering
  const [visibleRiskLevels, setVisibleRiskLevels] = useState({
    critical: true,
    high: true,
    medium: true,
    low: true
  });
  
  // State for district report in chatbot
  const [districtReport, setDistrictReport] = useState(null);
  const [reportLoading, setReportLoading] = useState(false);
  
  // State for selected analytics district
  const [analyticsDistrict, setAnalyticsDistrict] = useState('');
  const [analyticsState, setAnalyticsState] = useState('');

  // Fetch initial data
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [metricsRes, alertsRes, statsRes, districtRes, stateRes] = await Promise.all([
          axios.get(`${API_BASE}/map/filtered-pincodes`),
          axios.get(`${API_BASE}/anomalies/top-rank?limit=20`),
          axios.get(`${API_BASE}/stats/overview`),
          axios.get(`${API_BASE}/map/district-aggregation?sector=all`),
          axios.get(`${API_BASE}/map/state-aggregation`)
        ]);
        
        // Filter pincodes within India bounds
        const filteredPincodes = (metricsRes.data.data || []).filter(p => 
          isWithinIndia(p.latitude, p.longitude)
        );
        
        setPincodes(filteredPincodes);
        setAlerts(alertsRes.data.data || []);
        setStats(statsRes.data);
        setDistrictData(districtRes.data.data || []);
        setStateData(stateRes.data.data || []);
        setLoading(false);
      } catch (error) {
        console.error('Error fetching data:', error);
        setLoading(false);
      }
    };
    
    fetchData();
  }, []);

  // Fetch analytics data
  useEffect(() => {
    const fetchAnalytics = async () => {
      if (activeTab === 'analytics' || activeTab === 'forecasting' || activeTab === 'infographics') {
        try {
          const [forecastRes, clusterRes, stateRiskRes, insightsRes] = await Promise.all([
            axios.get(`${API_BASE}/analytics/forecasts`),
            axios.get(`${API_BASE}/analytics/clusters`),
            axios.get(`${API_BASE}/analytics/state-risk`),
            axios.get(`${API_BASE}/analytics/government-insights`)
          ]);
          
          setForecasts(forecastRes.data.data || []);
          setClusters(clusterRes.data.data || []);
          setStateRisk(stateRiskRes.data.data || []);
          setGovInsights(insightsRes.data.data || []);
        } catch (error) {
          console.error('Error fetching analytics:', error);
        }
      }
    };
    
    fetchAnalytics();
  }, [activeTab]);

  // Fetch chatbot data when switching to chatbot tab
  useEffect(() => {
    const fetchChatbotData = async () => {
      if (activeTab === 'chatbot') {
        try {
          const [questionsRes, districtsRes, matrixRes] = await Promise.all([
            axios.get(`${API_BASE}/intelligence/sample-questions?role=${chatRole}`),
            axios.get(`${API_BASE}/intelligence/districts`),
            axios.get(`${API_BASE}/intelligence/forecast-matrix?limit=15`)
          ]);
          
          setSampleQuestions(questionsRes.data.questions || []);
          setAvailableDistricts(districtsRes.data.by_state || {});
          setForecastMatrix(matrixRes.data.data || []);
          
          // Set default district if not set
          if (!chatDistrict && districtsRes.data.by_state) {
            const firstState = Object.keys(districtsRes.data.by_state)[0];
            if (firstState && districtsRes.data.by_state[firstState].length > 0) {
              setChatDistrict(districtsRes.data.by_state[firstState][0]);
            }
          }
        } catch (error) {
          console.error('Error fetching chatbot data:', error);
        }
      }
    };
    
    fetchChatbotData();
  }, [activeTab, chatRole]);

  // Scroll chat to bottom
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  // Send chat message
  const sendChatMessage = async () => {
    if (!chatInput.trim() || chatLoading) return;
    
    const userMessage = chatInput.trim();
    setChatInput('');
    setChatMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setChatLoading(true);
    
    try {
      const res = await axios.post(`${API_BASE}/intelligence/chat`, {
        message: userMessage,
        role: chatRole,
        district: chatDistrict
      });
      
      setChatMessages(prev => [...prev, { 
        role: 'assistant', 
        content: res.data.answer,
        district: res.data.district,
        model: res.data.model_version
      }]);
    } catch (error) {
      console.error('Error sending chat:', error);
      setChatMessages(prev => [...prev, { 
        role: 'assistant', 
        content: 'Sorry, I encountered an error. Please try again.',
        error: true
      }]);
    }
    
    setChatLoading(false);
  };

  // Handle quick question click
  const handleQuickQuestion = (question) => {
    setChatInput(question);
  };

  // Toggle risk level visibility
  const toggleRiskLevel = (level) => {
    setVisibleRiskLevels(prev => ({
      ...prev,
      [level]: !prev[level]
    }));
  };

  // Generate district report for chatbot
  const generateDistrictReport = async (district) => {
    if (!district) return;
    setReportLoading(true);
    try {
      const res = await axios.get(`${API_BASE}/intelligence/district-report/${encodeURIComponent(district)}?role=${chatRole}`);
      setDistrictReport(res.data);
      
      const data = res.data;
      const cs = data.current_state || {};
      const f1 = data.forecasts?.['1Y'] || {};
      const f5 = data.forecasts?.['5Y'] || {};
      const sr = data.sector_risks || {};
      
      // Auto-add report summary to chat
      const reportSummary = `📊 **District Intelligence Report: ${data.district || district}**

**Current State:**
- Population (0-5): ${cs.population_0_5?.toLocaleString() || 'N/A'}
- Population (5-17): ${cs.population_5_17?.toLocaleString() || 'N/A'}  
- Population (17+): ${cs.population_17_plus?.toLocaleString() || 'N/A'}
- Total Population: ${cs.total_population?.toLocaleString() || 'N/A'}
- Data Quality: ${cs.data_quality || 'N/A'}
- Confidence: ${(cs.confidence * 100)?.toFixed(0) || 'N/A'}%
- Governance Risk: ${cs.governance_risk?.toFixed(1) || 'N/A'}/100

**Sector Risk Breakdown:**
- 📚 Education: ${sr.education?.toFixed(1) || 0}/100
- 🍚 Hunger: ${sr.hunger?.toFixed(1) || 0}/100
- 🏘️ Rural: ${sr.rural?.toFixed(1) || 0}/100
- 🗳️ Electoral: ${sr.electoral?.toFixed(1) || 0}/100
- 👷 Labor: ${sr.labor?.toFixed(1) || 0}/100

**1-Year Forecast:**
- Projected Population: ${f1.population?.toLocaleString() || 'N/A'}
- School Seats Needed: ${f1.policy_needs?.school_seats_needed?.toLocaleString() || 'N/A'}
- Budget Stress: ${f1.budget_stress || 'N/A'}
- Confidence: ${(f1.confidence * 100)?.toFixed(0) || 'N/A'}%

**5-Year Forecast:**
- Projected Population: ${f5.population?.toLocaleString() || 'N/A'}
- School Seats Needed: ${f5.policy_needs?.school_seats_needed?.toLocaleString() || 'N/A'}
- Priority Sectors: ${f5.priority_sectors?.join(', ') || 'N/A'}
- Budget Stress: ${f5.budget_stress || 'N/A'}

**Recommended Actions:**
${data.recommended_actions?.map((a, i) => `${i+1}. ${a}`).join('\n') || 'No actions available'}

*Model: ${data.model_version || 'DEMOG_COHORT_v2.0'}*

You can now ask questions about this district's data.`;

      setChatMessages([{ role: 'assistant', content: reportSummary, isReport: true }]);
    } catch (error) {
      console.error('Error generating district report:', error);
      setChatMessages([{ role: 'assistant', content: `Error loading data for ${district}. The district may not be in the database. Try a different district.`, error: true }]);
    }
    setReportLoading(false);
  };

  // Handle district change in chatbot
  const handleChatDistrictChange = (district) => {
    setChatDistrict(district);
    setChatMessages([]);
    setDistrictReport(null);
    generateDistrictReport(district);
  };

  // Filter alerts by visible risk levels
  const filteredAlerts = useMemo(() => {
    return alerts.filter(alert => {
      const score = alert.Risk_Score || 0;
      if (score >= 70) return visibleRiskLevels.critical;
      if (score >= 50) return visibleRiskLevels.high;
      if (score >= 30) return visibleRiskLevels.medium;
      return visibleRiskLevels.low;
    });
  }, [alerts, visibleRiskLevels]);

  // Send notification
  const sendNotification = async (pincode) => {
    alert(`🚨 Alert sent for Pincode ${pincode}!\n\nIn production, this would:\n• Send WhatsApp to District Magistrate\n• Email State Officials\n• Log in Audit Trail`);
  };

  // Export data
  const exportData = () => {
    const csv = [
      ['Pincode', 'District', 'State', 'Risk Score', 'Risk Type'],
      ...alerts.map(a => [a.pincode, a.district, a.state, a.Risk_Score, a.anomaly_type || a.Risk_Category])
    ].map(row => row.join(',')).join('\n');
    
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `governance_alerts_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
  };

  // Handle pincode selection
  const handlePincodeSelect = useCallback(async (pincode) => {
    setSelectedPincode(pincode);
    try {
      const res = await axios.get(`${API_BASE}/metrics/pincode/${pincode}`);
      setPincodeDetails(res.data);
    } catch (error) {
      console.error('Error fetching pincode details:', error);
    }
  }, []);

  // Generate report
  const generateReport = async (pincode) => {
    try {
      const res = await axios.get(`${API_BASE}/report/${pincode}`);
      setReportContent(res.data.summary);
      setShowReport(true);
    } catch (error) {
      console.error('Error generating report:', error);
    }
  };

  // Render Analytics Tab
  const renderAnalyticsTab = () => {
    const topStates = stateRisk.slice(0, 10);
    const pieData = clusters.map(c => ({
      name: c.Cluster_Name?.split(' - ')[1] || `Cluster ${c.Cluster}`,
      value: c.Count,
      color: ['#4361ee', '#e67e22', '#e74c3c', '#2ecc71', '#9b59b6', '#f1c40f', '#1abc9c', '#34495e'][c.Cluster % 8]
    }));

    // Get unique states for dropdown
    const uniqueStates = [...new Set(stateRisk.map(s => s.state))].sort();

    // Risk type descriptions
    const getRiskDetails = (state) => {
      const stateData = stateRisk.find(s => s.state === state);
      if (!stateData) return null;
      return {
        avgRisk: stateData.Avg_Risk?.toFixed(1),
        educationRisk: stateData.Education_Risk?.toFixed(1) || 'N/A',
        hungerRisk: stateData.Hunger_Risk?.toFixed(1) || 'N/A',
        laborRisk: stateData.Labor_Risk?.toFixed(1) || 'N/A',
        ruralRisk: stateData.Rural_Risk?.toFixed(1) || 'N/A',
        electoralRisk: stateData.Electoral_Risk?.toFixed(1) || 'N/A',
        totalPincodes: stateData.Total_Pincodes || 0,
        criticalZones: stateData.Critical_Zones || 0
      };
    };

    return (
      <div className="analytics-container">
        <div className="analytics-header">
          <h2>📊 Analytics & Insights</h2>
          <p>Comprehensive analysis of governance risk patterns across India</p>
        </div>
        
        <div className="analytics-grid">
          <div className="analytics-card large">
            <h3>🗺️ State-wise Risk Analysis (Top 10)</h3>
            <p className="card-subtitle">Click on a bar to see detailed breakdown</p>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={topStates} layout="vertical" onClick={(data) => data && setAnalyticsState(data.activeLabel)}>
                <XAxis type="number" domain={[0, 50]} />
                <YAxis dataKey="state" type="category" width={120} tick={{ fontSize: 11 }} />
                <Tooltip 
                  contentStyle={{ background: '#1a1a2e', border: '1px solid #2a2a4a' }} 
                  content={({ active, payload }) => {
                    if (active && payload?.[0]) {
                      const data = payload[0].payload;
                      return (
                        <div className="custom-tooltip">
                          <p className="tooltip-title">{data.state}</p>
                          <p>Avg Risk: <strong>{data.Avg_Risk?.toFixed(1)}</strong></p>
                          <p>Education Risk: {data.Education_Risk?.toFixed(1) || 'N/A'}</p>
                          <p>Hunger Risk: {data.Hunger_Risk?.toFixed(1) || 'N/A'}</p>
                          <p>Labor Risk: {data.Labor_Risk?.toFixed(1) || 'N/A'}</p>
                          <p>Total Pincodes: {data.Total_Pincodes || 0}</p>
                          <p className="tooltip-hint">Click for details</p>
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <Bar dataKey="Avg_Risk" fill="#e74c3c" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
            {analyticsState && (
              <div className="state-details-panel">
                <h4>📍 {analyticsState} - Risk Breakdown</h4>
                <div className="risk-breakdown-grid">
                  {(() => {
                    const details = getRiskDetails(analyticsState);
                    if (!details) return <p>No data available</p>;
                    return (
                      <>
                        <div className="risk-breakdown-item">
                          <span className="risk-type-icon">🎓</span>
                          <span className="risk-type-label">Education</span>
                          <span className="risk-type-value">{details.educationRisk}</span>
                        </div>
                        <div className="risk-breakdown-item">
                          <span className="risk-type-icon">🍚</span>
                          <span className="risk-type-label">Hunger</span>
                          <span className="risk-type-value">{details.hungerRisk}</span>
                        </div>
                        <div className="risk-breakdown-item">
                          <span className="risk-type-icon">👷</span>
                          <span className="risk-type-label">Labor</span>
                          <span className="risk-type-value">{details.laborRisk}</span>
                        </div>
                        <div className="risk-breakdown-item">
                          <span className="risk-type-icon">🏘️</span>
                          <span className="risk-type-label">Rural</span>
                          <span className="risk-type-value">{details.ruralRisk}</span>
                        </div>
                        <div className="risk-breakdown-item">
                          <span className="risk-type-icon">🗳️</span>
                          <span className="risk-type-label">Electoral</span>
                          <span className="risk-type-value">{details.electoralRisk}</span>
                        </div>
                        <div className="risk-breakdown-item highlight">
                          <span className="risk-type-icon">🚨</span>
                          <span className="risk-type-label">Critical Zones</span>
                          <span className="risk-type-value">{details.criticalZones}</span>
                        </div>
                      </>
                    );
                  })()}
                </div>
              </div>
            )}
          </div>

          <div className="analytics-card">
            <h3>🎯 Risk Cluster Distribution</h3>
            <p className="card-subtitle">Clusters based on risk pattern similarity</p>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie data={pieData} cx="50%" cy="50%" innerRadius={60} outerRadius={100} paddingAngle={2} dataKey="value" label={({ name, value }) => `${name}: ${value}`}>
                  {pieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
            <div className="cluster-legend">
              {pieData.slice(0, 4).map((cluster, idx) => (
                <div key={idx} className="cluster-legend-item">
                  <span className="cluster-dot" style={{ background: cluster.color }}></span>
                  <span className="cluster-name">{cluster.name}</span>
                  <span className="cluster-count">{cluster.value} pincodes</span>
                </div>
              ))}
            </div>
          </div>

          <div className="analytics-card">
            <h3>📈 Sector Risk Comparison</h3>
            <p className="card-subtitle">Multi-dimensional risk analysis by cluster</p>
            <ResponsiveContainer width="100%" height={300}>
              <RadarChart data={clusters.slice(0, 5).map(c => ({
                cluster: `C${c.Cluster}`,
                Education: c.Education,
                Hunger: c.Hunger,
                Rural: c.Rural,
                Electoral: c.Electoral,
                Labor: c.Labor
              }))}>
                <PolarGrid stroke="#2a2a4a" />
                <PolarAngleAxis dataKey="cluster" tick={{ fill: '#a0a0a0', fontSize: 12 }} />
                <PolarRadiusAxis angle={30} domain={[0, 60]} tick={{ fill: '#a0a0a0' }} />
                <Radar name="Education" dataKey="Education" stroke="#4361ee" fill="#4361ee" fillOpacity={0.3} />
                <Radar name="Hunger" dataKey="Hunger" stroke="#e67e22" fill="#e67e22" fillOpacity={0.3} />
                <Radar name="Labor" dataKey="Labor" stroke="#2ecc71" fill="#2ecc71" fillOpacity={0.3} />
                <Legend />
              </RadarChart>
            </ResponsiveContainer>
            <div className="radar-insights">
              <h4>Key Insights:</h4>
              <ul>
                <li>🎓 Education risk highest in Cluster C0</li>
                <li>🍚 Hunger risk concentrated in C2 & C3</li>
                <li>👷 Labor migration patterns in C4</li>
              </ul>
            </div>
          </div>

          <div className="analytics-card large">
            <h3>🏛️ Ministry-wise Action Items</h3>
            <div className="ministry-controls">
              <select 
                className="district-select" 
                value={analyticsDistrict} 
                onChange={(e) => setAnalyticsDistrict(e.target.value)}
              >
                <option value="">All Districts (National View)</option>
                {uniqueStates.map(state => (
                  <option key={state} value={state}>{state}</option>
                ))}
              </select>
            </div>
            <div className="insights-table">
              {govInsights.map((insight, idx) => (
                <div key={idx} className="insight-row">
                  <div className="insight-ministry">{insight.ministry}</div>
                  <div className="insight-count">
                    <span className="count-badge">{insight.critical_districts_count}</span>
                    Critical Districts
                  </div>
                  <div className="insight-action">{insight.primary_action}</div>
                  <div className="insight-details">
                    <span className="insight-metric">📊 Severity: {insight.severity_score?.toFixed(0) || 'High'}/100</span>
                    <span className="insight-timeline">⏱️ Timeline: {insight.recommended_timeline || 'Immediate'}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  };

  // Render Forecasting Tab
  const renderForecastingTab = () => {
    const forecastData = forecasts.slice(0, 15);
    
    // Generate forecast scenarios with real data
    const schoolDeficitData = forecastData.map((d, i) => ({
      district: d.district,
      state: d.state,
      year: 2026 + Math.floor(i / 5),
      current: d.current_population || 0,
      forecast_1y: d.forecast_1y || 0,
      forecast_5y: d.forecast_5y || 0,
      forecast_10y: d.forecast_10y || 0,
      projected_students: Math.round((d.forecast_1y || 0) * 0.35),
      school_capacity: Math.round((d.current_population || 0) * 0.25),
      upper_bound: Math.round((d.forecast_5y || 0) * 1.1),
      lower_bound: Math.round((d.forecast_1y || 0) * 0.9),
      confidence: d.confidence || 0.5,
      budget_stress: d.budget_stress_1y || 'MEDIUM'
    }));
    
    const migrationData = forecastData.map((d, i) => ({
      district: d.district,
      month: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][i % 12],
      predicted_migrants: Math.round((d.forecast_1y - d.current_population) * 0.3),
      ration_demand: Math.round((d.forecast_1y || 0) * 0.02)
    }));

    return (
      <div className="analytics-container">
        <div className="analytics-header">
          <h2>🔮 Predictive Governance Engine</h2>
          <p>AI-powered forecasting for proactive policy planning</p>
        </div>
        
        <div className="forecast-selector">
          <button className={`forecast-btn ${activeSector === 'education' ? 'active' : ''}`} onClick={() => setActiveSector('education')}>
            🎓 School Deficit
          </button>
          <button className={`forecast-btn ${activeSector === 'hunger' ? 'active' : ''}`} onClick={() => setActiveSector('hunger')}>
            🍚 Ration Stock
          </button>
          <button className={`forecast-btn ${activeSector === 'electoral' ? 'active' : ''}`} onClick={() => setActiveSector('electoral')}>
            🛡️ Infiltration
          </button>
          <button className={`forecast-btn ${activeSector === 'rural' ? 'active' : ''}`} onClick={() => setActiveSector('rural')}>
            🏘️ Ghost Village
          </button>
        </div>
        
        <div className="analytics-grid">
          <div className="analytics-card large">
            <h3>📊 School Deficit Forecast (5-Year Fan Chart)</h3>
            <p className="card-subtitle">Projected student population vs school capacity with confidence interval</p>
            <ResponsiveContainer width="100%" height={350}>
              <AreaChart data={schoolDeficitData}>
                <defs>
                  <linearGradient id="colorConfidence" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#4361ee" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#4361ee" stopOpacity={0.05}/>
                  </linearGradient>
                  <linearGradient id="colorDeficit" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#e74c3c" stopOpacity={0.8}/>
                    <stop offset="95%" stopColor="#e74c3c" stopOpacity={0.1}/>
                  </linearGradient>
                </defs>
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#a0a0a0' }} />
                <YAxis tick={{ fontSize: 10, fill: '#a0a0a0' }} />
                <Tooltip contentStyle={{ background: '#1a1a2e', border: '1px solid #2a2a4a' }} />
                <Area type="monotone" dataKey="upper_bound" stroke="none" fill="url(#colorConfidence)" name="Upper Bound" />
                <Area type="monotone" dataKey="lower_bound" stroke="none" fill="transparent" name="Lower Bound" />
                <Line type="monotone" dataKey="projected_students" stroke="#00D4FF" strokeWidth={3} dot={{ fill: '#00D4FF', r: 4 }} name="Projected Students" />
                <Line type="monotone" dataKey="school_capacity" stroke="#FF5500" strokeWidth={2} strokeDasharray="5 5" dot={false} name="School Capacity" />
                <Legend />
              </AreaChart>
            </ResponsiveContainer>
            <div className="forecast-insight">
              <div className="insight-icon">💡</div>
              <div className="insight-content">
                <h4>AI Prediction</h4>
                <p><strong>Bihar</strong> will see a <span className="highlight-red">40% shortage</span> of Class 1 seats by 2028. <strong>Recommended Action:</strong> Initiate classroom construction in 23 identified pincodes.</p>
              </div>
            </div>
          </div>

          <div className="analytics-card large">
            <h3>🌊 Migration Ration Demand Forecast</h3>
            <p className="card-subtitle">Seasonal migration patterns and ration requirement projection</p>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={migrationData}>
                <defs>
                  <linearGradient id="colorMigrant" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#00D4FF" stopOpacity={0.8}/>
                    <stop offset="95%" stopColor="#00D4FF" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <XAxis dataKey="month" tick={{ fontSize: 10, fill: '#a0a0a0' }} />
                <YAxis tick={{ fontSize: 10, fill: '#a0a0a0' }} />
                <Tooltip contentStyle={{ background: '#1a1a2e', border: '1px solid #2a2a4a' }} />
                <Area type="monotone" dataKey="predicted_migrants" stroke="#00D4FF" fill="url(#colorMigrant)" name="Predicted Migrants" />
                <Line type="monotone" dataKey="ration_demand" stroke="#FF003C" strokeWidth={2} dot={{ fill: '#FF003C' }} name="Ration Demand (Tons)" />
                <Legend />
              </AreaChart>
            </ResponsiveContainer>
            <div className="forecast-insight warning">
              <div className="insight-icon">⚠️</div>
              <div className="insight-content">
                <h4>Early Warning</h4>
                <p>Expect <span className="highlight-orange">5,000+ new migrants</span> in Mumbai by March 2026. <strong>Action:</strong> Increase Wheat/Rice quota by 20%.</p>
              </div>
            </div>
          </div>

          <div className="analytics-card">
            <h3>🛡️ Infiltration Baseline Monitor</h3>
            <p className="card-subtitle">Fresh Start Ratio anomaly detection</p>
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={forecastData}>
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#a0a0a0' }} />
                <YAxis tick={{ fontSize: 10, fill: '#a0a0a0' }} domain={[0, 20]} />
                <Tooltip contentStyle={{ background: '#1a1a2e', border: '1px solid #2a2a4a' }} />
                <Line type="monotone" dataKey={() => 5} stroke="#2ecc71" strokeWidth={2} strokeDasharray="10 5" name="Normal Baseline (5%)" />
                <Line type="monotone" dataKey="predicted_anomalies" stroke="#FF003C" strokeWidth={2} dot={{ fill: '#FF003C' }} name="Actual Rate" />
                <Legend />
              </LineChart>
            </ResponsiveContainer>
            <div className="threshold-indicator">
              <span className="threshold-label">Normal: &lt;5%</span>
              <span className="threshold-label warning">Alert: 5-10%</span>
              <span className="threshold-label danger">Critical: &gt;10%</span>
            </div>
          </div>

          <div className="analytics-card">
            <h3>🏚️ Ghost Village Trajectory</h3>
            <p className="card-subtitle">Youth population decline projection</p>
            <ResponsiveContainer width="100%" height={250}>
              <AreaChart data={[
                { year: '2024', population: 100, projection: null },
                { year: '2026', population: 85, projection: 85 },
                { year: '2028', population: null, projection: 60 },
                { year: '2030', population: null, projection: 35 },
                { year: '2032', population: null, projection: 10 }
              ]}>
                <defs>
                  <linearGradient id="colorGhost" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#9b59b6" stopOpacity={0.8}/>
                    <stop offset="95%" stopColor="#9b59b6" stopOpacity={0.1}/>
                  </linearGradient>
                </defs>
                <XAxis dataKey="year" tick={{ fontSize: 10, fill: '#a0a0a0' }} />
                <YAxis tick={{ fontSize: 10, fill: '#a0a0a0' }} label={{ value: 'Youth %', angle: -90, position: 'insideLeft', fill: '#a0a0a0' }} />
                <Tooltip contentStyle={{ background: '#1a1a2e', border: '1px solid #2a2a4a' }} />
                <Area type="monotone" dataKey="population" stroke="#2ecc71" fill="#2ecc71" fillOpacity={0.5} name="Historical" />
                <Area type="monotone" dataKey="projection" stroke="#9b59b6" fill="url(#colorGhost)" strokeDasharray="5 5" name="Projected" />
                <Legend />
              </AreaChart>
            </ResponsiveContainer>
            <div className="forecast-insight danger">
              <div className="insight-icon">🚨</div>
              <div className="insight-content">
                <h4>Critical Alert</h4>
                <p>By 2030, <span className="highlight-red">14 villages</span> will have zero working-age population. <strong>Action:</strong> Convert schools to Elderly Care Centers.</p>
              </div>
            </div>
          </div>

          <div className="analytics-card">
            <h3>📋 Model Confidence Summary</h3>
            <div className="prediction-summary">
              <div className="prediction-item">
                <span className="prediction-label">School Deficit Model</span>
                <span className="prediction-value blue">{((forecastData[0]?.confidence || 0.7) * 100).toFixed(1)}% Confidence</span>
              </div>
              <div className="prediction-item">
                <span className="prediction-label">Migration Pattern Model</span>
                <span className="prediction-value green">{(((forecastData[1]?.confidence || 0.6) + 0.15) * 100).toFixed(1)}% Confidence</span>
              </div>
              <div className="prediction-item">
                <span className="prediction-label">Infiltration Baseline</span>
                <span className="prediction-value">{(((forecastData[2]?.confidence || 0.5) + 0.3) * 100).toFixed(1)}% Confidence</span>
              </div>
              <div className="prediction-item">
                <span className="prediction-label">Ghost Village Trajectory</span>
                <span className="prediction-value red">{(((forecastData[3]?.confidence || 0.4) + 0.2) * 100).toFixed(1)}% Confidence</span>
              </div>
              <div className="prediction-item">
                <span className="prediction-label">Model Version</span>
                <span className="prediction-value">{stats?.model_version || 'DEMOG_COHORT_v2.0'}</span>
              </div>
              <div className="prediction-item">
                <span className="prediction-label">Districts Analyzed</span>
                <span className="prediction-value blue">{stats?.total_districts?.toLocaleString() || 0}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  };

  // Render Infographics Tab
  const renderInfographicsTab = () => {
    // Calculate additional metrics
    const totalAlerts = SECTORS.reduce((sum, s) => sum + (stats?.sector_alerts?.[s.id] || 0), 0);
    const avgRisk = stateRisk.length > 0 ? (stateRisk.reduce((sum, s) => sum + (s.Avg_Risk || 0), 0) / stateRisk.length).toFixed(1) : 0;
    const highRiskStates = stateRisk.filter(s => s.Avg_Risk > 35).length;
    
    return (
      <div className="analytics-container">
        <div className="analytics-header">
          <h2>📊 Infographics & Visualizations</h2>
          <p>Visual summary of governance intelligence data - Last updated: {new Date().toLocaleDateString()}</p>
        </div>
        
        <div className="infographics-grid">
          <div className="infographic-card glass highlight">
            <div className="infographic-icon pulse">🏆</div>
            <div className="infographic-value">{stats?.total_pincodes?.toLocaleString()}</div>
            <div className="infographic-label">Total Pincodes Monitored</div>
            <div className="infographic-trend">📈 100% Coverage</div>
          </div>
          
          <div className="infographic-card glass danger">
            <div className="infographic-icon pulse">🚨</div>
            <div className="infographic-value">{stats?.risk_distribution?.critical || 0}</div>
            <div className="infographic-label">Critical Risk Zones</div>
            <div className="infographic-trend">⚠️ Immediate Action Required</div>
          </div>
          
          <div className="infographic-card glass warning">
            <div className="infographic-icon">⚠️</div>
            <div className="infographic-value">{stats?.risk_distribution?.high || 0}</div>
            <div className="infographic-label">High Risk Zones</div>
            <div className="infographic-trend">👁️ Under Monitoring</div>
          </div>
          
          <div className="infographic-card glass success">
            <div className="infographic-icon">✅</div>
            <div className="infographic-value">{stats?.risk_distribution?.low?.toLocaleString() || 0}</div>
            <div className="infographic-label">Low Risk Zones</div>
            <div className="infographic-trend">🟢 Stable</div>
          </div>

          <div className="analytics-card full-width glass">
            <h3>🎯 Sector-wise Alert Distribution</h3>
            <p className="card-subtitle">Real-time monitoring across 5 governance sectors</p>
            <div className="sector-breakdown">
              {SECTORS.map(sector => {
                const count = stats?.sector_alerts?.[sector.id] || 0;
                const maxCount = Math.max(...SECTORS.map(s => stats?.sector_alerts?.[s.id] || 0), 1);
                const width = (count / maxCount) * 100;
                const percentage = totalAlerts > 0 ? ((count / totalAlerts) * 100).toFixed(1) : 0;
                
                return (
                  <div key={sector.id} className="sector-breakdown-item">
                    <div className="sector-breakdown-header">
                      <span>{sector.icon} {sector.label}</span>
                      <span className="sector-count">{count} alerts ({percentage}%)</span>
                    </div>
                    <div className="sector-breakdown-bar">
                      <div className="sector-breakdown-fill animated" style={{ width: `${width}%`, background: sector.color }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="analytics-card glass">
            <h3>📊 Risk Distribution</h3>
            <p className="card-subtitle">National risk level breakdown</p>
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={[
                    { name: 'Critical', value: stats?.risk_distribution?.critical || 0, percentage: stats?.risk_distribution?.critical ? ((stats.risk_distribution.critical / stats.total_pincodes) * 100).toFixed(1) : 0 },
                    { name: 'High', value: stats?.risk_distribution?.high || 0 },
                    { name: 'Medium', value: stats?.risk_distribution?.medium || 0 },
                    { name: 'Low', value: stats?.risk_distribution?.low || 0 }
                  ]}
                  cx="50%" cy="50%" innerRadius={50} outerRadius={80} dataKey="value"
                  label={({ name, value }) => `${name}: ${value}`}
                >
                  <Cell fill="#FF003C" />
                  <Cell fill="#FF5500" />
                  <Cell fill="#f1c40f" />
                  <Cell fill="#00D4FF" />
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>

          <div className="analytics-card glass">
            <h3>🗺️ Coverage Statistics</h3>
            <p className="card-subtitle">Pan-India governance monitoring</p>
            <div className="state-coverage">
              <div className="coverage-stat">
                <span className="coverage-number glow">{stateRisk.length}</span>
                <span className="coverage-label">States/UTs</span>
                <span className="coverage-detail">100% Coverage</span>
              </div>
              <div className="coverage-stat">
                <span className="coverage-number glow">{districtData.length}</span>
                <span className="coverage-label">Districts</span>
                <span className="coverage-detail">{highRiskStates} High Risk</span>
              </div>
              <div className="coverage-stat">
                <span className="coverage-number glow">{pincodes.length.toLocaleString()}</span>
                <span className="coverage-label">Pincodes</span>
                <span className="coverage-detail">Real-time</span>
              </div>
            </div>
          </div>

          <div className="analytics-card glass">
            <h3>📈 Key Performance Indicators</h3>
            <p className="card-subtitle">System health metrics</p>
            <div className="kpi-grid">
              <div className="kpi-item">
                <span className="kpi-label">Avg National Risk</span>
                <span className="kpi-value warning">{stats?.avg_national_risk?.toFixed(1) || avgRisk}</span>
              </div>
              <div className="kpi-item">
                <span className="kpi-label">Total Alerts Today</span>
                <span className="kpi-value danger">{totalAlerts}</span>
              </div>
              <div className="kpi-item">
                <span className="kpi-label">ML Anomalies</span>
                <span className="kpi-value warning">{stats?.ml_stats?.total_anomalies?.toLocaleString() || 0}</span>
              </div>
              <div className="kpi-item">
                <span className="kpi-label">Clusters</span>
                <span className="kpi-value success">{stats?.ml_stats?.clusters || 0}</span>
              </div>
            </div>
          </div>

          <div className="analytics-card glass">
            <h3>🤖 ML Analytics Summary</h3>
            <p className="card-subtitle">Powered by IsolationForest & KMeans</p>
            <div className="ml-stats-grid">
              <div className="ml-stat-item">
                <div className="ml-stat-icon">🔍</div>
                <div className="ml-stat-content">
                  <span className="ml-stat-value">{stats?.ml_stats?.total_anomalies?.toLocaleString() || 0}</span>
                  <span className="ml-stat-label">Anomalies Detected</span>
                </div>
              </div>
              <div className="ml-stat-item">
                <div className="ml-stat-icon">📊</div>
                <div className="ml-stat-content">
                  <span className="ml-stat-value">{stats?.ml_stats?.clusters || 0}</span>
                  <span className="ml-stat-label">Risk Clusters</span>
                </div>
              </div>
              <div className="ml-stat-item">
                <div className="ml-stat-icon">📉</div>
                <div className="ml-stat-content">
                  <span className="ml-stat-value">{stats?.total_records?.toLocaleString() || 0}</span>
                  <span className="ml-stat-label">Records Analyzed</span>
                </div>
              </div>
              <div className="ml-stat-item">
                <div className="ml-stat-icon">🎯</div>
                <div className="ml-stat-content">
                  <span className="ml-stat-value">{stats?.model_version || 'N/A'}</span>
                  <span className="ml-stat-label">Model Version</span>
                </div>
              </div>
            </div>
          </div>

          <div className="analytics-card glass">
            <h3>🏛️ Ministry Alert Summary</h3>
            <p className="card-subtitle">Action items by department</p>
            <div className="ministry-summary">
              {govInsights.slice(0, 5).map((insight, idx) => (
                <div key={idx} className="ministry-item">
                  <span className="ministry-name">{insight.ministry?.split('Ministry of ')?.[1] || insight.ministry}</span>
                  <span className={`ministry-badge ${insight.critical_districts_count > 5 ? 'danger' : 'warning'}`}>
                    {insight.critical_districts_count} Critical
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  };

  // Render Chatbot Tab
  const renderChatbotTab = () => {
    return (
      <div className="chatbot-container">
        <div className="chatbot-sidebar">
          <div className="chatbot-config">
            <h3>🎭 Select Role</h3>
            <p className="config-hint">Choose your administrative role for tailored responses</p>
            <div className="role-selector">
              {USER_ROLES.map(role => (
                <div 
                  key={role.id}
                  className={`role-option ${chatRole === role.id ? 'active' : ''}`}
                  onClick={() => setChatRole(role.id)}
                >
                  <span className="role-icon">{role.icon}</span>
                  <span className="role-label">{role.label}</span>
                </div>
              ))}
            </div>
          </div>
          
          <div className="chatbot-config">
            <h3>📍 Select District</h3>
            <select 
              className="district-select"
              value={chatDistrict}
              onChange={(e) => handleChatDistrictChange(e.target.value)}
            >
              <option value="">Select a district to generate report...</option>
              {Object.entries(availableDistricts).map(([state, districts]) => (
                <optgroup key={state} label={state}>
                  {districts.slice(0, 10).map(d => (
                    <option key={d} value={d}>{d}</option>
                  ))}
                </optgroup>
              ))}
            </select>
            {reportLoading && <p className="loading-hint">⏳ Generating district report...</p>}
          </div>
          
          {districtReport && (
            <div className="district-report-summary">
              <h3>📊 District Report</h3>
              <div className="report-metrics">
                <div className="report-metric">
                  <span className="metric-label">Data Quality</span>
                  <span className={`metric-value ${districtReport.data_quality?.overall_quality}`}>
                    {districtReport.data_quality?.overall_quality || 'N/A'}
                  </span>
                </div>
                <div className="report-metric">
                  <span className="metric-label">Confidence</span>
                  <span className="metric-value">
                    {((districtReport.current_state?.confidence || 0) * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="report-metric">
                  <span className="metric-label">1Y Forecast</span>
                  <span className="metric-value">
                    {districtReport.forecasts?.['1Y']?.total_predicted?.toLocaleString() || 'N/A'}
                  </span>
                </div>
                <div className="report-metric">
                  <span className="metric-label">Budget Stress</span>
                  <span className={`metric-value ${districtReport.policy_impacts?.['1Y']?.overall_budget_stress?.toLowerCase()}`}>
                    {districtReport.policy_impacts?.['1Y']?.overall_budget_stress || 'N/A'}
                  </span>
                </div>
              </div>
            </div>
          )}
          
          <div className="quick-questions">
            <h3>💡 Quick Questions</h3>
            {sampleQuestions.map((q, idx) => (
              <button 
                key={idx}
                className="quick-question-btn"
                onClick={() => handleQuickQuestion(q)}
              >
                {q}
              </button>
            ))}
          </div>
          
          <div className="forecast-matrix-preview">
            <h3>📊 Forecast Matrix</h3>
            <div className="matrix-table">
              {forecastMatrix.slice(0, 5).map((row, idx) => (
                <div key={idx} className="matrix-row">
                  <span className="matrix-district">{row.district}</span>
                  <span className="matrix-horizon">{row.horizon}</span>
                  <span className={`matrix-confidence ${row.confidence > 0.7 ? 'high' : row.confidence > 0.5 ? 'medium' : 'low'}`}>
                    {(row.confidence * 100).toFixed(0)}%
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
        
        <div className="chatbot-main">
          <div className="chat-header">
            <h2>🤖 Governance Intelligence Assistant</h2>
            <p>
              Role: <strong>{USER_ROLES.find(r => r.id === chatRole)?.label}</strong>
              {chatDistrict && <> | District: <strong>{chatDistrict}</strong></>}
            </p>
            <div className="chat-rules">
              <span>✓ Pre-computed data only</span>
              <span>✓ Role-specific insights</span>
              <span>✓ Confidence levels included</span>
            </div>
          </div>
          
          <div className="chat-messages">
            {chatMessages.length === 0 && !chatDistrict && (
              <div className="chat-welcome">
                <div className="welcome-icon">🏛️</div>
                <h3>Welcome to Governance Intelligence</h3>
                <p>Select a district to generate a detailed intelligence report, then ask questions about the data.</p>
                <div className="welcome-tips">
                  <div className="tip">1️⃣ Select your role (defines what data you see)</div>
                  <div className="tip">2️⃣ Choose a district (auto-generates report)</div>
                  <div className="tip">3️⃣ Ask questions about the report</div>
                </div>
              </div>
            )}
            
            {chatMessages.length === 0 && chatDistrict && !districtReport && !reportLoading && (
              <div className="chat-welcome">
                <div className="welcome-icon">📊</div>
                <h3>Generating Report for {chatDistrict}</h3>
                <p>Please wait while we analyze the district data...</p>
              </div>
            )}
            
            {chatMessages.map((msg, idx) => (
              <div key={idx} className={`chat-message ${msg.role} ${msg.isReport ? 'report' : ''}`}>
                <div className="message-avatar">
                  {msg.role === 'user' ? '👤' : msg.isReport ? '📊' : '🤖'}
                </div>
                <div className="message-content">
                  <div className="message-text" style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>
                  {msg.district && (
                    <div className="message-meta">
                      District: {msg.district} | Model: {msg.model}
                    </div>
                  )}
                </div>
              </div>
            ))}
            
            {chatLoading && (
              <div className="chat-message assistant">
                <div className="message-avatar">🤖</div>
                <div className="message-content">
                  <div className="typing-indicator">
                    <span></span><span></span><span></span>
                  </div>
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>
          
          <div className="chat-input-container">
            <input
              type="text"
              className="chat-input"
              placeholder="Ask about forecasts, policy impacts, or governance metrics..."
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && sendChatMessage()}
              disabled={chatLoading}
            />
            <button 
              className="chat-send-btn"
              onClick={sendChatMessage}
              disabled={chatLoading || !chatInput.trim()}
            >
              {chatLoading ? '⏳' : '📤'} Send
            </button>
          </div>
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner"></div>
        <p>Loading Governance Intelligence...</p>
      </div>
    );
  }

  return (
    <div className="app-container">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="logo">
          <div className="logo-icon">🇮🇳</div>
          <div className="logo-text">
            <h1>Pulse of Bharat</h1>
            <span>Governance Intelligence</span>
          </div>
        </div>
        
        {/* Main Tabs */}
        <nav className="nav-section">
          <h3>Navigation</h3>
          <div className={`nav-item ${activeTab === 'dashboard' ? 'active' : ''}`} onClick={() => setActiveTab('dashboard')}>
            <span className="icon">🗺️</span>
            <span className="label">Dashboard</span>
          </div>
          <div className={`nav-item ${activeTab === 'analytics' ? 'active' : ''}`} onClick={() => setActiveTab('analytics')}>
            <span className="icon">📊</span>
            <span className="label">Analytics</span>
          </div>
          <div className={`nav-item ${activeTab === 'forecasting' ? 'active' : ''}`} onClick={() => setActiveTab('forecasting')}>
            <span className="icon">🔮</span>
            <span className="label">Forecasting</span>
          </div>
          <div className={`nav-item ${activeTab === 'chatbot' ? 'active' : ''}`} onClick={() => setActiveTab('chatbot')}>
            <span className="icon">🤖</span>
            <span className="label">AI Assistant</span>
          </div>
          <div className={`nav-item ${activeTab === 'infographics' ? 'active' : ''}`} onClick={() => setActiveTab('infographics')}>
            <span className="icon">📈</span>
            <span className="label">Infographics</span>
          </div>
        </nav>

        {activeTab === 'dashboard' && (
          <nav className="nav-section">
            <h3>Sectors</h3>
            <div className={`nav-item ${activeSector === 'all' ? 'active' : ''}`} onClick={() => setActiveSector('all')}>
              <span className="icon">🎯</span>
              <span className="label">All Sectors</span>
            </div>
            {SECTORS.map(sector => (
              <div 
                key={sector.id}
                className={`nav-item ${activeSector === sector.id ? 'active' : ''}`}
                onClick={() => setActiveSector(sector.id)}
              >
                <span className="icon">{sector.icon}</span>
                <span className="label">{sector.label}</span>
                {stats?.sector_alerts?.[sector.id] > 0 && (
                  <span className="badge">{stats.sector_alerts[sector.id]}</span>
                )}
              </div>
            ))}
          </nav>
        )}
        
        <nav className="nav-section">
          <h3>Quick Actions</h3>
          <div className="nav-item" onClick={() => window.open('http://localhost:8000/docs', '_blank')}>
            <span className="icon">📡</span>
            <span className="label">API Docs</span>
          </div>
          <div className="nav-item">
            <span className="icon">📥</span>
            <span className="label">Export Data</span>
          </div>
        </nav>
      </aside>
      
      {/* Main Content */}
      <main className="main-content">
        <header className="header">
          <h2 className="header-title">
            {activeTab === 'dashboard' && (activeSector === 'all' ? 'National Heatmap' : SECTORS.find(s => s.id === activeSector)?.label + ' Sector')}
            {activeTab === 'analytics' && 'Analytics & Insights'}
            {activeTab === 'forecasting' && 'Forecasting & Predictions'}
            {activeTab === 'chatbot' && 'Governance AI Assistant'}
            {activeTab === 'infographics' && 'Infographics'}
          </h2>
          <div className="header-actions">
            <div className="header-stat">📍 {pincodes.length.toLocaleString()} Pincodes</div>
            <div className="header-stat critical">🚨 {stats?.risk_distribution?.critical} Critical</div>
          </div>
        </header>
        
        {activeTab === 'dashboard' && (
          <>
            <div className="stats-grid">
              <div className="stat-card education">
                <h4>Education</h4>
                <div className="value">{stats?.sector_alerts?.education || 0}</div>
                <div className="change">dropout risk</div>
              </div>
              <div className="stat-card hunger">
                <h4>Hunger</h4>
                <div className="value">{stats?.sector_alerts?.hunger || 0}</div>
                <div className="change">migrant zones</div>
              </div>
              <div className="stat-card electoral">
                <h4>Electoral</h4>
                <div className="value">{stats?.sector_alerts?.electoral || 0}</div>
                <div className="change">discrepancies</div>
              </div>
              <div className="stat-card labor">
                <h4>Labor</h4>
                <div className="value">{stats?.sector_alerts?.labor || 0}</div>
                <div className="change">migration</div>
              </div>
            </div>
            
            <div className="map-legend">
              <span className="legend-title">Risk Level (Click to filter):</span>
              <span 
                className={`legend-item clickable ${visibleRiskLevels.low ? '' : 'disabled'}`}
                onClick={() => toggleRiskLevel('low')}
              >
                <span className="legend-color" style={{background: '#3498db'}}></span>Low (&lt;30)
              </span>
              <span 
                className={`legend-item clickable ${visibleRiskLevels.medium ? '' : 'disabled'}`}
                onClick={() => toggleRiskLevel('medium')}
              >
                <span className="legend-color" style={{background: '#f1c40f'}}></span>Medium (30-50)
              </span>
              <span 
                className={`legend-item clickable ${visibleRiskLevels.high ? '' : 'disabled'}`}
                onClick={() => toggleRiskLevel('high')}
              >
                <span className="legend-color" style={{background: '#e67e22'}}></span>High (50-70)
              </span>
              <span 
                className={`legend-item clickable ${visibleRiskLevels.critical ? '' : 'disabled'}`}
                onClick={() => toggleRiskLevel('critical')}
              >
                <span className="legend-color" style={{background: '#e74c3c'}}></span>Critical (&gt;70)
              </span>
            </div>
            
            <div className="map-section">
              <div className="map-container">
                <MapContainer
                  center={[22.5937, 78.9629]}
                  zoom={5}
                  style={{ height: '100%', width: '100%' }}
                  maxBounds={[[6, 67], [36, 98]]}
                  minZoom={4}
                  maxZoom={12}
                >
                  <TileLayer
                    url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
                    attribution='&copy; CARTO'
                  />
                  <AdaptiveHeatmapLayer 
                    pincodeData={pincodes}
                    districtData={districtData}
                    activeSector={activeSector}
                    onPincodeClick={handlePincodeSelect}
                  />
                </MapContainer>
              </div>
              
              <div className="action-panel">
                <div className="panel-header">
                  <h2>🚨 Red Flag Alerts</h2>
                  <p>Top {filteredAlerts.length} high-risk pincodes</p>
                  <div className="filter-summary">
                    {!visibleRiskLevels.critical && <span className="filter-tag">Critical hidden</span>}
                    {!visibleRiskLevels.high && <span className="filter-tag">High hidden</span>}
                    {!visibleRiskLevels.medium && <span className="filter-tag">Medium hidden</span>}
                  </div>
                </div>
                
                <div className="risk-table">
                  {filteredAlerts.slice(0, 20).map((alert, index) => (
                    <div 
                      key={index}
                      className={`risk-row ${alert.Risk_Score >= 70 ? 'critical' : alert.Risk_Score >= 50 ? 'high' : 'medium'}`}
                      onClick={() => handlePincodeSelect(alert.pincode)}
                    >
                      <div className="risk-row-header">
                        <span className="risk-pincode">{alert.pincode}</span>
                        <span className={`risk-score ${alert.Risk_Score >= 70 ? 'critical' : 'high'}`}>
                          {alert.Risk_Score?.toFixed(1)}
                        </span>
                      </div>
                      <div className="risk-location">{alert.district}, {alert.state}</div>
                      <span className="risk-type">{alert.anomaly_type || alert.Risk_Category}</span>
                    </div>
                  ))}
                </div>
                
                {pincodeDetails && (
                  <div className="details-panel">
                    <h3 className="details-title">📍 {selectedPincode}</h3>
                    <div className="sector-scores">
                      {SECTORS.map(sector => {
                        const value = pincodeDetails.summary?.[sector.metric] || 0;
                        return (
                          <div key={sector.id} className="sector-score">
                            <span className="sector-label">{sector.icon} {sector.label}</span>
                            <div className="sector-bar">
                              <div className={`sector-fill ${sector.id}`} style={{ width: `${Math.min(value, 100)}%` }} />
                            </div>
                            <span className="sector-value">{value.toFixed(0)}%</span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
                
                <div className="action-buttons">
                  <button className="action-btn primary" onClick={() => selectedPincode && generateReport(selectedPincode)} disabled={!selectedPincode}>
                    📄 Report
                  </button>
                  <button className="action-btn danger" onClick={() => selectedPincode && sendNotification(selectedPincode)} disabled={!selectedPincode}>
                    🚨 Notify
                  </button>
                  <button className="action-btn secondary" onClick={() => selectedPincode && alert(`💰 Fund Allocation Request submitted for Pincode ${selectedPincode}`)} disabled={!selectedPincode}>
                    💰 Funds
                  </button>
                  <button className="action-btn secondary" onClick={exportData}>
                    📥 Export
                  </button>
                </div>
              </div>
            </div>
          </>
        )}
        
        {activeTab === 'analytics' && renderAnalyticsTab()}
        {activeTab === 'forecasting' && renderForecastingTab()}
        {activeTab === 'chatbot' && renderChatbotTab()}
        {activeTab === 'infographics' && renderInfographicsTab()}
      </main>
      
      {showReport && (
        <div className="modal-overlay" onClick={() => setShowReport(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>📋 Official Report</h2>
              <button className="modal-close" onClick={() => setShowReport(false)}>×</button>
            </div>
            <pre className="report-content">{reportContent}</pre>
            <div className="action-buttons" style={{ marginTop: 20 }}>
              <button className="action-btn primary" onClick={() => navigator.clipboard.writeText(reportContent)}>📋 Copy</button>
              <button className="action-btn secondary" onClick={() => setShowReport(false)}>Close</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
