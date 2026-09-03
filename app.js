/**
 * FLOODX - APPLICATION CONTROLLER & MATHEMATICALLY CONSISTENT RISK ENGINE
 */

document.addEventListener('DOMContentLoaded', () => {
    // 01. STATE MANAGEMENT
    const state = {
        activeView: 'command-center',
        opMode: 'OPERATIONS', // 'OPERATIONS' (Mode A) or 'HISTORICAL' (Mode B)
        selectedRegionId: 'kedarnath',
        selectedLocationId: 'loc_riverside',
        selectedScenario: 'STORM_INTENSIFYING',
        selectedHistoricalEvent: 'kedarnath_2013',
        mapStyle: 'satellite',
        currentTimeStepIdx: 0, // 0: NOW, 1: +15m, 2: +30m, 3: +60m, 4: +120m
        sensor8Degraded: false,
        roadAFailed: false,
        demoInterval: null,

        layers: {
            zones: true,
            population: true,
            vulnerability: false,
            roads: true,
            sensors: true,
            shelters: true,
            terrain: true
        },

        mainMap: null,
        routingMap: null,
        tileLayer: null,
        tileLayerRef: null,
        routingTileLayer: null,
        
        mapMarkers: {},
        mapZones: {},
        mapPopMarkers: {},
        mapVulnMarkers: {},
        mapRoadPolys: {},
        mapSensorMarkers: {},
        mapShelterMarkers: {},
        nationalStateMarkers: [],
        nationalRiverPolys: []
    };

    // 02. MATHEMATICAL RISK ENGINE COMPUTATION
    function computeRiskIndex(hazard, exposure, vulnerability) {
        // Risk Index = (Hazard × 0.45) + (Exposure × 0.35) + (Vulnerability × 0.20)
        const score = (hazard * 0.45) + (exposure * 0.35) + (vulnerability * 0.20);
        return Math.min(1.0, Math.max(0.0, score));
    }

    function getActionState(score) {
        if (score < 0.40) return { label: 'MONITOR', badgeClass: 'badge-green', color: '#10b981' };
        if (score < 0.60) return { label: 'PREPARE', badgeClass: 'badge-yellow', color: '#eab308' };
        if (score < 0.80) return { label: 'EVACUATION PRE-ALERT', badgeClass: 'badge-orange', color: '#f97316' };
        return { label: 'EVACUATE NOW', badgeClass: 'badge-red', color: '#ef4444' };
    }

    // 03. INITIALIZATION
    initNavigation();
    initMaps();
    renderAllViews();
    initEventListeners();
    initRiverPropagationAnimation();
    startClock();

    // 04. NAVIGATION SYSTEM
    function initNavigation() {
        const navItems = document.querySelectorAll('.side-nav .nav-item[data-view]');
        navItems.forEach(item => {
            item.addEventListener('click', () => {
                const targetView = item.getAttribute('data-view');
                switchView(targetView);
            });
        });
    }

    function switchView(viewId) {
        state.activeView = viewId;
        
        document.querySelectorAll('.side-nav .nav-item').forEach(btn => {
            if (btn.getAttribute('data-view') === viewId) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });

        document.querySelectorAll('.app-view').forEach(view => {
            if (view.id === `view-${viewId}`) {
                view.classList.add('active');
            } else {
                view.classList.remove('active');
            }
        });

        if (viewId === 'command-center' && state.mainMap) {
            setTimeout(() => state.mainMap.invalidateSize(), 150);
        } else if (viewId === 'evacuation-view' && state.routingMap) {
            setTimeout(() => {
                state.routingMap.invalidateSize();
                renderRoutingMap();
            }, 150);
        } else if (viewId === 'forecast-view') {
            renderForecastCanvas();
        }
    }

    // 05. MAP INITIALIZATION
    function initMaps() {
        const mainMapElem = document.getElementById('main-map');
        if (mainMapElem) {
            state.mainMap = L.map('main-map', {
                center: [30.7380, 79.0650],
                zoom: 13,
                zoomControl: false,
                attributionControl: true
            });

            applyMapStyle('satellite');
            L.control.zoom({ position: 'bottomright' }).addTo(state.mainMap);
            renderMainMapElements();
        }

        const routingMapElem = document.getElementById('routing-map');
        if (routingMapElem) {
            state.routingMap = L.map('routing-map', {
                center: [30.7380, 79.0600],
                zoom: 13,
                zoomControl: false
            });

            state.routingTileLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
                maxZoom: 18,
                attribution: '&copy; Esri World Imagery'
            }).addTo(state.routingMap);
        }
    }

    function applyMapStyle(styleKey) {
        state.mapStyle = styleKey;
        if (!state.mainMap) return;

        if (state.tileLayer) state.mainMap.removeLayer(state.tileLayer);
        if (state.tileLayerRef) state.mainMap.removeLayer(state.tileLayerRef);

        if (styleKey === 'satellite') {
            state.tileLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
                maxZoom: 18,
                attribution: '&copy; Esri, Maxar, Earthstar Geographics'
            }).addTo(state.mainMap);

            state.tileLayerRef = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Transportation/MapServer/tile/{z}/{y}/{x}', {
                maxZoom: 18,
                opacity: 0.6
            }).addTo(state.mainMap);
        } else if (styleKey === 'osm') {
            state.tileLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                maxZoom: 18,
                attribution: '&copy; OpenStreetMap contributors'
            }).addTo(state.mainMap);
        } else {
            state.tileLayer = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
                maxZoom: 18,
                attribution: '&copy; CartoDB &copy; OpenStreetMap'
            }).addTo(state.mainMap);
        }
    }

    // 06. MAIN MAP RENDERER (DECLUTTERED & HIERARCHICAL LABELS)
    function renderMainMapElements() {
        if (!state.mainMap) return;

        const clearMapGroup = (group) => {
            Object.values(group).forEach(l => state.mainMap.removeLayer(l));
        };

        clearMapGroup(state.mapMarkers);
        clearMapGroup(state.mapZones);
        clearMapGroup(state.mapPopMarkers);
        clearMapGroup(state.mapVulnMarkers);
        clearMapGroup(state.mapRoadPolys);
        clearMapGroup(state.mapSensorMarkers);
        clearMapGroup(state.mapShelterMarkers);
        state.nationalStateMarkers.forEach(m => state.mainMap.removeLayer(m));
        state.nationalRiverPolys.forEach(p => state.mainMap.removeLayer(p));

        state.mapMarkers = {};
        state.mapZones = {};
        state.mapPopMarkers = {};
        state.mapVulnMarkers = {};
        state.mapRoadPolys = {};
        state.mapSensorMarkers = {};
        state.mapShelterMarkers = {};
        state.nationalStateMarkers = [];
        state.nationalRiverPolys = [];

        if (state.selectedRegionId === 'india_all') {
            document.getElementById('map-region-footer-label').textContent = '🇮🇳 FULL INDIA NATIONAL DISASTER RISK OVERVIEW • Indian Subcontinent Basins';

            window.FLOODX_DATA.national_rivers.forEach(r => {
                const poly = L.polyline(r.coords, {
                    color: '#38bdf8',
                    weight: 3.5,
                    opacity: 0.8,
                    dashArray: '6, 6'
                }).addTo(state.mainMap).bindTooltip(`<strong>${r.name}</strong> (National Flow Corridor)`, { permanent: false });
                state.nationalRiverPolys.push(poly);
            });

            window.FLOODX_DATA.indian_states.forEach(st => {
                const sMarker = L.marker(st.center, {
                    icon: L.divIcon({
                        className: 'national-state-pin',
                        html: `
                            <div style="
                                background: rgba(7, 9, 14, 0.92);
                                border: 2px solid ${st.color};
                                color: #fff;
                                font-size: 11px;
                                font-weight: 800;
                                font-family: monospace;
                                padding: 4px 8px;
                                border-radius: 4px;
                                box-shadow: 0 0 14px ${st.color};
                                text-align: center;
                                cursor: pointer;
                                white-space: nowrap;
                            ">
                                🇮🇳 ${st.name}<br>
                                <span style="color: ${st.color}; font-size: 10px;">${st.risk}</span>
                            </div>
                        `,
                        iconSize: [140, 36],
                        iconAnchor: [70, 18]
                    })
                }).addTo(state.mainMap);

                sMarker.on('click', () => {
                    if (st.name.includes('UTTARAKHAND')) selectRegion('kedarnath');
                    else if (st.name.includes('KERALA')) selectRegion('wayanad');
                    else if (st.name.includes('HIMACHAL')) selectRegion('mandi');
                    else if (st.name.includes('ASSAM')) selectRegion('silchar');
                });
                state.nationalStateMarkers.push(sMarker);
            });

            return;
        }

        const regInfo = window.FLOODX_DATA.regions[state.selectedRegionId] || window.FLOODX_DATA.regions.kedarnath;
        document.getElementById('map-region-footer-label').textContent = `DEMO REPLAY • ${regInfo.river} • ${regInfo.district}, ${regInfo.state}, India`;

        const riverCoords = [
            [30.7550, 79.0520],
            [30.7480, 79.0580],
            [30.7410, 79.0630],
            [30.7345, 79.0669],
            [30.7250, 79.0720],
            [30.7150, 79.0800]
        ];
        L.polyline(riverCoords, {
            color: '#38bdf8',
            weight: 4.5,
            opacity: 0.9,
            dashArray: '8, 6'
        }).addTo(state.mainMap).bindTooltip(`<strong>${regInfo.river}</strong> (Flow Axis)`, { permanent: false });

        window.FLOODX_DATA.locations.forEach(loc => {
            const stepData = loc.timesteps[state.currentTimeStepIdx] || loc.timesteps[0];
            const currentScore = computeRiskIndex(stepData.hazard, stepData.exposure, stepData.vuln);
            const actionState = getActionState(currentScore);
            const isCrit = currentScore >= 0.8;

            if (state.layers.zones) {
                const radiusMeters = 500 + (currentScore * 350);
                const zoneCircle = L.circle([loc.lat, loc.lng], {
                    radius: radiusMeters,
                    color: actionState.color,
                    fillColor: actionState.color,
                    fillOpacity: isCrit ? 0.32 : 0.16,
                    weight: isCrit ? 3 : 1.5,
                    className: isCrit ? 'crit-pulse predicted-risk-zone' : 'predicted-risk-zone'
                }).addTo(state.mainMap);

                zoneCircle.bindTooltip(`<strong>${loc.name}</strong><br>Calculated Risk: ${currentScore.toFixed(2)} (${actionState.label})`, { permanent: false });
                zoneCircle.on('click', () => openLocationDrawer(loc.id));
                state.mapZones[loc.id] = zoneCircle;
            }

            // CRITICAL LOCATION LABEL (PRIORITY #1)
            const customIcon = L.divIcon({
                className: 'custom-map-pin',
                html: `
                    <div style="
                        background: ${actionState.color};
                        color: #000;
                        font-weight: 800;
                        font-family: monospace;
                        font-size: 11px;
                        padding: 3px 8px;
                        border-radius: 4px;
                        box-shadow: 0 0 14px ${actionState.color};
                        border: 1px solid #fff;
                        white-space: nowrap;
                        cursor: pointer;
                    ">
                        ${isCrit ? 'CRITICAL ' : ''}${loc.name} • ${currentScore.toFixed(2)}
                    </div>
                `,
                iconSize: [140, 24],
                iconAnchor: [70, 12]
            });

            const marker = L.marker([loc.lat, loc.lng], { icon: customIcon }).addTo(state.mainMap);
            marker.on('click', () => openLocationDrawer(loc.id));
            state.mapMarkers[loc.id] = marker;

            // POPULATION PIN (PRIORITY #3 — SMART OFFSET TO AVOID COLLISION)
            if (state.layers.population) {
                const popIcon = L.divIcon({
                    className: 'pop-map-pin',
                    html: `
                        <div style="
                            background: rgba(14, 19, 31, 0.95);
                            color: ${actionState.color};
                            border: 1px solid ${actionState.color};
                            font-size: 10px;
                            font-weight: 800;
                            font-family: monospace;
                            padding: 2px 6px;
                            border-radius: 10px;
                            white-space: nowrap;
                            box-shadow: 0 2px 8px rgba(0,0,0,0.6);
                        ">
                            👥 ${stepData.people.toLocaleString()} EXPOSED
                        </div>
                    `,
                    iconSize: [120, 20],
                    iconAnchor: [60, -18] // Offset downward
                });
                const popMarker = L.marker([loc.lat, loc.lng], { icon: popIcon }).addTo(state.mainMap);
                popMarker.on('click', () => openLocationDrawer(loc.id));
                state.mapPopMarkers[loc.id] = popMarker;
            }
        });

        if (state.layers.roads) {
            window.FLOODX_DATA.roads.forEach(road => {
                const isRoadAFailed = (road.id === 'road_a' && state.roadAFailed);
                const rColor = isRoadAFailed ? '#ef4444' : road.current_risk > 0.5 ? '#f97316' : '#10b981';

                const roadPoly = L.polyline(road.coords, {
                    color: rColor,
                    weight: isRoadAFailed ? 5 : 4,
                    opacity: 0.85,
                    dashArray: isRoadAFailed ? '4, 4' : null
                }).addTo(state.mainMap);

                roadPoly.bindTooltip(`
                    <strong>${road.name}</strong><br>
                    Current Risk: ${isRoadAFailed ? '0.86' : road.current_risk}<br>
                    Status: ${isRoadAFailed ? '⚠ BLOCKED / UNSAFE' : road.status}
                `, { permanent: false });

                roadPoly.on('click', () => switchView('evacuation-view'));
                state.mapRoadPolys[road.id] = roadPoly;
            });
        }

        if (state.layers.sensors) {
            window.FLOODX_DATA.sensors.forEach(s => {
                const isDegraded = (s.id === 's08' && state.sensor8Degraded);
                const sColor = isDegraded ? '#eab308' : '#10b981';
                const sIcon = L.divIcon({
                    className: 'sensor-map-pin',
                    html: `
                        <div style="
                            background: rgba(7, 9, 14, 0.9);
                            border: 1px solid ${sColor};
                            color: ${sColor};
                            font-size: 10px;
                            padding: 2px 5px;
                            border-radius: 3px;
                            font-weight: 700;
                            font-family: monospace;
                            cursor: pointer;
                        ">
                            📡 ${s.name.split(' ')[0]} ${isDegraded ? '⚠ DEGRADED' : '● OK'}
                        </div>
                    `,
                    iconSize: [110, 20],
                    iconAnchor: [55, 25]
                });
                const sMarker = L.marker([s.lat, s.lng], { icon: sIcon }).addTo(state.mainMap);
                sMarker.on('click', () => switchView('system-health-view'));
                state.mapSensorMarkers[s.id] = sMarker;
            });
        }

        if (state.layers.shelters) {
            window.FLOODX_DATA.shelters.forEach(shelter => {
                const shelterIcon = L.divIcon({
                    className: 'shelter-map-pin',
                    html: `
                        <div style="
                            background: #0284c7;
                            color: #fff;
                            font-size: 10px;
                            font-weight: 800;
                            padding: 3px 6px;
                            border-radius: 4px;
                            border: 1px solid #38bdf8;
                            box-shadow: 0 0 10px rgba(2,132,199,0.6);
                            cursor: pointer;
                        ">
                            🏰 ${shelter.name.split(' ')[0]} ${shelter.name.split(' ')[1]}
                        </div>
                    `,
                    iconSize: [120, 22],
                    iconAnchor: [60, -32]
                });
                const shelterMarker = L.marker([shelter.lat, shelter.lng], { icon: shelterIcon }).addTo(state.mainMap);
                shelterMarker.on('click', () => switchView('evacuation-view'));
                state.mapShelterMarkers[shelter.id] = shelterMarker;
            });
        }
    }

    function selectRegion(regionId) {
        state.selectedRegionId = regionId;
        const reg = window.FLOODX_DATA.regions[regionId] || window.FLOODX_DATA.regions.kedarnath;
        document.getElementById('region-select').value = regionId;

        if (state.mainMap) {
            state.mainMap.flyTo(reg.center, reg.zoom, { duration: 1.5 });
        }

        renderMainMapElements();
        renderAllViews();
        addIncidentLog('INFO', 'GEOSPATIAL REGION', `Switched map focal region to: ${reg.name}`);
    }

    // 07. ANIMATION LOOP
    function initRiverPropagationAnimation() {
        if (!state.mainMap) return;

        const riverCoords = [
            [30.7550, 79.0520],
            [30.7480, 79.0580],
            [30.7410, 79.0630],
            [30.7345, 79.0669],
            [30.7250, 79.0720],
            [30.7150, 79.0800]
        ];

        let progress = 0;
        const particleMarker = L.circleMarker(riverCoords[0], {
            radius: 5,
            color: '#38bdf8',
            fillColor: '#38bdf8',
            fillOpacity: 1
        }).addTo(state.mainMap);

        setInterval(() => {
            if (state.selectedRegionId === 'india_all') return;
            progress = (progress + 0.05) % 1;
            const idx = Math.floor(progress * (riverCoords.length - 1));
            const nextIdx = Math.min(idx + 1, riverCoords.length - 1);
            const ratio = (progress * (riverCoords.length - 1)) - idx;

            const lat = riverCoords[idx][0] + ratio * (riverCoords[nextIdx][0] - riverCoords[idx][0]);
            const lng = riverCoords[idx][1] + ratio * (riverCoords[nextIdx][1] - riverCoords[idx][1]);

            particleMarker.setLatLng([lat, lng]);
        }, 100);
    }

    // 08. TIME SLIDER CONTROLLER
    function updateTimeSlider(stepIdx) {
        state.currentTimeStepIdx = stepIdx;
        const stepNames = ['CURRENT STATE (NOW)', '+15 MIN FORECAST', '+30 MIN FORECAST', '+60 MIN FORECAST', '+120 MIN FORECAST'];
        document.getElementById('time-slider-val-label').textContent = stepNames[stepIdx];

        document.querySelectorAll('.slider-ticks .tick').forEach(t => {
            if (parseInt(t.getAttribute('data-step')) === stepIdx) {
                t.classList.add('active');
            } else {
                t.classList.remove('active');
            }
        });

        renderMainMapElements();
        renderAllViews();
        openLocationDrawer(state.selectedLocationId);
    }

    // 09. LOCATION INTELLIGENCE DRAWER HANDLER (MATHEMATICALLY EXACT)
    function openLocationDrawer(locationId) {
        state.selectedLocationId = locationId;
        const loc = window.FLOODX_DATA.locations.find(l => l.id === locationId);
        if (!loc) return;

        const stepData = loc.timesteps[state.currentTimeStepIdx] || loc.timesteps[0];
        
        // MATHEMATICAL RISK FORMULA CALCULATION
        const hazardVal = stepData.hazard;
        const exposureVal = stepData.exposure;
        const vulnVal = stepData.vuln;

        const computedRisk = computeRiskIndex(hazardVal, exposureVal, vulnVal);
        const actionState = getActionState(computedRisk);

        document.getElementById('drawer-location-name').textContent = loc.name;
        document.getElementById('drawer-location-region').textContent = loc.region;
        document.getElementById('drawer-risk-num').textContent = computedRisk.toFixed(2);
        document.getElementById('drawer-risk-change').textContent = loc.risk_change;
        
        const badgeElem = document.getElementById('drawer-risk-badge');
        badgeElem.textContent = actionState.label;
        badgeElem.className = `badge ${actionState.badgeClass} badge-lg`;

        const warningWindow = stepData.time_to_crit;
        const evacEta = state.roadAFailed ? 21 : stepData.evac_eta;
        const actionGap = warningWindow - evacEta;

        document.getElementById('drawer-time-crit').textContent = `${warningWindow} MIN`;

        // DYNAMIC SENSOR FAILURE CONFIDENCE DROP (72% DQ / 63% CONFIDENCE)
        const confVal = state.sensor8Degraded ? 63 : loc.confidence;
        const dqVal = state.sensor8Degraded ? 72 : loc.data_quality_score;

        document.getElementById('drawer-conf-fill').style.width = `${confVal}%`;
        document.getElementById('drawer-conf-val').textContent = `${confVal}% (${confVal > 70 ? 'HIGH' : 'REDUCED'})`;
        document.getElementById('drawer-dq-fill').style.width = `${dqVal}%`;
        document.getElementById('drawer-dq-val').textContent = `${dqVal}% (${dqVal > 80 ? 'GOOD' : 'NOISY'})`;

        // FORMULA WEIGHT CARDS
        document.getElementById('drawer-hazard').innerHTML = `${hazardVal.toFixed(2)}<br><small style="color:#64748b;">WT 45%</small>`;
        document.getElementById('drawer-exposure').innerHTML = `${exposureVal.toFixed(2)}<br><small style="color:#64748b;">WT 35%</small>`;
        document.getElementById('drawer-vulnerability').innerHTML = `${vulnVal.toFixed(2)}<br><small style="color:#64748b;">WT 20%</small>`;
        document.getElementById('drawer-final-risk-txt').textContent = `${computedRisk.toFixed(2)} (${actionState.label})`;

        document.getElementById('drawer-env-rain').textContent = `${stepData.rain} mm/hr`;
        document.getElementById('drawer-env-river').innerHTML = `${stepData.river} m <small>(${loc.river_rise_rate} ↑)</small>`;
        document.getElementById('drawer-env-slope').textContent = `${loc.slope_deg}° Steep Runoff`;
        document.getElementById('drawer-env-soil').textContent = `${loc.soil_saturation}% Saturated`;

        document.getElementById('bar-rain').style.width = `${Math.min(100, stepData.rain * 1.5)}%`;
        document.getElementById('bar-river').style.width = `${Math.min(100, stepData.river * 30)}%`;
        document.getElementById('bar-soil').style.width = `${loc.soil_saturation}%`;

        const factorsContainer = document.getElementById('drawer-factors');
        factorsContainer.innerHTML = loc.top_factors.map(f => `
            <div class="factor-item" style="margin-bottom: 6px;">
                <div class="factor-name" style="display:flex; justify-content:space-between; font-size:0.75rem; font-weight:700;">
                    <span>${f.name}</span>
                    <span class="text-accent">${f.weight}</span>
                </div>
                <div class="conf-bar" style="height:4px; margin: 2px 0 4px 0;"><div class="conf-fill" style="width: ${f.weight}; background: #38bdf8;"></div></div>
                <div class="factor-desc" style="font-size:0.65rem; color:#94a3b8;">${f.desc}</div>
            </div>
        `).join('');

        document.getElementById('drawer-natural-summary').querySelector('span').textContent = loc.explanation;

        // WHY THIS ALERT & ACTION GAP BLOCK
        const actionGapStatus = actionGap >= 0 ? '✓ ACTION WINDOW AVAILABLE' : '⚠ ACTION WINDOW INSUFFICIENT';
        const actionGapColor = actionGap >= 0 ? '#10b981' : '#ef4444';

        const shelterObj = loc.recommended_shelter;
        const routeObj = loc.recommended_route;

        document.querySelector('.why-alert-card').innerHTML = `
            <h4 class="wa-title">ACTION INTELLIGENCE &amp; EVACUATION GAP</h4>
            <div class="wa-body">
                <div class="wa-row"><span>PREDICTED RISK SCORE:</span> <strong style="color:${actionState.color}">${computedRisk.toFixed(2)} (${actionState.label})</strong></div>
                <div class="wa-row"><span>ACTIONABLE WARNING WINDOW:</span> <strong>${warningWindow} MIN</strong></div>
                <div class="wa-row"><span>ESTIMATED EVACUATION ETA:</span> <strong>${evacEta} MIN</strong></div>
                <div class="wa-row"><span>ACTION GAP (WINDOW - ETA):</span> <strong style="color:${actionGapColor}">${actionGap >= 0 ? '+' : ''}${actionGap} MIN</strong></div>
                <div class="wa-row" style="margin-top:2px;"><span>STATUS:</span> <strong style="color:${actionGapColor}">${actionGapStatus}</strong></div>
                
                <hr style="border: 0; border-top: 1px solid #2e3d5c; margin: 6px 0;">
                
                <div class="wa-row"><span>RECOMMENDED SHELTER:</span> <strong style="color:#38bdf8">${shelterObj.name}</strong></div>
                <div class="wa-row"><span>SHELTER METRICS:</span> <span>${shelterObj.distance_km}km • ETA ${shelterObj.eta_min}m • ${shelterObj.occupancy}/${shelterObj.capacity} cap</span></div>
                
                <hr style="border: 0; border-top: 1px solid #2e3d5c; margin: 6px 0;">

                <div class="wa-row"><span>RECOMMENDED ROUTE:</span> <strong>${state.roadAFailed ? 'Road B (Gaurikund Bypass)' : 'Road A (NH-107 Highway)'}</strong></div>
                <div style="font-size:0.64rem; color:#94a3b8; margin-top:2px;">WHY: ${state.roadAFailed ? 'Road A reached 0.86 CRITICAL flood risk. Automatically rerouted to Road B.' : routeObj.why}</div>
                
                <div class="wa-action" style="margin-top:6px;">RECOMMENDED ACTION: <strong style="color:${actionState.color}">${actionState.label}</strong></div>
            </div>
        `;

        document.getElementById('location-drawer').classList.add('open');

        if (state.mainMap) {
            state.mainMap.panTo([loc.lat, loc.lng]);
        }
    }

    function closeLocationDrawer() {
        document.getElementById('location-drawer').classList.remove('open');
    }

    // 10. RENDER ALL VIEWS
    function renderAllViews() {
        renderLocationsGrid();
        renderForecastView();
        renderEvacuationView();
        renderIncidentsView();
        renderSystemHealthView();
        updateStripMetrics();
    }

    function updateStripMetrics() {
        const currentLocs = window.FLOODX_DATA.locations.map(l => {
            const st = l.timesteps[state.currentTimeStepIdx] || l.timesteps[0];
            const computedRisk = computeRiskIndex(st.hazard, st.exposure, st.vuln);
            const actionState = getActionState(computedRisk);
            const evacEta = state.roadAFailed ? 21 : st.evac_eta;
            return { ...l, risk_score: computedRisk, risk_label: actionState.label, people_exposure: st.people, time_to_crit: st.time_to_crit, evac_eta: evacEta };
        });

        const critCount = currentLocs.filter(l => l.risk_score >= 0.8).length;
        const exposed = currentLocs.filter(l => l.risk_score >= 0.6).reduce((acc, l) => acc + l.people_exposure, 0);
        const highestLoc = [...currentLocs].sort((a, b) => b.risk_score - a.risk_score)[0];

        document.getElementById('strip-critical-zones').textContent = `0${critCount}`;
        document.getElementById('strip-people-exposed').textContent = exposed.toLocaleString();
        document.getElementById('strip-highest-risk').textContent = highestLoc.risk_score.toFixed(2);
        document.getElementById('strip-risk-label').textContent = highestLoc.risk_label;
        document.getElementById('strip-time-critical').textContent = `${highestLoc.time_to_crit} min`;
        document.getElementById('nav-crit-count').textContent = critCount;

        const actionGap = highestLoc.time_to_crit - highestLoc.evac_eta;
        const windowStatus = actionGap >= 0 ? '✓ WINDOW AVAILABLE' : '⚠ WINDOW INSUFFICIENT';
        const windowElem = document.getElementById('strip-window-status');
        if (windowElem) {
            windowElem.textContent = windowStatus;
            windowElem.className = `badge ${actionGap >= 0 ? 'badge-green' : 'badge-alert'}`;
        }
    }

    function renderLocationsGrid() {
        const container = document.getElementById('locations-cards-container');
        if (!container) return;

        container.innerHTML = window.FLOODX_DATA.locations.map(loc => {
            const st = loc.timesteps[state.currentTimeStepIdx] || loc.timesteps[0];
            const computedRisk = computeRiskIndex(st.hazard, st.exposure, st.vuln);
            const actionState = getActionState(computedRisk);
            return `
                <div class="location-card" onclick="window.FLOODX_APP.selectAndOpenDrawer('${loc.id}')">
                    <div class="lc-header">
                        <div>
                            <h3 class="lc-title">${loc.name}</h3>
                            <span class="lc-sub">${loc.region}</span>
                        </div>
                        <span class="badge ${actionState.badgeClass}">${actionState.label}</span>
                    </div>
                    <div class="lc-score-row">
                        <span class="lc-score" style="color: ${actionState.color}">${computedRisk.toFixed(2)}</span>
                        <span class="risk-change positive">${loc.risk_change} in 15m</span>
                    </div>
                    <div class="lc-env-mini">
                        <span>RAIN: ${st.rain}mm/h</span>
                        <span>RIVER: ${st.river}m</span>
                        <span>TIME: ${st.time_to_crit}m</span>
                    </div>
                    <button class="btn btn-outline btn-sm" style="width: 100%; justify-content: center; margin-top: 4px;">
                        VIEW INTELLIGENCE DRAWER &rarr;
                    </button>
                </div>
            `;
        }).join('');
    }

    // 11. FORECAST SCREEN & UNCERTAINTY BAND CANVAS
    function renderForecastView() {
        const selectElem = document.getElementById('forecast-loc-select');
        if (!selectElem) return;

        selectElem.innerHTML = window.FLOODX_DATA.locations.map(loc => `
            <option value="${loc.id}" ${loc.id === state.selectedLocationId ? 'selected' : ''}>${loc.name}</option>
        `).join('');

        const loc = window.FLOODX_DATA.locations.find(l => l.id === state.selectedLocationId) || window.FLOODX_DATA.locations[0];
        const st = loc.timesteps[state.currentTimeStepIdx] || loc.timesteps[0];
        document.getElementById('forecast-target-name').textContent = loc.name;
        document.getElementById('dw-time-display').textContent = `${st.time_to_crit} MIN`;

        renderForecastCanvas();
    }

    function renderForecastCanvas() {
        const canvas = document.getElementById('forecast-canvas');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        const width = canvas.width;
        const height = canvas.height;

        ctx.clearRect(0, 0, width, height);

        const loc = window.FLOODX_DATA.locations.find(l => l.id === state.selectedLocationId) || window.FLOODX_DATA.locations[0];
        const dataPoints = loc.forecast;

        ctx.strokeStyle = '#1f293d';
        ctx.lineWidth = 1;

        for (let y = 0.2; y <= 1.0; y += 0.2) {
            const py = height - (y * (height - 40)) - 20;
            ctx.beginPath();
            ctx.moveTo(30, py);
            ctx.lineTo(width - 20, py);
            ctx.stroke();

            ctx.fillStyle = '#64748b';
            ctx.font = '10px IBM Plex Mono';
            ctx.fillText(y.toFixed(1), 5, py + 3);
        }

        const critY = height - (0.80 * (height - 40)) - 20;
        ctx.strokeStyle = 'rgba(239, 68, 68, 0.6)';
        ctx.lineWidth = 2;
        ctx.setLineDash([6, 4]);
        ctx.beginPath();
        ctx.moveTo(30, critY);
        ctx.lineTo(width - 20, critY);
        ctx.stroke();
        ctx.setLineDash([]);

        ctx.fillStyle = '#ef4444';
        ctx.font = '700 11px IBM Plex Mono';
        ctx.fillText('CRITICAL THRESHOLD (0.80)', width - 180, critY - 6);

        const paddingLeft = 40;
        const paddingRight = 30;
        const usableWidth = width - paddingLeft - paddingRight;

        const points = dataPoints.map((dp, idx) => {
            const x = paddingLeft + (idx / (dataPoints.length - 1)) * usableWidth;
            const y = height - (dp.score * (height - 40)) - 20;
            const yLow = height - (dp.unc_low * (height - 40)) - 20;
            const yHigh = height - (dp.unc_high * (height - 40)) - 20;
            return { x, y, yLow, yHigh, score: dp.score, unc_low: dp.unc_low, unc_high: dp.unc_high };
        });

        // UNCERTAINTY BAND SHADING
        ctx.beginPath();
        ctx.moveTo(points[0].x, points[0].yHigh);
        points.forEach(p => ctx.lineTo(p.x, p.yHigh));
        for (let i = points.length - 1; i >= 0; i--) {
            ctx.lineTo(points[i].x, points[i].yLow);
        }
        ctx.closePath();
        ctx.fillStyle = 'rgba(239, 68, 68, 0.18)';
        ctx.fill();

        // MEAN FORECAST LINE
        ctx.strokeStyle = '#ef4444';
        ctx.lineWidth = 3;
        ctx.beginPath();
        points.forEach((p, i) => {
            if (i === 0) ctx.moveTo(p.x, p.y);
            else ctx.lineTo(p.x, p.y);
        });
        ctx.stroke();

        points.forEach((p, i) => {
            ctx.fillStyle = i === 0 ? '#38bdf8' : '#ef4444';
            ctx.beginPath();
            ctx.arc(p.x, p.y, 5, 0, Math.PI * 2);
            ctx.fill();

            ctx.fillStyle = '#ffffff';
            ctx.font = '700 11px IBM Plex Mono';
            ctx.fillText(`${p.score.toFixed(2)}`, p.x - 12, p.y - 10);
        });
    }

    // 12. EVACUATION COMMAND ENGINE
    function renderEvacuationView() {
        const priorityContainer = document.getElementById('evac-priority-container');
        if (!priorityContainer) return;

        const currentLocs = window.FLOODX_DATA.locations.map(l => {
            const st = l.timesteps[state.currentTimeStepIdx] || l.timesteps[0];
            const computedRisk = computeRiskIndex(st.hazard, st.exposure, st.vuln);
            const actionState = getActionState(computedRisk);
            return { ...l, risk_score: computedRisk, risk_label: actionState.label, people_exposure: st.people, time_to_crit: st.time_to_crit };
        });

        const sortedLocations = [...currentLocs].sort((a, b) => b.risk_score - a.risk_score);

        priorityContainer.innerHTML = sortedLocations.map((loc, idx) => `
            <div class="evac-card ${loc.id === state.selectedLocationId ? 'active' : ''} ${idx === 0 ? 'priority-1' : ''}" onclick="window.FLOODX_APP.selectLocationForEvac('${loc.id}')">
                <div class="ec-rank-row">
                    <span class="ec-rank">#0${idx + 1} PRIORITY</span>
                    <span class="badge ${getActionState(loc.risk_score).badgeClass}">${loc.risk_label}</span>
                </div>
                <h4 class="ec-name">${loc.name}</h4>
                <div class="ec-meta-grid">
                    <div>
                        <span class="ec-m-lbl">IMPACT POPULATION</span>
                        <span class="ec-m-val">${loc.people_exposure.toLocaleString()}</span>
                    </div>
                    <div>
                        <span class="ec-m-lbl">TIME TO CRIT</span>
                        <span class="ec-m-val text-alert">${loc.time_to_crit} min</span>
                    </div>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 4px;">
                    <span class="badge ${getActionState(loc.risk_score).badgeClass}">${loc.risk_label}</span>
                    <span style="font-size: 0.65rem; color: #38bdf8; font-weight: 600;">[ VIEW ROUTE ]</span>
                </div>
            </div>
        `).join('');

        renderRoutingMap();
    }

    function renderRoutingMap() {
        if (!state.routingMap) return;

        Object.values(state.mapRoadPolys).forEach(r => state.routingMap.removeLayer(r));

        const routeData = window.FLOODX_DATA.routes['loc_riverside'];
        const routeA = routeData.options[0];
        const routeB = routeData.options[1];

        const originMarker = L.circleMarker([30.7345, 79.0669], { radius: 8, color: '#ef4444', fillColor: '#ef4444', fillOpacity: 1 }).addTo(state.routingMap);
        const shelterMarker = L.circleMarker([30.7450, 79.0500], { radius: 8, color: '#10b981', fillColor: '#10b981', fillOpacity: 1 }).addTo(state.routingMap);
        
        originMarker.bindTooltip('ORIGIN: Riverside Colony', { permanent: true, direction: 'left' });
        shelterMarker.bindTooltip('DESTINATION: Emergency Relief Camp Alpha', { permanent: true, direction: 'right' });

        if (!state.roadAFailed) {
            const polyA = L.polyline(routeA.coords, { color: '#10b981', weight: 5, opacity: 0.9 }).addTo(state.routingMap);
            const polyB = L.polyline(routeB.coords, { color: '#64748b', weight: 3, opacity: 0.5, dashArray: '6, 6' }).addTo(state.routingMap);

            document.getElementById('active-route-title').textContent = 'Riverside Colony → Emergency Relief Camp Alpha (via NH-107)';
            document.getElementById('route-status-txt').textContent = 'ROUTE OPTIMAL';
            document.getElementById('route-status-badge').className = 'route-status-badge';

            document.getElementById('rm-eta').textContent = '18 min';
            document.getElementById('rm-curr-risk').innerHTML = '<span class="badge badge-green">0.22 LOW</span>';
            document.getElementById('rm-pred-risk').innerHTML = '<span class="badge badge-green">0.34 LOW</span>';
            document.getElementById('rm-dist').textContent = '4.5 km';

            document.getElementById('reroute-alert-banner').classList.add('hidden');
            document.getElementById('route-explanation-text').textContent =
                'NH-107 Highway is currently shorter, but predicted flood risk is expected to reach 0.87 within 20 minutes due to Mandakini surge. Gaurikund Bypass remains below the critical threshold during the estimated evacuation window.';
        } else {
            const polyA = L.polyline(routeA.coords, { color: '#ef4444', weight: 4, opacity: 0.4, dashArray: '4, 4' }).addTo(state.routingMap);
            const polyB = L.polyline(routeB.coords, { color: '#38bdf8', weight: 6, opacity: 0.95 }).addTo(state.routingMap);

            document.getElementById('active-route-title').textContent = 'Riverside Colony → Emergency Relief Camp Alpha (via Gaurikund High Ridge Bypass)';
            document.getElementById('route-status-txt').textContent = 'AUTOMATICALLY REROUTED';
            document.getElementById('route-status-badge').className = 'route-status-badge rerouted';

            document.getElementById('rm-eta').textContent = '21 min';
            document.getElementById('rm-curr-risk').innerHTML = '<span class="badge badge-green">0.15 LOW</span>';
            document.getElementById('rm-pred-risk').innerHTML = '<span class="badge badge-green">0.28 LOW</span>';
            document.getElementById('rm-dist').textContent = '6.8 km';

            document.getElementById('reroute-alert-banner').classList.remove('hidden');
            document.getElementById('route-explanation-text').textContent =
                'NH-107 Highway exceeded critical flood-risk threshold (0.86) due to Mandakini surge. FLOODX Dynamic Decision Engine automatically recalculated and activated high-ridge Gaurikund bypass to guarantee safe evacuation.';
        }

        state.routingMap.fitBounds(L.latLngBounds(routeB.coords), { padding: [30, 30] });
    }

    // 13. INCIDENTS TIMELINE
    function renderIncidentsView() {
        const container = document.getElementById('incidents-timeline-list');
        if (!container) return;

        container.innerHTML = window.FLOODX_DATA.incidents.map(inc => `
            <div class="timeline-item ${inc.type === 'alert' ? 't-alert' : inc.type === 'warn' ? 't-warn' : ''}">
                <div class="t-header">
                    <span class="t-location">${inc.location}</span>
                    <span class="t-time">${inc.time}</span>
                </div>
                <div class="t-msg">${inc.msg}</div>
            </div>
        `).join('');
    }

    // 14. SYSTEM HEALTH SCREEN (SENSOR FAILURE CONFIDENCE REDUCTION)
    function renderSystemHealthView() {
        const s8Badge = document.getElementById('health-s8-badge');
        const degradedBanner = document.getElementById('sensor-degraded-banner');

        if (state.sensor8Degraded) {
            s8Badge.textContent = 'DEGRADED (HIGH NOISE)';
            s8Badge.className = 'badge badge-yellow';
            degradedBanner.classList.remove('hidden');
            
            document.getElementById('side-health-dot').className = 'status-dot dot-degraded';
            document.getElementById('hm-data-quality').textContent = '72% (NOISY / DEGRADED)';
            document.getElementById('hm-dq-bar').style.width = '72%';
            document.getElementById('hm-confidence').textContent = '63% (REDUCED CONFIDENCE)';
            document.getElementById('hm-conf-bar').style.width = '63%';
        } else {
            s8Badge.textContent = 'ONLINE';
            s8Badge.className = 'badge badge-green';
            degradedBanner.classList.add('hidden');

            document.getElementById('side-health-dot').className = 'status-dot dot-online';
            document.getElementById('hm-data-quality').textContent = '91% (GOOD INTEGRITY)';
            document.getElementById('hm-dq-bar').style.width = '91%';
            document.getElementById('hm-confidence').textContent = '77% (HIGH AGREEMENT)';
            document.getElementById('hm-conf-bar').style.width = '77%';
        }
    }

    // 15. EVENT LISTENERS
    function initEventListeners() {
        document.getElementById('btn-close-drawer')?.addEventListener('click', closeLocationDrawer);

        document.getElementById('demo-mode-indicator')?.addEventListener('click', openProvenanceModal);
        document.getElementById('btn-open-provenance-modal')?.addEventListener('click', openProvenanceModal);
        document.getElementById('btn-close-provenance')?.addEventListener('click', closeProvenanceModal);

        document.getElementById('btn-drawer-forecast')?.addEventListener('click', () => {
            switchView('forecast-view');
            closeLocationDrawer();
        });

        document.getElementById('btn-drawer-evac')?.addEventListener('click', () => {
            switchView('evacuation-view');
            closeLocationDrawer();
        });

        document.getElementById('region-select')?.addEventListener('change', (e) => {
            selectRegion(e.target.value);
        });

        document.getElementById('map-style-select')?.addEventListener('change', (e) => {
            applyMapStyle(e.target.value);
        });

        document.getElementById('op-mode-select')?.addEventListener('change', (e) => {
            state.opMode = e.target.value;
            const modeLabel = state.opMode === 'HISTORICAL' ? 'DATA MODE: HISTORICAL REPLAY' : 'DATA MODE: DEMO REPLAY';
            document.getElementById('header-data-mode-text').textContent = modeLabel;
            showToast(`Switched to ${state.opMode === 'HISTORICAL' ? 'MODE B: HISTORICAL REPLAY' : 'MODE A: DEMO OPERATIONS'}`);
        });

        document.getElementById('scenario-select')?.addEventListener('change', (e) => {
            applyScenario(e.target.value);
        });

        document.getElementById('forecast-loc-select')?.addEventListener('change', (e) => {
            state.selectedLocationId = e.target.value;
            renderForecastView();
        });

        document.getElementById('future-time-slider')?.addEventListener('input', (e) => {
            updateTimeSlider(parseInt(e.target.value));
        });

        const setupLayerToggle = (btnId, key) => {
            document.getElementById(btnId)?.addEventListener('click', (e) => {
                state.layers[key] = !state.layers[key];
                e.target.classList.toggle('active', state.layers[key]);
                renderMainMapElements();
            });
        };

        setupLayerToggle('toggle-zones-btn', 'zones');
        setupLayerToggle('toggle-pop-btn', 'population');
        setupLayerToggle('toggle-vuln-btn', 'vulnerability');
        setupLayerToggle('toggle-roads-btn', 'roads');
        setupLayerToggle('toggle-sensors-btn', 'sensors');
        setupLayerToggle('toggle-shelters-btn', 'shelters');
        setupLayerToggle('toggle-terrain-btn', 'terrain');

        document.getElementById('btn-trigger-road-failure')?.addEventListener('click', () => {
            toggleRoadAFailure();
        });

        document.getElementById('btn-toggle-sensor8')?.addEventListener('click', () => {
            state.sensor8Degraded = !state.sensor8Degraded;
            addIncidentLog(
                state.sensor8Degraded ? 'WARN' : 'INFO',
                'SENSOR #08',
                state.sensor8Degraded ? 'Radar input degraded. Data Quality drops 91%->72%, Confidence 77%->63%.' : 'Sensor #08 signal restored.'
            );
            renderSystemHealthView();
            openLocationDrawer(state.selectedLocationId);
        });

        document.getElementById('btn-run-master-scenario')?.addEventListener('click', () => {
            runMasterFloodScenario();
        });

        document.getElementById('btn-run-demo-seq')?.addEventListener('click', () => {
            run9StepDemoSequence();
        });
    }

    function openProvenanceModal() {
        document.getElementById('provenance-modal').classList.remove('hidden');
    }

    function closeProvenanceModal() {
        document.getElementById('provenance-modal').classList.add('hidden');
    }

    function applyScenario(scenarioKey) {
        state.selectedScenario = scenarioKey;
        const sc = window.FLOODX_DATA.scenarios[scenarioKey];
        if (!sc) return;

        const loc = window.FLOODX_DATA.locations.find(l => l.id === 'loc_riverside');
        if (loc) {
            loc.rainfall_mm_hr = sc.rain;
            loc.river_level_m = sc.river;
            state.roadAFailed = !!sc.trigger_reroute;
            state.sensor8Degraded = (sc.s8_status === 'DEGRADED');
        }

        renderMainMapElements();
        renderAllViews();
        addIncidentLog('INFO', 'SCENARIO ENGINE', `Switched to scenario: ${sc.name}`);
    }

    function toggleRoadAFailure() {
        state.roadAFailed = !state.roadAFailed;
        if (state.roadAFailed) {
            addIncidentLog('ALERT', 'NH-107 HIGHWAY', 'Road A flood risk reached 0.86 CRITICAL. Triggering dynamic reroute.');
        } else {
            addIncidentLog('INFO', 'NH-107 HIGHWAY', 'Road A risk normalized (0.22). Primary route restored.');
        }
        renderRoutingMap();
        renderMainMapElements();
        openLocationDrawer(state.selectedLocationId);
    }

    function addIncidentLog(type, location, msg) {
        const timeStr = new Date().toTimeString().split(' ')[0];
        window.FLOODX_DATA.incidents.unshift({
            time: timeStr,
            location: location,
            msg: msg,
            type: type.toLowerCase()
        });
        renderIncidentsView();
    }

    // 16. MASTER HERO SCENARIO
    function runMasterFloodScenario() {
        if (state.demoInterval) clearInterval(state.demoInterval);

        const sequence = [
            { t: 0, fn: () => { applyScenario('HEAVY_RAIN'); showToast('1. HEAVY RAINFALL detected in Mandakini Catchment.'); } },
            { t: 2500, fn: () => { updateTimeSlider(1); showToast('2. UPSTREAM RISK INCREASES (+15 MIN). River level rising.'); } },
            { t: 5000, fn: () => { updateTimeSlider(2); showToast('3. RISK PROPAGATES DOWNSTREAM (+30 MIN). Red risk zones expand.'); } },
            { t: 7500, fn: () => { applyScenario('STORM_INTENSIFYING'); updateTimeSlider(3); openLocationDrawer('loc_riverside'); showToast('4. RIVERSIDE COLONY -> CRITICAL. 2,400 People Exposed.'); } },
            { t: 10500, fn: () => { switchView('evacuation-view'); showToast('5. EVACUATION PRIORITY #1 Assigned. Safe route selected.'); } },
            { t: 13000, fn: () => { toggleRoadAFailure(); showToast('6. ROAD A RISK INTENSIFIES -> 0.86 UNSAFE. Automatic Reroute to Road B!'); } },
            { t: 16000, fn: () => { switchView('system-health-view'); state.sensor8Degraded = true; renderSystemHealthView(); showToast('7. SENSOR #08 DEGRADES. Fallback engine maintains forecast.'); } },
            { t: 19000, fn: () => { switchView('command-center'); updateTimeSlider(0); state.sensor8Degraded = false; renderSystemHealthView(); showToast('8. INTELLIGENCE WORKFLOW COMPLETE.'); } }
        ];

        sequence.forEach(step => {
            setTimeout(step.fn, step.t);
        });
    }

    // 17. DEMO SEQUENCE
    function run9StepDemoSequence() {
        if (state.demoInterval) clearInterval(state.demoInterval);

        const steps = [
            { view: 'command-center', scenario: 'NORMAL', msg: 'STEP 1: Baseline Normal Conditions across Kedarnath basin.' },
            { view: 'command-center', scenario: 'HEAVY_RAIN', msg: 'STEP 2: Storm Intensifies. Rainfall increases to 28mm/hr.' },
            { view: 'command-center', scenario: 'STORM_INTENSIFYING', msg: 'STEP 3: Risk score calculated at 0.81 at Riverside Colony.' },
            { view: 'forecast-view', scenario: 'STORM_INTENSIFYING', msg: 'STEP 4: Viewing 120-minute Risk Trajectory & Uncertainty Band.' },
            { view: 'command-center', scenario: 'STORM_INTENSIFYING', drawer: true, msg: 'STEP 5: Location Drawer Signal Breakdown & Explainability.' },
            { view: 'evacuation-view', scenario: 'STORM_INTENSIFYING', msg: 'STEP 6: Evacuation Priority #1 assigned to Riverside Colony.' },
            { view: 'evacuation-view', scenario: 'ROAD_FAILURE', msg: 'STEP 7: Road A becomes unsafe. Dynamic rerouting triggers Road B.' },
            { view: 'system-health-view', scenario: 'SENSOR_FAILURE', msg: 'STEP 8: Sensor #08 degrades. System maintains operational fallback.' },
            { view: 'command-center', scenario: 'STORM_INTENSIFYING', msg: 'STEP 9: INTELLIGENCE WORKFLOW COMPLETE.' }
        ];

        let currentStepIdx = 0;

        function executeStep() {
            if (currentStepIdx >= steps.length) {
                clearInterval(state.demoInterval);
                showToast('FLOODX Demo Sequence Completed!');
                return;
            }

            const step = steps[currentStepIdx];
            showToast(step.msg);

            if (step.scenario) {
                document.getElementById('scenario-select').value = step.scenario;
                applyScenario(step.scenario);
            }

            switchView(step.view);

            if (step.drawer) {
                openLocationDrawer('loc_riverside');
            } else {
                closeLocationDrawer();
            }

            currentStepIdx++;
        }

        executeStep();
        state.demoInterval = setInterval(executeStep, 4500);
    }

    function showToast(message) {
        let toast = document.getElementById('demo-toast');
        if (!toast) {
            toast = document.createElement('div');
            toast.id = 'demo-toast';
            toast.style.cssText = `
                position: fixed;
                bottom: 40px;
                left: 50%;
                transform: translateX(-50%);
                background: #0284c7;
                color: #fff;
                font-weight: 700;
                font-size: 0.85rem;
                padding: 10px 20px;
                border-radius: 6px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.5);
                z-index: 9999;
                transition: all 0.3s ease;
            `;
            document.body.appendChild(toast);
        }
        toast.textContent = message;
        toast.style.opacity = '1';
        setTimeout(() => { toast.style.opacity = '0'; }, 3800);
    }

    function startClock() {
        setInterval(() => {
            const now = new Date();
            const timeStr = now.toTimeString().split(' ')[0];
            document.getElementById('header-timestamp').textContent = timeStr;
        }, 1000);
    }

    window.FLOODX_APP = {
        selectAndOpenDrawer: (id) => {
            switchView('command-center');
            openLocationDrawer(id);
        },
        selectLocationForEvac: (id) => {
            state.selectedLocationId = id;
            renderEvacuationView();
        }
    };
});
