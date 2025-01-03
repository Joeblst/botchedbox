function generateColors(categories) {
    const colors = {};
    categories.forEach((category, index) => {
        const hue = (index * 137.5) % 360;
        colors[category] = `hsla(${hue}, 70%, 50%, 0.7)`;
    });
    return colors;
}

function createChartContainer(id) {
    const div = document.createElement('div');
    div.className = 'card mb-4';
    div.style.height = '60vh';
    div.style.display = 'flex';
    div.style.flexDirection = 'column';
    div.style.boxShadow = 'none';
    div.innerHTML = `
        <div class="download-controls" style="position: absolute; right: 10px; top: 10px; z-index: 10;">
            <button class="btn btn-primary btn-sm screenshot-exclude" onclick="downloadChart('${id}')">
                Download
            </button>
        </div>
        <div style="text-align: center; padding: 20px;">
            <h4 class="mb-0" id="${id}-title"></h4>
        </div>
        <div class="card-body" style="flex: 1; position: relative;">
            <canvas id="${id}"></canvas>
        </div>
    `;
    return div;
}

function createChart(containerId, chartData, modelColors) {
    const ctx = document.getElementById(containerId);
    const datasets = [];

    // Group data by model
    const modelData = {};
    chartData.models.forEach(model => {
        modelData[model] = chartData.temperatures.map(temp => {
            const dataPoint = chartData.data.find(d => d.temperature === temp && d.model === model);
            return dataPoint ? {
                min: dataPoint.min,
                q1: dataPoint.q1,
                median: dataPoint.median,
                q3: dataPoint.q3,
                max: dataPoint.max,
                mean: dataPoint.mean,
                std: dataPoint.std
            } : null;
        });
    });

    // Create datasets for each model
    chartData.models.forEach(model => {
        datasets.push({
            label: model,
            data: modelData[model],
            backgroundColor: modelColors[model],
            borderColor: modelColors[model].replace('0.7', '1'),
            borderWidth: 1,
            outlierBackgroundColor: '#666',
            itemRadius: 0,
            meanBackgroundColor: '#000'
        });
    });

    // Update chart title
    document.getElementById(`${containerId}-title`).textContent = `Temperature Performance Distribution for ${chartData.testcase_name}`;

    return new Chart(ctx, {
        type: 'boxplot',
        data: {
            labels: chartData.temperatures.map(t => `Temperature ${t}`),
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    title: {
                        display: true,
                        text: 'Score Distribution'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Temperature'
                    }
                }
            },
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        usePointStyle: true
                    }
                },
                tooltip: {
                    callbacks: {
                        label: (context) => {
                            const model = context.dataset.label;
                            const stats = context.raw;
                            return [
                                `Model: ${model}`,
                                `Min: ${stats.min.toFixed(1)}`,
                                `Q1: ${stats.q1.toFixed(1)}`,
                                `Median: ${stats.median.toFixed(1)}`,
                                `Mean: ${stats.mean.toFixed(1)}`,
                                `Std Dev: ${stats.std.toFixed(2)}`,
                                `Q3: ${stats.q3.toFixed(1)}`,
                                `Max: ${stats.max.toFixed(1)}`
                            ];
                        }
                    }
                }
            }
        }
    });
}

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
        link.download = `temperature-comparison-${chartId}.png`;
        link.href = canvas.toDataURL('image/png');
        link.click();
    });
}

function downloadAllCharts() {
    const chartIds = Array.from(document.querySelectorAll('canvas')).map(canvas => canvas.id);
    chartIds.forEach(id => downloadChart(id));
}

async function loadCharts() {
    try {
        const testcaseId = document.getElementById('testcase-select').value;
        const response = await fetch(`/evaluation/temperatures/load/?testcase=${testcaseId}`);
        const data = await response.json();

        const container = document.getElementById('charts-container');
        container.innerHTML = '';

        // Generate colors for models
        const modelColors = generateColors(data.models);

        // Create chart for the testcase
        const chartId = `chart-${testcaseId}`;
        const chartContainer = createChartContainer(chartId);
        container.appendChild(chartContainer);
        createChart(chartId, data, modelColors);

    } catch (error) {
        console.error('Error loading chart data:', error);
        document.getElementById('charts-container').innerHTML =
            '<div class="alert alert-danger">Error loading chart data</div>';
    }
}

async function initializeFilters() {
    try {
        const response = await fetch('/testcases/list/');
        const testcases = await response.json();

        const select = document.getElementById('testcase-select');
        testcases.forEach(testcase => {
            const option = document.createElement('option');
            option.value = testcase.id;
            option.textContent = testcase.name;
            select.appendChild(option);
        });

        select.addEventListener('change', loadCharts);
        if (testcases.length > 0) {
            loadCharts();
        }
    } catch (error) {
        console.error('Error loading testcases:', error);
    }
}

document.addEventListener('DOMContentLoaded', initializeFilters);