// frontend/src/theme/apexTheme.js
function cssVar(name, fallback) {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v || fallback;
}

export function chartColors() {
  return {
    accent: cssVar("--accent", "#0038FF"),
    good: cssVar("--c-resolved", "#10B981"),
    warn: cssVar("--c-high", "#F59E0B"),
    bad: cssVar("--c-urgent", "#EF4444"),
    text: cssVar("--text-2", "#4A5163"),
    grid: cssVar("--border", "#E4E7EF"),
  };
}

export function baseOptions() {
  const c = chartColors();
  const mono = { fontFamily: "JetBrains Mono, monospace" };
  return {
    chart: { fontFamily: "Space Grotesk, sans-serif", toolbar: { show: false },
             animations: { easing: "easeout", speed: 400 }, background: "transparent" },
    grid: { borderColor: c.grid, strokeDashArray: 0, padding: { left: 4, right: 4 } },
    dataLabels: { enabled: false },
    stroke: { width: 2, curve: "smooth" },
    tooltip: { style: mono },
    xaxis: { axisBorder: { color: c.grid }, axisTicks: { color: c.grid },
             labels: { style: { colors: c.text, ...mono, fontSize: "11px" } } },
    yaxis: { labels: { style: { colors: c.text, ...mono, fontSize: "11px" } } },
    legend: { labels: { colors: c.text }, fontFamily: "Space Grotesk, sans-serif" },
  };
}
