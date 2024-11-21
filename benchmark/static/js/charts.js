function generateColors(categories) {
    const colors = {};
    categories.forEach((category, index) => {
        const hue = (index * 137.5) % 360;
        colors[category] = `hsla(${hue}, 70%, 50%, 0.7)`;
    });
    return colors;
}

function createChart(containerId, chartData, maxY, modelColors) {
    const ctx = document.getElementById(containerId);
    const temperature = document.getElementById('temperature').value;
    const title = `${chartData.heading} (Temperature: ${temperature})`;

    return new Chart(ctx, {
        type: 'boxplot',
        data: {
            labels: chartData.data.map(item => item.name),
            datasets: [{
                label: title,
                data: chartData.data.map(item => ({
                    min: item.min,
                    q1: item.q1,
                    median: item.median,
                    q3: item.q3,
                    max: item.max,
                    mean: item.mean
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
                    text: title,
                    font: { size: 16 },
                    padding: 20
                },
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (context) => {
                            const item = context.raw;
                            return [
                                `Min: ${item.min.toFixed(1)}`,
                                `Q1: ${item.q1.toFixed(1)}`,
                                `Median: ${item.median.toFixed(1)}`,
                                `Mean: ${item.mean.toFixed(1)}`,
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

function createChartContainer(id) {
    const div = document.createElement('div');
    div.className = 'card mb-4';
    div.innerHTML = `
        <div class="card-body">
            <canvas id="${id}" style="width: 100%; height: 60vh;"></canvas>
        </div>
    `;
    return div;
}

async function loadCharts(endpoint) {
    try {
        const response = await fetch(`${endpoint}?temperature=${document.getElementById('temperature').value}`);
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
            const chartContainer = createChartContainer(chartId);
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
    document.getElementById('temperature').addEventListener('change', () => loadCharts('load/'));
});