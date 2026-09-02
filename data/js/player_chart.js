// Read data injected by the template
const data = window.playerChartData || {};

const matchLabels   = data.matchLabels || [];
const matchesData   = data.matchesData || [];
const goalsData     = data.goalsData || [];
const trainingsData = data.trainingsData || [];

// Get canvas
const ctx = document.getElementById('playerChart');
if (!ctx) {
  console.warn('playerChart canvas not found');
} else {
  const chart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: matchLabels,
      datasets: [
        {
          label: 'Matches played (cumulative)',
          data: matchesData,
          borderColor: 'rgba(16, 118, 110, 1)',
          backgroundColor: 'rgba(16, 118, 110, 0.1)',
          tension: 0.2,
        },
        {
          label: 'Goals per match',
          data: goalsData,
          borderColor: 'rgba(220, 38, 38, 1)',
          backgroundColor: 'rgba(220, 38, 38, 0.1)',
          tension: 0.2,
        },
        {
          label: 'Trainings attended (cumulative)',
          data: trainingsData,
          borderColor: 'rgba(37, 99, 235, 1)',
          backgroundColor: 'rgba(37, 99, 235, 0.1)',
          tension: 0.2,
        }
      ]
    },
    options: {
      responsive: true,
      interaction: { mode: 'index', intersect: false },
      scales: { y: { beginAtZero: true } }
    }
  });

  // Optional: wire up toggles
  const toggleMatches   = document.getElementById('toggleMatches');
  const toggleGoals     = document.getElementById('toggleGoals');
  const toggleTrainings = document.getElementById('toggleTrainings');

  if (toggleMatches) {
    toggleMatches.addEventListener('change', e => {
      chart.getDatasetMeta(0).hidden = !e.target.checked;
      chart.update();
    });
  }
  if (toggleGoals) {
    toggleGoals.addEventListener('change', e => {
      chart.getDatasetMeta(1).hidden = !e.target.checked;
      chart.update();
    });
  }
  if (toggleTrainings) {
    toggleTrainings.addEventListener('change', e => {
      chart.getDatasetMeta(2).hidden = !e.target.checked;
      chart.update();
    });
  }
}