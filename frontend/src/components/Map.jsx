import { useEffect, useRef, useState } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { useApp } from '../store/AppContext.jsx';

const STYLE_URL    = 'https://tiles.openfreemap.org/styles/positron';
const INDIA_CENTER = [78.9629, 20.5937];                  // [lon, lat]
const INDIA_BOUNDS = [[68.1, 6.7], [97.4, 37.1]];         // [[west,south],[east,north]]

// World-covering ring in GeoJSON [lon,lat] order
const WORLD_RING = [[-180,-90],[180,-90],[180,90],[-180,90],[-180,-90]];

const TYPE_COLORS = {
  software:  '#3B82F6',
  itsupport: '#22C55E',
  cloud:     '#A855F7',
  unknown:   '#6B7280',
};

function buildGeoJSON(companies) {
  return {
    type: 'FeatureCollection',
    features: companies.map(c => ({
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [c.lon, c.lat] },
      properties: {
        id: c.id, type: c.type, name: c.name,
        address: c.address ?? '', phone: c.phone ?? '', website: c.website ?? '',
      },
    })),
  };
}

export default function Map({ onSelect }) {
  const { filtered, selectedId, setSelectedId, cityBounds } = useApp();

  const mapElRef   = useRef(null);
  const mapRef     = useRef(null);
  const loadedRef  = useRef(false);   // true once map 'load' fires
  const filteredRef = useRef(filtered); // avoids stale closure in async callbacks
  filteredRef.current = filtered;

  const [popup, setPopup] = useState(null);

  // ── Init map once ────────────────────────────────────────────────────────────
  useEffect(() => {
    const map = new maplibregl.Map({
      container: mapElRef.current,
      style: STYLE_URL,
      center: INDIA_CENTER,
      zoom: 4,
      minZoom: 3,
      maxBounds: [[58, 2], [108, 42]],   // slightly generous so borders don't clip
    });

    mapRef.current = map;
    map.addControl(new maplibregl.NavigationControl(), 'top-right');

    map.on('load', async () => {
      // Load India border GeoJSON
      let indiaGeo;
      try {
        indiaGeo = await fetch('/india.geojson').then(r => r.json());
      } catch {
        console.warn('Could not load india.geojson');
      }

      // ── World mask with India cut out ──────────────────────────────────────
      if (indiaGeo) {
        const holeRings = indiaGeo.coordinates.map(polygon => polygon[0]);
        map.addSource('world-mask', {
          type: 'geojson',
          data: {
            type: 'Feature',
            geometry: {
              type: 'Polygon',
              coordinates: [WORLD_RING, ...holeRings],
            },
          },
        });
        map.addLayer({
          id: 'world-mask-fill',
          type: 'fill',
          source: 'world-mask',
          paint: { 'fill-color': '#f1f5f9', 'fill-opacity': 0.88 },
        });

        // India border line
        map.addSource('india-border', { type: 'geojson', data: indiaGeo });
        map.addLayer({
          id: 'india-border-line',
          type: 'line',
          source: 'india-border',
          paint: { 'line-color': '#475569', 'line-width': 1.5 },
        });
      }

      // ── Companies source + circle layer ────────────────────────────────────
      map.addSource('companies', {
        type: 'geojson',
        data: buildGeoJSON(filteredRef.current),
      });

      map.addLayer({
        id: 'companies-circles',
        type: 'circle',
        source: 'companies',
        paint: {
          'circle-radius': ['interpolate', ['linear'], ['zoom'], 4, 4, 14, 10],
          'circle-color': [
            'match', ['get', 'type'],
            'software',  TYPE_COLORS.software,
            'itsupport', TYPE_COLORS.itsupport,
            'cloud',     TYPE_COLORS.cloud,
            TYPE_COLORS.unknown,
          ],
          'circle-stroke-color': '#ffffff',
          'circle-stroke-width': 1.5,
          'circle-opacity': 0.9,
        },
      });

      // Pointer cursor on hover
      map.on('mouseenter', 'companies-circles', () => {
        map.getCanvas().style.cursor = 'pointer';
      });
      map.on('mouseleave', 'companies-circles', () => {
        map.getCanvas().style.cursor = '';
      });

      // Click → select + show popup
      map.on('click', 'companies-circles', e => {
        const props  = e.features[0].properties;
        const coords = e.features[0].geometry.coordinates;
        setSelectedId(props.id);
        onSelect?.(props.id);
        setPopup({ ...props, lon: coords[0], lat: coords[1] });
      });

      // Click on blank map → clear popup
      map.on('click', e => {
        const hit = map.queryRenderedFeatures(e.point, { layers: ['companies-circles'] });
        if (!hit.length) setPopup(null);
      });

      loadedRef.current = true;
    });

    return () => {
      loadedRef.current = false;
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // ── Update companies when filtered changes ──────────────────────────────────
  useEffect(() => {
    if (!loadedRef.current || !mapRef.current) return;
    mapRef.current.getSource('companies')?.setData(buildGeoJSON(filtered));
  }, [filtered]);

  // ── Fly to selected company ─────────────────────────────────────────────────
  useEffect(() => {
    if (!loadedRef.current || selectedId == null) return;
    const company = filtered.find(c => c.id === selectedId);
    if (!company) return;
    mapRef.current.flyTo({ center: [company.lon, company.lat], zoom: 14, duration: 700 });
  }, [selectedId]);

  // ── Fit to city bounds ──────────────────────────────────────────────────────
  useEffect(() => {
    if (!loadedRef.current || !cityBounds) return;
    const { south, north, west, east } = cityBounds;
    mapRef.current.fitBounds([[west, south], [east, north]], { padding: 50, maxZoom: 13 });
  }, [cityBounds]);

  return (
    <div className="relative w-full h-full" style={{ minHeight: '500px' }}>
      <div ref={mapElRef} className="absolute inset-0" />

      {/* Company info popup */}
      {popup && (
        <div className="absolute top-4 left-4 z-10 bg-white rounded-xl shadow-lg p-3 w-56 border border-gray-100">
          <div className="flex items-start justify-between gap-2 mb-1">
            <p className="text-sm font-semibold text-gray-900 leading-tight">{popup.name}</p>
            <button
              onClick={() => setPopup(null)}
              className="text-gray-400 hover:text-gray-600 shrink-0 text-base leading-none"
            >
              ×
            </button>
          </div>
          {popup.address && <p className="text-xs text-gray-500 mb-1">{popup.address}</p>}
          {popup.phone   && <p className="text-xs text-gray-600 mb-1">{popup.phone}</p>}
          {popup.website && (
            <a
              href={popup.website}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-blue-500 hover:underline truncate block"
            >
              {popup.website.replace(/^https?:\/\//, '')}
            </a>
          )}
        </div>
      )}

      {/* Reset view */}
      <button
        onClick={() => {
          mapRef.current?.fitBounds(INDIA_BOUNDS, { padding: 20, animate: true });
          setPopup(null);
        }}
        className="absolute bottom-8 right-12 z-10 bg-white hover:bg-gray-50 text-gray-700 text-xs font-medium px-3 py-1.5 rounded-lg shadow border border-gray-200 transition-colors"
      >
        Reset View
      </button>
    </div>
  );
}
