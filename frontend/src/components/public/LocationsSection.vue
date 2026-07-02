<template>
  <section id="locations" ref="root" class="loc">
    <div class="loc-inner">
      <p class="eyebrow">{{ $t("nav.locations") }}</p>

      <h2 class="lead">
        Estamos<span class="lead-accent"> cerca.</span>
      </h2>

      <div v-if="!apiKey && !locations.length" class="warn">
        <p>{{ $t("loading") }}</p>
      </div>

      <div v-else-if="!apiKey" class="warn">
        <p>Configura la API key de Google Maps desde el admin para ver el mapa.</p>
      </div>

      <div v-else class="layout">
        <div ref="mapEl" class="map"></div>

        <ul class="list">
          <li
            v-for="l in locations"
            :key="l.id"
            @click="focus(l)"
            :class="{ active: activeId === l.id }"
          >
            <p class="list-name">{{ l.name }}</p>
            <p class="list-addr">{{ l.address }}</p>
            <p v-if="l.phone" class="list-phone">{{ l.phone }}</p>
          </li>
        </ul>
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from "vue";
import { Loader } from "@googlemaps/js-api-loader";
import { useScrollReveal } from "../../composables/useScrollReveal";
import { useTheme } from "../../composables/useTheme";

const props = defineProps({
  locations: { type: Array, default: () => [] },
  settings: { type: Object, default: null },
});

const root = ref(null);
const mapEl = ref(null);
const activeId = ref(null);
const { isDark } = useTheme();

useScrollReveal(() => root.value);

const apiKey = computed(() => props.settings?.google_maps_api_key || "");

const stylesLight = [
  { elementType: "geometry", stylers: [{ color: "#F5F7FB" }] },
  { elementType: "labels.text.stroke", stylers: [{ color: "#FAFBFC" }] },
  { elementType: "labels.text.fill", stylers: [{ color: "#4A5163" }] },
  { featureType: "administrative", elementType: "geometry.stroke", stylers: [{ color: "#DEE3EE" }] },
  { featureType: "road", elementType: "geometry", stylers: [{ color: "#E4E7EF" }] },
  { featureType: "road.arterial", elementType: "geometry", stylers: [{ color: "#DDE2ED" }] },
  { featureType: "road.highway", elementType: "geometry", stylers: [{ color: "#C4CBD9" }] },
  { featureType: "water", elementType: "geometry", stylers: [{ color: "#E1E9FF" }] },
  { featureType: "water", elementType: "labels.text.fill", stylers: [{ color: "#5B7CFF" }] },
  { featureType: "landscape", elementType: "geometry", stylers: [{ color: "#F5F7FB" }] },
  { featureType: "poi", elementType: "geometry", stylers: [{ color: "#EEF1F8" }] },
  { featureType: "poi.park", elementType: "geometry", stylers: [{ color: "#E2ECE6" }] },
  { featureType: "transit", stylers: [{ visibility: "off" }] },
];

const stylesDark = [
  { elementType: "geometry", stylers: [{ color: "#0B101B" }] },
  { elementType: "labels.text.stroke", stylers: [{ color: "#05090F" }] },
  { elementType: "labels.text.fill", stylers: [{ color: "#A9B4C9" }] },
  { featureType: "administrative", elementType: "geometry.stroke", stylers: [{ color: "#1F2A44" }] },
  { featureType: "road", elementType: "geometry", stylers: [{ color: "#131A2A" }] },
  { featureType: "road.arterial", elementType: "geometry", stylers: [{ color: "#182035" }] },
  { featureType: "road.highway", elementType: "geometry", stylers: [{ color: "#243255" }] },
  { featureType: "water", elementType: "geometry", stylers: [{ color: "#080D18" }] },
  { featureType: "water", elementType: "labels.text.fill", stylers: [{ color: "#5B7CFF" }] },
  { featureType: "landscape", elementType: "geometry", stylers: [{ color: "#0B101B" }] },
  { featureType: "poi", elementType: "geometry", stylers: [{ color: "#0E1522" }] },
  { featureType: "poi.park", elementType: "geometry", stylers: [{ color: "#122032" }] },
  { featureType: "transit", stylers: [{ visibility: "off" }] },
];

let mapInstance = null;
let markers = [];

function markerIcon(active = false) {
  const color = active ? "#00E5FF" : (isDark.value ? "#5B7CFF" : "#0038FF");
  const stroke = isDark.value ? "#05090F" : "#FAFBFC";
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 20 20">
      <circle cx="10" cy="10" r="7" fill="${color}" stroke="${stroke}" stroke-width="3"/>
    </svg>
  `;
  return "data:image/svg+xml;charset=UTF-8," + encodeURIComponent(svg);
}

function cleanup() {
  markers.forEach(m => m.setMap && m.setMap(null));
  markers = [];
  if (mapInstance && window.google?.maps?.event) {
    window.google.maps.event.clearInstanceListeners(mapInstance);
  }
  mapInstance = null;
}

async function initMap() {
  if (!apiKey.value || !mapEl.value || !props.locations.length) return;
  const loader = new Loader({ apiKey: apiKey.value, version: "weekly", libraries: ["maps", "marker"] });
  const { Map, InfoWindow } = await loader.importLibrary("maps");
  const { Marker } = await loader.importLibrary("marker");

  cleanup();

  const first = props.locations[0];
  const center = { lat: Number(first.lat), lng: Number(first.lng) };

  mapInstance = new Map(mapEl.value, {
    center,
    zoom: 12,
    styles: isDark.value ? stylesDark : stylesLight,
    disableDefaultUI: true,
    zoomControl: true,
    gestureHandling: "cooperative",
    backgroundColor: isDark.value ? "#0B101B" : "#F5F7FB",
  });

  markers = props.locations.map(l => {
    const marker = new Marker({
      position: { lat: Number(l.lat), lng: Number(l.lng) },
      map: mapInstance,
      title: l.name,
      icon: { url: markerIcon(false), scaledSize: new window.google.maps.Size(20, 20), anchor: new window.google.maps.Point(10, 10) },
    });
    const info = new InfoWindow({
      content: `<div style="font-family:'Inter',sans-serif;font-size:13px;color:#0A0F1F;padding:2px 4px;line-height:1.5"><strong style="font-family:'Space Grotesk',sans-serif">${l.name}</strong><br>${l.address}${l.phone ? `<br><span style="color:#4A5163">${l.phone}</span>` : ""}</div>`,
    });
    marker.addListener("click", () => {
      activeId.value = l.id;
      info.open({ anchor: marker, map: mapInstance });
    });
    marker._id = l.id;
    return marker;
  });
}

function focus(l) {
  activeId.value = l.id;
  if (!mapInstance) return;
  mapInstance.panTo({ lat: Number(l.lat), lng: Number(l.lng) });
  mapInstance.setZoom(14);
  markers.forEach(m => {
    m.setIcon({
      url: markerIcon(m._id === l.id),
      scaledSize: new window.google.maps.Size(20, 20),
      anchor: new window.google.maps.Point(10, 10),
    });
  });
}

onMounted(() => { initMap(); });
watch(() => [apiKey.value, props.locations.length, isDark.value], () => initMap());
onBeforeUnmount(cleanup);
</script>

<style scoped>
.loc { border-top: 0.5px solid var(--border); padding: 96px 32px 80px; }
.loc-inner { max-width: 1240px; margin: 0 auto; }

.eyebrow {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: var(--text-3);
  margin: 0 0 20px;
}

.lead {
  font-family: var(--font-display);
  font-weight: 500;
  font-size: clamp(28px, 4vw, 48px);
  line-height: 1.08;
  letter-spacing: -0.02em;
  margin: 0 0 48px;
  color: var(--text);
}
.lead-accent { color: var(--accent); }
[data-theme="dark"] .lead-accent { color: var(--accent-2); }

.warn {
  text-align: center;
  padding: 48px 24px;
  border: 0.5px dashed var(--border);
  border-radius: var(--r-lg);
  color: var(--text-3);
  font-family: var(--font-mono);
  font-size: 12px;
  letter-spacing: 1px;
  text-transform: uppercase;
}

.layout {
  display: grid;
  grid-template-columns: 1.6fr 1fr;
  gap: 24px;
  align-items: stretch;
}

.map {
  min-height: 460px;
  border-radius: var(--r-lg);
  overflow: hidden;
  border: 0.5px solid var(--border);
  background: var(--surface-2);
}

.list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0;
  max-height: 460px;
  overflow-y: auto;
}
.list li {
  cursor: pointer;
  padding: 20px 16px;
  border-bottom: 0.5px solid var(--border);
  transition: background .15s;
}
.list li:hover { background: var(--surface-2); }
.list li.active {
  background: var(--accent-light);
  border-left: 2px solid var(--accent);
  padding-left: 14px;
}

.list-name {
  font-family: var(--font-display);
  font-weight: 500;
  font-size: 16px;
  color: var(--text);
  margin: 0;
  letter-spacing: -0.01em;
}
.list-addr {
  font-size: 13px;
  color: var(--text-2);
  margin: 6px 0 0;
  line-height: 1.5;
}
.list-phone {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--accent);
  margin: 8px 0 0;
  letter-spacing: 1px;
}
[data-theme="dark"] .list-phone { color: var(--accent-2); }

@media (max-width: 800px) {
  .loc { padding: 56px 20px 48px; }
  .layout { grid-template-columns: 1fr; }
  .map { min-height: 320px; }
  .list { max-height: none; }
}
</style>
