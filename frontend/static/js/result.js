// result.js

document.addEventListener('DOMContentLoaded', () => {
    initMap();
    hideLoadingOverlay();
});

let map;
let markers = [];
// Keep track of the user’s marker so we can remove it on relocate
let userMarker = null;

/**
 * Initialize the map by getting the user's location (if available),
 * otherwise fall back to a default location.
 */
function initMap() {
    if (!navigator.geolocation) {
        showLocationError();
        return;
    }

    navigator.geolocation.getCurrentPosition(
        (position) => {
            const { latitude, longitude } = position.coords;
            createMap([latitude, longitude]);
            generateVetClinics([latitude, longitude]);
        },
        (error) => {
            console.error('Geolocation error:', error);
            // Fallback to a default location, e.g., New Delhi
            createMap([28.6139, 77.2090]);
            generateVetClinics([28.6139, 77.2090]);
        }
    );
}

/**
 * Create a Leaflet map at the given center coordinate.
 * Also sets the tile layer, the user marker, and the locate button.
 */
function createMap(center) {
    map = L.map('vetMap').setView(center, 14);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);

    // Add the initial user marker
    addUserMarker(center);

    // Add the custom "Relocate to Current Position" button
    addLocateControl();
}

/**
 * Place or update the user's location marker.
 */
function addUserMarker(location) {
    // If there's an existing userMarker, remove it first
    if (userMarker) {
        userMarker.remove();
    }

    const userIcon = L.divIcon({
        className: 'user-marker',
        html: '<i class="fas fa-map-marker-alt pulse"></i>',
        iconSize: [30, 30],
        iconAnchor: [15, 30]
    });

    userMarker = L.marker(location, { icon: userIcon })
        .addTo(map)
        .bindPopup('Your Location')
        .openPopup();
}

/**
 * Add a Leaflet control in the top-right corner that, when clicked,
 * attempts to relocate the user’s position.
 */
function addLocateControl() {
    const locateControl = L.control({ position: 'topright' });

    locateControl.onAdd = function() {
        // Create a simple button
        const container = L.DomUtil.create(
            'div', 
            'leaflet-bar leaflet-control leaflet-control-custom'
        );
        container.innerHTML = '<i class="fas fa-location-arrow" style="padding: 8px;"></i>';
        container.style.cursor = 'pointer';
        container.title = 'Relocate to Current Position';

        // When clicked, call relocateToCurrentPosition()
        container.onclick = function() {
            relocateToCurrentPosition();
        };

        return container;
    };

    locateControl.addTo(map);
}

/**
 * Get the user’s location again and re-center the map, updating the user marker.
 */
function relocateToCurrentPosition() {
    if (!navigator.geolocation) {
        alert("Geolocation is not supported by your browser.");
        return;
    }

    navigator.geolocation.getCurrentPosition(
        (position) => {
            const { latitude, longitude } = position.coords;
            map.setView([latitude, longitude], 14);
            addUserMarker([latitude, longitude]);
        },
        (error) => {
            console.error('Relocation geolocation error:', error);
            alert("Unable to retrieve your location again.");
        }
    );
}

/**
 * For demo purposes, randomly generate veterinary clinics
 * near the provided user location.
 */
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
    if (clinicList) {
        clinicList.innerHTML = '';
    }

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

/**
 * Generate a random location near a given center (approx 2km radius).
 */
function generateNearbyLocation(center) {
    const radius = 0.02; // ~2km
    const angle = Math.random() * Math.PI * 2;
    const r = Math.sqrt(Math.random()) * radius;
    
    return [
        center[0] + r * Math.cos(angle),
        center[1] + r * Math.sin(angle)
    ];
}

/**
 * Place a marker on the map for a vet clinic.
 */
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
                <p><i class="fas fa-route"></i> ${clinic.distance.toFixed(1)} km away</p>
            </div>
        `);

    markers.push(marker);
}

/**
 * Create a "card" in the clinic-list section to display clinic info.
 */
function addClinicToList(clinic) {
    const clinicList = document.getElementById('clinic-list');
    if (!clinicList) return;

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
                    <i class="fas fa-route"></i> ${clinic.distance.toFixed(1)} km
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

/**
 * Animate the map to fly to a specific clinic location.
 */
function focusClinic(location) {
    map.flyTo(location, 16, {
        duration: 1.5,
        easeLinearity: 0.25
    });
}

/**
 * Calculate distance (in km) between two [lat, lng] points using Haversine formula.
 */
function calculateDistance(point1, point2) {
    const R = 6371; // Earth's radius in km
    const dLat = toRad(point2[0] - point1[0]);
    const dLon = toRad(point2[1] - point1[1]);
    const lat1 = toRad(point1[0]);
    const lat2 = toRad(point2[0]);

    const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
              Math.sin(dLon/2) * Math.sin(dLon/2) *
              Math.cos(lat1) * Math.cos(lat2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    return R * c;
}

/**
 * Generate a random phone number (demo only).
 */
function generatePhoneNumber() {
    return `+91 ${Math.floor(Math.random() * 9000000000 + 1000000000)}`;
}

/**
 * Generate sample clinic timings (demo only).
 */
function generateTimings() {
    return "9:00 AM - 8:00 PM";
}

/**
 * Remove all existing markers from the map and clear from array.
 */
function clearExistingMarkers() {
    markers.forEach((marker) => marker.remove());
    markers = [];
}

/**
 * Optionally hide a loading overlay if you have one in the DOM.
 */
function hideLoadingOverlay() {
    const loadingOverlay = document.querySelector('.loading-overlay');
    if (loadingOverlay) {
        loadingOverlay.style.display = 'none';
    }
}

/**
 * Show an error if geolocation is not supported or user denied it.
 */
function showLocationError() {
    const mapContainer = document.getElementById('vetMap');
    mapContainer.innerHTML = `
        <div class="location-error">
            <i class="fas fa-exclamation-circle"></i>
            <p>Unable to access location. Please enable location services.</p>
        </div>
    `;
}

/**
 * Helper function: Convert degrees to radians.
 */
function toRad(deg) {
    return deg * Math.PI / 180;
}

/**
 * Example function for handling feedback about incorrect prediction.
 * (If you use a "Report" button that calls reportPrediction())
 */
function reportPrediction(predictionId) {
    const correctLabel = prompt("Please enter the correct disease label:");

    if (correctLabel === null || correctLabel.trim() === "") {
        alert("Feedback canceled or no input provided.");
        return;
    }

    const data = {
        prediction_id: predictionId,
        correct_label: correctLabel.trim().toLowerCase()
    };

    fetch('/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    })
    .then((response) => response.json())
    .then((result) => {
        const feedbackSuccess = document.getElementById('feedbackSuccess');
        if (result.status === 'success') {
            feedbackSuccess.innerHTML = `
                <div class="alert alert-success">
                    ${result.message}
                </div>
            `;
        } else {
            feedbackSuccess.innerHTML = `
                <div class="alert alert-danger">
                    ${result.message}
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
