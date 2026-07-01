<template>
  <div class="overlay" @click.self="$emit('close')">
    <div class="modal">
      <header><h3>{{ location?.id ? "Editar ubicación" : "Agregar ubicación" }}</h3><button @click="$emit('close')">×</button></header>

      <label>Buscar dirección (Google Places)
        <input ref="placesInput" placeholder="Comienza a escribir una dirección..." />
      </label>

      <div ref="mapEl" class="map"></div>

      <div class="grid">
        <label>Lat <input :value="form.lat" readonly /></label>
        <label>Lng <input :value="form.lng" readonly /></label>
      </div>

      <div class="grid">
        <label>Nombre interno <input v-model="form.name" required /></label>
        <label>Tipo
          <select v-model="form.type">
            <option value="SUCURSAL">Sucursal</option>
            <option value="OFICINA">Oficina</option>
            <option value="CENTRO">Centro de servicio</option>
          </select>
        </label>
      </div>

      <label>Dirección <input v-model="form.address" /></label>

      <div class="grid">
        <label>Teléfono <input v-model="form.phone" /></label>
        <label>Email <input v-model="form.email" type="email" /></label>
      </div>

      <I18nField label="Horario" v-model:es="form.hours_es" v-model:en="form.hours_en" />
      <I18nField label="Descripción" type="textarea" v-model:es="form.description_es" v-model:en="form.description_en" />

      <label>Foto</label>
      <ImageDrop v-model:file="photoFile" :existingUrl="location?.photo" />

      <label class="check"><input type="checkbox" v-model="form.is_active" /> Activo</label>

      <footer>
        <button @click="$emit('close')">Cancelar</button>
        <button class="primary" @click="save" :disabled="busy">{{ busy ? "..." : "Guardar" }}</button>
      </footer>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from "vue";
import { Loader } from "@googlemaps/js-api-loader";
import { landingAdminApi } from "../../../api/landing.api";
import I18nField from "./I18nField.vue";
import ImageDrop from "./ImageDrop.vue";

const props = defineProps({ location: Object });
const emit = defineEmits(["close", "saved"]);

const form = reactive({
  name: props.location?.name || "",
  address: props.location?.address || "",
  lat: props.location?.lat ?? 19.4326,
  lng: props.location?.lng ?? -99.1332,
  type: props.location?.type || "OFICINA",
  phone: props.location?.phone || "",
  email: props.location?.email || "",
  hours_es: props.location?.hours_es || "",
  hours_en: props.location?.hours_en || "",
  description_es: props.location?.description_es || "",
  description_en: props.location?.description_en || "",
  is_active: props.location?.is_active ?? true,
  order: props.location?.order ?? 0,
});
const photoFile = ref(null);
const busy = ref(false);
const placesInput = ref(null);
const mapEl = ref(null);

let marker = null;
let mapInstance = null;

async function initMap() {
  const settings = await landingAdminApi.getSettings();
  const key = settings.google_maps_api_key;
  if (!key) { alert("Configura primero la Google Maps API key en Contenido del sitio."); return; }
  const loader = new Loader({ apiKey: key, version: "weekly", libraries: ["maps", "marker", "places"] });
  const { Map } = await loader.importLibrary("maps");
  const { Marker } = await loader.importLibrary("marker");
  const { Autocomplete } = await loader.importLibrary("places");

  const center = { lat: Number(form.lat), lng: Number(form.lng) };
  mapInstance = new Map(mapEl.value, { center, zoom: 13, mapTypeControl: false });
  marker = new Marker({ position: center, map: mapInstance, draggable: true });
  marker.addListener("dragend", () => {
    const p = marker.getPosition();
    form.lat = Number(p.lat().toFixed(6));
    form.lng = Number(p.lng().toFixed(6));
  });

  const ac = new Autocomplete(placesInput.value, { fields: ["formatted_address", "geometry"] });
  ac.addListener("place_changed", () => {
    const place = ac.getPlace();
    if (!place.geometry) return;
    const loc = place.geometry.location;
    form.address = place.formatted_address || form.address;
    form.lat = Number(loc.lat().toFixed(6));
    form.lng = Number(loc.lng().toFixed(6));
    mapInstance.panTo(loc);
    marker.setPosition(loc);
  });
}

async function save() {
  busy.value = true;
  const fd = new FormData();
  Object.entries(form).forEach(([k, v]) => fd.append(k, v ?? ""));
  if (photoFile.value) fd.append("photo", photoFile.value);
  emit("saved", { id: props.location?.id, formData: fd });
  busy.value = false;
}

onMounted(initMap);
</script>

<style scoped>
.overlay { position: fixed; inset: 0; background: rgba(0,0,0,.4); display: grid; place-items: center; z-index: 100; }
.modal { background: var(--surface); border-radius: var(--r-lg); padding: 24px; width: min(640px, 94vw); display: flex; flex-direction: column; gap: 12px; max-height: 92vh; overflow-y: auto; }
header { display: flex; justify-content: space-between; align-items: center; }
header h3 { margin: 0; font-size: 16px; }
header button { background: transparent; border: none; font-size: 22px; color: var(--text-3); cursor: pointer; }
.map { height: 220px; border-radius: var(--r); background: var(--surface-2); }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
label { display: flex; flex-direction: column; gap: 4px; font-size: 12px; color: var(--text-2); font-weight: 600; }
label.check { flex-direction: row; align-items: center; gap: 8px; font-weight: 400; }
input, select { padding: 8px 10px; border: 1px solid var(--border); border-radius: var(--r); background: var(--surface); color: var(--text); font-size: 14px; }
footer { display: flex; justify-content: flex-end; gap: 8px; margin-top: 8px; }
footer button { padding: 8px 16px; border-radius: var(--r); border: 1px solid var(--border); background: var(--surface); color: var(--text); cursor: pointer; }
footer button.primary { background: var(--accent); color: var(--accent-fg); border-color: transparent; }
</style>
