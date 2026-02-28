/**
 * SPRS Map Explorer
 * Uses Leaflet + OpenStreetMap (free, no API key needed)
 * Features: markers, marker clustering, info panels, sidebar list, filters
 */
(function() {
    'use strict';

    var map;
    var markers = [];
    var markerCluster;
    var allProperties = [];

    // DOM elements
    var mapContainer = document.getElementById('mapContainer');
    var sidebar = document.getElementById('mapSidebar');
    var infoPanel = document.getElementById('mapInfoPanel');
    var panelContent = document.getElementById('panelContent');
    var filterForm = document.getElementById('mapFilterForm');
    var propertyList = document.getElementById('propertyList');
    var resultCount = document.getElementById('resultCount');
    var toggleSidebarBtn = document.getElementById('toggleSidebar');
    var closeSidebarBtn = document.getElementById('closeSidebar');
    var closePanelBtn = document.getElementById('closePanel');
    var resetFiltersBtn = document.getElementById('resetFilters');

    if (!mapContainer) return;

    // Custom marker icon
    var propertyIcon = L.divIcon({
        className: 'sprs-marker',
        html: '<div class="sprs-marker-pin"><i class="bi bi-house-door-fill"></i></div>',
        iconSize: [36, 36],
        iconAnchor: [18, 36],
        popupAnchor: [0, -36],
    });

    var activeIcon = L.divIcon({
        className: 'sprs-marker active',
        html: '<div class="sprs-marker-pin active"><i class="bi bi-house-door-fill"></i></div>',
        iconSize: [42, 42],
        iconAnchor: [21, 42],
        popupAnchor: [0, -42],
    });

    // Initialize Leaflet map centered on Kathmandu, Nepal
    function initMap() {
        map = L.map('mapContainer', {
            center: [27.7172, 85.3240],
            zoom: 12,
            zoomControl: true,
            scrollWheelZoom: true,
        });

        // OpenStreetMap tile layer (free, no key needed)
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            maxZoom: 19,
        }).addTo(map);

        // Marker cluster group
        markerCluster = L.markerClusterGroup({
            maxClusterRadius: 50,
            spiderfyOnMaxZoom: true,
            showCoverageOnHover: false,
            zoomToBoundsOnClick: true,
        });
        map.addLayer(markerCluster);

        // Load properties
        loadProperties();
    }

    // Load properties from API
    function loadProperties(filters) {
        var url = API_URL;
        var params = new URLSearchParams();

        if (filters) {
            Object.keys(filters).forEach(function(key) {
                if (filters[key]) params.append(key, filters[key]);
            });
        }

        if (params.toString()) {
            url += '?' + params.toString();
        }

        resultCount.textContent = 'Loading properties...';

        fetch(url)
            .then(function(r) { return r.json(); })
            .then(function(data) {
                var properties = Array.isArray(data) ? data : (data.results || []);
                allProperties = properties;
                clearMarkers();
                addMarkers(properties);
                updatePropertyList(properties);
            })
            .catch(function(err) {
                console.error('Failed to load properties:', err);
                resultCount.textContent = 'Error loading properties';
            });
    }

    // Add markers to map
    function addMarkers(properties) {
        var bounds = [];

        properties.forEach(function(prop) {
            if (!prop.latitude || !prop.longitude) return;

            var lat = parseFloat(prop.latitude);
            var lng = parseFloat(prop.longitude);
            if (isNaN(lat) || isNaN(lng)) return;

            var marker = L.marker([lat, lng], { icon: propertyIcon });
            marker.propertyData = prop;

            // Popup with basic info
            marker.bindPopup(
                '<div class="map-popup">' +
                '<strong>' + escapeHtml(prop.title) + '</strong><br>' +
                '<span class="text-muted small"><i class="bi bi-geo-alt"></i> ' + escapeHtml(prop.district) + '</span><br>' +
                '<span style="color:#DC143C;font-weight:700;">Rs. ' + Number(prop.price).toLocaleString() + '/mo</span>' +
                '</div>',
                { maxWidth: 250 }
            );

            marker.on('click', function() {
                showInfoPanel(prop);
                highlightPropertyInList(prop.id);
            });

            markers.push(marker);
            markerCluster.addLayer(marker);
            bounds.push([lat, lng]);
        });

        // Fit map to show all markers
        if (bounds.length > 0) {
            map.fitBounds(bounds, { padding: [50, 50], maxZoom: 14 });
        }
    }

    // Clear markers
    function clearMarkers() {
        markerCluster.clearLayers();
        markers = [];
    }

    // Show info panel for a property
    function showInfoPanel(prop) {
        var imgHtml = prop.primary_image
            ? '<img src="' + prop.primary_image + '" class="panel-property-image" alt="' + escapeHtml(prop.title) + '">'
            : '<div class="d-flex align-items-center justify-content-center" style="height:200px;background:#f0f0f0;border-radius:8px;"><i class="bi bi-image text-muted" style="font-size:3rem;"></i></div>';

        var ratingHtml = '';
        var rating = Math.round(prop.average_rating || 0);
        if (rating > 0) {
            ratingHtml = '<div class="panel-property-rating mb-2">';
            for (var i = 1; i <= 5; i++) {
                ratingHtml += i <= rating
                    ? '<i class="bi bi-star-fill text-warning"></i>'
                    : '<i class="bi bi-star text-warning"></i>';
            }
            ratingHtml += '</div>';
        }

        panelContent.innerHTML = imgHtml
            + '<div class="panel-property-content">'
            + '<span class="badge bg-primary mb-2">' + escapeHtml(prop.property_type_display || prop.property_type) + '</span>'
            + '<h5 class="panel-property-title">' + escapeHtml(prop.title) + '</h5>'
            + ratingHtml
            + '<div class="panel-property-price">Rs. ' + Number(prop.price).toLocaleString() + '<small class="text-muted fw-normal">/mo</small></div>'
            + '<div class="panel-property-meta">'
            + '<span><i class="bi bi-geo-alt me-1"></i>' + escapeHtml(prop.district) + '</span>'
            + (prop.num_rooms ? '<span><i class="bi bi-door-open me-1"></i>' + prop.num_rooms + ' Room(s)</span>' : '')
            + '</div>'
            + '<a href="/properties/' + prop.id + '/" class="btn btn-primary w-100 mt-3">'
            + '<i class="bi bi-eye me-1"></i>View Full Details</a>'
            + '</div>';

        infoPanel.classList.add('open');

        // Highlight the marker
        markers.forEach(function(m) {
            if (m.propertyData && m.propertyData.id === prop.id) {
                m.setIcon(activeIcon);
            } else {
                m.setIcon(propertyIcon);
            }
        });
    }

    // Update property list in sidebar
    function updatePropertyList(properties) {
        resultCount.textContent = properties.length + ' propert' + (properties.length === 1 ? 'y' : 'ies') + ' found';

        if (properties.length === 0) {
            propertyList.innerHTML = '<div class="p-4 text-center text-muted">'
                + '<i class="bi bi-house-x fs-3 d-block mb-2"></i>'
                + '<p class="mb-0">No properties found matching your filters</p></div>';
            return;
        }

        propertyList.innerHTML = properties.map(function(p) {
            var imgHtml = p.primary_image
                ? '<img src="' + p.primary_image + '" alt="' + escapeHtml(p.title) + '">'
                : '<div class="no-image"><i class="bi bi-image"></i></div>';

            var hasCoords = p.latitude && p.longitude;
            var coordsAttr = hasCoords
                ? ' data-lat="' + p.latitude + '" data-lng="' + p.longitude + '"'
                : '';

            return '<div class="map-property-item" data-id="' + p.id + '"' + coordsAttr + '>'
                + '<div class="d-flex gap-3">'
                + '<div class="map-property-thumb">' + imgHtml + '</div>'
                + '<div class="flex-grow-1">'
                + '<h6 class="mb-1 fw-bold small text-truncate">' + escapeHtml(p.title) + '</h6>'
                + '<p class="mb-1 text-muted small"><i class="bi bi-geo-alt"></i> ' + escapeHtml(p.district) + '</p>'
                + '<div class="d-flex justify-content-between align-items-center">'
                + '<span class="fw-bold small" style="color:#DC143C;">Rs. ' + Number(p.price).toLocaleString() + '/mo</span>'
                + '<a href="/properties/' + p.id + '/" class="btn btn-sm btn-outline-primary py-0 px-2">View</a>'
                + '</div></div></div></div>';
        }).join('');

        // Add click handlers to list items
        document.querySelectorAll('.map-property-item').forEach(function(item) {
            item.addEventListener('click', function(e) {
                if (e.target.tagName === 'A') return;
                var id = parseInt(this.dataset.id);
                var lat = parseFloat(this.dataset.lat);
                var lng = parseFloat(this.dataset.lng);

                var prop = allProperties.find(function(p) { return p.id === id; });
                if (prop) {
                    showInfoPanel(prop);
                    if (map && !isNaN(lat) && !isNaN(lng)) {
                        map.setView([lat, lng], 16, { animate: true });
                    }
                    highlightPropertyInList(id);
                }
            });
        });
    }

    function highlightPropertyInList(id) {
        document.querySelectorAll('.map-property-item').forEach(function(item) {
            item.classList.remove('active');
        });
        var active = document.querySelector('.map-property-item[data-id="' + id + '"]');
        if (active) {
            active.classList.add('active');
            active.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }

    // Filter form
    if (filterForm) {
        filterForm.addEventListener('submit', function(e) {
            e.preventDefault();
            var formData = new FormData(filterForm);
            var filters = {};
            formData.forEach(function(value, key) {
                if (value) filters[key] = value;
            });
            loadProperties(filters);
            // Close sidebar on mobile after applying filters
            if (window.innerWidth < 992) {
                sidebar.classList.remove('open');
            }
        });
    }

    // Reset filters
    if (resetFiltersBtn) {
        resetFiltersBtn.addEventListener('click', function() {
            filterForm.reset();
            loadProperties();
        });
    }

    // Close info panel
    if (closePanelBtn) {
        closePanelBtn.addEventListener('click', function() {
            infoPanel.classList.remove('open');
            // Reset marker icons
            markers.forEach(function(m) { m.setIcon(propertyIcon); });
        });
    }

    // Mobile sidebar toggle
    if (toggleSidebarBtn) {
        toggleSidebarBtn.addEventListener('click', function() {
            sidebar.classList.toggle('open');
        });
    }

    if (closeSidebarBtn) {
        closeSidebarBtn.addEventListener('click', function() {
            sidebar.classList.remove('open');
        });
    }

    function escapeHtml(text) {
        if (!text) return '';
        var div = document.createElement('div');
        div.appendChild(document.createTextNode(text));
        return div.innerHTML;
    }

    // Initialize map when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initMap);
    } else {
        initMap();
    }
})();
