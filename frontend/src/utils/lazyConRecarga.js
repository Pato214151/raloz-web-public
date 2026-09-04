// Carga diferida a prueba de despliegues.
//
// Cuando se despliega una versión nueva, los archivos .js del build anterior
// dejan de existir. Un panel abierto sigue pidiendo los viejos, la carga
// falla y la pantalla queda EN BLANCO — sin error visible ni forma de salir
// salvo saber limpiar la caché. Para quien atiende el mostrador eso es el
// sistema "dañado".
//
// Aquí lo detectamos y recargamos una sola vez, con una marca en
// sessionStorage para no caer en un bucle de recargas si el fallo es otro
// (sin internet, servidor caído).
import { lazy } from 'react'

const MARCA = 'raloz_recarga_chunk'

export function lazyConRecarga(importar) {
  return lazy(async () => {
    try {
      const mod = await importar()
      try { sessionStorage.removeItem(MARCA) } catch { /* modo privado */ }
      return mod
    } catch (e) {
      let yaRecargue = false
      try { yaRecargue = sessionStorage.getItem(MARCA) === '1' } catch { /* ignore */ }
      if (!yaRecargue) {
        try { sessionStorage.setItem(MARCA, '1') } catch { /* ignore */ }
        window.location.reload()
        // Devolvemos algo mientras el navegador recarga, para no romper React.
        return { default: () => null }
      }
      throw e
    }
  })
}
