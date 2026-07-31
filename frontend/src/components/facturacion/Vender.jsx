import { useState, useEffect, useCallback, useMemo } from 'react'
import { Link } from 'react-router-dom'
import api from '../../services/api'
import toast from 'react-hot-toast'
import {
  Search, ShoppingCart, Plus, Minus, Trash2, X, Printer, Check, Package,
} from 'lucide-react'
import { fotoPrenda } from '../../data/prendasFotos'

const METODOS_PAGO = ['EFECTIVO', 'NEQUI', 'DAVIPLATA', 'BANCOLOMBIA', 'TRANSFERENCIA']

const money = (n) => '$' + Math.round(n || 0).toLocaleString('es-CO')

// Categoría a partir del nombre del producto (para los filtros)
const categoriaDe = (nombre) => {
  const n = (nombre || '').toLowerCase()
  if (n.includes('completo')) return 'Completos'
  if (n.includes('media')) return 'Medias'
  if (n.includes('física') || n.includes('fisica') || n.includes('pantaloneta') || n.includes('sudadera')) return 'Ed. Física'
  if (n.includes('pantal') || n.includes('camisa') || n.includes('blusa') || n.includes('blazer') ||
      n.includes('chaleco') || n.includes('jardinera') || n.includes('chaqueta diario') || n.includes('delantal') || n.includes('camibuso')) return 'Diario'
  return 'Otros'
}
const CATEGORIAS = ['Todos', 'Diario', 'Ed. Física', 'Completos', 'Medias', 'Otros']

export default function Vender() {
  const [colegios, setColegios] = useState([])
  const [productos, setProductos] = useState([])   // del catálogo: {..., tallas:[{talla,precio,stock}]}
  const [colegioId, setColegioId] = useState('')
  const [busqueda, setBusqueda] = useState('')
  const [categoria, setCategoria] = useState('Todos')
  const [loadingCatalogo, setLoadingCatalogo] = useState(false)

  const [carrito, setCarrito] = useState([])       // {id_producto, nombre, talla_individual, cantidad, precio_unitario}
  const [picker, setPicker] = useState(null)       // producto en selección de talla
  const [verCarrito, setVerCarrito] = useState(false)   // sheet de carrito (móvil)
  const [checkout, setCheckout] = useState(false)  // modal de cobro
  const [saving, setSaving] = useState(false)
  const [exito, setExito] = useState(null)         // snapshot de la venta creada

  const [pago, setPago] = useState({
    cliente_nombre: '', cliente_telefono: '', metodo_pago: 'EFECTIVO',
    entrega_inmediata: true, domicilio: false, valor_domicilio: '',
    descuento: '', abono: '',
  })

  // Carga inicial: lista de colegios
  useEffect(() => {
    api.get('/colegios')
      .then((col) => {
        const cols = col.data.colegios || []
        setColegios(cols)
        if (cols.length) setColegioId(String(cols[0].id_colegio))
      })
      .catch(() => toast.error('Error cargando colegios'))
  }, [])

  // Catálogo del colegio: trae producto + tallas (talla, precio, stock) listas.
  // Es la MISMA fuente de la tienda, así que medias y completos salen correctos.
  const cargarCatalogo = useCallback(async (id) => {
    if (!id) { setProductos([]); return }
    setLoadingCatalogo(true)
    try {
      const res = await api.get(`/tienda/catalogo/${id}`)
      setProductos(res.data.productos || [])
    } catch { setProductos([]); toast.error('No pude cargar el catálogo') }
    finally { setLoadingCatalogo(false) }
  }, [])

  useEffect(() => { cargarCatalogo(colegioId) }, [colegioId, cargarCatalogo])

  const colegioNombre = colegios.find(c => String(c.id_colegio) === String(colegioId))?.nombre || ''

  const productosColegio = useMemo(() => {
    return (productos || [])
      .filter(p => (p.tallas || []).length > 0)
      .map(p => {
        const precios = (p.tallas || []).map(t => t.precio).filter(v => v > 0)
        return {
          ...p,
          precioDesde: precios.length ? Math.min(...precios) : 0,
          categoria: categoriaDe(p.nombre),
        }
      })
  }, [productos])

  const productosFiltrados = useMemo(() => {
    const q = busqueda.trim().toLowerCase()
    return productosColegio.filter(p => {
      if (categoria !== 'Todos' && p.categoria !== categoria) return false
      if (q && !p.nombre.toLowerCase().includes(q)) return false
      return true
    })
  }, [productosColegio, busqueda, categoria])

  // Tallas del producto en selección (ya vienen con precio y stock del catálogo)
  const tallasDisponibles = useMemo(
    () => (picker?.tallas || []).filter(t => t.precio > 0),
    [picker],
  )

  // ---- Carrito ----
  // tallaObj = { talla, precio, stock } (viene del catálogo)
  const agregarAlCarrito = (producto, tallaObj, cantidad) => {
    const talla = tallaObj.talla
    setCarrito(prev => {
      const i = prev.findIndex(x => x.id_producto === producto.id_producto && x.talla_individual === talla)
      if (i >= 0) {
        const n = [...prev]; n[i] = { ...n[i], cantidad: n[i].cantidad + cantidad }; return n
      }
      return [...prev, { id_producto: producto.id_producto, nombre: producto.nombre, talla_individual: talla, cantidad, precio_unitario: tallaObj.precio }]
    })
    toast.success(`${producto.nombre} T${talla} agregada`)
  }
  const cambiarCantidad = (idx, delta) => setCarrito(prev => {
    const n = [...prev]; const nueva = n[idx].cantidad + delta
    if (nueva <= 0) return n.filter((_, i) => i !== idx)
    n[idx] = { ...n[idx], cantidad: nueva }; return n
  })
  const quitarDelCarrito = (idx) => setCarrito(prev => prev.filter((_, i) => i !== idx))

  const subtotal = carrito.reduce((s, x) => s + x.cantidad * x.precio_unitario, 0)
  const totalUnidades = carrito.reduce((s, x) => s + x.cantidad, 0)
  const descuento = parseFloat(pago.descuento) || 0
  const valorDomicilio = pago.domicilio ? (parseFloat(pago.valor_domicilio) || 0) : 0
  const total = Math.max(0, subtotal - descuento) + valorDomicilio
  const abono = parseFloat(pago.abono) || 0
  const saldo = total - abono

  // ---- Cobro ----
  const cobrar = async () => {
    if (!colegioId) { toast.error('Selecciona un colegio'); return }
    if (carrito.length === 0) { toast.error('El carrito está vacío'); return }
    if (!pago.cliente_nombre.trim()) { toast.error('Ingresa el nombre del cliente'); return }
    if (abono > total) { toast.error('El abono no puede ser mayor al total'); return }

    setSaving(true)
    const payload = {
      id_colegio: colegioId,
      cliente_nombre: pago.cliente_nombre,
      cliente_telefono: pago.cliente_telefono,
      fecha_factura: new Date().toISOString().split('T')[0],
      metodo_pago: pago.metodo_pago,
      entrega_inmediata: pago.entrega_inmediata,
      domicilio: valorDomicilio,
      descuento,
      abono,
      detalles: carrito.map(d => ({
        id_producto: parseInt(d.id_producto),
        talla_individual: d.talla_individual,
        cantidad: parseInt(d.cantidad),
        precio_unitario: parseFloat(d.precio_unitario),
      })),
    }

    const doPost = async (permitir_sobreventa) => {
      const res = await api.post('/facturas', { ...payload, permitir_sobreventa })
      const f = res.data.factura
      toast.success(`Factura ${f.numero_factura} creada`)
      setExito({
        numero: f.numero_factura,
        fecha: payload.fecha_factura,
        cliente: pago.cliente_nombre,
        colegio: colegioNombre,
        items: carrito.map(d => ({ nombre: d.nombre, talla: d.talla_individual, cantidad: d.cantidad, precio: d.precio_unitario })),
        subtotal, descuento, domicilio: valorDomicilio, total, abono, saldo,
      })
      // limpiar
      setCarrito([]); setCheckout(false); setVerCarrito(false)
      setPago({ cliente_nombre: '', cliente_telefono: '', metodo_pago: 'EFECTIVO', entrega_inmediata: true, domicilio: false, valor_domicilio: '', descuento: '', abono: '' })
    }

    try {
      await doPost(false)
    } catch (err) {
      if (err.response?.status === 409 && err.response?.data?.code === 'sin_stock_suficiente') {
        const lista = (err.response.data.faltantes || [])
          .map(x => `• ${x.producto} talla ${x.talla}: pides ${x.pedido}, hay ${x.disponible}`).join('\n')
        if (window.confirm(`⚠️ No hay stock suficiente:\n\n${lista}\n\n¿Facturar de todos modos? (el stock quedará en 0)`)) {
          try { await doPost(true) } catch (e2) { toast.error(e2.response?.data?.error || 'Error al crear factura') }
        }
      } else {
        toast.error(err.response?.data?.error || 'Error al crear factura')
      }
    } finally {
      setSaving(false)
    }
  }

  // ---- Ticket 76mm (Epson TM-U220) ----
  const imprimirTicket = (v) => {
    let empresa = { nombre: 'RALOZ COL SAS', nit: '', direccion: '', telefono: '', ciudad: '', web: '' }
    try { empresa = JSON.parse(localStorage.getItem('raloz_empresa') || 'null') || empresa } catch { /* default */ }
    const web = empresa.web || 'ralozcolsas.com'
    const w = window.open('', '_blank')
    const itemsHTML = v.items.map(it =>
      `<div class="it"><div class="itn">${it.nombre}${it.talla ? ' · T' + it.talla : ''}</div>` +
      `<div class="row"><span>${it.cantidad} x ${money(it.precio)}</span><span>${money(it.cantidad * it.precio)}</span></div></div>`
    ).join('')
    w.document.write(`<!DOCTYPE html><html><head><meta charset="utf-8"><title>Ticket ${v.numero}</title>
    <style>
      @page { size: 76mm auto; margin: 0; }
      *{box-sizing:border-box} body{width:76mm;margin:0;padding:2mm 3mm;color:#000;line-height:1.4;font-family:'Courier New',monospace;font-size:12px}
      h1{font-size:16px;margin:0 0 2px}.c{text-align:center}.b{font-weight:bold}.big{font-size:14px;font-weight:bold}
      .sep{border-top:1px dashed #000;margin:6px 0}.row{display:flex;justify-content:space-between;gap:8px}
      .it{margin:4px 0}.itn{font-weight:bold}.terms{font-size:10px;line-height:1.35;margin-top:2px}
      @media print{body{margin:0}}
    </style></head><body>
    <div class="c"><h1 class="b">${empresa.nombre}</h1>${empresa.nit ? `<p>NIT ${empresa.nit}</p>` : ''}${empresa.direccion ? `<p>${empresa.direccion}</p>` : ''}${empresa.ciudad ? `<p>${empresa.ciudad}</p>` : ''}${empresa.telefono ? `<p>Cel: ${empresa.telefono}</p>` : ''}<p>${web}</p></div>
    <div class="sep"></div>
    <div class="row"><span>Recibo:</span><span class="b">${v.numero}</span></div>
    <div class="row"><span>Fecha:</span><span>${v.fecha}</span></div>
    ${v.cliente ? `<div class="row"><span>Cliente:</span><span>${v.cliente}</span></div>` : ''}
    ${v.colegio ? `<div class="row"><span>Colegio:</span><span>${v.colegio}</span></div>` : ''}
    <div class="sep"></div>${itemsHTML}<div class="sep"></div>
    ${v.descuento > 0 ? `<div class="row"><span>Descuento</span><span>-${money(v.descuento)}</span></div>` : ''}
    ${v.domicilio > 0 ? `<div class="row"><span>Domicilio</span><span>+${money(v.domicilio)}</span></div>` : ''}
    <div class="row big"><span>TOTAL</span><span>${money(v.total)}</span></div>
    ${v.abono > 0 ? `<div class="row"><span>Abono</span><span>${money(v.abono)}</span></div>` : ''}
    ${v.saldo > 0 ? `<div class="row big"><span>SALDO</span><span>${money(v.saldo)}</span></div>` : ''}
    <div class="sep"></div>
    <div class="terms"><div class="b c">GARANTÍA Y CAMBIOS</div>
      - Garantía de 6 meses por defectos de confección (costuras/hilo).<br>
      - Cambio por talla: 5 días hábiles, prenda sin uso, limpia y con etiquetas.<br>
      - Personalizados/bordados: sin cambio salvo defecto.<br>
      - Reembolsos por el mismo medio de pago.<br>- Conserva este ticket.<br>${web}/terminos.html</div>
    <div class="sep"></div><p class="c">¡Gracias por tu compra!</p>
    </body></html>`)
    w.document.close(); w.focus(); w.print()
  }

  // ---------------- UI ----------------
  return (
    <div className="lg:flex lg:gap-4 lg:h-[calc(100vh-120px)]">

      {/* ===== Columna de productos ===== */}
      <div className="lg:flex-1 lg:min-w-0 lg:overflow-y-auto lg:pr-1">
        {/* Enlace de escape al modo clásico */}
        <div className="flex justify-end mb-1">
          <Link to="/facturacion" className="text-xs text-gray-400 hover:text-blue-600 underline underline-offset-2">
            Modo clásico
          </Link>
        </div>
        {/* Colegios */}
        <div className="flex gap-2 overflow-x-auto pb-2 -mx-1 px-1 scrollbar-thin">
          {colegios.map(c => (
            <button
              key={c.id_colegio}
              onClick={() => { setColegioId(String(c.id_colegio)); setCategoria('Todos') }}
              className={`shrink-0 px-4 py-1.5 rounded-full text-sm font-semibold transition-colors ${
                String(c.id_colegio) === String(colegioId) ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 border border-gray-200 hover:bg-gray-50'
              }`}
            >
              {c.nombre}
            </button>
          ))}
        </div>

        {/* Búsqueda */}
        <div className="relative my-2">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            value={busqueda}
            onChange={e => setBusqueda(e.target.value)}
            placeholder="Buscar prenda…"
            className="w-full pl-9 pr-3 py-2.5 rounded-xl border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {/* Categorías */}
        <div className="flex gap-2 overflow-x-auto pb-2 -mx-1 px-1 scrollbar-thin">
          {CATEGORIAS.map(cat => (
            <button
              key={cat}
              onClick={() => setCategoria(cat)}
              className={`shrink-0 px-3 py-1 rounded-full text-xs font-semibold transition-colors ${
                categoria === cat ? 'bg-slate-800 text-white' : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        {/* Grid de prendas */}
        {loadingCatalogo ? (
          <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-3 mt-2">
            {[...Array(6)].map((_, i) => <div key={i} className="h-52 bg-gray-100 rounded-2xl animate-pulse" />)}
          </div>
        ) : productosFiltrados.length === 0 ? (
          <div className="text-center py-16 text-gray-400">
            <Package size={40} className="mx-auto mb-2 text-gray-300" />
            <p className="text-sm">No hay prendas para mostrar</p>
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-3 mt-2">
            {productosFiltrados.map(p => (
              <button
                key={p.id_producto}
                onClick={() => setPicker(p)}
                className="bg-white rounded-2xl border border-gray-100 overflow-hidden text-left hover:shadow-md hover:border-gray-200 active:scale-[0.98] transition-all flex flex-col"
              >
                <div className="aspect-square bg-gray-50 flex items-center justify-center overflow-hidden">
                  <ProductoImagen colegio={colegioNombre} producto={p.nombre} />
                </div>
                <div className="p-2.5 flex-1 flex flex-col">
                  <p className="text-[13px] font-semibold text-gray-800 leading-tight line-clamp-2 flex-1">{p.nombre}</p>
                  <p className="text-blue-700 font-bold text-sm mt-1">{p.precioDesde ? `${money(p.precioDesde)}` : '—'}</p>
                </div>
              </button>
            ))}
          </div>
        )}
        <div className="h-24 lg:hidden" />
      </div>

      {/* ===== Carrito: columna en desktop ===== */}
      <aside className="hidden lg:flex lg:w-80 xl:w-96 shrink-0 bg-white rounded-2xl border border-gray-100 flex-col">
        <CarritoPanel
          carrito={carrito} subtotal={subtotal} total={total} totalUnidades={totalUnidades}
          onMas={i => cambiarCantidad(i, 1)} onMenos={i => cambiarCantidad(i, -1)} onQuitar={quitarDelCarrito}
          onVaciar={() => setCarrito([])} onCobrar={() => setCheckout(true)}
        />
      </aside>

      {/* ===== Barra flotante de carrito (móvil) ===== */}
      {carrito.length > 0 && (
        <button
          onClick={() => setVerCarrito(true)}
          className="lg:hidden fixed left-3 right-3 bottom-20 z-30 bg-blue-600 text-white rounded-2xl shadow-lg px-4 py-3 flex items-center justify-between active:scale-[0.99] transition-transform"
        >
          <span className="flex items-center gap-2 font-semibold">
            <span className="relative"><ShoppingCart size={20} />
              <span className="absolute -top-2 -right-2 bg-amber-400 text-slate-900 text-[10px] font-black rounded-full min-w-[16px] h-[16px] px-1 flex items-center justify-center">{totalUnidades}</span>
            </span>
            Ver carrito
          </span>
          <span className="font-bold">{money(subtotal)}</span>
        </button>
      )}

      {/* ===== Sheet de carrito (móvil) ===== */}
      {verCarrito && (
        <div className="lg:hidden fixed inset-0 z-50 flex flex-col justify-end">
          <div className="absolute inset-0 bg-black/50" onClick={() => setVerCarrito(false)} />
          <div className="relative bg-white rounded-t-3xl max-h-[85vh] flex flex-col">
            <CarritoPanel
              carrito={carrito} subtotal={subtotal} total={total} totalUnidades={totalUnidades}
              onMas={i => cambiarCantidad(i, 1)} onMenos={i => cambiarCantidad(i, -1)} onQuitar={quitarDelCarrito}
              onVaciar={() => setCarrito([])} onCobrar={() => { setVerCarrito(false); setCheckout(true) }}
              onCerrar={() => setVerCarrito(false)}
            />
          </div>
        </div>
      )}

      {/* ===== Modal: elegir talla y cantidad ===== */}
      {picker && (
        <PickerTalla
          producto={picker} colegio={colegioNombre} tallas={tallasDisponibles}
          onCerrar={() => setPicker(null)}
          onAgregar={(tallaObj, cant) => { agregarAlCarrito(picker, tallaObj, cant); setPicker(null) }}
        />
      )}

      {/* ===== Modal: cobro ===== */}
      {checkout && (
        <ModalCobro
          pago={pago} setPago={setPago}
          subtotal={subtotal} descuento={descuento} valorDomicilio={valorDomicilio} total={total} abono={abono} saldo={saldo}
          saving={saving} onCerrar={() => setCheckout(false)} onCobrar={cobrar}
        />
      )}

      {/* ===== Modal: éxito ===== */}
      {exito && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white rounded-2xl shadow-2xl max-w-sm w-full p-6 text-center space-y-4">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto"><Check className="text-green-600" size={32} /></div>
            <div>
              <h3 className="text-xl font-bold text-gray-900">¡Venta registrada!</h3>
              <p className="text-gray-500 text-sm mt-1">Factura {exito.numero} · {money(exito.total)}</p>
            </div>
            <button onClick={() => imprimirTicket(exito)} className="w-full inline-flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2.5 rounded-xl">
              <Printer size={18} /> Imprimir ticket
            </button>
            <button onClick={() => setExito(null)} className="w-full py-2.5 rounded-xl border border-gray-200 text-gray-600 font-semibold hover:bg-gray-50">
              Nueva venta
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Imagen de producto con fallback ───────────────────────────────
function ProductoImagen({ colegio, producto }) {
  const [error, setError] = useState(false)
  const src = fotoPrenda(colegio, producto)
  if (!src || error) {
    return <Package size={40} className="text-gray-300" />
  }
  return <img src={src} alt={producto} loading="lazy" onError={() => setError(true)} className="w-full h-full object-cover" />
}

// ─── Panel del carrito (reusado en desktop y en el sheet móvil) ─────
function CarritoPanel({ carrito, subtotal, total, totalUnidades, onMas, onMenos, onQuitar, onVaciar, onCobrar, onCerrar }) {
  return (
    <>
      <div className="flex items-center justify-between p-4 border-b border-gray-100">
        <div className="flex items-center gap-2">
          <ShoppingCart size={18} className="text-gray-500" />
          <h3 className="font-bold text-gray-800">Carrito</h3>
          <span className="bg-gray-100 text-gray-500 text-xs font-bold rounded-full px-2 py-0.5">{totalUnidades}</span>
        </div>
        {carrito.length > 0 && (
          <button onClick={onVaciar} className="text-xs text-gray-400 hover:text-red-500">Vaciar</button>
        )}
        {onCerrar && <button onClick={onCerrar} className="lg:hidden text-gray-400 p-1"><X size={20} /></button>}
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-2 min-h-[120px]">
        {carrito.length === 0 ? (
          <div className="text-center py-10 text-gray-400">
            <ShoppingCart size={32} className="mx-auto mb-2 text-gray-200" />
            <p className="text-sm">Toca una prenda para agregarla</p>
          </div>
        ) : carrito.map((it, i) => (
          <div key={i} className="flex items-center gap-2 bg-gray-50 rounded-xl p-2.5">
            <div className="flex-1 min-w-0">
              <p className="text-[13px] font-semibold text-gray-800 truncate">{it.nombre}</p>
              <p className="text-xs text-gray-400">T{it.talla_individual} · {money(it.precio_unitario)}</p>
            </div>
            <div className="flex items-center gap-1.5">
              <button onClick={() => onMenos(i)} className="w-7 h-7 rounded-lg bg-white border border-gray-200 flex items-center justify-center text-gray-600 active:scale-90"><Minus size={13} /></button>
              <span className="w-5 text-center text-sm font-bold">{it.cantidad}</span>
              <button onClick={() => onMas(i)} className="w-7 h-7 rounded-lg bg-white border border-gray-200 flex items-center justify-center text-gray-600 active:scale-90"><Plus size={13} /></button>
            </div>
            <span className="w-16 text-right text-sm font-bold text-gray-800">{money(it.cantidad * it.precio_unitario)}</span>
            <button onClick={() => onQuitar(i)} className="text-gray-300 hover:text-red-500 p-1"><Trash2 size={15} /></button>
          </div>
        ))}
      </div>

      <div className="border-t border-gray-100 p-4 space-y-3">
        <div className="flex justify-between text-sm text-gray-500"><span>Subtotal</span><span className="font-semibold text-gray-700">{money(subtotal)}</span></div>
        <div className="flex justify-between items-center">
          <span className="font-bold text-gray-800">Total</span>
          <span className="text-2xl font-black text-blue-700">{money(total)}</span>
        </div>
        <button
          onClick={onCobrar}
          disabled={carrito.length === 0}
          className="w-full py-3.5 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:bg-gray-200 disabled:text-gray-400 text-white font-bold text-lg transition-colors"
        >
          Cobrar {money(total)}
        </button>
      </div>
    </>
  )
}

// ─── Modal: elegir talla + cantidad ────────────────────────────────
function PickerTalla({ producto, colegio, tallas, onCerrar, onAgregar }) {
  const [sel, setSel] = useState(null)   // objeto {talla, precio, stock}
  const [cantidad, setCantidad] = useState(1)
  const precio = sel ? sel.precio : (producto.precioDesde || 0)
  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4 bg-black/50">
      <div className="bg-white rounded-t-3xl sm:rounded-2xl w-full sm:max-w-sm max-h-[90vh] overflow-y-auto">
        <div className="flex items-start gap-3 p-4 border-b border-gray-100">
          <div className="w-16 h-16 rounded-xl bg-gray-50 flex items-center justify-center overflow-hidden shrink-0">
            <ProductoImagen colegio={colegio} producto={producto.nombre} />
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-bold text-gray-800 leading-tight">{producto.nombre}</p>
            <p className="text-blue-700 font-bold mt-1">{money(precio)}{!sel && ' +'}</p>
          </div>
          <button onClick={onCerrar} className="text-gray-400 p-1"><X size={20} /></button>
        </div>

        <div className="p-4 space-y-4">
          <div>
            <p className="text-xs font-bold text-gray-500 uppercase tracking-wide mb-2">Elige la talla</p>
            {tallas.length === 0 ? (
              <p className="text-sm text-gray-400">Este producto no tiene tallas con precio para este colegio.</p>
            ) : (
              <div className="grid grid-cols-4 gap-2">
                {tallas.map(t => {
                  const activa = sel?.talla === t.talla
                  const sinStock = (t.stock || 0) <= 0
                  return (
                    <button
                      key={t.talla}
                      onClick={() => setSel(t)}
                      className={`py-2 rounded-xl text-sm font-bold border transition-colors flex flex-col items-center leading-tight ${
                        activa ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-gray-700 border-gray-200 hover:border-blue-300'
                      }`}
                    >
                      <span>{t.talla}</span>
                      <span className={`text-[9px] font-medium ${activa ? 'text-blue-100' : sinStock ? 'text-amber-500' : 'text-gray-400'}`}>
                        {sinStock ? 'encargo' : `${t.stock} disp`}
                      </span>
                    </button>
                  )
                })}
              </div>
            )}
            {sel && (
              <p className="text-xs text-gray-400 mt-2">
                {money(sel.precio)} c/u · {(sel.stock || 0) > 0 ? `${sel.stock} en stock` : 'sin stock (queda por encargo/entregar)'}
              </p>
            )}
          </div>

          <div className="flex items-center justify-between">
            <p className="text-xs font-bold text-gray-500 uppercase tracking-wide">Cantidad</p>
            <div className="flex items-center gap-3">
              <button onClick={() => setCantidad(c => Math.max(1, c - 1))} className="w-9 h-9 rounded-lg bg-gray-100 flex items-center justify-center active:scale-90"><Minus size={16} /></button>
              <span className="w-6 text-center text-lg font-bold">{cantidad}</span>
              <button onClick={() => setCantidad(c => c + 1)} className="w-9 h-9 rounded-lg bg-gray-100 flex items-center justify-center active:scale-90"><Plus size={16} /></button>
            </div>
          </div>

          <button
            onClick={() => sel && onAgregar(sel, cantidad)}
            disabled={!sel}
            className="w-full py-3 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:bg-gray-200 disabled:text-gray-400 text-white font-bold transition-colors"
          >
            Agregar {sel ? `· ${money(precio * cantidad)}` : ''}
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── Modal: cobro (cliente + pago) ─────────────────────────────────
function ModalCobro({ pago, setPago, subtotal, descuento, valorDomicilio, total, abono, saldo, saving, onCerrar, onCobrar }) {
  const set = (k, v) => setPago(p => ({ ...p, [k]: v }))
  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4 bg-black/50">
      <div className="bg-white rounded-t-3xl sm:rounded-2xl w-full sm:max-w-md max-h-[92vh] overflow-y-auto">
        <div className="flex items-center justify-between p-4 border-b border-gray-100 sticky top-0 bg-white">
          <h3 className="font-bold text-gray-800">Cobrar {money(total)}</h3>
          <button onClick={onCerrar} className="text-gray-400 p-1"><X size={20} /></button>
        </div>
        <div className="p-4 space-y-3">
          <div>
            <label className="block text-xs font-semibold text-gray-600 mb-1">Nombre del cliente *</label>
            <input value={pago.cliente_nombre} onChange={e => set('cliente_nombre', e.target.value)} placeholder="Nombre completo"
              className="w-full px-3 py-2.5 rounded-xl border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" autoFocus />
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-600 mb-1">Teléfono</label>
            <input value={pago.cliente_telefono} onChange={e => set('cliente_telefono', e.target.value)} inputMode="tel" placeholder="300 123 4567"
              className="w-full px-3 py-2.5 rounded-xl border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-600 mb-1">Método de pago</label>
            <select value={pago.metodo_pago} onChange={e => set('metodo_pago', e.target.value)}
              className="w-full px-3 py-2.5 rounded-xl border border-gray-200 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500">
              {METODOS_PAGO.map(m => <option key={m}>{m}</option>)}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1">Descuento</label>
              <input value={pago.descuento} onChange={e => set('descuento', e.target.value)} inputMode="numeric" placeholder="0"
                className="w-full px-3 py-2.5 rounded-xl border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1">Abono</label>
              <input value={pago.abono} onChange={e => set('abono', e.target.value)} inputMode="numeric" placeholder="0"
                className="w-full px-3 py-2.5 rounded-xl border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
          </div>

          <div className="flex items-center gap-4 pt-1">
            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input type="checkbox" checked={pago.entrega_inmediata} onChange={e => set('entrega_inmediata', e.target.checked)} className="w-4 h-4 accent-blue-600" />
              Entregué las prendas
            </label>
            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input type="checkbox" checked={pago.domicilio} onChange={e => set('domicilio', e.target.checked)} className="w-4 h-4 accent-blue-600" />
              Domicilio
            </label>
          </div>
          {pago.domicilio && (
            <input value={pago.valor_domicilio} onChange={e => set('valor_domicilio', e.target.value)} inputMode="numeric" placeholder="Valor domicilio"
              className="w-full px-3 py-2.5 rounded-xl border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
          )}

          {/* Resumen */}
          <div className="bg-gray-50 rounded-xl p-3 space-y-1.5 text-sm">
            <div className="flex justify-between text-gray-500"><span>Subtotal</span><span>{money(subtotal)}</span></div>
            {descuento > 0 && <div className="flex justify-between text-orange-600"><span>Descuento</span><span>-{money(descuento)}</span></div>}
            {valorDomicilio > 0 && <div className="flex justify-between text-blue-600"><span>Domicilio</span><span>+{money(valorDomicilio)}</span></div>}
            <div className="flex justify-between font-bold text-gray-800 text-base border-t border-gray-200 pt-1.5"><span>{abono > 0 ? 'Saldo' : 'Total'}</span><span className="text-blue-700">{money(abono > 0 ? saldo : total)}</span></div>
          </div>

          <button onClick={onCobrar} disabled={saving}
            className="w-full py-3.5 rounded-xl bg-green-600 hover:bg-green-700 disabled:opacity-60 text-white font-bold text-lg transition-colors">
            {saving ? 'Guardando…' : `Confirmar cobro · ${money(total)}`}
          </button>
        </div>
      </div>
    </div>
  )
}
