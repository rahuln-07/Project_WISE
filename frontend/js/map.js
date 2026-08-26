/* ============================================================
   map.js — Leaflet Map Logic with Stats & Histogram
   ============================================================ */

let mapInstance = null;
let hazyPane = null;
let heatmapLayers = [];
let trainingPointLayers = [];
let trainingPointsVisible = false;

// Sample of labeled training points for overlay (subset from labels.csv)
const TRAINING_POINTS = [
  {lat:14.7389,lon:77.5643,label:1},{lat:14.7564,lon:77.5811,label:1},
  {lat:14.7427,lon:77.6789,label:0},{lat:14.7323,lon:77.6048,label:0},
  {lat:14.6405,lon:77.5827,label:0},{lat:14.6253,lon:77.5470,label:0},
  {lat:14.7535,lon:77.6608,label:0},{lat:14.7107,lon:77.6631,label:0},
  {lat:14.6783,lon:77.5785,label:1},{lat:14.7254,lon:77.5963,label:1},
  {lat:14.6931,lon:77.6234,label:1},{lat:14.7012,lon:77.5512,label:1},
  {lat:14.7198,lon:77.6435,label:0},{lat:14.6547,lon:77.6102,label:0},
  {lat:14.7421,lon:77.5989,label:1},{lat:14.6832,lon:77.6541,label:0},
  {lat:14.7101,lon:77.5678,label:1},{lat:14.6674,lon:77.5843,label:0},
  {lat:14.7345,lon:77.5731,label:1},{lat:14.6912,lon:77.6378,label:0},
  {lat:14.7189,lon:77.6123,label:1},{lat:14.6501,lon:77.5956,label:0},
  {lat:14.7456,lon:77.6267,label:0},{lat:14.6623,lon:77.6689,label:0},
  {lat:14.7298,lon:77.5534,label:1},{lat:14.6478,lon:77.6401,label:0},
  {lat:14.7567,lon:77.5912,label:1},{lat:14.6734,lon:77.5602,label:1},
  {lat:14.7089,lon:77.6756,label:0},{lat:14.6856,lon:77.5478,label:0},
  {lat:14.7234,lon:77.6089,label:1},{lat:14.7512,lon:77.5678,label:1},
  {lat:14.6389,lon:77.6234,label:0},{lat:14.6945,lon:77.6012,label:1},
  {lat:14.7156,lon:77.5845,label:1},{lat:14.6601,lon:77.5723,label:0},
  {lat:14.7378,lon:77.6156,label:0},{lat:14.6712,lon:77.6478,label:0},
  {lat:14.7045,lon:77.5534,label:1},{lat:14.6523,lon:77.6567,label:0},
];

// Auto-detect: try backend API first, fall back to bundled static file
const API_URL = window.location.origin + '/api/suitability';
const STATIC_GEOJSON = 'data/suitability.geojson';
const AOI_CENTER = [14.68, 77.60];
const AOI_ZOOM = 12;

function suitabilityColor(prob) {
  const low = [201, 164, 104];
  const high = [27, 110, 140];
  const rgb = low.map((c, i) => Math.round(c + (high[i] - c) * prob));
  return `rgb(${rgb[0]},${rgb[1]},${rgb[2]})`;
}

function initSuitabilityMap() {
  const mapEl = document.getElementById('map');
  if (!mapEl) return;

  mapInstance = L.map('map').setView(AOI_CENTER, AOI_ZOOM);

  // Use OpenStreetMap tiles (free, no API key required)
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
  }).addTo(mapInstance);

  // Create hazy pane
  hazyPane = mapInstance.createPane('hazyHeatmap');
  hazyPane.style.opacity = '0.75';
  hazyPane.style.filter = 'blur(12px)';

  // Geocoder search
  L.Control.geocoder({
    defaultMarkGeocode: true,
    position: 'topright'
  }).addTo(mapInstance);

  // Opacity slider
  const slider = document.getElementById('opacitySlider');
  if (slider) {
    slider.addEventListener('input', function (e) {
      if (hazyPane) hazyPane.style.opacity = e.target.value;
    });
  }

  // Toggle training points
  const toggle = document.getElementById('togglePoints');
  if (toggle) {
    toggle.addEventListener('change', function () {
      trainingPointsVisible = this.checked;
      trainingPointLayers.forEach(m => {
        if (trainingPointsVisible) m.addTo(mapInstance);
        else mapInstance.removeLayer(m);
      });
    });
  }

  // Add training point markers (hidden by default)
  TRAINING_POINTS.forEach(pt => {
    const marker = L.circleMarker([pt.lat, pt.lon], {
      radius: 5,
      fillColor: pt.label === 1 ? '#22c55e' : '#f43f5e',
      fillOpacity: 0.9,
      color: '#fff',
      weight: 1,
    });
    marker.bindPopup(`
      <div style="font-size:13px;">
        <strong>${pt.label === 1 ? '✅ Suitable' : '❌ Unsuitable'}</strong><br>
        <span style="color:#94a3b8;">Lat: ${pt.lat.toFixed(4)}, Lon: ${pt.lon.toFixed(4)}</span>
      </div>
    `);
    trainingPointLayers.push(marker);
  });

  // Load suitability data
  loadSuitabilityData();
}

async function loadSuitabilityData() {
  const statusEl = document.getElementById('map-status');
  try {
    // Try backend API first, fall back to static file (for GitHub Pages / Vercel)
    let res;
    try {
      res = await fetch(API_URL);
      if (!res.ok) throw new Error('API unavailable');
    } catch {
      res = await fetch(STATIC_GEOJSON);
    }
    if (!res.ok) throw new Error(`Failed to load suitability data`);
    const geojson = await res.json();
    const probs = [];

    geojson.features.forEach((feature) => {
      const [lng, lat] = feature.geometry.coordinates;
      const prob = feature.properties.suitability_probability;
      probs.push(prob);

      const halfWidth = 0.0087;
      const bounds = [
        [lat - halfWidth, lng - halfWidth],
        [lat + halfWidth, lng + halfWidth]
      ];

      const square = L.rectangle(bounds, {
        fillColor: suitabilityColor(prob),
        fillOpacity: 1,
        stroke: false,
        pane: 'hazyHeatmap'
      }).addTo(mapInstance);

      square.bindPopup(`
        <div style="font-size:13px; padding:4px;">
          <strong>Suitability: ${(prob * 100).toFixed(1)}%</strong><br>
          <span style="color:#94a3b8;">Lat: ${lat.toFixed(4)}, Lon: ${lng.toFixed(4)}</span>
        </div>
      `);

      heatmapLayers.push(square);
    });

    // Update stats
    updateMapStats(probs);

    // Render charts (use setTimeout to ensure canvas elements are fully laid out)
    setTimeout(() => {
      if (typeof renderDistributionChart === 'function') {
        renderDistributionChart(probs);
      }
      if (typeof renderLabelBalanceChart === 'function') {
        renderLabelBalanceChart();
      }
    }, 100);

    if (statusEl) statusEl.textContent = `${geojson.features.length} cells loaded successfully`;
  } catch (err) {
    if (statusEl) statusEl.textContent = 'Failed to load data — is the backend running on port 8000?';
    console.error(err);
  }
}

function updateMapStats(probs) {
  const total = probs.length;
  const mean = probs.reduce((a, b) => a + b, 0) / total;
  const high = probs.filter(p => p > 0.6).length;
  const low = probs.filter(p => p < 0.2).length;

  const elTotal = document.getElementById('ms-total');
  const elMean = document.getElementById('ms-mean');
  const elHigh = document.getElementById('ms-high');
  const elLow = document.getElementById('ms-low');

  if (elTotal) elTotal.textContent = total;
  if (elMean) elMean.textContent = (mean * 100).toFixed(1) + '%';
  if (elHigh) elHigh.textContent = high;
  if (elLow) elLow.textContent = low;
}

function destroyMap() {
  if (mapInstance) {
    mapInstance.remove();
    mapInstance = null;
    hazyPane = null;
    heatmapLayers = [];
    trainingPointLayers = [];
    trainingPointsVisible = false;
  }
}
