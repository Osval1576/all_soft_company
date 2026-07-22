import { ref } from 'vue'

// `theme` en localStorage == elección EXPLÍCITA del usuario (sólo la escribe el
// toggle). Al cargar aplicamos el tema al DOM pero NO lo persistimos, así un
// usuario nuevo queda con `theme === null` y la org puede imponer su default.
const stored = localStorage.getItem('theme')
const isDark = ref(stored === 'dark')

function setDom(dark) {
  document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light')
}

setDom(isDark.value)

// Aplica el tema oscuro por defecto de la org, pero sólo si el usuario nunca
// eligió un tema por su cuenta: su elección persistida siempre gana. No se
// persiste, porque es un default de la organización, no una elección del usuario.
export function applyDefaultTheme(dark) {
  if (localStorage.getItem('theme') !== null) return
  isDark.value = !!dark
  setDom(isDark.value)
}

export function useTheme() {
  function toggle() {
    isDark.value = !isDark.value
    setDom(isDark.value)
    localStorage.setItem('theme', isDark.value ? 'dark' : 'light')
  }
  return { isDark, toggle }
}
