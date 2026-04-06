<template>
  <div style="max-width:420px;margin:60px auto;">
    <h2>Login</h2>

    <form @submit.prevent="onSubmit">
      <div style="margin:10px 0;">
        <input v-model="username" placeholder="username" style="width:100%;padding:10px;" />
      </div>

      <div style="margin:10px 0;">
        <input v-model="password" type="password" placeholder="password" style="width:100%;padding:10px;" />
      </div>

      <button :disabled="loading" style="padding:10px 14px;">
        {{ loading ? "Entrando..." : "Entrar" }}
      </button>

      <div v-if="error" style="margin-top:10px;color:#b91c1c;">{{ error }}</div>
    </form>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { useAuthStore } from "../stores/auth.store";

const auth = useAuthStore();
const username = ref("");
const password = ref("");
const loading = ref(false);
const error = ref("");

async function onSubmit() {
  loading.value = true;
  error.value = "";
  try {
    await auth.login(username.value, password.value);
   } catch (e) {
  error.value =
    e?.response?.data?.detail ||
    JSON.stringify(e?.response?.data || {}) ||
    e.message ||
    "Error";
} finally {
    loading.value = false;
  }
}
</script>