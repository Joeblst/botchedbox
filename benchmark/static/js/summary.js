// Color generation for chart datasets
function generateColors(categories) {
    const colors = {};
    categories.forEach((category, index) => {
        const hue = (index * 137.5) % 360;
        colors[category] = {
            fill: `hsla(${hue}, 70%, 50%, 0.2)`,
            stroke: `hsl(${hue}, 70%, 50%)`
        };
    });
    return colors;
}

// Radar chart creation
function createRadarChart(containerId, data, models, problems) {
    const ctx = document.getElementById(containerId);
    const modelColors = generateColors(models);

    const datasets = models.map(model => ({
        label: model,
        data: problems.map(type =>
            data.find(item => item.problem === type)?.[model] || 0
        ),
        backgroundColor: modelColors[model].fill,
        borderColor: modelColors[model].stroke,
        pointBackgroundColor: modelColors[model].stroke,
        pointBorderColor: '#fff',
        pointHoverBackgroundColor: '#fff',
        pointHoverBorderColor: modelColors[model].stroke,
        borderWidth: 1
    }));

    if (window.radarChart) {
        window.radarChart.destroy();
    }

    window.radarChart = new Chart(ctx, {
        type: 'radar',
        data: {
            labels: problems,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                r: {
                    beginAtZero: true,
                    min: 0,
                    max: 100,
                    ticks: {
                        stepSize: 20
                    }
                }
            },
            plugins: {
                title: {
                    display: true,
                    text: 'Model Performance by Problem',
                    font: {
                        size: 16
                    },
                    padding: 20
                },
                legend: {
                    position: 'top'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.dataset.label}: ${context.raw.toFixed(1)}%`;
                        }
                    }
                }
            }
        }
    });
}

// Data filtering functions
function filterData(data, selectedProblems, selectedModels) {
    return data.filter(item => selectedProblems.includes(item.problem))
        .map(item => {
            const filteredItem = { problem: item.problem };
            selectedModels.forEach(model => {
                if (item.hasOwnProperty(model)) {
                    filteredItem[model] = item[model];
                }
            });
            return filteredItem;
        });
}

function updateTable(filteredData, selectedModels) {
    const tbody = document.querySelector('table tbody');
    const rows = tbody.querySelectorAll('tr');

    rows.forEach(row => {
        const problem = row.dataset.problem;
        if (!problem) return;

        const shouldShow = filteredData.some(item => item.problem === problem);
        row.style.display = shouldShow ? '' : 'none';

        if (shouldShow) {
            const cells = row.querySelectorAll('td');
            cells.forEach((cell, index) => {
                if (index === 0) return; // Skip problem column
                const columnHeader = document.querySelector(`th[data-model]:nth-child(${index + 1})`);
                if (columnHeader) {
                    const model = columnHeader.dataset.model;
                    cell.style.display = selectedModels.includes(model) ? '' : 'none';
                }
            });
        }
    });

    // Update header visibility
    document.querySelectorAll('th[data-model]').forEach(th => {
        const model = th.dataset.model;
        th.style.display = selectedModels.includes(model) ? '' : 'none';
    });
}

function createChartContainer(id) {
    const div = document.createElement('div');
    div.className = 'card-body';
    div.innerHTML = `<canvas id="${id}" style="width: 100%; height: 100vh;"></canvas>`;
    return div;
}

// Filter handling functions
function toggleAllFilters(state) {
    document.querySelectorAll('.filter-checkbox').forEach(checkbox => {
        checkbox.checked = state;
    });
    updateVisualization();
}

function getSelectedFilters(type) {
    return Array.from(document.querySelectorAll(`[data-filter-type="${type}"]:checked`))
        .map(cb => cb.value);
}

function updateVisualization() {
    const selectedProblems = getSelectedFilters('problem');
    const selectedModels = getSelectedFilters('model');
    loadCharts('load/', selectedProblems, selectedModels);
}

// Data loading and chart initialization
async function loadCharts(endpoint, selectedProblems, selectedModels) {
    try {
        const response = await fetch(endpoint);
        const jsonData = await response.json();
        const data = jsonData.data;

        // Filter data
        const filteredData = filterData(data, selectedProblems, selectedModels);

        // Update table
        updateTable(filteredData, selectedModels);

        // Update chart
        const container = document.getElementById('radar-container');
        container.innerHTML = '';

        const chartId = 'radar-chart';
        const chartContainer = createChartContainer(chartId);
        container.appendChild(chartContainer);
        createRadarChart(chartId, filteredData, selectedModels, selectedProblems);

    } catch (error) {
        console.error('Error loading chart data:', error);
        document.getElementById('radar-container').innerHTML =
            '<div class="alert alert-danger">Error loading chart data</div>';
    }
}

// Initialize everything when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Initial load
    updateVisualization();
    
    // Add event listeners to checkboxes
    document.querySelectorAll('.filter-checkbox').forEach(checkbox => {
        checkbox.addEventListener('change', updateVisualization);
    });
});
