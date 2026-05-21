export const API_BASE_DEFAULT = 'https://tapish-backend-163379998754.asia-south1.run.app';

export const AGENT_COLORS: Record<string, string> = {
  observer:   '#00bcd4',
  analyst:    '#ffab00',
  strategist: '#aa00ff',
  operator:   '#00e676',
  auditor:    '#ff1744',
  predictor:  '#00e5ff',
};

// #L — System event colors (ported from vanilla)
export const EVENT_COLORS: Record<string, string> = {
  routing_decision: '#0091ea',
  pipeline_complete: '#00c853',
  pipeline_error: '#ff3d00',
  auditor_verdict: '#ff1744',
  crisis_detected: '#ff6d00',
  crisis_retracted: '#ff3d00',
};

export const CRISIS_ICONS: Record<string, string> = {
  heatwave: '🔥', power_outage: '⚡', flood: '🌊',
  accident: '🚨', infrastructure: '🏗️', protest: '📢',
  disease_cluster: '🦠',
};

export const PHASE_MAP: Record<string, { label: string; emoji: string; color: string }> = {
  observe:  { label: 'OBSERVE',  emoji: '👁',  color: '#00bcd4' },
  reason:   { label: 'REASON',   emoji: '🧠', color: '#ffab00' },
  decide:   { label: 'DECIDE',   emoji: '⚖️', color: '#aa00ff' },
  act:      { label: 'ACT',      emoji: '⚡', color: '#00e676' },
  evaluate: { label: 'EVALUATE', emoji: '✅', color: '#ff1744' },
  adapt:    { label: 'ADAPT',    emoji: '🔄', color: '#0091ea' },  // #P — fixed: was #e040fb
  predict:  { label: 'PREDICT',  emoji: '🔮', color: '#00e5ff' },
};

export const LAHORE_CENTER = { lat: 31.52, lng: 74.35 };

// #I — Lahore geocoding fallback (19 locations from vanilla)
export const LAHORE_LOCATIONS: Record<string, { lat: number; lng: number }> = {
  'bhati gate':       { lat: 31.5780, lng: 74.3180 },
  'liberty market':   { lat: 31.5150, lng: 74.3450 },
  'model town':       { lat: 31.4750, lng: 74.3350 },
  'gulberg':          { lat: 31.5100, lng: 74.3500 },
  'misri shah':       { lat: 31.5700, lng: 74.3200 },
  'anarkali':         { lat: 31.5600, lng: 74.3300 },
  'mall road':        { lat: 31.5500, lng: 74.3400 },
  'data darbar':      { lat: 31.5700, lng: 74.3150 },
  'shah alam':        { lat: 31.5710, lng: 74.3050 },
  'ichhra':           { lat: 31.5230, lng: 74.3380 },
  'garden town':      { lat: 31.5080, lng: 74.3340 },
  'dha':              { lat: 31.4500, lng: 74.4000 },
  'dha phase 5':      { lat: 31.4500, lng: 74.4050 },
  'johar town':       { lat: 31.4700, lng: 74.3700 },
  'township':         { lat: 31.4520, lng: 74.3150 },
  'walled city':      { lat: 31.5800, lng: 74.3200 },
  'shadman':          { lat: 31.5350, lng: 74.3350 },
  'ferozepur road':   { lat: 31.4900, lng: 74.3600 },
  'canal road':       { lat: 31.5000, lng: 74.3400 },
};

export const DARK_MAP_STYLE = [
  { elementType: 'geometry', stylers: [{ color: '#1d2c4d' }] },
  { elementType: 'labels.text.fill', stylers: [{ color: '#8ec3b9' }] },
  { elementType: 'labels.text.stroke', stylers: [{ color: '#1a3646' }] },
  { featureType: 'water', elementType: 'geometry.fill', stylers: [{ color: '#0e1626' }] },
  { featureType: 'road', elementType: 'geometry', stylers: [{ color: '#304a7d' }] },
  { featureType: 'road', elementType: 'geometry.stroke', stylers: [{ color: '#255763' }] },
  { featureType: 'poi', elementType: 'geometry', stylers: [{ color: '#283d6a' }] },
  { featureType: 'transit', elementType: 'geometry', stylers: [{ color: '#2f3948' }] },
];

// Escape HTML for Google Maps InfoWindow content strings (not JSX)
export function escapeHtml(s: string): string {
  const div = document.createElement('div');
  div.textContent = s;
  return div.innerHTML;
}

// #I — Geocoding fallback (longest-match like backend)
export function geocode(crisis: { lat?: number; lng?: number; latitude?: number; longitude?: number; primary_location?: string }): { lat: number; lng: number } | null {
  if (crisis.lat && crisis.lng) return { lat: crisis.lat, lng: crisis.lng };
  if (crisis.latitude && crisis.longitude) return { lat: crisis.latitude, lng: crisis.longitude };
  const loc = (crisis.primary_location || '').toLowerCase().trim();
  if (!loc) return null;
  // Longest-match: "dha phase 5" should match 'dha phase 5' not 'dha'
  let bestKey = '';
  let bestCoords: { lat: number; lng: number } | null = null;
  for (const [key, coords] of Object.entries(LAHORE_LOCATIONS)) {
    if ((loc.includes(key) || key.includes(loc)) && key.length > bestKey.length) {
      bestKey = key;
      bestCoords = coords;
    }
  }
  return bestCoords;
}

// #M — PKT timezone formatting
export function formatTimePKT(ts: string): string {
  if (!ts) return '';
  try {
    const d = new Date(ts);
    if (isNaN(d.getTime())) return ts;
    return d.toLocaleTimeString('en-US', {
      hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit',
      timeZone: 'Asia/Karachi',
    });
  } catch { return ts; }
}
