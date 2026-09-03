// Pie del ticket térmico (Xprinter XP-N160, 80 mm): QR a la tienda.
// Compartido por Nueva Venta, Vender y la reimpresión de Buscar Facturas
// para que las tres impriman exactamente lo mismo.
import QRCode from 'qrcode'

export const URL_TIENDA = 'https://ralozcolsas.com'

// Logo para la térmica: silueta en blanco y negro puro, incrustada.
// La impresora sólo marca o no marca — no tiene grises — y un umbral por
// luminancia habría borrado el amarillo del logo, que es casi tan claro
// como el papel. Va embebido para que imprima aunque no haya internet.
const LOGO_TERMICO = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAUAAAAFxAQAAAAAqzUwPAAAG3klEQVR42sVbO3LbSBBtPLJsBq4iQ2XiERQ6Wx5FNzGCPcAeQXsT+AY8ArZqA4WwSwGsAjEbkCDAmdef1bJqFdHyY890z+vpz7SkkevP55RSSkkeE/nBAvirqtYiJ/mrOkjxg9t/nnayEpHv8IDyU6QRkXTwgOkgX0VEvtc5Mv/FNo0iIrLKlcm/+EOq+rJbc2mRgzxfvuEAj/Jw/rB3gG+yPn/42wGe6tX0wQZKI5fT+sMBHqfd/XSAb3KxTKpt4Em+SLk2AUqNq2wb2FT1JNsGHhenZAL7K+BoAwd5KjfJgOPCACYw1V9KtjKgNNffvtjA9vqps4HdZMiFNhTI9KLA2ZAzLyhwmN2gMYGj7Aq9nD3OalNgks28XVNivZ63G1x6tIHzGaaoxCstOLCtJDekK7E1gd1MxM4E9uVHbelDbkh3j6MJHLJbNCIxRYGT/nA84GpxTeLuX+9xOhqIw9y4xC4K7KPA8NKDCZy9Ky5xvPse090lXuijABt8QGJz9z2Gge1dJB4KQv4vyoSB/V0k1mPuCwGJ6yjQljjE9lh9yDzjfQzex4CIS+xiwPWHtE4GcBOX2MaAu7jEJgbcf8xnah14KCosLZMKL51iwOomDhvAT4xQ30hB25cu858Z3keBXRTYRoFN+JK6t9YpChyjwCEK7KPALgpso8AmCExRVxgZ64lt5demND+C1lHqwiiwjQKboDJ5Jyb59bWz9BuLdwgqTYFtFNhIUOssCFejIjHRRQnwPequfRTYRbOUNiqxkZh5iubc555LHHlMRuQ64cDXKLDlwRtBpUWKaFQgHnmjMilRHjFKEGCvJO8IOQxTplEQiFonJ0X5zYpnpGM0cqmhHzFKlMBWSzoRVLrQukzVt7SUStF4/a4mnXBviT0FdmrllwFfJKh1FazYUzRLGfXrF9GkA5511hR41MsGeJTYUeci2v7GnjSSUZLfGPzXJtg3640ohmimBYcSa0oKQokta1Qmq6iCc0vsGXCwOhvLPf7YGcEbNiUqStzGqmyWS1vWWUo8mSUnbKWf2dKm0kuJnZkBIZp8w7TOml0pCZZ1FhIZJZ7Y0oPd7JqXtq2zkGhbZwF8sa+6eWmTEosvnZwuBCyl92xpR+lZoqP0DPTqMcQoMV+k7KQf2dvw6HVUEKPEbB7POleJ5JZYURM0XsU+Le1Q4ioxuY0pBK0zLe0qPUns3DoJ0RIdQUpMe3Stc5GY7FtiBr57lJiW9q1zkehSYgL6Sl+W9pU+S0yBXiVilLgsbSUdNxJfA/1rRLs2CFrnvMeAdQQxSpyBo0+J89IBSpwldj4lzsCXSEO8SjGlBTFKiEClRFOUhz0vKx+LsR2eh55K4h45JfriV4QSX0TehmI3PHB0q3yPJ670ccyXVgJHk6+UOm4dkW/Z0pwSKVcSzGHW7NpiSm9T6rKYmaBQostpCoUSbX40GHiHrSkCLgsc51qput0jL01OZUBqKSVIz4AXbq8iWZsdqtLZ0UChhEReWKYC8dEpGVdTFrQ1Z+JE1pMH984eN1PfdXCAu+m4Rgc4Wef2aFa0//hno1ynhBLLkplrrdxvYJR4J1kqmNI94SqY0h2pt9kQ4vVSH8xKeXGpV6MhcaV0VKBSQsvsF5QYGFlBouUrK+xAlG6dtvPVD2qW2xuUuHUG8FuiPBqYt8SgA3c3YoyT2d9wJunAw61Nass6rH9UaL1Sm2zQKXF7NBnwIbsf1GnFfZb69RowU1rr9GeUuIkMVd5XTvDbOCKf9GYzdD+4PRoYlDAGJZ+LkNfGlF5wHE7PVS+2D0qrGM68BZ+o3JQ1Ap+ofCpTTH4yBzKcUWuvFkOgmVpZT+SIvpji9pYojc46mju2ezZ6+ezHv2UTpC3ygVzriib1o9mUs1vIaz43UxfAB06hpgDuzYcYGGWW95Al1GtQOkztTFR+UrZQDEpulIK5mH/cKfVW8UjyrE0q1drrXU+dAeUtsbZdAc4bGUo53BmQUULcub294/Mg53GwXgaXFUQr5L+guq0yRrY2hsjqJXAjznwoSLthzSwOoikifqA6A9ixMWegr6rM4mD7Z84AjxLZFMne7FLUWrdwo7KnsjspjTWnkR8NmAgQZwDbVEWcAbQDVWvKHOyO1KC+8RNngFKhFUcDeomQowE9iU1pcdAOFHEG0LlIKH3G5LUft52AJ1ClMyA6Qg9+xR7oEW7cnuvpDHwKtuwi0bLmMywshIBTojwa8LhSOgO4c5bOADpTK3SEdS9+e3ZQuoVSDiZByan3uTMgOAxcQ4m6m/LPDR5CuU4LrjTphyt1YF4wbqEUEsXRABKaTR3wu/h/XyAiAi1a5iEETxL62530D5dbkhT6YkRhAAAAAElFTkSuQmCC'

export function bloqueLogo() {
  return `<div class="logo"><img src="${LOGO_TERMICO}" alt=""></div>`
}

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
  '.logo{text-align:center;margin:0 0 3px}' +
  '.logo img{width:26mm;display:block;margin:0 auto}' +
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
  const pendientes = Array.from(w.document.images).filter(i => !i.complete)
  if (!pendientes.length) { go(); return }
  let faltan = pendientes.length
  const una = () => { if (--faltan <= 0) go() }
  pendientes.forEach(i => {
    i.addEventListener('load', una, { once: true })
    i.addEventListener('error', una, { once: true })
  })
  setTimeout(go, 1500)
}
