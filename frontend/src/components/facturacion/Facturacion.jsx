import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../../services/api'
import toast from 'react-hot-toast'
import { Plus, Trash2, Save, DollarSign, User, School, ShoppingCart, Mail, MapPin, FileText, Printer } from 'lucide-react'

const TALLAS_NORMAL = ['4', '6', '8', '10', '12', '14', '16', 'S', 'M', 'L', 'XL', 'Única']
const TALLAS_MEDIAS = ['6-8', '8-10', '10-12', '12-14', '14-16']
const METODOS_PAGO = ['EFECTIVO', 'NEQUI', 'DAVIPLATA', 'BANCOLOMBIA', 'TRANSFERENCIA']
const DOMINIOS_EMAIL = ['gmail.com', 'hotmail.com', 'outlook.com', 'yahoo.com', 'outlook.es', 'live.com']

export default function Facturacion() {
  const navigate = useNavigate()
  const [colegios, setColegios] = useState([])
  const [productos, setProductos] = useState([])
  const [preciosColegio, setPreciosColegio] = useState({})
  const [form, setForm] = useState({
    id_colegio: '',
    cliente_nombre: '',
    cliente_telefono: '',
    cliente_email_user: '',
    cliente_email_domain: 'gmail.com',
    cliente_direccion: '',
    cliente_nit: '',
    fecha_factura: new Date().toISOString().split('T')[0],
    numero_factura: '',
    metodo_pago: 'EFECTIVO',
    estado_entrega: 'POR_ENTREGAR',
    entrega_inmediata: false,
    domicilio: false,
    valor_domicilio: '',
    abono: '',
    descuento: '',
    genero_estudiante: '',
    observaciones: '',
  })
  const [detalles, setDetalles] = useState([])
  const [saving, setSaving] = useState(false)
  const [loadingPrecios, setLoadingPrecios] = useState(false)

  // Post-save dialog
  const [showPostSave, setShowPostSave] = useState(false)
  const [lastFacturaId, setLastFacturaId] = useState(null)
  const [recibo, setRecibo] = useState(null)   // snapshot para imprimir el recibo

  useEffect(() => {
    Promise.all([
      api.get('/colegios'),
      api.get('/productos'),
    ]).then(([colRes, prodRes]) => {
      setColegios(colRes.data.colegios || [])
      setProductos(prodRes.data.productos || [])
    }).catch(() => toast.error('Error cargando datos iniciales'))
  }, [])

  const cargarPrecios = useCallback(async (colegioId) => {
    if (!colegioId) { setPreciosColegio({}); return }
    setLoadingPrecios(true)
    try {
      const res = await api.get('/precios', { params: { colegio_id: colegioId, per_page: 500 } })
      const mapa = {}
      for (const p of (res.data.precios || [])) {
        const key = `${p.id_producto}_${p.talla_grupo}`
        mapa[key] = p.precio_unitario
      }
      setPreciosColegio(mapa)
    } catch { setPreciosColegio({}) }
    finally { setLoadingPrecios(false) }
  }, [])

  const handleColegioChange = (colegioId) => {
    setForm(f => ({ ...f, id_colegio: colegioId }))
    cargarPrecios(colegioId)
    setDetalles(prev => prev.map(d => ({ ...d, precio_unitario: 0 })))
  }

  const obtenerTallaGrupo = (talla) => {
    const mapeo = {
      '4': '4', '6': '6-8', '8': '6-8', '10': '10-12', '12': '10-12',
      '14': '14-16', '16': '14-16', 'S': 'S-M', 'M': 'S-M', 'L': 'L', 'XL': 'XL',
      // Medias (ya son grupos, mapean directo)
      '6-8': '6-8', '8-10': '8-10', '10-12': '10-12', '12-14': '12-14', '14-16': '14-16',
    }
    return mapeo[talla] || talla
  }

  const buscarPrecio = (productoId, talla) => {
    if (!productoId || !talla) return 0
    const grupo = obtenerTallaGrupo(talla)
    return preciosColegio[`${productoId}_${grupo}`] || 0
  }

  const agregarLinea = () => {
    setDetalles([...detalles, { id_producto: '', producto_nombre: '', talla_individual: '', cantidad: 1, precio_unitario: 0 }])
  }

  const actualizarLinea = (idx, field, value) => {
    setDetalles(prev => {
      const nuevos = [...prev]
      nuevos[idx] = { ...nuevos[idx], [field]: value }
      if (field === 'id_producto' || field === 'talla_individual') {
        const productoId = field === 'id_producto' ? value : nuevos[idx].id_producto
        const talla = field === 'talla_individual' ? value : nuevos[idx].talla_individual
        const precioAuto = buscarPrecio(productoId, talla)
        if (precioAuto > 0) nuevos[idx].precio_unitario = precioAuto
      }
      if (field === 'id_producto') {
        const prod = productos.find(p => String(p.id_producto) === String(value))
        nuevos[idx].producto_nombre = prod?.nombre || ''
      }
      return nuevos
    })
  }

  const eliminarLinea = (idx) => setDetalles(detalles.filter((_, i) => i !== idx))

  const subtotal = detalles.reduce((sum, d) => sum + (d.cantidad * d.precio_unitario), 0)
  const valorDomicilio = form.domicilio ? (parseFloat(form.valor_domicilio) || 0) : 0
  const descuento = parseFloat(form.descuento) || 0
  const totalConDomicilio = Math.max(0, subtotal - descuento) + valorDomicilio
  const abono = parseFloat(form.abono) || 0
  const saldo = totalConDomicilio - abono

  // Fecha helpers
  const ajustarFecha = (dias) => {
    const fecha = new Date(form.fecha_factura + 'T12:00:00')
    fecha.setDate(fecha.getDate() + dias)
    setForm(f => ({ ...f, fecha_factura: fecha.toISOString().split('T')[0] }))
  }
  const fechaHoy = () => setForm(f => ({ ...f, fecha_factura: new Date().toISOString().split('T')[0] }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.id_colegio) { toast.error('Selecciona un colegio'); return }
    if (!form.cliente_nombre.trim()) { toast.error('Ingresa el nombre del cliente'); return }
    if (detalles.length === 0) { toast.error('Agrega al menos un producto'); return }

    for (let i = 0; i < detalles.length; i++) {
      if (!detalles[i].id_producto) { toast.error(`Línea ${i + 1}: Selecciona un producto`); return }
      if (!detalles[i].talla_individual) { toast.error(`Línea ${i + 1}: Selecciona una talla`); return }
      if (detalles[i].precio_unitario <= 0) { toast.error(`Línea ${i + 1}: El precio debe ser mayor a 0`); return }
    }
    if (abono > totalConDomicilio) { toast.error('El abono no puede ser mayor al total'); return }

    setSaving(true)

    // Combinar email
    const clienteEmail = form.cliente_email_user.trim()
      ? `${form.cliente_email_user.trim()}@${form.cliente_email_domain}`
      : ''

    const basePayload = {
      id_colegio: form.id_colegio,
      cliente_nombre: form.cliente_nombre,
      cliente_telefono: form.cliente_telefono,
      cliente_email: clienteEmail,
      cliente_direccion: form.cliente_direccion,
      cliente_nit: form.cliente_nit,
      genero_estudiante: form.genero_estudiante,
      fecha_factura: form.fecha_factura,
      metodo_pago: form.metodo_pago,
      entrega_inmediata: form.entrega_inmediata,
      observaciones: form.observaciones,
      numero_factura: form.numero_factura.trim() || undefined,
      domicilio: valorDomicilio,
      descuento: descuento,
      abono: abono,
      detalles: detalles.map(d => ({
        id_producto: parseInt(d.id_producto),
        talla_individual: d.talla_individual,
        cantidad: parseInt(d.cantidad),
        precio_unitario: parseFloat(d.precio_unitario),
      })),
    }

    const doPost = async (permitirSobreventa) => {
      const res = await api.post('/facturas', { ...basePayload, permitir_sobreventa: permitirSobreventa })
      const facturaCreada = res.data.factura
      toast.success(`Factura ${facturaCreada.numero_factura} creada exitosamente`)
      setLastFacturaId(facturaCreada.id_factura)
      // Snapshot del recibo ANTES de limpiar el formulario (para poder imprimirlo)
      setRecibo({
        numero: facturaCreada.numero_factura,
        fecha: form.fecha_factura,
        cliente: form.cliente_nombre,
        telefono: form.cliente_telefono,
        colegio: colegioNombre,
        items: detalles.map(d => ({
          nombre: productos.find(p => String(p.id_producto) === String(d.id_producto))?.nombre || 'Producto',
          talla: d.talla_individual,
          cantidad: parseInt(d.cantidad) || 0,
          precio: parseFloat(d.precio_unitario) || 0,
        })),
        subtotal, descuento, domicilio: valorDomicilio,
        total: totalConDomicilio, abono, saldo,
      })
      setShowPostSave(true)
      setDetalles([])
      setForm(f => ({
        ...f,
        cliente_nombre: '', cliente_telefono: '', cliente_email_user: '',
        cliente_direccion: '', cliente_nit: '', abono: '', descuento: '',
        genero_estudiante: '', observaciones: '', numero_factura: '',
        domicilio: false, valor_domicilio: '',
      }))
    }

    try {
      await doPost(false)
    } catch (err) {
      // Sin stock suficiente para entrega inmediata: ofrecer facturar igual
      if (err.response?.status === 409 && err.response?.data?.code === 'sin_stock_suficiente') {
        const faltantes = err.response.data.faltantes || []
        const lista = faltantes
          .map(x => `• ${x.producto} talla ${x.talla}: pides ${x.pedido}, hay ${x.disponible}`)
          .join('\n')
        if (window.confirm(`⚠️ No hay stock suficiente:\n\n${lista}\n\n¿Facturar de todos modos? (el stock quedará en 0)`)) {
          try {
            await doPost(true)
          } catch (e2) {
            toast.error(e2.response?.data?.error || 'Error al crear factura')
          }
        }
      } else {
        toast.error(err.response?.data?.error || 'Error al crear factura')
      }
    } finally {
      setSaving(false)
    }
  }

  const colegioNombre = colegios.find(c => String(c.id_colegio) === String(form.id_colegio))?.nombre || ''

  // === IMPRIMIR RECIBO (reusa el patrón window.open + @media print del proyecto) ===
  const imprimirRecibo = () => {
    if (!recibo) return
    let empresa = { nombre: 'RALOZ COL SAS', nit: '', direccion: '', telefono: '', ciudad: '', email: '', web: '' }
    try { empresa = { ...empresa, ...(JSON.parse(localStorage.getItem('raloz_empresa') || 'null') || {}) } } catch { /* usa default */ }
    const web = empresa.web || 'ralozcolsas.com'
    const money = (n) => '$' + Math.round(n || 0).toLocaleString('es-CO')

    const w = window.open('', '_blank')
    if (!w) { toast.error('Habilita las ventanas emergentes para imprimir el recibo'); return }

    const itemsHTML = recibo.items.map(it =>
      `<div class="it"><div class="itn">${it.nombre}${it.talla ? ' · T' + it.talla : ''}</div>` +
      `<div class="row"><span>${it.cantidad} x ${money(it.precio)}</span><span>${money(it.cantidad * it.precio)}</span></div></div>`
    ).join('')

    // Ticket 76 mm (Epson TM-U220, matriz de puntos): una sola columna, monoespaciada.
    w.document.write(`<!DOCTYPE html><html><head><meta charset="utf-8"><title>Ticket ${recibo.numero}</title>
    <style>
      @page { size: 76mm auto; margin: 0; }
      *{box-sizing:border-box}
      body{width:76mm;margin:0;padding:2mm 3mm;color:#000;line-height:1.4;
           font-family:'Courier New',monospace;font-size:12px}
      h1{font-size:16px;margin:0 0 2px}
      p{margin:1px 0}
      .c{text-align:center}
      .b{font-weight:bold}
      .big{font-size:14px;font-weight:bold}
      .sep{border-top:1px dashed #000;margin:6px 0}
      .row{display:flex;justify-content:space-between;gap:8px}
      .it{margin:4px 0}
      .itn{font-weight:bold}
      .terms{font-size:10px;line-height:1.35;margin-top:2px}
      @media print{body{margin:0}}
    </style></head><body>
    <div class="c">
      <h1 class="b">${empresa.nombre}</h1>
      ${empresa.nit ? `<p>NIT ${empresa.nit}</p>` : ''}
      ${empresa.direccion ? `<p>${empresa.direccion}</p>` : ''}
      ${empresa.ciudad ? `<p>${empresa.ciudad}</p>` : ''}
      ${empresa.telefono ? `<p>Cel: ${empresa.telefono}</p>` : ''}
      <p>${web}</p>
    </div>
    <div class="sep"></div>
    <div class="row"><span>Recibo:</span><span class="b">${recibo.numero}</span></div>
    <div class="row"><span>Fecha:</span><span>${recibo.fecha}</span></div>
    ${recibo.cliente ? `<div class="row"><span>Cliente:</span><span>${recibo.cliente}</span></div>` : ''}
    ${recibo.colegio ? `<div class="row"><span>Colegio:</span><span>${recibo.colegio}</span></div>` : ''}
    <div class="sep"></div>
    ${itemsHTML}
    <div class="sep"></div>
    ${recibo.descuento > 0 ? `<div class="row"><span>Descuento</span><span>-${money(recibo.descuento)}</span></div>` : ''}
    ${recibo.domicilio > 0 ? `<div class="row"><span>Domicilio</span><span>+${money(recibo.domicilio)}</span></div>` : ''}
    <div class="row big"><span>TOTAL</span><span>${money(recibo.total)}</span></div>
    ${recibo.abono > 0 ? `<div class="row"><span>Abono</span><span>${money(recibo.abono)}</span></div>` : ''}
    ${recibo.saldo > 0 ? `<div class="row big"><span>SALDO</span><span>${money(recibo.saldo)}</span></div>` : ''}
    <div class="sep"></div>
    <div class="terms">
      <div class="b c">GARANTÍA Y CAMBIOS</div>
      - Garantía de 6 meses por defectos de confección (costuras/hilo).<br>
      - Cambio por talla: 5 días hábiles, prenda sin uso, limpia y con etiquetas.<br>
      - Personalizados/bordados: sin cambio salvo defecto.<br>
      - Reembolsos por el mismo medio de pago.<br>
      - Conserva este ticket.<br>
      ${web}/terminos.html
    </div>
    <div class="sep"></div>
    <p class="c">¡Gracias por tu compra!</p>
    </body></html>`)
    w.document.close()
    w.focus()
    w.print()
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900">Nueva Venta</h2>
        {colegioNombre && (
          <span className="text-sm text-raloz-600 font-medium bg-raloz-50 px-3 py-1 rounded-full">{colegioNombre}</span>
        )}
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* === DATOS DEL CLIENTE === */}
        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <User size={18} className="text-gray-400" />
            <h3 className="text-lg font-semibold">Datos del Cliente</h3>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1"><School size={14} className="inline mr-1" />Colegio *</label>
              <select value={form.id_colegio} onChange={e => handleColegioChange(e.target.value)} className="input-field" required>
                <option value="">Seleccionar colegio...</option>
                {colegios.map(c => <option key={c.id_colegio} value={c.id_colegio}>{c.nombre}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Nombre del Cliente *</label>
              <input value={form.cliente_nombre} onChange={e => setForm({...form, cliente_nombre: e.target.value})} className="input-field" required placeholder="Nombre completo" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Teléfono</label>
              <input value={form.cliente_telefono} onChange={e => setForm({...form, cliente_telefono: e.target.value})} className="input-field" placeholder="300 123 4567" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Género Estudiante</label>
              <select value={form.genero_estudiante} onChange={e => setForm({...form, genero_estudiante: e.target.value})} className="input-field">
                <option value="">Seleccionar...</option>
                <option value="NIÑO">Niño</option>
                <option value="NIÑA">Niña</option>
              </select>
            </div>
            {/* Email con selector de dominio */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1"><Mail size={14} className="inline mr-1" />Email</label>
              <div className="flex">
                <input value={form.cliente_email_user} onChange={e => setForm({...form, cliente_email_user: e.target.value})}
                  className="input-field rounded-r-none flex-1" placeholder="usuario" />
                <span className="inline-flex items-center px-2 bg-gray-100 border border-l-0 border-gray-300 text-gray-500 text-sm">@</span>
                <select value={form.cliente_email_domain} onChange={e => setForm({...form, cliente_email_domain: e.target.value})}
                  className="input-field rounded-l-none w-36">
                  {DOMINIOS_EMAIL.map(d => <option key={d} value={d}>{d}</option>)}
                </select>
              </div>
            </div>
            {/* Dirección */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1"><MapPin size={14} className="inline mr-1" />Dirección</label>
              <input value={form.cliente_direccion} onChange={e => setForm({...form, cliente_direccion: e.target.value})} className="input-field" placeholder="Dirección" />
            </div>
            {/* NIT/CC */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1"><FileText size={14} className="inline mr-1" />NIT / CC</label>
              <input value={form.cliente_nit} onChange={e => setForm({...form, cliente_nit: e.target.value})} className="input-field" placeholder="NIT o Cédula" />
            </div>
            {/* Número de facturero + Fecha */}
            <div className="flex gap-3">
              <div className="w-36">
                <label className="block text-sm font-medium text-gray-700 mb-1"># Facturero <span className="text-gray-400 font-normal">(opcional)</span></label>
                <input value={form.numero_factura} onChange={e => setForm({...form, numero_factura: e.target.value})}
                  className="input-field w-full" placeholder="Ej: R-981" />
              </div>
              <div className="flex-1">
                <label className="block text-sm font-medium text-gray-700 mb-1">Fecha</label>
                <div className="flex gap-1">
                  <input type="date" value={form.fecha_factura} onChange={e => setForm({...form, fecha_factura: e.target.value})} className="input-field flex-1" />
                  <button type="button" onClick={() => ajustarFecha(-1)} className="px-2 py-1 text-xs bg-gray-100 border rounded hover:bg-gray-200">-1</button>
                  <button type="button" onClick={fechaHoy} className="px-2 py-1 text-xs bg-blue-100 text-blue-700 border rounded hover:bg-blue-200">Hoy</button>
                  <button type="button" onClick={() => ajustarFecha(1)} className="px-2 py-1 text-xs bg-gray-100 border rounded hover:bg-gray-200">+1</button>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* === PRODUCTOS === */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <ShoppingCart size={18} className="text-gray-400" />
              <h3 className="text-lg font-semibold">Productos</h3>
              {loadingPrecios && <span className="text-xs text-raloz-500 animate-pulse">Cargando precios...</span>}
            </div>
            <button type="button" onClick={agregarLinea} className="btn-secondary flex items-center gap-2">
              <Plus size={16} /> Agregar Producto
            </button>
          </div>

          {detalles.length === 0 ? (
            <div className="text-center py-12 border-2 border-dashed border-gray-200 rounded-lg">
              <ShoppingCart size={32} className="mx-auto text-gray-300 mb-2" />
              <p className="text-gray-400">Agrega productos a la factura</p>
              <button type="button" onClick={agregarLinea} className="mt-3 text-raloz-600 text-sm font-medium hover:underline">+ Agregar primer producto</button>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="hidden md:grid md:grid-cols-12 gap-3 px-3 text-xs font-medium text-gray-500 uppercase">
                <div className="col-span-4">Producto</div>
                <div className="col-span-2">Talla</div>
                <div className="col-span-1">Cant.</div>
                <div className="col-span-2">Precio Unit.</div>
                <div className="col-span-2 text-right">Subtotal</div>
                <div className="col-span-1"></div>
              </div>
              {detalles.map((det, idx) => (
                <div key={idx} className="p-3 bg-gray-50 rounded-lg space-y-2 md:space-y-0 md:grid md:grid-cols-12 md:gap-3 md:items-center">
                  {/* Producto */}
                  <div className="md:col-span-4">
                    <label className="md:hidden block text-xs font-medium text-gray-500 mb-1">Producto</label>
                    <select value={det.id_producto} onChange={e => actualizarLinea(idx, 'id_producto', e.target.value)} className="input-field w-full">
                      <option value="">Seleccionar producto...</option>
                      {productos.map(p => <option key={p.id_producto} value={p.id_producto}>{p.nombre}</option>)}
                    </select>
                  </div>
                  {/* Talla + Cantidad (juntas en móvil, sueltas en la tabla) */}
                  <div className="grid grid-cols-2 gap-2 md:contents">
                    <div className="md:col-span-2">
                      <label className="md:hidden block text-xs font-medium text-gray-500 mb-1">Talla</label>
                      {(() => {
                        const prod = productos.find(p => String(p.id_producto) === String(det.id_producto))
                        const tallas = prod?.tipo === 'medias' ? TALLAS_MEDIAS : TALLAS_NORMAL
                        return (
                          <select value={det.talla_individual} onChange={e => actualizarLinea(idx, 'talla_individual', e.target.value)} className="input-field w-full">
                            <option value="">Talla...</option>
                            {tallas.map(t => <option key={t} value={t}>{t}</option>)}
                          </select>
                        )
                      })()}
                    </div>
                    <div className="md:col-span-1">
                      <label className="md:hidden block text-xs font-medium text-gray-500 mb-1">Cant.</label>
                      <input type="number" inputMode="numeric" min="1" value={det.cantidad} onChange={e => actualizarLinea(idx, 'cantidad', parseInt(e.target.value) || 1)} className="input-field w-full text-center" />
                    </div>
                  </div>
                  {/* Precio unitario */}
                  <div className="md:col-span-2">
                    <label className="md:hidden block text-xs font-medium text-gray-500 mb-1">Precio Unit.</label>
                    <div className="relative">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm">$</span>
                      <input type="number" inputMode="numeric" min="0" value={det.precio_unitario} onChange={e => actualizarLinea(idx, 'precio_unitario', parseFloat(e.target.value) || 0)} className="input-field w-full pl-7" placeholder="Precio" />
                    </div>
                  </div>
                  {/* Subtotal + eliminar */}
                  <div className="flex items-center justify-between pt-1 border-t border-gray-200 md:border-0 md:pt-0 md:col-span-3 md:justify-end md:gap-3">
                    <span className="md:hidden text-xs font-medium text-gray-500">Subtotal</span>
                    <span className="text-base md:text-sm font-bold text-gray-900">${(det.cantidad * det.precio_unitario).toLocaleString('es-CO')}</span>
                    <button type="button" onClick={() => eliminarLinea(idx)} className="text-red-500 hover:text-red-600 p-2 md:p-1 rounded hover:bg-red-50 transition-colors" aria-label="Eliminar"><Trash2 size={18} /></button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* === PAGO === */}
        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <DollarSign size={18} className="text-gray-400" />
            <h3 className="text-lg font-semibold">Pago</h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Método de Pago</label>
              <select value={form.metodo_pago} onChange={e => setForm({...form, metodo_pago: e.target.value})} className="input-field">
                {METODOS_PAGO.map(m => <option key={m}>{m}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">¿Entregaste las prendas?</label>
              <div className="flex rounded-lg overflow-hidden border border-gray-300">
                <button type="button"
                  onClick={() => setForm({...form, entrega_inmediata: false})}
                  className={`flex-1 py-2 text-sm font-medium transition-colors ${
                    !form.entrega_inmediata
                      ? 'bg-amber-500 text-white'
                      : 'bg-white text-gray-600 hover:bg-gray-50'
                  }`}>
                  No, pendiente
                </button>
                <button type="button"
                  onClick={() => setForm({...form, entrega_inmediata: true})}
                  className={`flex-1 py-2 text-sm font-medium transition-colors ${
                    form.entrega_inmediata
                      ? 'bg-green-600 text-white'
                      : 'bg-white text-gray-600 hover:bg-gray-50'
                  }`}>
                  Sí, entregué
                </button>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">¿Domicilio?</label>
              <div className="flex rounded-lg overflow-hidden border border-gray-300">
                <button type="button"
                  onClick={() => setForm({...form, domicilio: false, valor_domicilio: ''})}
                  className={`flex-1 py-2 text-sm font-medium transition-colors ${
                    !form.domicilio ? 'bg-gray-500 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'
                  }`}>
                  No
                </button>
                <button type="button"
                  onClick={() => setForm({...form, domicilio: true})}
                  className={`flex-1 py-2 text-sm font-medium transition-colors ${
                    form.domicilio ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'
                  }`}>
                  Sí
                </button>
              </div>
              {form.domicilio && (
                <div className="relative mt-2">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">$</span>
                  <input type="number" inputMode="numeric" min="0" value={form.valor_domicilio}
                    onChange={e => setForm({...form, valor_domicilio: e.target.value})}
                    className="input-field pl-7 w-full" placeholder="Valor domicilio" />
                </div>
              )}
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Descuento</label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">$</span>
                <input type="number" inputMode="numeric" min="0" max={subtotal} value={form.descuento} onChange={e => setForm({...form, descuento: e.target.value})} className="input-field pl-7" placeholder="0" />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Abono Inicial</label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">$</span>
                <input type="number" inputMode="numeric" min="0" max={totalConDomicilio} value={form.abono} onChange={e => setForm({...form, abono: e.target.value})} className="input-field pl-7" placeholder="0" />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Observaciones</label>
              <input value={form.observaciones} onChange={e => setForm({...form, observaciones: e.target.value})} className="input-field" placeholder="Notas adicionales..." />
            </div>
          </div>

          {/* Summary */}
          <div className="bg-gray-50 rounded-lg p-4 space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">Subtotal ({detalles.length} items)</span>
              <span className="font-medium">${subtotal.toLocaleString('es-CO')}</span>
            </div>
            {descuento > 0 && (
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Descuento</span>
                <span className="font-medium text-orange-600">-${descuento.toLocaleString('es-CO')}</span>
              </div>
            )}
            {valorDomicilio > 0 && (
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Domicilio</span>
                <span className="font-medium text-blue-600">+${valorDomicilio.toLocaleString('es-CO')}</span>
              </div>
            )}
            {abono > 0 && (
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Abono</span>
                <span className="font-medium text-green-600">-${abono.toLocaleString('es-CO')}</span>
              </div>
            )}
            <div className="flex justify-between text-lg border-t pt-2">
              <span className="font-semibold text-gray-700">{abono > 0 ? 'Saldo Pendiente' : 'Total'}</span>
              <span className={`text-2xl font-bold ${saldo > 0 && abono > 0 ? 'text-red-600' : 'text-raloz-700'}`}>
                ${(abono > 0 ? saldo : totalConDomicilio).toLocaleString('es-CO')}
              </span>
            </div>
          </div>

          <button type="submit" disabled={saving || detalles.length === 0}
            className="btn-primary w-full mt-4 py-3 flex items-center justify-center gap-2 text-lg">
            <Save size={20} /> {saving ? 'Guardando...' : 'Crear Factura'}
          </button>
        </div>
      </form>

      {/* === DIALOG POST-GUARDADO === */}
      {showPostSave && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-md w-full p-6 text-center space-y-4">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto">
              <Save className="text-green-600" size={32} />
            </div>
            <h3 className="text-xl font-bold text-gray-900">Factura Guardada</h3>
            {recibo && (
              <button
                onClick={imprimirRecibo}
                className="w-full inline-flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2.5 px-6 rounded-lg"
              >
                <Printer size={18} /> Imprimir ticket
              </button>
            )}
            <p className="text-gray-600">¿Quedaron prendas debiendo de esta factura?</p>
            <div className="flex gap-3 justify-center">
              <button
                onClick={() => {
                  setShowPostSave(false)
                  navigate('/empaque')
                }}
                className="bg-red-600 hover:bg-red-700 text-white font-semibold py-2 px-6 rounded-lg"
              >
                Sí, registrar pendientes
              </button>
              <button
                onClick={() => setShowPostSave(false)}
                className="bg-green-600 hover:bg-green-700 text-white font-semibold py-2 px-6 rounded-lg"
              >
                No, todo listo
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
