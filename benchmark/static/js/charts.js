/**
 * Ensure all models have the same color
 * @param categories
 * @returns {{}}
 */
function generateColors(categories) {
    const colors = {};
    categories.forEach((category, index) => {
        const hue = (index * 137.5) % 360;
        colors[category] = `hsla(${hue}, 70%, 50%, 0.7)`;
    });
    return colors;
}

/**
 * Places the container for the charts
 * @param id
 * @param title
 * @returns {HTMLDivElement}
 */
function createChartContainer(id, title) {
    const div = document.createElement('div');
    div.className = 'card mb-4';
    div.style.height = '60vh';
    div.style.display = 'flex';
    div.style.flexDirection = 'column';
    div.style.boxShadow = 'none';
    div.innerHTML = `
        <div class="download-controls" style="position: absolute; right: 10px; top: 10px; z-index: 10;">
            <button class="btn btn-primary btn-sm screenshot-exclude" data-chart="${id}">
                Download
            </button>
        </div>
        <div style="text-align: center; padding: 20px;">
            <h4 class="mb-0">${title}</h4>
        </div>
        <div class="card-body" style="flex: 1; position: relative;">
            <canvas id="${id}"></canvas>
        </div>
    `;
    return div;
}

/**
 * Create the chart
 * @param containerId
 * @param chartData
 * @param maxY
 * @param modelColors
 * @returns {Chart}
 */
function createChart(containerId, chartData, maxY, modelColors) {
    const ctx = document.getElementById(containerId);

    // Configure Chart and set Data
    return new Chart(ctx, {
        type: 'boxplot',
        data: {
            labels: chartData.data.map(item => item.name),
            datasets: [{
                data: chartData.data.map(item => ({
                    min: item.min,
                    q1: item.q1,
                    median: item.median,
                    q3: item.q3,
                    max: item.max,
                    mean: item.mean,
                    std: item.std
                })),
                backgroundColor: chartData.data.map(item => modelColors[item.name]),
                borderColor: chartData.data.map(item => modelColors[item.name].replace('0.7', '1')),
                borderWidth: 1,
                outlierBackgroundColor: '#666',
                itemRadius: 0,
                meanBackgroundColor: '#000'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    max: maxY,
                    title: {
                        display: true,
                        text: chartData.yaxis
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: chartData.xaxis
                    }
                }
            },
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        usePointStyle: true,
                        generateLabels: (chart) => {
                            return chartData.data.map(item => ({
                                text: item.name,
                                fillStyle: modelColors[item.name],
                                strokeStyle: modelColors[item.name].replace('0.7', '1'),
                                lineWidth: 1,
                                hidden: false,
                                pointStyle: 'circle'
                            }));
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: (context) => {
                            const item = context.raw;
                            const modelName = chartData.data[context.dataIndex].name;
                            return [
                                `Model: ${modelName}`,
                                `Min: ${item.min.toFixed(1)}`,
                                `Q1: ${item.q1.toFixed(1)}`,
                                `Median: ${item.median.toFixed(1)}`,
                                `Mean: ${item.mean.toFixed(1)}`,
                                `Std Dev: ${item.std.toFixed(2)}`,
                                `Q3: ${item.q3.toFixed(1)}`,
                                `Max: ${item.max.toFixed(1)}`
                            ];
                        }
                    }
                }
            }
        }
    });
}

/**
 * Create screenshots
 * @param chartId
 * @returns {Promise<void>}
 */
async function downloadChart(chartId) {
    const canvas = document.getElementById(chartId);
    const container = canvas.closest('.card');

    // Hide elements with screenshot-exclude class
    const excludedElements = container.querySelectorAll('.screenshot-exclude');
    excludedElements.forEach(el => el.style.display = 'none');

    html2canvas(container, {
        backgroundColor: '#ffffff',
        removeContainer: true,
        scale: 2,
        useCORS: true,
        shadow: false,
        ignoreElements: (element) => element.classList.contains('screenshot-exclude')
    }).then(canvas => {
        // Restore visibility of excluded elements
        excludedElements.forEach(el => el.style.display = '');
        const link = document.createElement('a');
        link.download = `chart-${chartId}-screenshot.png`;
        link.href = canvas.toDataURL('image/png');
        link.click();
    });
}

function downloadAllCharts() {
    const chartIds = Array.from(document.querySelectorAll('canvas')).map(canvas => canvas.id);
    chartIds.forEach(id => downloadChart(id));
}

async function loadCharts(endpoint) {
    try {
        const temperature = document.getElementById('temperature').value;
        const response = await fetch(`${endpoint}?temperature=${temperature}`);
        const data = await response.json();

        const container = document.getElementById('charts-container');
        container.innerHTML = '';

        const allCategories = new Set();
        data.resultList.forEach(chart => {
            chart.data.forEach(item => allCategories.add(item.name));
        });

        const categoryColors = generateColors(Array.from(allCategories));

        data.resultList.forEach((chartData, index) => {
            const chartId = `chart-${index}`;
            const title = `${chartData.heading} (Temperature: ${temperature})`;
            const chartContainer = createChartContainer(chartId, title);
            container.appendChild(chartContainer);
            createChart(chartId, chartData, data.maxY, categoryColors);
        });
    } catch (error) {
        console.error('Error loading chart data:', error);
        document.getElementById('charts-container').innerHTML =
            '<div class="alert alert-danger">Error loading chart data</div>';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    loadCharts('load/');

    // Add event listener for temperature filter
    document.getElementById('temperature').addEventListener('change', () => loadCharts('load/'));

    // Add click handlers for screenshot buttons
    document.addEventListener('click', (e) => {
        if (e.target.matches('.screenshot-exclude')) {
            const chartId = e.target.getAttribute('data-chart');
            downloadChart(chartId);
        }
    });
});