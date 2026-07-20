// Mapea (colegio, producto) → ruta de la foto empacada en /public/prendas/.
// Las fotos se generan desde fotos-prendas/ optimizadas a webp ~400px.
// Si no existe foto, el componente debe usar onError para caer a un placeholder.

const quitarAcentos = (s) =>
  (s || '').normalize('NFD').replace(/[̀-ͯ]/g, '')

// Normaliza a slug: minúsculas, sin acentos ni puntuación, espacios→guiones.
export const slugify = (s) =>
  quitarAcentos(s)
    .toLowerCase()
    .replace(/[.'"]/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-|-$)/g, '')

// El colegio en la BD viene en MAYÚSCULAS ("MARILLAC"); "manyannet"/"padre manyanet" → manyanet.
const colegioSlug = (nombre) => {
  const s = slugify(nombre)
  if (s.includes('manyan')) return 'manyanet'
  if (s.includes('marillac')) return 'marillac'
  if (s.includes('adventista')) return 'adventista'
  return s
}

// El nombre de la prenda → slug de la carpeta de fotos.
// Ajuste: "Educación Física" en los nombres = "ed-fisica" en las carpetas.
const prendaSlug = (nombre) =>
  slugify(nombre).replace('educacion-fisica', 'ed-fisica')

/**
 * Devuelve la ruta de la foto de una prenda, o null si no hay colegio/producto.
 * No garantiza que el archivo exista: usa onError en el <img> para el fallback.
 */
export function fotoPrenda(colegioNombre, productoNombre) {
  if (!colegioNombre || !productoNombre) return null
  return `/prendas/${colegioSlug(colegioNombre)}/${prendaSlug(productoNombre)}.webp`
}
