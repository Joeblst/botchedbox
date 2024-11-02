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

        function recalculateScores() {
            const button = document.getElementById('recalculateBtn');
            button.disabled = true;
            button.innerHTML = 'Recalculating...';

            fetch(`recalculate/`, {
                method: 'GET',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'Content-Type': 'application/json',
                },
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    location.reload();
                } else {
                    alert('Error: ' + data.message);
                    button.disabled = false;
                    button.innerHTML = 'Recalculate Scores';
                }
            })
            .catch(error => {
                alert('Error: ' + error);
                button.disabled = false;
                button.innerHTML = 'Recalculate Scores';
            });
        }