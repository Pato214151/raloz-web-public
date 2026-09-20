/**
 * Buscador de facturas: filtros, detalle, abonos, reimpresión del ticket y
 * enlace para escribirle al cliente por WhatsApp.
 */

import { useState, useEffect, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import api from '../../services/api'
import toast from 'react-hot-toast'
import { Search, FileText, CreditCard, XCircle, RefreshCw, Filter, ChevronDown, Printer, Edit3, Trash2, Plus, Save, X, PackageCheck, MessageCircle } from 'lucide-react'
import { qrTienda, bloqueQR, bloqueLogo, CSS_QR, imprimirCuandoListo, datosEmpresa, bloqueCredito } from '../../utils/ticket'

const ESTADOS = [
  { value: '', label: 'Todos' },
  { value: 'PENDIENTE', label: 'Pendientes' },
  { value: 'PAGADA', label: 'Pagadas' },
  { value: 'ANULADA', label: 'Anuladas' },
]
const METODOS = ['EFECTIVO', 'NEQUI', 'DAVIPLATA', 'BANCOLOMBIA', 'TRANSFERENCIA']
const TALLAS_NORMAL = ['4', '6', '8', '10', '12', '14', '16', 'S', 'M', 'L', 'XL', 'Única']
const TALLAS_MEDIAS = ['6-8', '8-10', '10-12', '12-14', '14-16']

export default function BuscarFacturas() {
  const { isAdmin } = useAuth()
  const [buscar, setBuscar] = useState('')
  const [estado, setEstado] = useState('')
  const [colegioId, setColegioId] = useState('')
  const [colegios, setColegios] = useState([])
  const [productos, setProductos] = useState([])
  const [facturas, setFacturas] = useState([])
  const [total, setTotal] = useState(0)
  const [saldoTotal, setSaldoTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pages, setPages] = useState(0)
  const [loading, setLoading] = useState(false)
  const [selected, setSelected] = useState(null)
  const [showFilters, setShowFilters] = useState(false)

  // Payment modal
  const [showPago, setShowPago] = useState(false)
  const [pagoValor, setPagoValor] = useState('')
  const [pagoMetodo, setPagoMetodo] = useState('EFECTIVO')
  const [savingPago, setSavingPago] = useState(false)

  // Edit payment
  const [editingPago, setEditingPago] = useState(null)
  const [editPagoValor, setEditPagoValor] = useState('')
  const [editPagoMetodo, setEditPagoMetodo] = useState('')

  // Edit modal
  const [showEditProducts, setShowEditProducts] = useState(false)
  const [editTab, setEditTab] = useState('cliente')
  const [editDetalles, setEditDetalles] = useState([])
  const [editCliente, setEditCliente] = useState({})
  const [savingEdit, setSavingEdit] = useState(false)

  // Print ref
  const printRef = useRef()
  const [searchParams] = useSearchParams()

  useEffect(() => {
    Promise.all([
      api.get('/colegios'),
      api.get('/productos'),
    ]).then(([colRes, prodRes]) => {
      setColegios(colRes.data.colegios || [])
      setProductos(prodRes.data.productos || [])
    }).catch(() => {})
    // Cargar todas las facturas al abrir
    handleSearch(1)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Abrir directamente una factura si llegamos con ?ver=<id> (desde otras pantallas)
  useEffect(() => {
    const ver = searchParams.get('ver')
    if (ver) verDetalle(parseInt(ver))
  }, [searchParams]) // eslint-disable-line react-hooks/exhaustive-deps

  const handleSearch = async (pageNum = 1) => {
    setLoading(true)
    try {
      const params = { page: pageNum, per_page: 20 }
      if (buscar.trim()) params.buscar = buscar.trim()
      if (estado) params.estado = estado
      if (colegioId) params.colegio_id = colegioId

      const res = await api.get('/facturas', { params })
      setFacturas(res.data.facturas || [])
      setTotal(res.data.total || 0)
      setPages(res.data.pages || 0)
      setPage(pageNum)
      setSaldoTotal(res.data.saldo_total || 0)

      if (res.data.facturas?.length === 0 && buscar.trim()) {
        toast('No se encontraron facturas', { icon: '🔍' })
      }
    } catch {
      toast.error('Error en búsqueda')
    } finally {
      setLoading(false)
    }
  }

  const verTodas = () => {
    setBuscar('')
    setEstado('')
    setColegioId('')
    // Llamar directamente con params vacíos en vez de depender del estado que aún no se actualizó
    setLoading(true)
    api.get('/facturas', { params: { page: 1, per_page: 20 } })
      .then(res => {
        setFacturas(res.data.facturas || [])
        setTotal(res.data.total || 0)
        setPages(res.data.pages || 0)
        setPage(1)
        setSaldoTotal(res.data.saldo_total || 0)
      })
      .catch(() => toast.error('Error cargando facturas'))
      .finally(() => setLoading(false))
  }

  const verDetalle = async (id) => {
    try {
      const res = await api.get(`/facturas/${id}`)
      setSelected(res.data.factura)
    } catch {
      toast.error('Error cargando detalle')
    }
  }

  // === ENTREGAR PRENDA PENDIENTE (desde el mismo detalle de la factura) ===
  const entregarPrenda = async (idPendiente) => {
    try {
      await api.post(`/prendas/${idPendiente}/entregar`)
      toast.success('Prenda marcada como entregada')
      verDetalle(selected.id_factura)
    } catch (e) {
      toast.error(e.response?.data?.error || 'Error al entregar')
    }
  }

  // === ANULAR ===
  const anularFactura = async () => {
    if (!selected || !isAdmin()) return
    if (!confirm(`¿Anular factura ${selected.numero_factura}? Esta acción devuelve el stock.`)) return
    try {
      await api.post(`/facturas/${selected.id_factura}/anular`)
      toast.success('Factura anulada')
      verDetalle(selected.id_factura)
      handleSearch(page)
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error anulando')
    }
  }

  // === REACTIVAR ===
  const reactivarFactura = async () => {
    if (!selected || !isAdmin()) return
    if (!confirm(`¿Reactivar factura ${selected.numero_factura}?`)) return
    try {
      const res = await api.post(`/facturas/${selected.id_factura}/reactivar`)
      toast.success(`Factura reactivada - Estado: ${res.data.resumen?.estado || 'OK'}`)
      verDetalle(selected.id_factura)
      handleSearch(page)
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error reactivando')
    }
  }

  // === REGISTRAR PAGO ===
  const registrarPago = async () => {
    if (!selected || !pagoValor) return
    setSavingPago(true)
    try {
      await api.post('/pagos', {
        id_factura: selected.id_factura,
        valor: parseFloat(pagoValor),
        metodo_pago: pagoMetodo,
      })
      toast.success('Pago registrado')
      setShowPago(false)
      setPagoValor('')
      verDetalle(selected.id_factura)
      handleSearch(page)
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error registrando pago')
    } finally {
      setSavingPago(false)
    }
  }

  // === EDITAR PAGO ===
  const startEditPago = (pago) => {
    setEditingPago(pago.id_pago)
    setEditPagoValor(String(pago.valor))
    setEditPagoMetodo(pago.metodo_pago)
  }

  const guardarEditPago = async () => {
    if (!editingPago || !editPagoValor) return
    try {
      await api.put(`/pagos/${editingPago}`, {
        valor: parseFloat(editPagoValor),
        metodo_pago: editPagoMetodo,
      })
      toast.success('Pago actualizado')
      setEditingPago(null)
      verDetalle(selected.id_factura)
      handleSearch(page)
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error editando pago')
    }
  }

  // === ELIMINAR PAGO ===
  const eliminarPago = async (idPago) => {
    if (!confirm('¿Eliminar este pago?')) return
    try {
      await api.delete(`/pagos/${idPago}`)
      toast.success('Pago eliminado')
      verDetalle(selected.id_factura)
      handleSearch(page)
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error eliminando pago')
    }
  }

  // === EDITAR PRODUCTOS ===
  const openEditProducts = () => {
    if (!selected) return
    setEditDetalles((selected.detalles || []).map(d => ({
      id_producto: String(d.id_producto),
      producto_nombre: d.producto_nombre,
      talla_individual: d.talla_individual,
      cantidad: d.cantidad,
      precio_unitario: d.precio_unitario,
    })))
    setEditCliente({
      numero_factura: selected.numero_factura || '',
      cliente_nombre: selected.cliente_nombre || '',
      cliente_telefono: selected.cliente_telefono || '',
      cliente_email: selected.cliente_email || '',
      cliente_direccion: selected.cliente_direccion || '',
      cliente_nit: selected.cliente_nit || '',
      fecha_factura: selected.fecha_factura || '',
      metodo_pago: selected.metodo_pago || 'EFECTIVO',
      observaciones: selected.observaciones || '',
    })
    setEditTab('cliente')
    setShowEditProducts(true)
  }

  const addEditLine = () => {
    setEditDetalles([...editDetalles, { id_producto: '', producto_nombre: '', talla_individual: '', cantidad: 1, precio_unitario: 0 }])
  }

  const updateEditLine = (idx, field, value) => {
    setEditDetalles(prev => {
      const n = [...prev]
      n[idx] = { ...n[idx], [field]: value }
      if (field === 'id_producto') {
        const prod = productos.find(p => String(p.id_producto) === String(value))
        n[idx].producto_nombre = prod?.nombre || ''
      }
      return n
    })
  }

  const removeEditLine = (idx) => {
    setEditDetalles(editDetalles.filter((_, i) => i !== idx))
  }

  const guardarEditProducts = async () => {
    if (editDetalles.length === 0) { toast.error('Agrega al menos un producto'); return }
    for (const d of editDetalles) {
      if (!d.id_producto || !d.talla_individual || d.precio_unitario <= 0) {
        toast.error('Completa todos los campos de cada producto')
        return
      }
    }
    setSavingEdit(true)
    try {
      await api.put(`/facturas/${selected.id_factura}`, {
        ...editCliente,
        detalles: editDetalles.map(d => ({
          id_producto: parseInt(d.id_producto),
          talla_individual: d.talla_individual,
          cantidad: parseInt(d.cantidad),
          precio_unitario: parseFloat(d.precio_unitario),
        }))
      })
      toast.success('Factura actualizada')
      setShowEditProducts(false)
      verDetalle(selected.id_factura)
      handleSearch(page)
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error editando factura')
    } finally {
      setSavingEdit(false)
    }
  }

  // === CONTACTAR POR WHATSAPP (abre el chat con el cliente, no envía solo) ===
  const contactarWhatsApp = () => {
    const tel = String(selected?.cliente_telefono || '').replace(/\D/g, '')
    if (!tel) { toast.error('Esta factura no tiene teléfono del cliente'); return }
    const num = tel.length === 10 ? '57' + tel : tel   // celular CO sin indicativo
    const nombre = (selected?.cliente_nombre || '').split(' ')[0]
    const saldo = Number(selected?.saldo || 0)
    const msg = saldo > 0
      ? `¡Hola ${nombre}! 👋 Te escribimos de RALOZ COL por tu factura ${selected?.numero_factura || ''}. Tienes un saldo pendiente de ${fmt(saldo)}. ¿Coordinamos el pago? 🙌`
      : `¡Hola ${nombre}! 👋 Te escribimos de RALOZ COL sobre tu factura ${selected?.numero_factura || ''}.`
    window.open(`https://wa.me/${num}?text=${encodeURIComponent(msg)}`, '_blank', 'noopener')
  }

  // === IMPRIMIR ===
  const imprimirFactura = () => {
    if (!selected) return
    const empresa = datosEmpresa()

    const printWindow = window.open('', '_blank')
    const detallesHTML = (selected.detalles || []).map(d =>
      `<tr><td>${d.producto_nombre}</td><td style="text-align:center">${d.talla_individual}</td><td style="text-align:center">${d.cantidad}</td><td style="text-align:right">${fmt(d.precio_unitario)}</td><td style="text-align:right">${fmt(d.total_linea)}</td></tr>`
    ).join('')
    const pagosHTML = (selected.pagos || []).map(p =>
      `<tr><td>${p.fecha_pago}</td><td>${p.metodo_pago}</td><td style="text-align:right">${fmt(p.valor)}</td></tr>`
    ).join('')

    const headerLines = [
      empresa.nit ? `NIT: ${empresa.nit}` : '',
      empresa.direccion ? empresa.direccion : '',
      empresa.ciudad ? empresa.ciudad : '',
      empresa.telefono ? `Tel: ${empresa.telefono}` : '',
      empresa.email ? empresa.email : '',
    ].filter(Boolean).join(' | ')

    const domicilioHTML = selected.domicilio > 0
      ? `<div class="flex-between text-sm"><span>Domicilio</span><span>+${fmt(selected.domicilio)}</span></div>`
      : ''

    printWindow.document.write(`<!DOCTYPE html><html><head><title>Factura ${selected.numero_factura}</title>
    <style>
      body{font-family:Arial,sans-serif;margin:20px;color:#333}
      .header{border-bottom:3px solid #FFC107;padding-bottom:10px;margin-bottom:12px}
      .header h1{color:#1976D2;font-size:20px;margin:0 0 4px}
      .header p{margin:2px 0;font-size:12px;color:#555}
      .info{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:12px 0;font-size:13px}
      .info b{color:#555}
      table{width:100%;border-collapse:collapse;margin:12px 0;font-size:13px}
      th{background:#f5f5f5;padding:8px;text-align:left;border:1px solid #ddd;font-size:12px}
      td{padding:6px 8px;border:1px solid #eee}
      .total-row{font-weight:bold;font-size:16px;text-align:right;margin:6px 0}
      .sub-row{font-size:13px;text-align:right;margin:4px 0;color:#555}
      .estado{display:inline-block;padding:3px 10px;border-radius:12px;font-size:12px;font-weight:bold}
      .PENDIENTE{background:#FFF3CD;color:#856404}.PAGADA{background:#D4EDDA;color:#155724}.ANULADA{background:#F8D7DA;color:#721C24}
      @media print{body{margin:0}}
    </style></head><body>
    <div class="header">
      <h1>${empresa.nombre} <span class="estado ${selected.estado}">${selected.estado}</span></h1>
      ${headerLines ? `<p>${headerLines}</p>` : ''}
      <p style="font-size:13px;font-weight:bold;margin-top:6px">FACTURA N° ${selected.numero_factura}</p>
    </div>
    <div class="info">
      <div><b>Cliente:</b> ${selected.cliente_nombre}</div>
      <div><b>Teléfono:</b> ${selected.cliente_telefono || '—'}</div>
      <div><b>Colegio:</b> ${selected.colegio_nombre}</div>
      <div><b>Fecha:</b> ${selected.fecha_factura}</div>
      ${selected.cliente_email ? `<div><b>Email:</b> ${selected.cliente_email}</div>` : ''}
      ${selected.cliente_nit ? `<div><b>NIT/CC:</b> ${selected.cliente_nit}</div>` : ''}
      ${selected.observaciones ? `<div class="col-span-2"><b>Obs:</b> ${selected.observaciones}</div>` : ''}
    </div>
    <h3>Productos</h3>
    <table><thead><tr><th>Producto</th><th>Talla</th><th>Cant.</th><th>P.Unit</th><th>Total</th></tr></thead><tbody>${detallesHTML}</tbody></table>
    ${selected.domicilio > 0 ? `<div class="sub-row">Subtotal: ${fmt(selected.subtotal || selected.total)}</div><div class="sub-row">Domicilio: +${fmt(selected.domicilio)}</div>` : ''}
    <div class="total-row">TOTAL: ${fmt(selected.total)}</div>
    ${(selected.pagos || []).length > 0 ? `<h3>Pagos Registrados</h3><table><thead><tr><th>Fecha</th><th>Método</th><th>Valor</th></tr></thead><tbody>${pagosHTML}</tbody></table>` : ''}
    <div class="total-row" style="color:${selected.saldo > 0 ? '#D32F2F' : '#2E7D32'}">SALDO: ${fmt(selected.saldo || 0)}</div>
    <hr><p style="text-align:center;font-size:11px;color:#999">${empresa.nombre} — Sistema de Facturación</p>
    </body></html>`)
    printWindow.document.close()
    printWindow.print()
  }

  // Reimprime el TICKET de 80mm (Xprinter XP-N160, termica) desde una factura ya guardada.
  // Sirve para imprimir desde el computador ventas hechas en el celular, o reimpresos.
  const imprimirTicket = async () => {
    if (!selected) return
    const empresa = datosEmpresa()
    const web = empresa.web || 'ralozcolsas.com'
    const money = (n) => '$' + Math.round(n || 0).toLocaleString('es-CO')

    const total = selected.total || 0
    const saldo = selected.saldo || 0
    const abono = Math.max(0, total - saldo)   // lo pagado hasta ahora
    const descuento = selected.descuento || 0
    const domicilio = selected.domicilio || 0

    const itemsHTML = (selected.detalles || []).map(d =>
      `<div class="it"><div class="itn">${d.producto_nombre}${d.talla_individual ? ' · T' + d.talla_individual : ''}</div>` +
      `<div class="row"><span>${d.cantidad} x ${money(d.precio_unitario)}</span><span>${money(d.total_linea)}</span></div></div>`
    ).join('')

    const w = window.open('', '_blank')
    const qr = await qrTienda()
    w.document.write(`<!DOCTYPE html><html><head><meta charset="utf-8"><title>Ticket ${selected.numero_factura}</title>
    <style>
      @page { size: 80mm auto; margin: 0; }
      *{box-sizing:border-box}
      body{width:80mm;margin:0;padding:2mm 4mm;color:#000;line-height:1.4;
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
      ${CSS_QR}
      @media print{body{margin:0}}
    </style></head><body>
    ${bloqueLogo()}
    <div class="c">
      <h1 class="b">${empresa.nombre}</h1>
      ${empresa.nit ? `<p>NIT ${empresa.nit}</p>` : ''}
      ${empresa.direccion ? `<p>${empresa.direccion}</p>` : ''}
      ${empresa.ciudad ? `<p>${empresa.ciudad}</p>` : ''}
      ${empresa.telefono ? `<p>Cel: ${empresa.telefono}</p>` : ''}
      <p>${web}</p>
    </div>
    <div class="sep"></div>
    <div class="row"><span>Recibo:</span><span class="b">${selected.numero_factura}</span></div>
    <div class="row"><span>Fecha:</span><span>${selected.fecha_factura}</span></div>
    ${selected.cliente_nombre ? `<div class="row"><span>Cliente:</span><span>${selected.cliente_nombre}</span></div>` : ''}
    ${selected.colegio_nombre ? `<div class="row"><span>Colegio:</span><span>${selected.colegio_nombre}</span></div>` : ''}
    <div class="sep"></div>
    ${itemsHTML}
    <div class="sep"></div>
    ${(descuento > 0 || (selected.domicilio || 0) > 0) ? `<div class="row"><span>Subtotal</span><span>${money(selected.subtotal || selected.total)}</span></div>` : ''}
    ${descuento > 0 ? `<div class="row"><span>Descuento</span><span>-${money(descuento)}</span></div>` : ''}
    ${domicilio > 0 ? `<div class="row"><span>Domicilio</span><span>+${money(domicilio)}</span></div>` : ''}
    <div class="row big"><span>TOTAL</span><span>${money(total)}</span></div>
    ${abono > 0 ? `<div class="row"><span>Abono</span><span>${money(abono)}</span></div>` : ''}
    ${saldo > 0 ? `<div class="row big"><span>SALDO</span><span>${money(saldo)}</span></div>` : ''}
    <div class="sep"></div>
    <div class="terms">
      <div class="b c">GARANTÍA Y CAMBIOS</div>
      - Garantía de 6 meses por defectos de confección (costuras/hilo).<br>
      - Cambio por talla: 5 días hábiles, prenda sin uso, limpia y con etiquetas.<br>
      - Personalizados/bordados: sin cambio salvo defecto.<br>
      - Reembolsos por el mismo medio de pago.<br>
      - <b>Conserva este ticket: es tu comprobante de compra. Sin comprobante no se tramitan cambios, garantias ni reembolsos.</b><br>
      ${web}/terminos.html
    </div>
    <div class="sep"></div>
    <p class="c">¡Gracias por tu compra!</p>
    ${bloqueQR(qr)}
    ${bloqueCredito()}
    </body></html>`)
    w.document.close()
    imprimirCuandoListo(w)
  }

  const badgeEstado = (est) => {
    const styles = {
      PENDIENTE: 'bg-yellow-50 text-yellow-700 border-yellow-200',
      PAGADA: 'bg-green-50 text-green-700 border-green-200',
      ANULADA: 'bg-red-50 text-red-700 border-red-200',
    }
    return `px-2 py-0.5 text-xs font-medium rounded-full border ${styles[est] || styles.PENDIENTE}`
  }

  const fmt = (n) => '$' + Math.round(n || 0).toLocaleString('es-CO')

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900">Buscar Facturas</h2>
        <button onClick={verTodas} className="btn-secondary flex items-center gap-1 text-sm">
          <RefreshCw size={14} /> Ver Todas
        </button>
      </div>

      {/* Search bar */}
      <form onSubmit={e => { e.preventDefault(); handleSearch() }} className="flex gap-3">
        <div className="relative flex-1">
          <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            value={buscar} onChange={e => setBuscar(e.target.value)}
            className="input-field pl-10 w-full"
            placeholder="Buscar por número de factura, nombre o teléfono..."
          />
        </div>
        <button type="button" onClick={() => setShowFilters(!showFilters)}
          className={`btn-secondary flex items-center gap-1 ${showFilters ? 'bg-gray-200' : ''}`}>
          <Filter size={16} /> Filtros <ChevronDown size={14} className={`transition-transform ${showFilters ? 'rotate-180' : ''}`} />
        </button>
        <button type="submit" disabled={loading} className="btn-primary flex items-center gap-2">
          <Search size={18} /> Buscar
        </button>
      </form>

      {/* Filters */}
      {showFilters && (
        <div className="bg-white p-4 rounded-lg border border-gray-200 flex flex-wrap gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Estado</label>
            <select value={estado} onChange={e => setEstado(e.target.value)} className="input-field">
              {ESTADOS.map(e => <option key={e.value} value={e.value}>{e.label}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Colegio</label>
            <select value={colegioId} onChange={e => setColegioId(e.target.value)} className="input-field">
              <option value="">Todos</option>
              {colegios.map(c => <option key={c.id_colegio} value={c.id_colegio}>{c.nombre}</option>)}
            </select>
          </div>
          <div className="flex items-end">
            <button onClick={() => { setEstado(''); setColegioId(''); setBuscar('') }}
              className="text-sm text-gray-500 hover:text-gray-700">Limpiar filtros</button>
          </div>
        </div>
      )}

      {/* Results count + saldo total */}
      {total > 0 && (
        <div className="flex items-center justify-between text-sm">
          <p className="text-gray-500">{total} factura{total !== 1 ? 's' : ''} encontrada{total !== 1 ? 's' : ''}</p>
          {saldoTotal > 0 && (
            <p className="text-red-600 font-semibold">Saldo total pendiente: {fmt(saldoTotal)}</p>
          )}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Results list */}
        <div className="lg:col-span-2 space-y-2">
          {loading ? (
            <div className="flex items-center justify-center h-32">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-raloz-600"></div>
            </div>
          ) : facturas.length > 0 ? (
            <>
              {facturas.map(f => (
                <div key={f.id_factura} onClick={() => verDetalle(f.id_factura)}
                  className={`card cursor-pointer hover:shadow-md transition-all ${selected?.id_factura === f.id_factura ? 'ring-2 ring-raloz-500 shadow-md' : ''}`}>
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-semibold text-gray-900">{f.numero_factura}</p>
                      <p className="text-sm text-gray-600">{f.cliente_nombre}</p>
                      <p className="text-xs text-gray-400">{f.colegio_nombre} · {f.fecha_factura}</p>
                    </div>
                    <div className="text-right">
                      <p className="font-bold text-gray-900">{fmt(f.total)}</p>
                      <span className={badgeEstado(f.estado)}>{f.estado}</span>
                    </div>
                  </div>
                </div>
              ))}
              {pages > 1 && (
                <div className="flex items-center justify-center gap-2 py-4">
                  <button disabled={page <= 1} onClick={() => handleSearch(page - 1)} className="px-3 py-1 text-sm border rounded disabled:opacity-50">Anterior</button>
                  <span className="text-sm text-gray-500">Página {page} de {pages}</span>
                  <button disabled={page >= pages} onClick={() => handleSearch(page + 1)} className="px-3 py-1 text-sm border rounded disabled:opacity-50">Siguiente</button>
                </div>
              )}
            </>
          ) : (
            <div className="text-center py-12 text-gray-400">
              <Search size={32} className="mx-auto mb-2" />
              <p>Busca facturas o haz clic en "Ver Todas"</p>
            </div>
          )}
        </div>

        {/* Detail panel */}
        <div className="lg:col-span-3">
          {selected ? (
            <div className="card sticky top-4 space-y-4">
              {/* Header */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <FileText className="text-raloz-600" size={20} />
                  <h3 className="text-lg font-semibold">{selected.numero_factura}</h3>
                  <span className={badgeEstado(selected.estado)}>{selected.estado}</span>
                </div>
                {/* El icono rapido imprime el TICKET: es lo del dia a dia en el
                    mostrador. La factura A4 queda en su boton, mas abajo. */}
                <button onClick={imprimirTicket} className="text-gray-400 hover:text-blue-600 p-2 rounded hover:bg-blue-50" title="Imprimir ticket">
                  <Printer size={18} />
                </button>
              </div>

              {/* Client info */}
              <div className="grid grid-cols-2 gap-3 text-sm bg-gray-50 p-3 rounded-lg">
                <div><span className="text-gray-500">Cliente:</span> <span className="font-medium">{selected.cliente_nombre}</span></div>
                <div><span className="text-gray-500">Teléfono:</span> <span className="font-medium">{selected.cliente_telefono || '—'}</span></div>
                <div><span className="text-gray-500">Colegio:</span> <span className="font-medium">{selected.colegio_nombre}</span></div>
                <div><span className="text-gray-500">Fecha:</span> <span className="font-medium">{selected.fecha_factura}</span></div>
                {selected.cliente_email && <div><span className="text-gray-500">Email:</span> <span className="font-medium">{selected.cliente_email}</span></div>}
                {selected.cliente_nit && <div><span className="text-gray-500">NIT/CC:</span> <span className="font-medium">{selected.cliente_nit}</span></div>}
                {selected.observaciones && <div className="col-span-2"><span className="text-gray-500">Obs:</span> <span className="font-medium">{selected.observaciones}</span></div>}
              </div>

              {/* Financial summary */}
              <div className="grid grid-cols-3 gap-3">
                <div className="text-center p-3 bg-blue-50 rounded-lg">
                  <p className="text-xs text-blue-600">Total</p>
                  <p className="text-lg font-bold text-blue-700">{fmt(selected.total)}</p>
                </div>
                <div className="text-center p-3 bg-green-50 rounded-lg">
                  <p className="text-xs text-green-600">Pagado</p>
                  <p className="text-lg font-bold text-green-700">{fmt(selected.total_pagado)}</p>
                </div>
                <div className="text-center p-3 bg-red-50 rounded-lg">
                  <p className="text-xs text-red-600">Saldo</p>
                  <p className="text-lg font-bold text-red-700">{fmt(selected.saldo)}</p>
                </div>
              </div>

              {/* Products */}
              {selected.detalles?.length > 0 && (
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="text-sm font-semibold text-gray-700">Productos ({selected.detalles.length})</h4>
                    {selected.estado !== 'ANULADA' && (
                      <button onClick={openEditProducts} className="text-xs text-blue-600 hover:underline flex items-center gap-1">
                        <Edit3 size={12} /> Editar Productos
                      </button>
                    )}
                  </div>
                  <div className="border rounded-lg overflow-hidden">
                    <table className="w-full text-sm">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="text-left px-3 py-2 text-gray-500 font-medium">Producto</th>
                          <th className="text-center px-3 py-2 text-gray-500 font-medium">Talla</th>
                          <th className="text-center px-3 py-2 text-gray-500 font-medium">Cant.</th>
                          <th className="text-right px-3 py-2 text-gray-500 font-medium">P.Unit</th>
                          <th className="text-right px-3 py-2 text-gray-500 font-medium">Total</th>
                        </tr>
                      </thead>
                      <tbody>
                        {selected.detalles.map(d => (
                          <tr key={d.id_detalle} className="border-t border-gray-100">
                            <td className="px-3 py-2">{d.producto_nombre}</td>
                            <td className="px-3 py-2 text-center">{d.talla_individual}</td>
                            <td className="px-3 py-2 text-center">{d.cantidad}</td>
                            <td className="px-3 py-2 text-right">{fmt(d.precio_unitario)}</td>
                            <td className="px-3 py-2 text-right font-medium">{fmt(d.total_linea)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Prendas pendientes de entrega (de esta misma factura) */}
              {selected.prendas_pendientes?.length > 0 && (
                <div>
                  <h4 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-1.5">
                    <PackageCheck size={15} className="text-amber-500" />
                    Pendientes de entrega ({selected.prendas_pendientes.filter(p => p.estado === 'PENDIENTE').length})
                  </h4>
                  <div className="space-y-1">
                    {selected.prendas_pendientes.map(p => (
                      <div key={p.id_pendiente}
                        className={`flex items-center justify-between text-sm py-2 px-3 rounded ${p.estado === 'PENDIENTE' ? 'bg-amber-50' : 'bg-gray-50'}`}>
                        <div>
                          <span className="font-medium text-gray-700">{p.producto_nombre}</span>
                          <span className="ml-2 text-xs text-gray-500">Talla {p.talla} · x{p.cantidad}</span>
                          {p.estado !== 'PENDIENTE' && (
                            <span className="ml-2 text-xs px-2 py-0.5 bg-green-100 text-green-700 rounded">
                              Entregado{p.fecha_entrega ? ` ${p.fecha_entrega}` : ''}
                            </span>
                          )}
                        </div>
                        {p.estado === 'PENDIENTE' && selected.estado !== 'ANULADA' && (
                          <button onClick={() => entregarPrenda(p.id_pendiente)}
                            className="text-xs bg-emerald-600 text-white px-3 py-1 rounded hover:bg-emerald-700 flex items-center gap-1">
                            <PackageCheck size={13} /> Entregar
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Payments history */}
              {selected.pagos?.length > 0 && (
                <div>
                  <h4 className="text-sm font-semibold text-gray-700 mb-2">Historial de Pagos ({selected.pagos.length})</h4>
                  <div className="space-y-1">
                    {selected.pagos.map(p => (
                      <div key={p.id_pago} className="flex items-center justify-between text-sm py-2 px-3 bg-green-50 rounded">
                        {editingPago === p.id_pago ? (
                          <>
                            <div className="flex gap-2 items-center flex-1">
                              <input type="number" value={editPagoValor} onChange={e => setEditPagoValor(e.target.value)}
                                className="input-field w-28 text-sm" min="1" />
                              <select value={editPagoMetodo} onChange={e => setEditPagoMetodo(e.target.value)} className="input-field text-sm">
                                {METODOS.map(m => <option key={m}>{m}</option>)}
                              </select>
                            </div>
                            <div className="flex gap-1">
                              <button onClick={guardarEditPago} className="text-green-600 hover:bg-green-100 p-1 rounded"><Save size={14} /></button>
                              <button onClick={() => setEditingPago(null)} className="text-gray-400 hover:bg-gray-100 p-1 rounded"><X size={14} /></button>
                            </div>
                          </>
                        ) : (
                          <>
                            <div>
                              <span className="text-gray-700">{p.fecha_pago}</span>
                              <span className="ml-2 text-xs px-2 py-0.5 bg-white rounded text-gray-500">{p.metodo_pago}</span>
                            </div>
                            <div className="flex items-center gap-2">
                              <span className="font-medium text-green-700">{fmt(p.valor)}</span>
                              {isAdmin() && (
                                <div className="flex gap-1">
                                  <button onClick={() => startEditPago(p)} className="text-blue-400 hover:text-blue-600 p-1" title="Editar pago"><Edit3 size={13} /></button>
                                  <button onClick={() => eliminarPago(p.id_pago)} className="text-red-400 hover:text-red-600 p-1" title="Eliminar pago"><Trash2 size={13} /></button>
                                </div>
                              )}
                            </div>
                          </>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Actions */}
              <div className="flex gap-2 pt-2 border-t flex-wrap">
                {selected.estado !== 'ANULADA' && selected.saldo > 0 && (
                  <button onClick={() => setShowPago(true)} className="btn-success flex items-center gap-2 flex-1">
                    <CreditCard size={16} /> Registrar Pago
                  </button>
                )}
                {selected.estado !== 'ANULADA' && isAdmin() && (
                  <button onClick={anularFactura} className="btn-danger flex items-center gap-2">
                    <XCircle size={16} /> Anular
                  </button>
                )}
                {selected.estado === 'ANULADA' && isAdmin() && (
                  <button onClick={reactivarFactura} className="bg-purple-600 hover:bg-purple-700 text-white font-medium py-2 px-4 rounded-lg flex items-center gap-2">
                    <RefreshCw size={16} /> Reactivar
                  </button>
                )}
                {selected.cliente_telefono && (
                  <button onClick={contactarWhatsApp} title="Escribirle al cliente por WhatsApp"
                    className="bg-green-600 hover:bg-green-700 text-white font-medium py-2 px-4 rounded-lg flex items-center gap-2">
                    <MessageCircle size={16} /> WhatsApp
                  </button>
                )}
                <button onClick={imprimirTicket} className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg flex items-center gap-2">
                  <Printer size={16} /> Imprimir ticket
                </button>
                <button onClick={imprimirFactura} className="btn-secondary flex items-center gap-2">
                  <Printer size={16} /> Factura A4
                </button>
              </div>

              {/* Inline payment form */}
              {showPago && (
                <div className="bg-blue-50 p-4 rounded-lg border border-blue-200 space-y-3">
                  <h4 className="font-semibold text-blue-800">Nuevo Pago — Saldo: {fmt(selected.saldo)}</h4>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs text-blue-700 mb-1">Valor</label>
                      <input type="number" min="1" max={selected.saldo} value={pagoValor}
                        onChange={e => setPagoValor(e.target.value)} className="input-field" placeholder={`Máx ${fmt(selected.saldo)}`} />
                    </div>
                    <div>
                      <label className="block text-xs text-blue-700 mb-1">Método</label>
                      <select value={pagoMetodo} onChange={e => setPagoMetodo(e.target.value)} className="input-field">
                        {METODOS.map(m => <option key={m}>{m}</option>)}
                      </select>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button onClick={registrarPago} disabled={savingPago || !pagoValor} className="btn-primary flex items-center gap-2">
                      {savingPago ? 'Guardando...' : 'Confirmar Pago'}
                    </button>
                    <button onClick={() => setShowPago(false)} className="btn-secondary">Cancelar</button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="card text-center py-16 text-gray-400">
              <FileText size={40} className="mx-auto mb-3" />
              <p>Selecciona una factura para ver el detalle</p>
            </div>
          )}
        </div>
      </div>

      {/* === MODAL: Editar Factura === */}
      {showEditProducts && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-bold">Editar Factura — {selected?.numero_factura}</h3>
                <button onClick={() => setShowEditProducts(false)} className="text-gray-400 hover:text-gray-600"><X size={20} /></button>
              </div>

              {/* Tabs */}
              <div className="flex gap-1 border-b border-gray-200">
                <button onClick={() => setEditTab('cliente')}
                  className={`px-4 py-2 text-sm font-medium rounded-t-lg border-b-2 transition-colors ${editTab === 'cliente' ? 'border-raloz-500 text-raloz-600 bg-raloz-50' : 'border-transparent text-gray-500 hover:text-gray-700'}`}>
                  Datos del Cliente
                </button>
                <button onClick={() => setEditTab('productos')}
                  className={`px-4 py-2 text-sm font-medium rounded-t-lg border-b-2 transition-colors ${editTab === 'productos' ? 'border-raloz-500 text-raloz-600 bg-raloz-50' : 'border-transparent text-gray-500 hover:text-gray-700'}`}>
                  Productos
                </button>
              </div>

              {/* Tab: Datos del Cliente */}
              {editTab === 'cliente' && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {isAdmin() && (
                    <div className="md:col-span-2">
                      <label className="block text-xs font-medium text-gray-600 mb-1">
                        # Número de factura <span className="text-purple-600 font-semibold">(solo admin)</span>
                      </label>
                      <input type="text" value={editCliente.numero_factura || ''}
                        onChange={e => setEditCliente({ ...editCliente, numero_factura: e.target.value })}
                        className="input-field w-full text-sm font-mono" />
                    </div>
                  )}
                  {[
                    { label: 'Nombre del cliente *', key: 'cliente_nombre', type: 'text' },
                    { label: 'Teléfono', key: 'cliente_telefono', type: 'text' },
                    { label: 'Email', key: 'cliente_email', type: 'email' },
                    { label: 'Dirección', key: 'cliente_direccion', type: 'text' },
                    { label: 'NIT / CC', key: 'cliente_nit', type: 'text' },
                    { label: 'Fecha factura', key: 'fecha_factura', type: 'date' },
                  ].map(({ label, key, type }) => (
                    <div key={key}>
                      <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
                      <input type={type} value={editCliente[key] || ''}
                        onChange={e => setEditCliente({ ...editCliente, [key]: e.target.value })}
                        className="input-field w-full text-sm" />
                    </div>
                  ))}
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Método de pago</label>
                    <select value={editCliente.metodo_pago || 'EFECTIVO'}
                      onChange={e => setEditCliente({ ...editCliente, metodo_pago: e.target.value })}
                      className="input-field w-full text-sm">
                      {METODOS.map(m => <option key={m}>{m}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Observaciones</label>
                    <input value={editCliente.observaciones || ''}
                      onChange={e => setEditCliente({ ...editCliente, observaciones: e.target.value })}
                      className="input-field w-full text-sm" placeholder="Notas..." />
                  </div>
                </div>
              )}

              {/* Tab: Productos */}
              {editTab === 'productos' && (
                <div className="space-y-2">
                  <div className="hidden md:grid grid-cols-12 gap-2 px-2 text-xs font-medium text-gray-500 uppercase">
                    <div className="col-span-4">Producto</div>
                    <div className="col-span-2">Talla</div>
                    <div className="col-span-1">Cant.</div>
                    <div className="col-span-2">Precio</div>
                    <div className="col-span-2 text-right">Subtotal</div>
                    <div className="col-span-1"></div>
                  </div>

                  {editDetalles.map((det, idx) => {
                    const prod = productos.find(p => String(p.id_producto) === String(det.id_producto))
                    const tallas = prod?.tipo === 'medias' ? TALLAS_MEDIAS : TALLAS_NORMAL
                    return (
                      <div key={idx} className="grid grid-cols-1 md:grid-cols-12 gap-2 p-2 bg-gray-50 rounded items-center">
                        <div className="md:col-span-4">
                          <select value={det.id_producto} onChange={e => updateEditLine(idx, 'id_producto', e.target.value)} className="input-field w-full text-sm">
                            <option value="">Producto...</option>
                            {productos.map(p => <option key={p.id_producto} value={p.id_producto}>{p.nombre}</option>)}
                          </select>
                        </div>
                        <div className="md:col-span-2">
                          <select value={det.talla_individual} onChange={e => updateEditLine(idx, 'talla_individual', e.target.value)} className="input-field w-full text-sm">
                            <option value="">Talla</option>
                            {tallas.map(t => <option key={t}>{t}</option>)}
                          </select>
                        </div>
                        <div className="md:col-span-1">
                          <input type="number" min="1" value={det.cantidad} onChange={e => updateEditLine(idx, 'cantidad', parseInt(e.target.value) || 1)} className="input-field w-full text-sm text-center" />
                        </div>
                        <div className="md:col-span-2">
                          <input type="number" min="0" value={det.precio_unitario} onChange={e => updateEditLine(idx, 'precio_unitario', parseFloat(e.target.value) || 0)} className="input-field w-full text-sm" />
                        </div>
                        <div className="md:col-span-2 text-right text-sm font-bold">
                          {fmt(det.cantidad * det.precio_unitario)}
                        </div>
                        <div className="md:col-span-1 text-right">
                          <button onClick={() => removeEditLine(idx)} className="text-red-400 hover:text-red-600 p-1"><Trash2 size={14} /></button>
                        </div>
                      </div>
                    )
                  })}

                  <button onClick={addEditLine} className="text-sm text-blue-600 hover:underline flex items-center gap-1">
                    <Plus size={14} /> Agregar producto
                  </button>

                  <div className="text-right text-lg font-bold border-t pt-3">
                    Nuevo Total: {fmt(editDetalles.reduce((s, d) => s + (d.cantidad * d.precio_unitario), 0))}
                  </div>
                </div>
              )}

              <div className="flex gap-3 justify-end border-t pt-4">
                <button onClick={() => setShowEditProducts(false)} className="btn-secondary">Cancelar</button>
                <button onClick={guardarEditProducts} disabled={savingEdit} className="btn-primary flex items-center gap-2">
                  <Save size={16} /> {savingEdit ? 'Guardando...' : 'Guardar Cambios'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
