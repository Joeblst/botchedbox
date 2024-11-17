// static/js/charts.js

// Generate consistent colors for models
function generateColors(modelNames) {
    const colors = {};
    modelNames.forEach((model, index) => {
        // Using HSL for better control over colors
        const hue = (index * 137.5) % 360;  // Golden angle approximation for good distribution
        colors[model] = `hsl(${hue}, 70%, 50%)`;
    });
    return colors;
}

function createChart(containerId, chartData, maxY, modelColors) {
    const ctx = document.getElementById(containerId);

    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels: chartData.data.map(item => item.name),
            datasets: [{
                label: chartData.heading,
                data: chartData.data.map(item => item.value),
                backgroundColor: chartData.data.map(item => modelColors[item.name]),
                borderColor: chartData.data.map(item => modelColors[item.name]),
                borderWidth: 1
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
                    },
                    ticks: {
                        maxRotation: 0,
                        minRotation: 0
                    }
                }
            },
            plugins: {
                title: {
                    display: true,
                    text: chartData.heading,
                    font: {
                        size: 16
                    },
                    padding: 20
                },
                legend: {
                    display: false
                },
                tooltip: {
                    enabled: true
                },
                datalabels: {
                    anchor: 'end',
                    align: 'top',
                    formatter: function(value) {
                        return value.toFixed(1);
                    },
                    font: {
                        weight: 'bold'
                    },
                    padding: 4
                }
            }
        },
        plugins: [{
            afterDraw: function(chart) {
                var ctx = chart.ctx;
                chart.data.datasets.forEach(function(dataset) {
                    var meta = chart.getDatasetMeta(0);
                    meta.data.forEach(function(bar, index) {
                        var data = dataset.data[index];
                        var position = bar.getCenterPoint();

                        ctx.fillStyle = '#000000';
                        ctx.textAlign = 'center';
                        ctx.textBaseline = 'bottom';
                        ctx.font = 'bold 12px Arial';

                        ctx.fillText(data.toFixed(1), position.x, bar.base - 5);
                    });
                });
            }
        }]
    });
}

function createChartContainer(id) {
    const div = document.createElement('div');
    div.className = 'card mb-4';
    div.innerHTML = `
        <div class="card-body">
            <canvas id="${id}" style="width: 100%; height: 400px;"></canvas>
        </div>
    `;
    return div;
}

async function loadCharts(endpoint) {
    try {
        const response = await fetch(endpoint);
        const data = await response.json();

        const container = document.getElementById('charts-container');
        container.innerHTML = ''; // Clear any existing content

        // Get all unique model names from all charts
        const allModels = new Set();
        data.resultList.forEach(chart => {
            chart.data.forEach(item => allModels.add(item.name));
        });

        // Generate consistent colors for all models
        const modelColors = generateColors(Array.from(allModels));

        data.resultList.forEach((chartData, index) => {
            const chartId = `chart-${index}`;
            const chartContainer = createChartContainer(chartId);
            container.appendChild(chartContainer);

            createChart(chartId, chartData, data.maxY, modelColors);
        });
    } catch (error) {
        console.error('Error loading chart data:', error);
        document.getElementById('charts-container').innerHTML =
            '<div class="alert alert-danger">Error loading chart data</div>';
    }
}