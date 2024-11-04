class ValidationForm {
    constructor() {
        this.form = document.getElementById('manualValidationForm');
        if (!this.form) return;

        this.responseId = this.form.dataset.responseId;
        this.saveButton = document.getElementById('saveValidation');
        this.scoreDisplay = document.getElementById('calculatedScore');
        this.checkboxes = document.querySelectorAll('.validation-check');

        this.initializeListeners();
        this.updateScore();
    }

    initializeListeners() {
        // Update score when checkboxes change
        this.checkboxes.forEach(checkbox => {
            checkbox.addEventListener('change', () => this.updateScore());
        });

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
        const score = Array.from(this.checkboxes)
            .filter(checkbox => checkbox.checked)
            .length * 20;

        this.scoreDisplay.textContent = score;
    }

    setLoading(isLoading) {
        this.saveButton.disabled = isLoading;
        this.saveButton.innerHTML = isLoading
            ? '<span class="spinner-border spinner-border-sm me-2"></span>Saving...'
            : '<i class="bi bi-save me-2"></i>Save Validation';
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

    async submitForm() {
        this.setLoading(true);

        const formData = new FormData();
        formData.append('valid', document.getElementById('validCheck').checked);
        formData.append('executable', document.getElementById('executableCheck').checked);
        formData.append('available_function', document.getElementById('availableFunctionCheck').checked);
        formData.append('formatting', document.getElementById('formattingCheck').checked);
        formData.append('knowledge', document.getElementById('knowledgeCheck').checked);
        formData.append('score_override', document.getElementById('scoreOverride').value);
        formData.append('comment', document.getElementById('comment').value);

        try {
            const response = await fetch(`/response/${this.responseId}/validate/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                },
                body: formData
            });

            const data = await response.json();

            if (data.status === 'success') {
                this.showToast('Validation saved successfully');
                // Optionally reload after save
                // setTimeout(() => location.reload(), 1500);
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

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    new ValidationForm();
});