<template>
  <section id="locations" ref="root" class="loc">
    <h2 class="title">{{ $t("nav.locations") }}</h2>
    <div v-if="!apiKey" class="warn">Google Maps no configurado.</div>
    <div v-else class="layout">
      <div ref="mapEl" class="map"></div>
      <ul class="list">
        <li v-for="l in locations" :key="l.id" @click="focus(l)">
          <p class="name">{{ l.name }}</p>
          <p class="addr">{{ l.address }}</p>
          <p v-if="l.phone" class="phone">{{ l.phone }}</p>
        </li>
      </ul>
    </div>
  </section>
</template>

<script setup>
import { ref, computed, watch, onMounted } from "vue";
import { Loader } from "@googlemaps/js-api-loader";
import { useScrollReveal } from "../../composables/useScrollReveal";

const props = defineProps({
  locations: { type: Array, default: () => [] },
  settings: { type: Object, default: null },
});

const root = ref(null);
const mapEl = ref(null);
useScrollReveal(() => root.value);

const apiKey = computed(() => props.settings?.google_maps_api_key || "");

let mapInstance = null;
let markers = [];

async function initMap() {
  if (!apiKey.value || !mapEl.value) return;
  const loader = new Loader({ apiKey: apiKey.value, version: "weekly", libraries: ["maps", "marker"] });
  const { Map, InfoWindow } = await loader.importLibrary("maps");
  const { Marker } = await loader.importLibrary("marker");

  const center = props.locations[0]
    ? { lat: Number(props.locations[0].lat), lng: Number(props.locations[0].lng) }
    : { lat: 19.4326, lng: -99.1332 };
  mapInstance = new Map(mapEl.value, { center, zoom: 12, mapTypeControl: false });

  markers.forEach(m => m.setMap(null));
  markers = props.locations.map(l => {
    const marker = new Marker({
      position: { lat: Number(l.lat), lng: Number(l.lng) },
      map: mapInstance, title: l.name,
    });
    const info = new InfoWindow({
      content: `<strong>${l.name}</strong><br>${l.address}${l.phone ? `<br>${l.phone}` : ""}`,
    });
    marker.addListener("click", () => info.open({ anchor: marker, map: mapInstance }));
    return marker;
  });
}

function focus(l) {
  if (!mapInstance) return;
  mapInstance.panTo({ lat: Number(l.lat), lng: Number(l.lng) });
  mapInstance.setZoom(14);
}

onMounted(() => { if (apiKey.value && props.locations.length) initMap(); });
watch(() => [apiKey.value, props.locations.length], () => initMap());
</script>

<style scoped>
.loc { padding: 64px 0; }
.title { text-align: center; font-size: 32px; margin: 0 0 36px; }
.warn { text-align: center; color: var(--text-3); padding: 32px; border: 1px dashed var(--border); border-radius: var(--r); }
.layout { display: grid; grid-template-columns: 2fr 1fr; gap: 16px; }
@media (max-width: 720px) { .layout { grid-template-columns: 1fr; } }
.map { height: 420px; border-radius: var(--r-lg); overflow: hidden; background: var(--surface-2); }
.list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 10px; max-height: 420px; overflow-y: auto; }
.list li { background: var(--surface); border: 1px solid var(--border); border-radius: var(--r); padding: 14px; cursor: pointer; transition: background .15s; }
.list li:hover { background: var(--surface-2); }
.list .name { font-weight: 600; margin: 0; font-size: 14px; }
.list .addr { color: var(--text-2); margin: 4px 0 0; font-size: 13px; }
.list .phone { color: var(--text-3); margin: 4px 0 0; font-size: 12px; }
</style>
