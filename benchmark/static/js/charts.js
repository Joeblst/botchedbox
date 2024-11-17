// static/js/charts.js

function createChart(containerId, chartData, maxY) {
    const ctx = document.getElementById(containerId);

    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels: chartData.data.map(item => item.name),
            datasets: [{
                label: chartData.heading,
                data: chartData.data.map(item => item.value),
                backgroundColor: 'rgba(54, 162, 235, 0.8)',
                borderColor: 'rgba(54, 162, 235, 1)',
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
            <canvas id="${id}" style="width: 100%; height: 45vh;"></canvas>
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

        data.resultList.forEach((chartData, index) => {
            const chartId = `chart-${index}`;
            const chartContainer = createChartContainer(chartId);
            container.appendChild(chartContainer);

            createChart(chartId, chartData, data.maxY);
        });
    } catch (error) {
        console.error('Error loading chart data:', error);
        document.getElementById('charts-container').innerHTML =
            '<div class="alert alert-danger">Error loading chart data</div>';
    }
}