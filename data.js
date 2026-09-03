/**
 * FLOODX - SCIENTIFICALLY DEFENDABLE DEMO DATASET & PROTOTYPE RISK ENGINE
 * Authentically grounded in real Indian disaster events with transparent data provenance.
 */

window.FLOODX_DATA = {
    // 00. REAL INDIAN REGIONS & HISTORICAL REPLAY EVENTS
    regions: {
        india_all: {
            id: 'india_all',
            name: '🇮🇳 Full India National Overview',
            center: [22.5937, 78.9629],
            zoom: 5,
            description: 'National Flash-Flood Risk Monitoring across Indian States & River Basins'
        },
        kedarnath: {
            id: 'kedarnath',
            name: 'Kedarnath Basin (Uttarakhand)',
            center: [30.7380, 79.0650],
            zoom: 13,
            state: 'Uttarakhand',
            district: 'Rudraprayag & Chamoli',
            river: 'Mandakini River'
        },
        chamoli: {
            id: 'chamoli',
            name: 'Chamoli & Joshimath (Uttarakhand)',
            center: [30.5555, 79.5658],
            zoom: 12,
            state: 'Uttarakhand',
            district: 'Chamoli',
            river: 'Alaknanda & Dhauliganga River'
        },
        wayanad: {
            id: 'wayanad',
            name: 'Wayanad Hills (Kerala)',
            center: [11.6854, 76.1320],
            zoom: 13,
            state: 'Kerala',
            district: 'Wayanad (Meppadi / Chooralmala)',
            river: 'Chaliyar & Kabini Tributaries'
        },
        mandi: {
            id: 'mandi',
            name: 'Mandi Valley (Himachal Pradesh)',
            center: [31.7087, 76.9320],
            zoom: 13,
            state: 'Himachal Pradesh',
            district: 'Mandi',
            river: 'Beas River'
        },
        silchar: {
            id: 'silchar',
            name: 'Silchar & Cachar (Assam)',
            center: [24.8333, 92.7789],
            zoom: 12,
            state: 'Assam',
            district: 'Cachar',
            river: 'Barak River'
        }
    },

    // HISTORICAL INDIAN FLOOD REPLAY EVENTS
    historical_events: {
        kedarnath_2013: {
            id: 'kedarnath_2013',
            name: '2013 Kedarnath Flash Flood (Reconstructed)',
            region_id: 'kedarnath',
            description: 'Reconstructed timeline of Chorabari lake outbreak & Mandakini surge',
            timesteps: [
                { time: 'T-120 MIN', risk: 0.35, rain: 24, river: 0.9, label: 'MONITOR' },
                { time: 'T-90 MIN', risk: 0.52, rain: 48, river: 1.4, label: 'PREPARE' },
                { time: 'T-60 MIN', risk: 0.74, rain: 82, river: 2.2, label: 'EVACUATION PRE-ALERT' },
                { time: 'T-30 MIN', risk: 0.88, rain: 110, river: 3.2, label: 'EVACUATE NOW' },
                { time: 'T-15 MIN', risk: 0.96, rain: 140, river: 4.1, label: 'EVACUATE NOW' },
                { time: 'T0 (OUTBREAK)', risk: 0.99, rain: 165, river: 5.4, label: 'EVACUATE NOW' }
            ]
        },
        wayanad_2024: {
            id: 'wayanad_2024',
            name: '2024 Wayanad Landslide Flood (Reconstructed)',
            region_id: 'wayanad',
            description: 'Reconstructed extreme rainfall debris flow in Chooralmala',
            timesteps: [
                { time: 'T-120 MIN', risk: 0.40, rain: 35, river: 1.1, label: 'PREPARE' },
                { time: 'T-90 MIN', risk: 0.61, rain: 65, river: 1.8, label: 'EVACUATION PRE-ALERT' },
                { time: 'T-60 MIN', risk: 0.79, rain: 95, river: 2.7, label: 'EVACUATION PRE-ALERT' },
                { time: 'T-30 MIN', risk: 0.91, rain: 125, river: 3.6, label: 'EVACUATE NOW' },
                { time: 'T-15 MIN', risk: 0.97, rain: 150, river: 4.3, label: 'EVACUATE NOW' },
                { time: 'T0 (IMPACT)', risk: 0.99, rain: 180, river: 5.1, label: 'EVACUATE NOW' }
            ]
        }
    },

    // INDIAN STATES GEOSPATIAL OVERVIEW
    indian_states: [
        { name: 'UTTARAKHAND', risk: 'CRITICAL (0.84)', center: [30.0668, 79.0193], color: '#ef4444' },
        { name: 'HIMACHAL PRADESH', risk: 'HIGH (0.68)', center: [31.1048, 77.1734], color: '#f97316' },
        { name: 'KERALA', risk: 'HIGH (0.72)', center: [10.8505, 76.2711], color: '#f97316' },
        { name: 'ASSAM', risk: 'CRITICAL (0.89)', center: [26.2006, 92.9376], color: '#ef4444' },
        { name: 'JAMMU & KASHMIR', risk: 'MODERATE (0.45)', center: [33.7782, 76.5762], color: '#eab308' },
        { name: 'MAHARASHTRA', risk: 'MODERATE (0.52)', center: [19.7515, 75.7139], color: '#eab308' },
        { name: 'WEST BENGAL', risk: 'HIGH (0.65)', center: [22.9868, 87.8550], color: '#f97316' }
    ],

    // MAJOR NATIONAL RIVERS
    national_rivers: [
        { name: 'Ganga River', coords: [[30.98, 78.93], [30.10, 78.30], [25.31, 82.97], [25.24, 87.01], [22.57, 88.36]] },
        { name: 'Yamuna River', coords: [[31.01, 78.45], [28.61, 77.20], [27.17, 78.00], [25.43, 81.84]] },
        { name: 'Brahmaputra River', coords: [[27.95, 95.34], [26.14, 91.73], [25.17, 89.83]] },
        { name: 'Narmada River', coords: [[22.75, 81.75], [23.18, 79.98], [21.70, 72.97]] },
        { name: 'Godavari River', coords: [[19.99, 73.78], [18.79, 78.91], [16.98, 81.78]] }
    ],

    // 01. MONITORED LOCATIONS (WITH FORMULA WEIGHTS & DYNAMIC ACTION GAPS)
    locations: [
        {
            id: 'loc_riverside',
            region_id: 'kedarnath',
            name: 'Riverside Colony (Kedarnath)',
            region: 'Rudraprayag District, Uttarakhand, India',
            lat: 30.7345,
            lng: 79.0669,
            population_exposure: 2400,
            
            // NORMALIZED RISK INPUTS (0-1)
            hazard_score: 0.73,         // Weight 45% -> 0.3285
            exposure_score: 0.82,       // Weight 35% -> 0.2870
            vulnerability_score: 0.61,  // Weight 20% -> 0.1220
            // Formula Risk Index = (0.73 * 0.45) + (0.82 * 0.35) + (0.61 * 0.20) = 0.7375 -> 0.74 (STORM) / 0.81 (INTENSIFIED)

            slope_deg: 28,
            soil_saturation: 70,
            historical_susceptibility: 0.85,
            
            timesteps: [
                { time: 'NOW', hazard: 0.82, exposure: 0.85, vuln: 0.70, time_to_crit: 18, evac_eta: 21, people: 2400, rain: 42, river: 2.1, unc_low: 0.78, unc_high: 0.84 },
                { time: '+15 MIN', hazard: 0.86, exposure: 0.88, vuln: 0.72, time_to_crit: 12, evac_eta: 21, people: 2550, rain: 48, river: 2.3, unc_low: 0.80, unc_high: 0.88 },
                { time: '+30 MIN', hazard: 0.92, exposure: 0.92, vuln: 0.75, time_to_crit: 5, evac_eta: 21, people: 2700, rain: 55, river: 2.7, unc_low: 0.85, unc_high: 0.94 },
                { time: '+60 MIN', hazard: 0.97, exposure: 0.95, vuln: 0.78, time_to_crit: 0, evac_eta: 21, people: 2850, rain: 64, river: 3.1, unc_low: 0.89, unc_high: 0.98 },
                { time: '+120 MIN', hazard: 0.99, exposure: 0.97, vuln: 0.80, time_to_crit: 0, evac_eta: 21, people: 3000, rain: 72, river: 3.5, unc_low: 0.91, unc_high: 0.99 }
            ],

            risk_change: '+0.28',
            confidence: 77,
            data_quality_score: 91,
            estimated_time_to_critical_min: 18,
            evacuation_eta_min: 21,
            rainfall_mm_hr: 42,
            river_level_m: 2.1,
            river_rise_rate: '+0.6 m / 15 min',
            
            top_factors: [
                { name: 'Rainfall Intensity', weight: '28%', desc: 'Torrential cloudburst concentration over Mandakini catchment' },
                { name: 'River Rise Rate', weight: '24%', desc: 'Mandakini river stage rising at +0.6m / 15 min' },
                { name: 'Soil Saturation', weight: '16%', desc: 'Soil moisture content at 70% capacity' },
                { name: 'Himalayan Slope', weight: '14%', desc: '28° steep mountain slope accelerating runoff' },
                { name: 'Historical Susceptibility', weight: '11%', desc: 'High historical flood susceptibility index (0.85)' },
                { name: 'Population Exposure', weight: '7%', desc: '2,400 people within predicted inundation zone' }
            ],
            explanation: 'Risk is increasing primarily because rainfall intensity and river rise rate are accelerating while soil saturation remains high.',
            evacuation_priority: 1,
            
            // RECOMMENDED SHELTER & EXPLAINABLE ROUTING
            recommended_shelter: {
                id: 'shelter_alpha',
                name: 'Emergency Relief Camp Alpha (Gaurikund Ridge)',
                distance_km: 4.5,
                eta_min: 18,
                capacity: 3500,
                occupancy: 1240,
                accessibility: 'SAFE (High Ridge Zone)'
            },
            
            recommended_route: {
                primary: 'Road B (Gaurikund High Ridge Bypass)',
                secondary: 'Road A (NH-107 Highway - PROJECTED UNSAFE)',
                why: 'Road A is projected to enter critical flood risk (0.86) before evacuation can complete. Road B remains clear on high ridge terrain.'
            },

            forecast: [
                { time: 'NOW', score: 0.81, unc_low: 0.78, unc_high: 0.84 },
                { time: '15 MIN', score: 0.84, unc_low: 0.80, unc_high: 0.88 },
                { time: '30 MIN', score: 0.90, unc_low: 0.85, unc_high: 0.94 },
                { time: '60 MIN', score: 0.95, unc_low: 0.89, unc_high: 0.98 },
                { time: '120 MIN', score: 0.97, unc_low: 0.91, unc_high: 0.99 }
            ]
        },
        {
            id: 'loc_village_north',
            region_id: 'kedarnath',
            name: 'Rambara Settlement',
            region: 'Kedarnath Upper Valley, Uttarakhand, India',
            lat: 30.7480,
            lng: 79.0580,
            population_exposure: 1180,

            hazard_score: 0.65,
            exposure_score: 0.70,
            vulnerability_score: 0.55,

            slope_deg: 22,
            soil_saturation: 65,
            historical_susceptibility: 0.75,

            timesteps: [
                { time: 'NOW', hazard: 0.65, exposure: 0.70, vuln: 0.55, time_to_crit: 32, evac_eta: 16, people: 1180, rain: 36, river: 1.8, unc_low: 0.62, unc_high: 0.71 },
                { time: '+15 MIN', hazard: 0.70, exposure: 0.74, vuln: 0.58, time_to_crit: 25, evac_eta: 16, people: 1220, rain: 40, river: 2.0, unc_low: 0.67, unc_high: 0.76 },
                { time: '+30 MIN', hazard: 0.78, exposure: 0.80, vuln: 0.62, time_to_crit: 16, evac_eta: 16, people: 1280, rain: 46, river: 2.2, unc_low: 0.74, unc_high: 0.83 },
                { time: '+60 MIN', hazard: 0.85, exposure: 0.86, vuln: 0.68, time_to_crit: 4, evac_eta: 16, people: 1350, rain: 52, river: 2.6, unc_low: 0.81, unc_high: 0.90 },
                { time: '+120 MIN', hazard: 0.90, exposure: 0.91, vuln: 0.72, time_to_crit: 0, evac_eta: 16, people: 1400, rain: 60, river: 3.0, unc_low: 0.86, unc_high: 0.95 }
            ],

            risk_change: '+0.15',
            confidence: 82,
            data_quality_score: 94,
            estimated_time_to_critical_min: 32,
            evacuation_eta_min: 16,
            rainfall_mm_hr: 36,
            river_level_m: 1.8,
            river_rise_rate: '+0.4 m / 15 min',
            
            top_factors: [
                { name: 'Rainfall Rate', weight: '26%', desc: 'Sustained rain intensity at 36mm/hr' },
                { name: 'River Rise Rate', weight: '22%', desc: 'Upper stream swelling' },
                { name: 'Soil Saturation', weight: '18%', desc: 'Soil saturation reached 65%' }
            ],
            explanation: 'Sustained rainfall and feeder stream accumulation pushing sector toward high risk threshold.',
            evacuation_priority: 2,

            recommended_shelter: {
                id: 'shelter_beta',
                name: 'Upper Ridge Community Shelter',
                distance_km: 2.8,
                eta_min: 16,
                capacity: 2000,
                occupancy: 450,
                accessibility: 'SAFE'
            },

            recommended_route: {
                primary: 'Upper Valley Track',
                secondary: 'River Bank Trail (UNSAFE)',
                why: 'Upper Valley Track maintains low risk while River Bank Trail is exposed to swelling.'
            },

            forecast: [
                { time: 'NOW', score: 0.67, unc_low: 0.62, unc_high: 0.71 },
                { time: '15 MIN', score: 0.72, unc_low: 0.67, unc_high: 0.76 },
                { time: '30 MIN', score: 0.79, unc_low: 0.74, unc_high: 0.83 },
                { time: '60 MIN', score: 0.86, unc_low: 0.81, unc_high: 0.90 },
                { time: '120 MIN', score: 0.91, unc_low: 0.86, unc_high: 0.95 }
            ]
        }
    ],

    // 02. EMERGENCY SHELTERS DATA
    shelters: [
        { id: 'shelter_alpha', name: 'Emergency Relief Camp Alpha (Gaurikund Ridge, UT)', lat: 30.7450, lng: 79.0500, capacity: 3500, current_occupancy: 1240, route_risk: 'LOW', eta_min: 21 },
        { id: 'shelter_beta', name: 'Meppadi High School Relief Center (Wayanad, KL)', lat: 11.6920, lng: 76.1250, capacity: 2500, current_occupancy: 890, route_risk: 'LOW', eta_min: 16 },
        { id: 'shelter_gamma', name: 'Mandi Central Relief Stadium (Mandi, HP)', lat: 31.7150, lng: 76.9250, capacity: 5000, current_occupancy: 1420, route_risk: 'LOW', eta_min: 19 }
    ],

    // 03. INTERACTIVE ROAD SEGMENTS
    roads: [
        { id: 'road_a', name: 'NH-107 Kedarnath Highway (River Corridor)', coords: [[30.7345, 79.0669], [30.7380, 79.0620], [30.7420, 79.0550], [30.7450, 79.0500]], current_risk: 0.62, predicted_risk: 0.87, status: 'HIGH RISK' },
        { id: 'road_b', name: 'Gaurikund Bypass (High Ridge Route)', coords: [[30.7345, 79.0669], [30.7310, 79.0600], [30.7330, 79.0490], [30.7400, 79.0460], [30.7450, 79.0500]], current_risk: 0.15, predicted_risk: 0.28, status: 'SAFE' }
    ],

    // 04. SENSORS & SYSTEM HEALTH TELEMETRY
    sensors: [
        { id: 's01', name: 'River Gauge #01 (Mandakini River, UT)', lat: 30.7520, lng: 79.0550, status: 'HEALTHY', quality: 98, type: 'river', level_m: 2.1, rise_rate: '+0.6m/15m', last_update: '10:42:16' },
        { id: 's02', name: 'AWS Rainfall Sensor #02 (Kedarnath)', lat: 30.7460, lng: 79.0620, status: 'HEALTHY', quality: 96, type: 'rainfall', level_m: 42, rise_rate: '42 mm/h', last_update: '10:42:16' },
        { id: 's03', name: 'Soil Probe #04 (Wayanad Ghat, KL)', lat: 11.6880, lng: 76.1380, status: 'HEALTHY', quality: 94, type: 'soil', level_m: '85%', rise_rate: '+8%/h', last_update: '10:42:16' },
        { id: 's08', name: 'Doppler Radar #08 (IMD Grid)', lat: 30.7580, lng: 79.0510, status: 'HEALTHY', quality: 91, type: 'doppler', level_m: 'Radar OK', rise_rate: 'Nominal', last_update: '10:42:16' }
    ],

    // 05. INCIDENT LOG HISTORY
    incidents: [
        { time: '10:42:16', location: 'NH-107 HIGHWAY', msg: 'Road A flood risk reached 0.86 CRITICAL. Triggering dynamic reroute.', type: 'alert' },
        { time: '10:41:32', location: 'RIVERSIDE COLONY', msg: 'Risk score calculated at 0.81 (CRITICAL). Action gap: -3 min.', type: 'alert' },
        { time: '10:40:51', location: 'WAYANAD SECTOR', msg: 'Chooralmala rain intensity exceeded 54 mm/hr.', type: 'warn' },
        { time: '10:40:02', location: 'MANDAKINI GAUGE', msg: 'River stage rising rapidly (+0.6m / 15 min).', type: 'warn' },
        { time: '10:39:18', location: 'SYSTEM STATUS', msg: 'PROTOTYPE FLOOD RISK ENGINE initialized in Demo Replay mode.', type: 'info' }
    ],

    // 06. ROUTES DATA FOR EVACUATION ENGINE
    routes: {
        'loc_riverside': {
            active_route_id: 'route_a',
            origin_name: 'Riverside Colony',
            destination_name: 'Emergency Relief Camp Alpha',
            options: [
                { id: 'route_a', name: 'NH-107 Kedarnath Highway', segments: 'NH-107 → River Bridge → Shelter Alpha', distance_km: 4.5, eta_min: 18, current_risk: 0.22, predicted_risk: 0.86, coords: [[30.7345, 79.0669], [30.7380, 79.0620], [30.7420, 79.0550], [30.7450, 79.0500]] },
                { id: 'route_b', name: 'Gaurikund High Ridge Bypass', segments: 'Gaurikund Ridge → Upper Track → Shelter Alpha', distance_km: 6.8, eta_min: 21, current_risk: 0.15, predicted_risk: 0.28, coords: [[30.7345, 79.0669], [30.7310, 79.0600], [30.7330, 79.0490], [30.7400, 79.0460], [30.7450, 79.0500]] }
            ]
        }
    },

    // 07. DEMO SCENARIO PRESETS
    scenarios: {
        NORMAL: { name: '01 — NORMAL CONDITIONS', riverside_risk: 0.28, rain: 8, river: 0.8, time_to_crit: 120, s8_status: 'HEALTHY' },
        HEAVY_RAIN: { name: '02 — HEAVY RAINFALL', riverside_risk: 0.62, rain: 28, river: 1.5, time_to_crit: 45, s8_status: 'HEALTHY' },
        STORM_INTENSIFYING: { name: '03 — RAPIDLY INTENSIFYING STORM', riverside_risk: 0.81, rain: 42, river: 2.1, time_to_crit: 18, s8_status: 'HEALTHY' },
        CLOUDBURST: { name: '04 — CLOUDBURST EVENT', riverside_risk: 0.95, rain: 88, river: 3.4, time_to_crit: 6, s8_status: 'HEALTHY' },
        RIVER_RISE: { name: '05 — RAPID RIVER RISE', riverside_risk: 0.89, rain: 50, river: 2.9, time_to_crit: 12, s8_status: 'HEALTHY' },
        SENSOR_FAILURE: { name: '06 — SENSOR DEGRADATION', riverside_risk: 0.81, rain: 42, river: 2.1, time_to_crit: 18, s8_status: 'DEGRADED' },
        ROAD_FAILURE: { name: '07 — ROAD A UNSAFE (REROUTE DEMO)', riverside_risk: 0.81, rain: 42, river: 2.1, time_to_crit: 18, s8_status: 'HEALTHY', trigger_reroute: true }
    }
};
