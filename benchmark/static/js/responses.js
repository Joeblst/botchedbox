class ValidationForm {
    constructor() {
        this.form = document.getElementById('manualValidationForm');
        if (!this.form) return;

        this.responseId = this.form.dataset.responseId;
        this.saveButton = document.getElementById('saveValidation');
        this.scoreDisplay = document.getElementById('calculatedScore');
        this.checkboxes = document.querySelectorAll('.validation-check');
        this.isManual = this.checkboxes.length > 0; // Check if it's manual validation

        this.initializeListeners();
        if (this.isManual) {
            this.updateScore();
        }
    }

    initializeListeners() {
        // Update score when checkboxes change (manual only)
        if (this.isManual) {
            this.checkboxes.forEach(checkbox => {
                checkbox.addEventListener('change', () => this.updateScore());
            });
        }

        // Handle form submission
        this.form.addEventListener('submit', (e) => {
            e.preventDefault();
            this.submitForm();
        });

        // Validate score override
        const scoreOverride = document.getElementById('scoreOverride');
        if (scoreOverride) {
            scoreOverride.addEventListener('input', (e) => {
                const value = parseInt(e.target.value);
                if (value < 0 || value > 100) {
                    e.target.classList.add('is-invalid');
                } else {
                    e.target.classList.remove('is-invalid');
                }
            });
        }
    }

    updateScore() {
        const score = Math.ceil(Array.from(this.checkboxes)
            .filter(checkbox => checkbox.checked)
            .length * 100 / 6);

        this.scoreDisplay.textContent = score;
    }

    setLoading(isLoading) {
        this.saveButton.disabled = isLoading;
        const saveText = this.isManual ? 'Save Validation' : 'Save Score Override';
        this.saveButton.innerHTML = isLoading
            ? `<span class="spinner-border spinner-border-sm me-2"></span>Saving...`
            : `<i class="bi bi-save me-2"></i>${saveText}`;
    }

    showToast(message, type = 'success') {
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type} border-0 position-fixed bottom-0 end-0 m-3`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;

        document.body.appendChild(toast);
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();

        toast.addEventListener('hidden.bs.toast', () => toast.remove());
    }

    getCSRFToken() {
        // Try to get token from the form first
        const tokenInput = document.querySelector('[name=csrfmiddlewaretoken]');
        if (tokenInput) return tokenInput.value;

        // Fallback to cookie
        const name = 'csrftoken';
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

    async submitForm() {
        this.setLoading(true);

        const formData = new FormData();

        // Add manual validation data if it's a manual validation
        if (this.isManual) {
            formData.append('valid', document.getElementById('validCheck').checked);
            formData.append('functional', document.getElementById('functionalCheck').checked);
            formData.append('executable', document.getElementById('executableCheck').checked);
            formData.append('available_function', document.getElementById('availableFunctionCheck').checked);
            formData.append('formatting', document.getElementById('formattingCheck').checked);
            formData.append('knowledge', document.getElementById('knowledgeCheck').checked);
        }

        // Add score override and comment for both types
        const scoreOverride = document.getElementById('scoreOverride');
        const comment = document.getElementById('comment');

        if (scoreOverride) {
            formData.append('score_override', scoreOverride.value);
        }
        if (comment) {
            formData.append('comment', comment.value);
        }

        try {
            const response = await fetch(`/response/${this.responseId}/validate/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: formData
            });

            const data = await response.json();

            if (data.status === 'success') {
                this.showToast(this.isManual ? 'Validation saved successfully' : 'Score override saved successfully');
                // Reload after save to show updated scores
                setTimeout(() => location.reload(), 1500);
            } else {
                this.showToast(data.message || 'Error saving validation', 'danger');
            }
        } catch (error) {
            console.error('Error:', error);
            this.showToast('Error saving validation', 'danger');
        } finally {
            this.setLoading(false);
        }
    }
}

// Handle recalculate button
class RecalculateScore {
    constructor() {
        this.button = document.getElementById('recalculateBtn');
        if (!this.button) return;

        this.initializeListener();
    }

    initializeListener() {
        this.button.addEventListener('click', () => this.recalculate());
    }

    setLoading(isLoading) {
        this.button.disabled = isLoading;
        this.button.innerHTML = isLoading
            ? '<span class="spinner-border spinner-border-sm me-2"></span>Recalculating...'
            : '<i class="bi bi-arrow-repeat me-2"></i>Recalculate Score';
    }

    showToast(message, type = 'success') {
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type} border-0 position-fixed bottom-0 end-0 m-3`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;

        document.body.appendChild(toast);
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();

        toast.addEventListener('hidden.bs.toast', () => toast.remove());
    }

    getCSRFToken() {
        // Try to get token from the form first
        const tokenInput = document.querySelector('[name=csrfmiddlewaretoken]');
        if (tokenInput) return tokenInput.value;

        // Fallback to cookie
        const name = 'csrftoken';
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

    async recalculate() {
        this.setLoading(true);

        try {
            // Extract test ID from the URL
            const urlParts = window.location.pathname.split('/');
            const testId = urlParts[urlParts.indexOf('tests') + 1];

            const response = await fetch(`/tests/${testId}/recalculate/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            const data = await response.json();

            if (data.status === 'success') {
                this.showToast('Score recalculated successfully');
                // Reload the page after successful recalculation
                setTimeout(() => location.reload(), 1500);
            } else {
                this.showToast(data.message || 'Error recalculating score', 'danger');
            }
        } catch (error) {
            console.error('Error:', error);
            this.showToast('Error recalculating score', 'danger');
        } finally {
            this.setLoading(false);
        }
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    new ValidationForm();
    new RecalculateScore();
});