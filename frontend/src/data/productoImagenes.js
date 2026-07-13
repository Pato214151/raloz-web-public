// Fotos de producto por colegio+producto — espejo de Raloz/js/data/imagenes.js.
// Las imágenes se sirven desde la tienda pública (Cloudflare). Si un producto no
// tiene foto aquí, la tarjeta cae a un ícono por tipo.
// Colegio 2 (Adventista) aún no tiene fotos cargadas.

export const TIENDA_BASE = 'https://ralozcolsas.com/'

export const PRODUCTO_IMAGENES = {
  1: {
    1: 'img/productos/marillac/pantalon-diario-nino/pantalondelantero.jpeg',
    2: 'img/productos/marillac/camisa-cuello-nino/camisacuellonino.jpeg',
    3: 'img/productos/marillac/blazer/blaizerdelantero.jpeg',
    4: 'img/productos/marillac/chaleco/chaleco.jpeg',
    6: 'img/productos/marillac/jardinera-nina/jardineradelantero.jpeg',
    7: 'img/productos/marillac/blusa-nina/camisacuellonino.jpeg',
    8: 'img/productos/marillac/pantalon-ed-fisica/pantalonedufrontal.jpeg',
    9: 'img/productos/marillac/camiseta-ed-fisica/camisetaedu.jpeg',
    10: 'img/productos/marillac/chaqueta-ed-fisica/chaquetaedufrontal.jpeg',
    11: 'img/productos/marillac/pantaloneta/pantaloneta trasera.jpeg',
    12: 'img/productos/marillac/medias-ed-fisica/medias.jpeg',
    13: 'img/productos/marillac/uniformecompleto-diario-nino/uniformecompletonino.jpeg',
    14: 'img/productos/marillac/uniformecompleto-diario-nina/unifromednina.jpeg',
    15: 'img/productos/marillac/sudadera-completa/sudaderacompleta.jpeg',
  },
  3: {
    1: 'img/productos/manyanet/pantalon-diario-nino/pantalondiarionino.jpeg',
    2: 'img/productos/manyanet/camisa-cuello-nino/camisacuellonino.jpeg',
    5: 'img/productos/manyanet/chaqueta-diario/chaquetadiariodelantero.jpeg',
    6: 'img/productos/manyanet/jardinera-nina/jardineratraserodelantero.jpeg',
    7: 'img/productos/manyanet/blusa-nina/blusatrasero.jpeg',
    8: 'img/productos/manyanet/pantalon-ed-fisica/pantalonedu.jpeg',
    11: 'img/productos/manyanet/pantaloneta/pantaloneta.jpeg',
    12: 'img/productos/manyanet/medias-ed-fisica/medias-ed-fisica.jpeg',
    15: 'img/productos/manyanet/uniformecompleto-edu-nino/uniformecompleto-edu-nino.jpeg',
    16: 'img/productos/manyanet/uniformecompleto-diario-nino/uniformecompletodiarionino.jpeg',
    17: 'img/productos/manyanet/uniformecompleto-diario-nina/uniformediarioninacompleto.jpeg',
    19: 'img/productos/manyanet/camiseta-ed-fisica-nino/camisetaninodelantero.jpeg',
    20: 'img/productos/manyanet/camiseta-ed-fisica-nina/camisetaeduninafrontal.jpeg',
    21: 'img/productos/manyanet/chaqueta-ed-fisica-nino/chaquetaedudelantero.jpeg',
    22: 'img/productos/manyanet/chaqueta-ed-fisica-nina/chaquetaedunina.jpeg',
  },
}

export function fotoProducto(idColegio, idProducto) {
  const rel = PRODUCTO_IMAGENES[idColegio]?.[idProducto]
  return rel ? encodeURI(TIENDA_BASE + rel) : null
}
