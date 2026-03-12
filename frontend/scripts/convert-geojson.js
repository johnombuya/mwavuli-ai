/**
 * Convert kenya.geojson to SVG path data for KenyaHotspotMap.tsx.
 * Run: node scripts/convert-geojson.js
 * Output: prints a TypeScript COUNTY_PATHS constant to stdout.
 */
const fs = require('fs');
const path = require('path');

const geojson = JSON.parse(
  fs.readFileSync(path.join(__dirname, '..', 'public', 'kenya.geojson'), 'utf8')
);

// Map GeoJSON COUNTY_NAM (uppercase) to our system's title-case names
const NAME_MAP = {
  'BARINGO': 'Baringo',
  'BOMET': 'Bomet',
  'BUNGOMA': 'Bungoma',
  'BUSIA': 'Busia',
  'ELEGEYO-MARAKWET': 'Elgeyo Marakwet',
  'EMBU': 'Embu',
  'GARISSA': 'Garissa',
  'HOMA BAY': 'Homa Bay',
  'ISIOLO': 'Isiolo',
  'KAJIADO': 'Kajiado',
  'KAKAMEGA': 'Kakamega',
  'KERICHO': 'Kericho',
  'KIAMBU': 'Kiambu',
  'KILIFI': 'Kilifi',
  'KIRINYAGA': 'Kirinyaga',
  'KISII': 'Kisii',
  'KISUMU': 'Kisumu',
  'KITUI': 'Kitui',
  'KWALE': 'Kwale',
  'LAIKIPIA': 'Laikipia',
  'LAMU': 'Lamu',
  'MACHAKOS': 'Machakos',
  'MAKUENI': 'Makueni',
  'MANDERA': 'Mandera',
  'MARSABIT': 'Marsabit',
  'MERU': 'Meru',
  'MIGORI': 'Migori',
  'MOMBASA': 'Mombasa',
  "MURANG'A": 'Muranga',
  'NAIROBI': 'Nairobi',
  'NAKURU': 'Nakuru',
  'NANDI': 'Nandi',
  'NAROK': 'Narok',
  'NYAMIRA': 'Nyamira',
  'NYANDARUA': 'Nyandarua',
  'NYERI': 'Nyeri',
  'SAMBURU': 'Samburu',
  'SIAYA': 'Siaya',
  'TAITA TAVETA': 'Taita Taveta',
  'TANA RIVER': 'Tana River',
  'THARAKA - NITHI': 'Tharaka Nithi',
  'TRANS NZOIA': 'Trans Nzoia',
  'TURKANA': 'Turkana',
  'UASIN GISHU': 'Uasin Gishu',
  'VIHIGA': 'Vihiga',
  'WAJIR': 'Wajir',
  'WEST POKOT': 'West Pokot',
};

// SVG viewBox dimensions
const SVG_W = 500;
const SVG_H = 600;
const PADDING = 15;

// Find bounding box of all coordinates
let minLon = Infinity, maxLon = -Infinity, minLat = Infinity, maxLat = -Infinity;

function visitCoords(coords) {
  for (const c of coords) {
    if (Array.isArray(c[0])) {
      visitCoords(c);
    } else {
      const [lon, lat] = c;
      if (lon < minLon) minLon = lon;
      if (lon > maxLon) maxLon = lon;
      if (lat < minLat) minLat = lat;
      if (lat > maxLat) maxLat = lat;
    }
  }
}

for (const feature of geojson.features) {
  visitCoords(feature.geometry.coordinates);
}

console.error(`Bounding box: lon [${minLon}, ${maxLon}], lat [${minLat}, ${maxLat}]`);

// Mercator projection
function projectLon(lon) {
  return PADDING + ((lon - minLon) / (maxLon - minLon)) * (SVG_W - 2 * PADDING);
}

function projectLat(lat) {
  // Invert Y axis (SVG Y goes down, lat goes up)
  return PADDING + ((maxLat - lat) / (maxLat - minLat)) * (SVG_H - 2 * PADDING);
}

// Simplify a ring by keeping every Nth point (Douglas-Peucker is overkill here)
function simplifyRing(ring, maxPoints) {
  if (ring.length <= maxPoints) return ring;
  const step = Math.max(1, Math.floor(ring.length / maxPoints));
  const result = [];
  for (let i = 0; i < ring.length; i += step) {
    result.push(ring[i]);
  }
  // Always include the last point to close the polygon
  if (result[result.length - 1] !== ring[ring.length - 1]) {
    result.push(ring[ring.length - 1]);
  }
  return result;
}

function ringToPath(ring) {
  const simplified = simplifyRing(ring, 80);
  const parts = simplified.map((coord, i) => {
    const x = projectLon(coord[0]).toFixed(1);
    const y = projectLat(coord[1]).toFixed(1);
    return `${i === 0 ? 'M' : 'L'}${x},${y}`;
  });
  return parts.join(' ') + ' Z';
}

function geometryToPath(geometry) {
  if (geometry.type === 'Polygon') {
    // Only use the outer ring (index 0), skip holes
    return ringToPath(geometry.coordinates[0]);
  } else if (geometry.type === 'MultiPolygon') {
    return geometry.coordinates
      .map(polygon => ringToPath(polygon[0]))
      .join(' ');
  }
  return '';
}

// Merge features with the same county name (in case of duplicates)
const countyPaths = {};

for (const feature of geojson.features) {
  const rawName = (feature.properties.COUNTY_NAM || '').trim();
  if (!rawName) continue;
  
  const name = NAME_MAP[rawName] || rawName;
  const pathD = geometryToPath(feature.geometry);
  
  if (countyPaths[name]) {
    countyPaths[name] += ' ' + pathD;
  } else {
    countyPaths[name] = pathD;
  }
}

// Output TypeScript
console.log('const COUNTY_PATHS: Record<string, { d: string }> = {');
const sorted = Object.keys(countyPaths).sort();
for (const name of sorted) {
  const escaped = countyPaths[name].replace(/'/g, "\\'");
  console.log(`  '${name}': { d: '${escaped}' },`);
}
console.log('};');

console.error(`\nGenerated ${sorted.length} county paths.`);
console.error(`ViewBox: 0 0 ${SVG_W} ${SVG_H}`);
