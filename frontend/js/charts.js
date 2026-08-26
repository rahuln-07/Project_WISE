/* ============================================================
   charts.js — Chart.js Visualizations
   ============================================================ */

let distChartInstance = null;
let labelChartInstance = null;

/**
 * Renders the suitability probability distribution histogram
 * @param {number[]} probs - Array of suitability probabilities
 */
function renderDistributionChart(probs) {
  const canvas = document.getElementById('distChart');
  if (!canvas) return;

  // Destroy existing chart if any
  if (distChartInstance) {
    distChartInstance.destroy();
    distChartInstance = null;
  }

  // Bucket the probabilities
  const buckets = [0, 0, 0, 0, 0];
  probs.forEach(p => {
    if (p < 0.2) buckets[0]++;
    else if (p < 0.4) buckets[1]++;
    else if (p < 0.6) buckets[2]++;
    else if (p < 0.8) buckets[3]++;
    else buckets[4]++;
  });

  distChartInstance = new Chart(canvas, {
    type: 'bar',
    data: {
      labels: ['0–20%', '20–40%', '40–60%', '60–80%', '80–100%'],
      datasets: [{
        label: 'Grid Cells',
        data: buckets,
        backgroundColor: [
          'rgba(201, 164, 104, 0.7)',
          'rgba(166, 148, 110, 0.7)',
          'rgba(130, 140, 118, 0.7)',
          'rgba(75, 124, 132, 0.7)',
          'rgba(27, 110, 140, 0.7)',
        ],
        borderColor: [
          'rgba(201, 164, 104, 1)',
          'rgba(166, 148, 110, 1)',
          'rgba(130, 140, 118, 1)',
          'rgba(75, 124, 132, 1)',
          'rgba(27, 110, 140, 1)',
        ],
        borderWidth: 1,
        borderRadius: 4,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#1a2332',
          titleColor: '#f1f5f9',
          bodyColor: '#94a3b8',
          borderColor: 'rgba(255,255,255,0.1)',
          borderWidth: 1,
          cornerRadius: 8,
          padding: 10,
        }
      },
      scales: {
        x: {
          ticks: { color: '#64748b', font: { size: 10 } },
          grid: { display: false },
        },
        y: {
          ticks: { color: '#64748b', font: { size: 10 } },
          grid: { color: 'rgba(255,255,255,0.05)' },
        }
      }
    }
  });
}

/**
 * Renders the label balance pie chart (278 positive vs 834 negative)
 */
function renderLabelBalanceChart() {
  const canvas = document.getElementById('labelChart');
  if (!canvas) return;

  // Destroy existing chart if any
  if (labelChartInstance) {
    labelChartInstance.destroy();
    labelChartInstance = null;
  }

  labelChartInstance = new Chart(canvas, {
    type: 'doughnut',
    data: {
      labels: ['Suitable (278)', 'Unsuitable (834)'],
      datasets: [{
        data: [278, 834],
        backgroundColor: [
          'rgba(34, 197, 94, 0.7)',
          'rgba(244, 63, 94, 0.5)',
        ],
        borderColor: [
          'rgba(34, 197, 94, 1)',
          'rgba(244, 63, 94, 1)',
        ],
        borderWidth: 1,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '60%',
      plugins: {
        legend: {
          position: 'bottom',
          labels: {
            color: '#94a3b8',
            font: { size: 11 },
            padding: 12,
            usePointStyle: true,
            pointStyleWidth: 10,
          }
        },
        tooltip: {
          backgroundColor: '#1a2332',
          titleColor: '#f1f5f9',
          bodyColor: '#94a3b8',
          borderColor: 'rgba(255,255,255,0.1)',
          borderWidth: 1,
          cornerRadius: 8,
          padding: 10,
        }
      }
    }
  });
}
