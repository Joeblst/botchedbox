function generateColors(categories) {
    const colors = {};
    categories.forEach((category, index) => {
        const hue = (index * 137.5) % 360;
        colors[category] = `hsl(${hue}, 70%, 50%)`;
    });
    return colors;
}

function createChart(containerId, chartData, maxY, typeColors) {
    const ctx = document.getElementById(containerId);

    return new Chart(ctx, {
        type: 'line',
        data: {
            datasets: chartData.data.map(series => ({
                label: series.name,
                data: series.data.map(point => ({
                    x: point.temperature,
                    y: point.score
                })),
                borderColor: typeColors[series.name],
                backgroundColor: typeColors[series.name],
                tension: 0.3
            }))
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
                    type: 'linear',
                    title: {
                        display: true,
                        text: chartData.xaxis
                    }
                }
            },
            plugins: {
                title: {
                    display: true,
                    text: chartData.heading,
                    font: { size: 16 },
                    padding: 20
                },
                legend: {
                    display: true,
                    position: 'bottom'
                },
                tooltip: {
                    callbacks: {
                        title: (items) => `Temperature: ${items[0].parsed.x}`,
                        label: (item) => `${item.dataset.label}: ${item.parsed.y.toFixed(1)}`
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
        const response = await fetch(endpoint);
        const data = await response.json();

        const container = document.getElementById('charts-container');
        container.innerHTML = '';

        const allTypes = new Set();
        data.resultList.forEach(chart => {
            chart.data.forEach(item => allTypes.add(item.name));
        });

        const typeColors = generateColors(Array.from(allTypes));

        data.resultList.forEach((chartData, index) => {
            const chartId = `chart-${index}`;
            const chartContainer = createChartContainer(chartId);
            container.appendChild(chartContainer);
            createChart(chartId, chartData, data.maxY, typeColors);
        });
    } catch (error) {
        console.error('Error loading chart data:', error);
        document.getElementById('charts-container').innerHTML =
            '<div class="alert alert-danger">Error loading chart data</div>';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    loadCharts('load/');
});