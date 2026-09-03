// Pie del ticket térmico (Xprinter XP-N160, 80 mm): QR a la tienda.
// Compartido por Nueva Venta, Vender y la reimpresión de Buscar Facturas
// para que las tres impriman exactamente lo mismo.
import QRCode from 'qrcode'

export const URL_TIENDA = 'https://ralozcolsas.com'

// Datos del punto de venta. Van como valores por defecto (no sólo en
// Configuración) porque la config vive en localStorage: en un equipo nuevo,
// o si alguien borra los datos del navegador, el ticket saldría sin
// dirección ni teléfono.
export const EMPRESA_DEFAULT = {
  nombre: 'RALOZ COL SAS',
  nit: '',
  direccion: 'San Andresito de la 68 - Local M14',
  telefono: '321 341 2903',
  ciudad: 'Bogotá',
  email: '',
  web: 'ralozcolsas.com',
}

// Lo guardado en Configuración manda, pero un campo vacío no borra el dato
// real: un equipo con la configuración a medio llenar seguiría imprimiendo
// tickets sin dirección.
export function datosEmpresa() {
  const datos = { ...EMPRESA_DEFAULT }
  try {
    const guardado = JSON.parse(localStorage.getItem('raloz_empresa') || 'null') || {}
    for (const [campo, valor] of Object.entries(guardado)) {
      if (valor !== null && valor !== undefined && String(valor).trim() !== '') {
        datos[campo] = valor
      }
    }
  } catch { /* se queda con los valores por defecto */ }
  return datos
}

// El QR es siempre el mismo, así que se genera una vez por sesión: la
// impresión no puede quedarse esperando en cada venta.
let _qrCache = null

export async function qrTienda() {
  if (_qrCache !== null) return _qrCache
  try {
    _qrCache = await QRCode.toDataURL(URL_TIENDA, {
      margin: 2,               // zona blanca mínima o el lector no lo agarra
      width: 192,              // ~22 mm a 203 dpi, la resolución de la térmica
      errorCorrectionLevel: 'M',
    })
  } catch {
    _qrCache = ''              // sin QR el ticket igual debe salir
  }
  return _qrCache
}

export function bloqueQR(dataUrl) {
  if (!dataUrl) return ''
  return `<div class="qr">
    <img src="${dataUrl}" alt="QR ralozcolsas.com">
    <p class="qrt">Escanea y compra en línea</p>
    <p class="qrt b">ralozcolsas.com</p>
  </div>`
}

export const CSS_QR =
  '.qr{text-align:center;margin:8px 0 2px}' +
  '.qr img{width:22mm;height:22mm;display:block;margin:0 auto}' +
  '.qrt{font-size:10px;margin:1px 0}'

// Imprime sólo cuando el QR ya cargó: si se llama antes, sale el recuadro
// en blanco. El timeout es la red de seguridad para que un QR que falle
// nunca deje al cliente sin su ticket.
export function imprimirCuandoListo(w) {
  let hecho = false
  const go = () => {
    if (hecho) return
    hecho = true
    w.focus()
    w.print()
  }
  const img = w.document.querySelector('.qr img')
  if (!img || img.complete) { go(); return }
  img.addEventListener('load', go, { once: true })
  img.addEventListener('error', go, { once: true })
  setTimeout(go, 1500)
}
