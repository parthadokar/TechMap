<script>
  import { onMount, onDestroy, createEventDispatcher } from 'svelte';
  import { filtered, selectedId, cityBounds } from '$lib/stores/companies';

  const dispatch = createEventDispatcher();

  const TYPE_COLORS = {
    software:  '#3B82F6',
    itsupport: '#22C55E',
    cloud:     '#A855F7',
    unknown:   '#6B7280',
  };

  let mapEl;
  let L;
  let map;
  let markerLayer;
  let markers = {};

  function makeIcon(type) {
    const color = TYPE_COLORS[type] ?? TYPE_COLORS.unknown;
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="36" viewBox="0 0 24 36">
      <path d="M12 0C5.373 0 0 5.373 0 12c0 9 12 24 12 24s12-15 12-24C24 5.373 18.627 0 12 0z"
            fill="${color}" stroke="#fff" stroke-width="1.5"/>
      <circle cx="12" cy="12" r="5" fill="#fff"/>
    </svg>`;
    return L.divIcon({ html: svg, className: '', iconSize: [24, 36], iconAnchor: [12, 36], popupAnchor: [0, -36] });
  }

  onMount(async () => {
    const leaflet = await import('leaflet');
    L = leaflet.default ?? leaflet;

    // India bounds: SW [6.7, 68.1] → NE [37.1, 97.4]
    const INDIA_BOUNDS = L.latLngBounds([6.7, 68.1], [37.1, 97.4]);

    map = L.map(mapEl, {
      zoomControl: true,
      maxBounds: INDIA_BOUNDS,
      maxBoundsViscosity: 0.85,
      minZoom: 4,
      center: [20.5937, 78.9629],
      zoom: 5,
    });

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19,
    }).addTo(map);

    markerLayer = L.layerGroup().addTo(map);

    setTimeout(() => {
      map.invalidateSize();
      map.fitBounds(INDIA_BOUNDS, { padding: [10, 10] });
    }, 150);
  });

  $: if (map && L && markerLayer) {
    markerLayer.clearLayers();
    markers = {};

    $filtered.forEach((c) => {
      const websiteLink = c.website
        ? `<a href="${c.website}" target="_blank" rel="noopener" style="color:#3b82f6">${c.website.replace(/^https?:\/\//, '')}</a>`
        : '';
      const popup = `<div style="min-width:140px;font-size:13px">
        <b>${c.name}</b>
        ${c.address ? `<br><span style="color:#6b7280;font-size:11px">${c.address}</span>` : ''}
        ${c.phone   ? `<br><span style="font-size:11px">${c.phone}</span>` : ''}
        ${websiteLink ? `<br>${websiteLink}` : ''}
      </div>`;

      const m = L.marker([c.lat, c.lon], { icon: makeIcon(c.type) })
        .bindPopup(popup)
        .on('click', () => { selectedId.set(c.id); dispatch('select', c.id); });

      markerLayer.addLayer(m);
      markers[c.id] = m;
    });
  }

  // Zoom to city when a search result comes in
  $: if (map && $cityBounds) {
    const { south, north, west, east } = $cityBounds;
    map.fitBounds([[south, west], [north, east]], { padding: [30, 30], maxZoom: 13 });
  }

  $: if (map && $selectedId != null && markers[$selectedId]) {
    map.flyTo(markers[$selectedId].getLatLng(), 15, { duration: 0.7 });
    markers[$selectedId].openPopup();
  }

  onDestroy(() => map?.remove());
</script>

<!-- wrapper gives the map a real pixel height via absolute fill -->
<div class="relative w-full h-full" style="min-height:500px">
  <div bind:this={mapEl} style="position:absolute;inset:0;" />
</div>
