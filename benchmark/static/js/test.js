async function fetchAndUpdate() {
    try {
        const response = await fetch(window.location.href + 'tests');
        document.getElementById('test-table').innerHTML = await response.text();
    } catch (error) {
        console.error('Error fetching HTML:', error);
    }
}

setInterval(fetchAndUpdate, 1000);

fetchAndUpdate()