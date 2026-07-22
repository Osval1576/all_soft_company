import { applyDefaultTheme } from './useTheme'

// Sobreescribe en runtime las CSS custom properties del acento a partir del
// branding de la org. Un único punto de inyección: el resto de componentes ya
// consume var(--accent) y derivados. Los tokens neutros NO se tocan.
const ACCENT_VARS = ['--accent', '--accent-hover', '--accent-2', '--accent-light', '--accent-glow']

const HEX_COLOR_RE = /^#[0-9A-Fa-f]{6}$/

export function applyBranding(branding) {
  if (!branding || !HEX_COLOR_RE.test(branding.accent_color || '')) {
    clearBranding()
  } else {
    const c = branding.accent_color
    const root = document.documentElement.style
    root.setProperty('--accent', c)
    root.setProperty('--accent-hover', `color-mix(in srgb, ${c}, black 18%)`)
    root.setProperty('--accent-2', c)
    root.setProperty('--accent-light', `color-mix(in srgb, ${c} 8%, transparent)`)
    root.setProperty('--accent-glow', `color-mix(in srgb, ${c} 35%, transparent)`)
  }
  // Tema oscuro por defecto de la org: sólo si el usuario no eligió tema.
  if (branding && branding.default_dark) {
    applyDefaultTheme(true)
  }
}

export function clearBranding() {
  const root = document.documentElement.style
  ACCENT_VARS.forEach((v) => root.removeProperty(v))
}
