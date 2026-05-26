import { ref } from 'vue'

const isDark = ref(localStorage.getItem('theme') === 'dark')

function applyTheme(dark) {
  document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light')
  localStorage.setItem('theme', dark ? 'dark' : 'light')
}

applyTheme(isDark.value)

export function useTheme() {
  function toggle() {
    isDark.value = !isDark.value
    applyTheme(isDark.value)
  }
  return { isDark, toggle }
}