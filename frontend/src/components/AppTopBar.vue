<template>
  <header class="topbar">
    <div class="topbar-left">
      <div class="brand">
        <span class="brand-mark">AS</span>
        <span class="brand-name">AllSafe</span>
      </div>
      <template v-if="title">
        <span class="sep">›</span>
        <span class="page-title">{{ title }}</span>
      </template>
    </div>

    <div class="topbar-right">
      <div class="user-chip">
        <span class="user-name">{{ auth.user?.username }}</span>
        <span class="role-badge">{{ roleLabel }}</span>
      </div>
      <button class="btn-icon" @click="toggle" :title="isDark ? 'Modo claro' : 'Modo oscuro'">
        <span v-if="isDark">&#9788;</span>
        <span v-else>&#9790;</span>
      </button>
      <button class="btn-logout" @click="auth.logout()">Salir</button>
    </div>
  </header>
</template>

<script setup>
import { computed } from 'vue'
import { useAuthStore } from '../stores/auth.store.js'
import { useTheme } from '../composables/useTheme.js'

defineProps({ title: { type: String, default: '' } })

const auth = useAuthStore()
const { isDark, toggle } = useTheme()

const roleLabel = computed(() => {
  if (auth.user?.is_superuser) return 'Admin'
  if (auth.user?.is_staff)     return 'Técnico'
  return 'Cliente'
})
</script>

<style scoped>
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 56px;
  padding: 0 20px;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
  gap: 12px;
}
.topbar-left { display: flex; align-items: center; gap: 10px; }
.brand { display: flex; align-items: center; gap: 8px; }
.brand-mark {
  width: 30px;
  height: 30px;
  background: var(--accent);
  color: var(--accent-fg);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: .5px;
}
.brand-name { font-weight: 700; font-size: 15px; color: var(--text); }
.sep { color: var(--text-3); font-size: 18px; line-height: 1; }
.page-title { color: var(--text-2); font-size: 14px; font-weight: 500; }
.topbar-right { display: flex; align-items: center; gap: 10px; }
.user-chip { display: flex; align-items: center; gap: 8px; }
.user-name { font-size: 13px; font-weight: 500; color: var(--text); }
.role-badge {
  font-size: 10px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 100px;
  background: var(--accent-light);
  color: var(--accent);
  text-transform: uppercase;
  letter-spacing: .4px;
}
.btn-icon {
  width: 34px;
  height: 34px;
  border-radius: var(--r-sm);
  border: 1px solid var(--border);
  background: var(--surface-2);
  color: var(--text-2);
  font-size: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all .15s;
}
.btn-icon:hover { background: var(--border); color: var(--text); }
.btn-logout {
  padding: 6px 14px;
  border-radius: var(--r-sm);
  background: var(--surface-2);
  border: 1px solid var(--border);
  color: var(--text-2);
  font-size: 13px;
  font-weight: 500;
  transition: all .15s;
}
.btn-logout:hover { background: var(--c-urgent-bg); color: var(--c-urgent); border-color: var(--c-urgent); }
</style>