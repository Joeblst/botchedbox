function generateColors(categories) {
    const colors = {};
    categories.forEach((category, index) => {
        const hue = (index * 137.5) % 360;
        colors[category] = `hsl(${hue}, 70%, 50%)`;
    });
    return colors;
}

function createChart(containerId, chartData, maxY, modelColors) {
    const ctx = document.getElementById(containerId);
    const temperature = document.getElementById('temperature').value;
    const title = `${chartData.heading} (Temperature: ${temperature})`;

    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels: chartData.data.map(item => item.name),
            datasets: [{
                label: title,
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
                    text: title,
                    font: { size: 16 },
                    padding: 20
                },
                legend: { display: false },
                tooltip: { enabled: true },
                datalabels: {
                    anchor: 'end',
                    align: 'top',
                    formatter: value => value.toFixed(1),
                    font: { weight: 'bold' },
                    padding: 4
                }
            }
        },
        plugins: [{
            afterDraw: function(chart) {
                const ctx = chart.ctx;
                chart.data.datasets.forEach(dataset => {
                    const meta = chart.getDatasetMeta(0);
                    meta.data.forEach((bar, index) => {
                        const data = dataset.data[index];
                        const position = bar.getCenterPoint();
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