// result.js
document.addEventListener('DOMContentLoaded', () => {
    initMap();
    hideLoadingOverlay();
});

let map;
let markers = [];

function initMap() {
    if (!navigator.geolocation) {
        showLocationError();
        return;
    }

    navigator.geolocation.getCurrentPosition(
        position => {
            const { latitude, longitude } = position.coords;
            createMap([latitude, longitude]);
            generateVetClinics([latitude, longitude]);
        },
        error => {
            console.error('Geolocation error:', error);
            createMap([28.6139, 77.2090]); // Default location (e.g., New Delhi)
        }
    );
}

function createMap(center) {
    map = L.map('vetMap').setView(center, 14);
    
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);

    addUserMarker(center);
}

function addUserMarker(location) {
    const userIcon = L.divIcon({
        className: 'user-marker',
        html: '<i class="fas fa-map-marker-alt pulse"></i>',
        iconSize: [30, 30],
        iconAnchor: [15, 30]
    });

    L.marker(location, { icon: userIcon })
        .addTo(map)
        .bindPopup('Your Location')
        .openPopup();
}

function generateVetClinics(userLocation) {
    const vetClinics = [
        'PawCare Veterinary Hospital',
        'Happy Tails Pet Clinic',
        'City Pet Care Center',
        'Animal Wellness Hospital',
        'Pet Health Specialists',
        'FurFriends Clinic',
        'Modern Pet Hospital'
    ];

    clearExistingMarkers();
    const clinicList = document.getElementById('clinic-list');
    clinicList.innerHTML = '';

    for (let i = 0; i < 5; i++) {
        const clinic = {
            name: vetClinics[Math.floor(Math.random() * vetClinics.length)],
            location: generateNearbyLocation(userLocation),
            rating: (3.5 + Math.random() * 1.5).toFixed(1),
            phone: generatePhoneNumber(),
            timings: generateTimings()
        };

        clinic.distance = calculateDistance(userLocation, clinic.location);
        addClinicMarker(clinic);
        addClinicToList(clinic);
    }
}

function generateNearbyLocation(center) {
    const radius = 0.02; // Approximately 2km
    const angle = Math.random() * Math.PI * 2;
    const r = Math.sqrt(Math.random()) * radius;
    
    return [
        center[0] + r * Math.cos(angle),
        center[1] + r * Math.sin(angle)
    ];
}

function addClinicMarker(clinic) {
    const clinicIcon = L.divIcon({
        className: 'clinic-marker',
        html: '<i class="fas fa-hospital"></i>',
        iconSize: [40, 40],
        iconAnchor: [20, 40]
    });

    const marker = L.marker(clinic.location, { icon: clinicIcon })
        .addTo(map)
        .bindPopup(`
            <div class="clinic-popup">
                <h4>${clinic.name}</h4>
                <div class="clinic-rating">
                    <i class="fas fa-star"></i> ${clinic.rating}/5.0
                </div>
                <p><i class="fas fa-phone"></i> ${clinic.phone}</p>
                <p><i class="fas fa-clock"></i> ${clinic.timings}</p>
                <p><i class="fas fa-route"></i> ${clinic.distance.toFixed(1)}km away</p>
            </div>
        `);

    markers.push(marker);
}

function addClinicToList(clinic) {
    const clinicList = document.getElementById('clinic-list');
    const card = document.createElement('div');
    card.className = 'clinic-card';
    
    card.innerHTML = `
        <div class="clinic-info">
            <h5>${clinic.name}</h5>
            <div class="clinic-details">
                <span class="rating">
                    <i class="fas fa-star"></i> ${clinic.rating}
                </span>
                <span class="distance">
                    <i class="fas fa-route"></i> ${clinic.distance.toFixed(1)}km
                </span>
            </div>
            <div class="clinic-contact">
                <span><i class="fas fa-phone"></i> ${clinic.phone}</span>
                <span><i class="fas fa-clock"></i> ${clinic.timings}</span>
            </div>
        </div>
        <button class="btn-view btn btn-primary btn-sm mt-2" onclick="focusClinic([${clinic.location}])">
            <i class="fas fa-map-marker-alt"></i> View
        </button>
    `;

    clinicList.appendChild(card);
}

function focusClinic(location) {
    map.flyTo(location, 16, {
        duration: 1.5,
        easeLinearity: 0.25
    });
}

function calculateDistance(point1, point2) {
    const R = 6371; // Earth's radius in km
    const dLat = toRad(point2[0] - point1[0]);
    const dLon = toRad(point2[1] - point1[1]);
    const lat1 = toRad(point1[0]);
    const lat2 = toRad(point2[0]);

    const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
        Math.sin(dLon/2) * Math.sin(dLon/2) * Math.cos(lat1) * Math.cos(lat2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    return R * c;
}

function generatePhoneNumber() {
    return `+91 ${Math.floor(Math.random() * 9000000000 + 1000000000)}`;
}

function generateTimings() {
    return "9:00 AM - 8:00 PM";
}

function clearExistingMarkers() {
    markers.forEach(marker => marker.remove());
    markers = [];
}

function hideLoadingOverlay() {
    const loadingOverlay = document.querySelector('.loading-overlay');
    if (loadingOverlay) {
        loadingOverlay.style.display = 'none';
    }
}

function showLocationError() {
    const mapContainer = document.getElementById('vetMap');
    mapContainer.innerHTML = `
        <div class="location-error">
            <i class="fas fa-exclamation-circle"></i>
            <p>Unable to access location. Please enable location services.</p>
        </div>
    `;
}

function toRad(degrees) {
    return degrees * Math.PI / 180;
}

// Handle report submission
// static/js/result.js

/**
 * Function to handle reporting an incorrect prediction.
 * Prompts the user to enter the correct label and sends it to the server.
 * @param {string} predictionId - The ID of the prediction to report.
 */
function reportPrediction(predictionId) {
    // Prompt the user to enter the correct label
    const correctLabel = prompt("Please enter the correct disease label:");

    // If the user cancels the prompt or enters nothing, do nothing
    if (correctLabel === null || correctLabel.trim() === "") {
        alert("Feedback canceled or no input provided.");
        return;
    }

    // Optional: Validate the correct label against known disease classes
    // You can implement additional validation here if needed

    // Prepare the data to send
    const data = {
        prediction_id: predictionId,
        correct_label: correctLabel.trim().toLowerCase()
    };

    // Send the POST request to the /feedback route
    fetch('/feedback', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        const feedbackSuccess = document.getElementById('feedbackSuccess');
        if (data.status === 'success') {
            feedbackSuccess.innerHTML = `
                <div class="alert alert-success">
                    ${data.message}
                </div>
            `;
        } else {
            feedbackSuccess.innerHTML = `
                <div class="alert alert-danger">
                    ${data.message}
                </div>
            `;
        }
    })
    .catch((error) => {
        console.error('Error:', error);
        const feedbackSuccess = document.getElementById('feedbackSuccess');
        feedbackSuccess.innerHTML = `
            <div class="alert alert-danger">
                An error occurred while submitting your feedback.
            </div>
        `;
    });
}

