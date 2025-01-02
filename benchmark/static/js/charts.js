function generateColors(categories) {
    const colors = {};
    categories.forEach((category, index) => {
        const hue = (index * 137.5) % 360;
        colors[category] = `hsla(${hue}, 70%, 50%, 0.7)`;
    });
    return colors;
}

function createLegend(categories, modelColors) {
    const legendDiv = document.createElement('div');
    legendDiv.style.display = 'flex';
    legendDiv.style.flexWrap = 'wrap';
    legendDiv.style.justifyContent = 'center';
    legendDiv.style.gap = '20px';
    legendDiv.style.padding = '20px';

    categories.forEach(category => {
        const itemDiv = document.createElement('div');
        itemDiv.style.display = 'flex';
        itemDiv.style.alignItems = 'center';
        itemDiv.style.marginRight = '10px';

        const colorBox = document.createElement('span');
        colorBox.style.width = '20px';
        colorBox.style.height = '20px';
        colorBox.style.backgroundColor = modelColors[category];
        colorBox.style.display = 'inline-block';
        colorBox.style.marginRight = '5px';
        colorBox.style.border = `1px solid ${modelColors[category].replace('0.7', '1')}`;

        const label = document.createElement('span');
        label.textContent = category;

        itemDiv.appendChild(colorBox);
        itemDiv.appendChild(label);
        legendDiv.appendChild(itemDiv);
    });

    return legendDiv;
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
                            const modelName = chartData.data[context.dataIndex].name;
                            return [
                                `Model: ${modelName}`,
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
    div.className = 'card';
    div.style.height = '100vh';
    div.style.display = 'flex';
    div.style.flexDirection = 'column';
    div.style.margin = '0';
    div.innerHTML = `
        <div class="card-header" style="display: flex; justify-content: flex-end; padding: 0.5rem;">
            <button class="btn btn-primary screenshot-btn" data-chart="${id}">
                Download
            </button>
        </div>
        <div class="card-body" style="padding-bottom: 0; flex: 1; display: flex; flex-direction: column;">
            <div style="flex: 1; min-height: 0;">
                <canvas id="${id}" style="width: 100%; height: 100%;"></canvas>
            </div>
        </div>
        <div class="legend-container" style="padding: 1rem;"></div>
    `;
    return div;
}

async function loadCharts(endpoint) {
    try {
        const response = await fetch(`${endpoint}?temperature=${document.getElementById('temperature').value}`);
        const data = await response.json();

        const container = document.getElementById('charts-container');
        container.innerHTML = '';
        container.style.height = '100vh';
        container.style.margin = '0';
        container.style.padding = '0';

        const allCategories = new Set();
        data.resultList.forEach(chart => {
            chart.data.forEach(item => allCategories.add(item.name));
        });

        const categoryColors = generateColors(Array.from(allCategories));

        data.resultList.forEach((chartData, index) => {
            const chartId = `chart-${index}`;
            const chartContainer = createChartContainer(chartId);
            container.appendChild(chartContainer);

            // Create and append legend
            const legend = createLegend(
                chartData.data.map(item => item.name),
                categoryColors
            );
            chartContainer.querySelector('.legend-container').appendChild(legend);

            createChart(chartId, chartData, data.maxY, categoryColors);
        });
    } catch (error) {
        console.error('Error loading chart data:', error);
        document.getElementById('charts-container').innerHTML =
            '<div class="alert alert-danger">Error loading chart data</div>';
    }
}

function downloadScreenshot(chartId) {
    const canvas = document.getElementById(chartId);
    const legendContainer = canvas.closest('.card').querySelector('.legend-container');

    // Create a temporary canvas to combine chart and legend
    const tempCanvas = document.createElement('canvas');
    const tempCtx = tempCanvas.getContext('2d');

    // Calculate the required height for the combined image
    const legendHeight = legendContainer.offsetHeight;
    tempCanvas.width = canvas.width;
    tempCanvas.height = canvas.height + legendHeight;

    // Draw the chart
    tempCtx.fillStyle = 'white';
    tempCtx.fillRect(0, 0, tempCanvas.width, tempCanvas.height);
    tempCtx.drawImage(canvas, 0, 0);

    // Draw the legend
    // Convert legend container to canvas using html2canvas
    html2canvas(legendContainer).then(legendCanvas => {
        tempCtx.drawImage(legendCanvas, 0, canvas.height);

        // Create download link
        const link = document.createElement('a');
        link.download = `chart-${chartId}-screenshot.png`;
        link.href = tempCanvas.toDataURL('image/png');
        link.click();
    });
}

document.addEventListener('DOMContentLoaded', () => {
    loadCharts('load/');
    document.getElementById('temperature').addEventListener('change', () => loadCharts('load/'));

    // Add click handlers for screenshot buttons
    document.addEventListener('click', (e) => {
        if (e.target.matches('.screenshot-btn')) {
            const chartId = e.target.getAttribute('data-chart');
            downloadScreenshot(chartId);
        }
    });
});