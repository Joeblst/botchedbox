document.addEventListener('DOMContentLoaded', function () {

    // Refresh Button
    const refreshButton = document.getElementById('refreshTable');
    refreshButton.addEventListener('click', function () {
        this.disabled = true;
        const originalContent = this.innerHTML;
        this.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Refreshing...';

        let href = document.getElementById('testcase-table') ? '/testcases/load/' : window.location.href;

        fetch(href)
            .then(response => response.text())
            .then(html => {
                const parser = new DOMParser();
                const doc = parser.parseFromString(html, 'text/html');
                const newTable = doc.querySelector('.overview-table');
                document.querySelector('.overview-table').innerHTML = newTable.innerHTML;
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Failed to refresh. Please try again.');
            })
            .finally(() => {
                this.disabled = false;
                this.innerHTML = originalContent;
            });
    });
});