document.addEventListener('DOMContentLoaded', function () {
    // Start benchmark button
    const startButton = document.getElementById('start-button');
    const temperature = document.getElementById('temperature').value;
    startButton.addEventListener('click', function () {
        this.disabled = true;
        this.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Starting...';

        fetch('/benchmarks/start/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                temperature: parseInt(temperature)
            })
        })
            .then(response => {
                if (response.ok) {
                    location.reload();
                } else {
                    throw new Error('Failed to start benchmark');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                this.disabled = false;
                this.innerHTML = 'Start New Benchmark';
                alert('Failed to start benchmark. Please try again.');
            });
    });

    // Search functionality
    const searchInput = document.getElementById('searchBenchmark');
    searchInput.addEventListener('input', function () {
        const searchTerm = this.value.toLowerCase();
        const rows = document.querySelectorAll('.benchmark-row');

        rows.forEach(row => {
            const benchmarkId = row.querySelector('td:first-child').textContent.toLowerCase();
            const status = row.querySelector('td:nth-child(2)').textContent.toLowerCase();

            if (benchmarkId.includes(searchTerm) || status.includes(searchTerm)) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    });

    // Auto-refresh for running benchmarks
    function autoRefresh() {
        const runningBenchmarks = document.querySelectorAll('.badge.bg-running');
        if (runningBenchmarks.length > 0) {
            setTimeout(() => {
                refreshButton.click();
                autoRefresh();
            }, 5000);
        }
    }

    autoRefresh();
});

// Helper function to get CSRF token
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}