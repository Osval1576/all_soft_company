// frontend/src/utils/metricsFormat.js
export function fmtPct(v) {
  return v === null || v === undefined ? "—" : `${Math.round(v * 100)}%`;
}

export function fmtNum(v) {
  return v === null || v === undefined ? "—" : String(v);
}

export function fmtMin(v) {
  if (v === null || v === undefined) return "—";
  const m = Math.round(v);
  if (m < 60) return `${m} min`;
  const h = Math.floor(m / 60);
  const rem = m % 60;
  return rem ? `${h}h ${rem}m` : `${h}h`;
}
