# Pulse of Bharat - Frontend Dashboard

## Governance Intelligence UI

Interactive React-based dashboard for visualizing national security and welfare metrics across India. Features real-time map visualization, sector-based filtering, and automated report generation.

---

## 🎨 UI Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         FRONTEND DASHBOARD                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│  │   SIDEBAR    │    │   MAP VIEW   │    │ ACTION PANEL │              │
│  │   (Sectors)  │    │  (Leaflet)   │    │  (Alerts)    │              │
│  └──────────────┘    └──────────────┘    └──────────────┘              │
│         │                    │                    │                     │
│         ▼                    ▼                    ▼                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│  │ • Navigation │    │ • Circle     │    │ • Red Flags  │              │
│  │ • Sector     │    │   Markers    │    │ • Details    │              │
│  │   Selection  │    │ • Popups     │    │ • Reports    │              │
│  │ • Stats      │    │ • Zoom/Pan   │    │ • Actions    │              │
│  └──────────────┘    └──────────────┘    └──────────────┘              │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## ✨ Features

### 🗺️ Interactive Map
- **Dark theme** CARTO basemap for professional visualization
- **Circle markers** sized by risk score with color coding:
  - 🔴 Critical (≥70): Red
  - 🟠 High (50-69): Orange
  - 🟡 Medium (30-49): Yellow
  - 🟢 Low (<30): Green
- **Click-to-zoom** functionality for pincode selection
- **Popups** with quick info on hover

### 📊 Sector Navigation
| Sector | Icon | Metric |
|--------|------|--------|
| Education | 📚 | School Dropout Risk Index |
| Ration/Hunger | 🍚 | Migrant Hunger Score |
| Rural Dev | 🏘️ | Village Hollow-Out Rate |
| Electoral | 🗳️ | Electoral Discrepancy Index |
| Labor | 👷 | Skill Gap Migration Flow |

### 📈 Statistics Dashboard
- Total pincodes monitored
- Critical alerts count
- Sector-wise alert breakdown
- State-wise aggregation

### 🚨 Red Flag Alerts Panel
- Top 20 high-risk pincodes
- Anomaly type classification
- Severity scoring
- One-click selection for details

### 📄 Report Generation
- Automated official governance reports
- Risk level assessment
- Recommended actions
- Sector breakdown analysis
- Copy-to-clipboard functionality

### 🎛️ Action Buttons
- Generate Report
- Notify District Magistrate
- Release Funds
- Export Data

---

## 🛠️ Technology Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| React | 18.2.0 | UI Framework |
| React-Leaflet | 4.2.1 | Map Integration |
| Leaflet | 1.9.4 | Map Library |
| Recharts | 2.10.0 | Charts & Graphs |
| Axios | 1.6.0 | HTTP Client |

---

## 🎨 Design System

### Color Palette (Dark Theme)
```css
--bg-primary: #0f0f1a       /* Main background */
--bg-secondary: #1a1a2e     /* Sidebar background */
--bg-card: #16213e          /* Card background */
--text-primary: #eaeaea     /* Primary text */
--text-secondary: #a0a0a0   /* Secondary text */
--accent-blue: #4361ee      /* Education sector */
--accent-green: #2ecc71     /* Labor/Low risk */
--accent-yellow: #f1c40f    /* Rural/Medium risk */
--accent-orange: #e67e22    /* Hunger/High risk */
--accent-red: #e74c3c       /* Electoral/Critical */
```

### Typography
- Font Family: 'Inter', system fonts
- Responsive sizing for all screen sizes

---

## 🚀 Quick Start

### Prerequisites
- Node.js 18+
- npm or yarn
- Backend API running at http://localhost:8000

### Installation

```bash
# 1. Navigate to frontend directory
cd frontend

# 2. Install dependencies
npm install

# 3. Start development server
npm start
```

### Available Scripts

```bash
npm start    # Start development server (http://localhost:3000)
npm build    # Build for production
npm test     # Run tests
npm eject    # Eject from Create React App
```

---

## 📁 Project Structure

```
frontend/
├── public/
│   ├── index.html          # HTML template
│   └── favicon.ico         # App icon
├── src/
│   ├── App.js              # Main application component
│   ├── index.js            # React entry point
│   └── index.css           # Global styles (dark theme)
├── package.json            # Dependencies & scripts
└── README.md               # This file
```

---

## 🔌 API Integration

### Base Configuration
```javascript
const API_BASE = 'http://localhost:8000/api';
```

### API Endpoints Used

| Endpoint | Purpose |
|----------|---------|
| `/metrics/all` | Load all pincode data for map |
| `/metrics/sector/{sector}` | Filter by sector |
| `/metrics/pincode/{pincode}` | Get pincode details |
| `/anomalies/top-rank` | Fetch top 20 alerts |
| `/stats/overview` | Dashboard statistics |
| `/report/{pincode}` | Generate official report |

### Data Flow
1. **On Load**: Fetch all metrics, alerts, and stats in parallel
2. **Sector Change**: Reload data filtered by sector
3. **Pincode Click**: Fetch detailed analysis and timeseries
4. **Report Request**: Generate and display official report

---

## 🖥️ Component Overview

### App.js - Main Component
```javascript
// State Management
const [activeSector, setActiveSector] = useState('all');
const [pincodes, setPincodes] = useState([]);
const [alerts, setAlerts] = useState([]);
const [stats, setStats] = useState(null);
const [selectedPincode, setSelectedPincode] = useState(null);
const [pincodeDetails, setPincodeDetails] = useState(null);
const [showReport, setShowReport] = useState(false);
```

### Key Functions
- `handlePincodeSelect(pincode)` - Select pincode and fetch details
- `generateReport(pincode)` - Generate official governance report
- `getMetricValue(pincode)` - Get appropriate metric based on sector
- `getRiskColor(score)` - Color coding based on risk level

---

## 🗺️ Map Configuration

### Center & Zoom
- **Center**: India (22.5937, 78.9629)
- **Initial Zoom**: 5 (country view)
- **Fly-to Zoom**: 10 (on pincode selection)

### Tile Layer
```javascript
<TileLayer
  url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
  attribution='&copy; CARTO'
/>
```

---

## 📱 Responsive Design

The dashboard is optimized for:
- Desktop (1920x1080+)
- Laptop (1366x768)
- Large tablets (landscape)

**Note**: For mobile viewing, consider implementing a dedicated mobile layout.

---

## 🔧 Configuration

### Changing API URL
Update in `App.js`:
```javascript
const API_BASE = 'http://your-api-url:port/api';
```

### Adding New Sectors
Add to the SECTORS array:
```javascript
const SECTORS = [
  { id: 'new_sector', label: 'New Sector', icon: '🆕', color: '#hex', metric: 'Metric_Name' },
  ...
];
```

---

## 🐛 Troubleshooting

### Common Issues

**Map not loading**
- Ensure `leaflet.css` is imported
- Check browser console for CORS errors

**API connection failed**
- Verify backend is running at correct port
- Check CORS configuration on backend

**Markers not showing**
- Verify data has valid latitude/longitude
- Check if API returns data in expected format

---

## 📦 Build for Production

```bash
# Create optimized production build
npm run build

# Output in build/ folder
# Serve with any static file server
```

---

## 👥 Team

**Pulse of Bharat** - UIDAI Hackathon 2026

## 📜 License

This project is developed for the UIDAI Hackathon. All data used is synthetic/anonymized.
