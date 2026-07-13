// Resuelve la ruta del dashboard según el rol del usuario autenticado.
export function dashboardRoute(user) {
  if (user?.role === "ADMIN") return { name: "admin" };
  if (user?.role === "AGENT") return { name: "tecnico-inbox" };
  return { name: "cliente" };
}
