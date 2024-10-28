document.addEventListener('DOMContentLoaded', function() {
    const reloadButton = document.getElementById('reload-button');
    const tableContainer = document.getElementById('testcases-table');

    reloadButton.addEventListener('click', function() {
        fetch("/testcases/load/")
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.text();
            })
            .then(html => {
                tableContainer.innerHTML = html;
            })
            .catch(error => {
                console.error('There was a problem with the fetch operation:', error);
            });
    });
});