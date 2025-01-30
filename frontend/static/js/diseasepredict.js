document.addEventListener('DOMContentLoaded', function() {
    // Cache DOM elements
    const analysisForm = document.getElementById('analysisForm');
    const symptomsContainer = document.getElementById('symptomsContainer');
    const loadingOverlay = document.querySelector('.loading-overlay');
    const petTypeRadios = document.querySelectorAll('input[name="petType"]');

    // Initialize loading overlay
    if (loadingOverlay) {
        loadingOverlay.style.display = 'none';
    }
    
    // Symptom options for Cats and Dogs
    const symptoms = {
        Cat: [
            { id: 'redness', label: 'Redness', icon: 'fa-circle' },
            { id: 'swelling', label: 'Swelling', icon: 'fa-circle-plus' },
            { id: 'itching', label: 'Itching', icon: 'fa-hand-dots' },
            { id: 'scratching', label: 'Excessive Scratching', icon: 'fa-hand-back-fist' },
            { id: 'hairLoss', label: 'Hair Loss', icon: 'fa-paintbrush' },
            { id: 'circularLoss', label: 'Circular Hair Loss', icon: 'fa-circle-dot' },
            { id: 'scaly', label: 'Scaly Patches', icon: 'fa-layer-group' },
            { id: 'crusty', label: 'Crusty Skin', icon: 'fa-virus-covid' },
            { id: 'wounds', label: 'Wounds', icon: 'fa-bandage' },
            { id: 'patchyLoss', label: 'Patchy Hair Loss', icon: 'fa-droplet' },
            { id: 'intenseItch', label: 'Intense Itching', icon: 'fa-hand-dots' },
            { id: 'thickSkin', label: 'Thickened Skin', icon: 'fa-layer-group' }
        ],
        Dog: [
            { id: 'cloudyEyes', label: 'Cloudy Eyes', icon: 'fa-eye' },
            { id: 'visionLoss', label: 'Vision Loss', icon: 'fa-eye-slash' },
            { id: 'redEyes', label: 'Red Eyes', icon: 'fa-eye' },
            { id: 'discharge', label: 'Discharge', icon: 'fa-droplet' },
            { id: 'swelling', label: 'Swelling', icon: 'fa-circle-plus' },
            { id: 'pus', label: 'Pus', icon: 'fa-virus-covid' },
            { id: 'wound', label: 'Wound', icon: 'fa-bandage' },
            { id: 'nasalDischarge', label: 'Nasal Discharge', icon: 'fa-droplet' },
            { id: 'crustyNose', label: 'Crusty Nose', icon: 'fa-virus-covid' },
            { id: 'intenseItch', label: 'Intense Itching', icon: 'fa-hand-dots' },
            { id: 'scaling', label: 'Scaling', icon: 'fa-layer-group' },
            { id: 'scabs', label: 'Scabs', icon: 'fa-virus-covid' },
            { id: 'hairLoss', label: 'Hair Loss', icon: 'fa-paintbrush' },
            { id: 'inflammation', label: 'Inflammation', icon: 'fa-circle-plus' },
            { id: 'scratching', label: 'Constant Scratching', icon: 'fa-hand-back-fist' },
            { id: 'lesions', label: 'Circular Lesions', icon: 'fa-circle-dot' }
        ]
    };

    // Handle image previews
    function setupImagePreview(inputId, previewId) {
        const input = document.getElementById(inputId);
        const preview = document.getElementById(previewId);
        const container = input.closest('.upload-card');

        if (!input || !preview) return;

        input.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(event) {
                    preview.src = event.target.result;
                    preview.style.display = 'block';
                    preview.closest('.image-preview-wrapper').style.display = 'block';
                    container.classList.add('has-preview');
                };
                reader.readAsDataURL(file);
            }
        });

        // Handle drag and drop
        const dropZone = input.closest('.file-upload-container');
        
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, preventDefaults, false);
        });

        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }

        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, highlight, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, unhighlight, false);
        });

        function highlight(e) {
            dropZone.classList.add('drag-over');
        }

        function unhighlight(e) {
            dropZone.classList.remove('drag-over');
        }

        dropZone.addEventListener('drop', handleDrop, false);

        function handleDrop(e) {
            const dt = e.dataTransfer;
            const file = dt.files[0];
            input.files = dt.files;
            
            if (file) {
                const reader = new FileReader();
                reader.onload = function(event) {
                    preview.src = event.target.result;
                    preview.style.display = 'block';
                    preview.closest('.image-preview-wrapper').style.display = 'block';
                    container.classList.add('has-preview');
                };
                reader.readAsDataURL(file);
            }
        }
    }

    // Initialize image previews
    setupImagePreview('fullAnimalImage', 'fullAnimalPreview');
    setupImagePreview('diseaseImage', 'diseasePreview');

    // Initialize remove image buttons
    document.querySelectorAll('.remove-image').forEach(button => {
        button.addEventListener('click', function() {
            const targetId = this.dataset.target;
            const input = document.getElementById(targetId);
            const previewWrapper = this.closest('.image-preview-wrapper');
            const container = input.closest('.file-upload-container');
            
            input.value = '';
            previewWrapper.style.display = 'none';
            container.classList.remove('has-preview');
        });
    });

    // Update symptoms based on pet type
    function updateSymptoms(petType) {
        symptomsContainer.innerHTML = '';
        if (symptoms[petType]) {
            symptoms[petType].forEach(symptom => {
                const symptomItem = document.createElement('div');
                symptomItem.className = 'symptom-item';
                
                symptomItem.innerHTML = `
                    <input type="checkbox" id="${symptom.id}" name="symptoms" value="${symptom.label}">
                    <label for="${symptom.id}">
                        <i class="fas ${symptom.icon} mr-2"></i>
                        ${symptom.label}
                    </label>
                `;
                
                symptomsContainer.appendChild(symptomItem);

                // Add animation
                setTimeout(() => {
                    symptomItem.style.opacity = '1';
                    symptomItem.style.transform = 'translateY(0)';
                }, 50);
            });
        }
    }

    // Pet type change handler
    petTypeRadios.forEach(radio => {
        radio.addEventListener('change', () => {
            updateSymptoms(radio.value);
        });
    });

    // Form submission handler
    analysisForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Validate form
        const requiredFields = analysisForm.querySelectorAll('[required]');
        let isValid = true;
        
        requiredFields.forEach(field => {
            if (!field.value) {
                isValid = false;
                field.classList.add('is-invalid');
            } else {
                field.classList.remove('is-invalid');
            }
        });

        // Check if pet type is selected
        const petType = document.querySelector('input[name="petType"]:checked');
        if (!petType) {
            isValid = false;
            document.querySelector('.pet-type-buttons').classList.add('is-invalid');
        }

        // Check if at least one symptom is selected
        const selectedSymptoms = document.querySelectorAll('input[name="symptoms"]:checked');
        if (selectedSymptoms.length === 0) {
            isValid = false;
            const symptomsError = document.createElement('div');
            symptomsError.className = 'alert alert-danger mt-3';
            symptomsError.innerHTML = 'Please select at least one symptom';
            symptomsContainer.parentNode.insertBefore(symptomsError, symptomsContainer.nextSibling);
            
            setTimeout(() => {
                symptomsError.remove();
            }, 3000);
        }

        if (isValid) {
            // Show loading overlay
            if (loadingOverlay) {
                loadingOverlay.style.display = 'flex';
            }
            
            // Submit form
            this.submit();
        }
    });

    // Reset form handler
    analysisForm.addEventListener('reset', function() {
        // Clear image previews
        document.querySelectorAll('.image-preview-wrapper').forEach(wrapper => {
            wrapper.style.display = 'none';
        });

        // Clear upload success states
        document.querySelectorAll('.file-upload-container').forEach(container => {
            container.classList.remove('has-preview');
        });

        // Clear symptoms
        symptomsContainer.innerHTML = '';

        // Remove any error states
        document.querySelectorAll('.is-invalid').forEach(field => {
            field.classList.remove('is-invalid');
        });

        // Reset file inputs
        document.querySelectorAll('.file-input').forEach(input => {
            input.value = '';
        });
    });
});