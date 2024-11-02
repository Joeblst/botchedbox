document.addEventListener('DOMContentLoaded', function() {
    const reloadButton = document.getElementById('start-button');

    reloadButton.addEventListener('click', function() {
        fetch("/benchmarks/start/")
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.text();
            })
            .then(html => {
                console.log(html);
            })
            .catch(error => {
                console.error('There was a problem with the fetch operation:', error);
            });
    });
});

async function fetchAndUpdate() {
    try {
        const response = await fetch('/benchmarks/');
        document.getElementById('overview-table').innerHTML = await response.text();
    } catch (error) {
        console.error('Error fetching HTML:', error);
    }
}

setInterval(fetchAndUpdate, 1000);

fetchAndUpdate()