<template>
  <div class="inbox">
    <aside class="tickets">
      <div class="top">
        <h2>Mis tickets</h2>
        <button class="refresh" @click="loadTickets" :disabled="loadingTickets">
          {{ loadingTickets ? "..." : "Actualizar" }}
        </button>
      </div>

      <div v-if="loadingTickets">Cargando...</div>

      <div v-else>
        <button
          v-for="t in tickets"
          :key="t.id"
          class="ticket"
          :class="{ active: selectedTicket?.id === t.id }"
          @click="selectTicket(t)"
        >
          <div class="title">{{ t.reference }} - {{ t.titulo }}</div>
          <div class="meta">{{ t.estado }} · {{ t.prioridad }}</div>
        </button>

        <div v-if="tickets.length === 0" class="empty-list">
          No tienes tickets asignados.
        </div>
      </div>
    </aside>

    <main class="chat">
      <div v-if="!selectedTicket" class="empty-chat">
        Selecciona un ticket para abrir el chat.
      </div>

      <ChatPanel
        v-else
        :ticket-id="selectedTicket.id"
        :title="`${selectedTicket.reference} - ${selectedTicket.titulo}`"
      />
    </main>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import ChatPanel from "../../components/ChatPanel.vue";
import { listMyAssignedTickets } from "../../api/tickets.api";

const tickets = ref([]);
const selectedTicket = ref(null);
const loadingTickets = ref(false);

async function loadTickets() {
  loadingTickets.value = true;
  try {
    tickets.value = await listMyAssignedTickets();
    if (tickets.value.length && !selectedTicket.value) {
      selectedTicket.value = tickets.value[0];
    }
  } finally {
    loadingTickets.value = false;
  }
}

function selectTicket(t) {
  selectedTicket.value = t;
}

onMounted(loadTickets);
</script>

<style scoped>
.inbox { display: grid; grid-template-columns: 340px 1fr; height: 100vh; gap: 12px; padding: 12px; background: #f3f4f6; }
.tickets { border: 1px solid #eee; border-radius: 8px; padding: 12px; overflow: auto; background: white; }
.top { display: flex; align-items: center; justify-content: space-between; }
.refresh { padding: 8px 10px; }
.ticket { width: 100%; text-align: left; padding: 10px; margin: 8px 0; border: 1px solid #eee; background: white; border-radius: 8px; cursor: pointer; }
.ticket.active { border-color: #2563eb; }
.title { font-weight: 600; }
.meta { font-size: 12px; color: #666; margin-top: 4px; }
.chat { min-height: 0; }
.empty-chat { height: 100%; display: grid; place-items: center; color: #666; border: 1px dashed #ccc; border-radius: 8px; background: white; }
.empty-list { color: #666; padding: 12px 0; }
</style>