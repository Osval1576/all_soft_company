// Resuelve la ruta del dashboard según el rol del usuario autenticado.
// NOTA: no tocar la lógica de rol acá (eso es parte del proyecto G).
export function dashboardRoute(user) {
  if (user?.is_superuser) return { name: "admin" };
  if (user?.is_staff) return { name: "tecnico-inbox" };
  return { name: "cliente" };
}
