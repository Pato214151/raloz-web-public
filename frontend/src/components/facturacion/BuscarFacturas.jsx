import { useState, useEffect } from 'react'
import { useAuth } from '../../context/AuthContext'
import api from '../../services/api'
import toast from 'react-hot-toast'
import { Search, FileText, CreditCard, XCircle, RefreshCw, Filter, ChevronDown } from 'lucide-react'

/**
 * Buscador de Facturas — Mirrors desktop's buscador_facturas.py
 * Multi-criteria search, status filters, detail view, and actions
 * (register payment, annul/reactivate invoice).
 */

const ESTADOS = [
  { value: '', label: 'Todos', color: 'text-gray-600' },
  { value: 'PENDIENTE', label: 'Pendientes', color: 'text-yellow-600' },
  { value: 'PAGADA', label: 'Pagadas', color: 'text-green-600' },
  { value: 'ANULADA', label: 'Anuladas', color: 'text-red-600' },
]

export default function BuscarFacturas() {
  const { isAdmin } = useAuth()
  const [buscar, setBuscar] = useState('')
  const [estado, setEstado] = useState('')
  const [colegioId, setColegioId] = useState('')
  const [colegios, setColegios] = useState([])
  const [facturas, setFacturas] = useState([])
  const [total, setTotal] = useState(0)
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

  useEffect(() => {
    api.get('/colegios').then(res => setColegios(res.data.colegios || [])).catch(() => {})
  }, [])

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

      if (res.data.facturas?.length === 0 && buscar.trim()) {
        toast('No se encontraron facturas', { icon: '🔍' })
      }
    } catch {
      toast.error('Error en búsqueda')
    } finally {
      setLoading(false)
    }
  }

  const verDetalle = async (id) => {
    try {
      const res = await api.get(`/facturas/${id}`)
      setSelected(res.data.factura)
    } catch {
      toast.error('Error cargando detalle')
    }
  }

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
      <h2 className="text-2xl font-bold text-gray-900">Buscar Facturas</h2>

      {/* Search bar */}
      <form onSubmit={e => { e.preventDefault(); handleSearch() }} className="flex gap-3">
        <div className="relative flex-1">
          <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            value={buscar}
            onChange={e => setBuscar(e.target.value)}
            className="input-field pl-10 w-full"
            placeholder="Buscar por número de factura, nombre o teléfono..."
          />
        </div>
        <button
          type="button"
          onClick={() => setShowFilters(!showFilters)}
          className={`btn-secondary flex items-center gap-1 ${showFilters ? 'bg-gray-200' : ''}`}
        >
          <Filter size={16} /> Filtros <ChevronDown size={14} className={`transition-transform ${showFilters ? 'rotate-180' : ''}`} />
        </button>
        <button type="submit" disabled={loading} className="btn-primary flex items-center gap-2">
          <Search size={18} /> Buscar
        </button>
      </form>

      {/* Filters panel */}
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
            <button
              onClick={() => { setEstado(''); setColegioId(''); setBuscar('') }}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              Limpiar filtros
            </button>
          </div>
        </div>
      )}

      {/* Results count */}
      {total > 0 && (
        <p className="text-sm text-gray-500">{total} factura{total !== 1 ? 's' : ''} encontrada{total !== 1 ? 's' : ''}</p>
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
                <div
                  key={f.id_factura}
                  onClick={() => verDetalle(f.id_factura)}
                  className={`card cursor-pointer hover:shadow-md transition-all ${
                    selected?.id_factura === f.id_factura ? 'ring-2 ring-raloz-500 shadow-md' : ''
                  }`}
                >
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

              {/* Pagination */}
              {pages > 1 && (
                <div className="flex items-center justify-center gap-2 py-4">
                  <button
                    disabled={page <= 1}
                    onClick={() => handleSearch(page - 1)}
                    className="px-3 py-1 text-sm border rounded disabled:opacity-50"
                  >
                    Anterior
                  </button>
                  <span className="text-sm text-gray-500">Página {page} de {pages}</span>
                  <button
                    disabled={page >= pages}
                    onClick={() => handleSearch(page + 1)}
                    className="px-3 py-1 text-sm border rounded disabled:opacity-50"
                  >
                    Siguiente
                  </button>
                </div>
              )}
            </>
          ) : (
            <div className="text-center py-12 text-gray-400">
              <Search size={32} className="mx-auto mb-2" />
              <p>Busca facturas por número, nombre o teléfono</p>
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
              </div>

              {/* Client info */}
              <div className="grid grid-cols-2 gap-3 text-sm bg-gray-50 p-3 rounded-lg">
                <div><span className="text-gray-500">Cliente:</span> <span className="font-medium">{selected.cliente_nombre}</span></div>
                <div><span className="text-gray-500">Teléfono:</span> <span className="font-medium">{selected.cliente_telefono || '—'}</span></div>
                <div><span className="text-gray-500">Colegio:</span> <span className="font-medium">{selected.colegio_nombre}</span></div>
                <div><span className="text-gray-500">Fecha:</span> <span className="font-medium">{selected.fecha_factura}</span></div>
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
                  <h4 className="text-sm font-semibold text-gray-700 mb-2">Productos ({selected.detalles.length})</h4>
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

              {/* Payments history */}
              {selected.pagos?.length > 0 && (
                <div>
                  <h4 className="text-sm font-semibold text-gray-700 mb-2">Historial de Pagos ({selected.pagos.length})</h4>
                  <div className="space-y-1">
                    {selected.pagos.map(p => (
                      <div key={p.id_pago} className="flex justify-between text-sm py-2 px-3 bg-green-50 rounded">
                        <div>
                          <span className="text-gray-700">{p.fecha_pago}</span>
                          <span className="ml-2 text-xs px-2 py-0.5 bg-white rounded text-gray-500">{p.metodo_pago}</span>
                        </div>
                        <span className="font-medium text-green-700">{fmt(p.valor)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Actions */}
              <div className="flex gap-3 pt-2 border-t">
                {selected.estado === 'PENDIENTE' && selected.saldo > 0 && (
                  <button
                    onClick={() => setShowPago(true)}
                    className="btn-success flex items-center gap-2 flex-1"
                  >
                    <CreditCard size={16} /> Registrar Pago
                  </button>
                )}
                {selected.estado !== 'ANULADA' && isAdmin() && (
                  <button
                    onClick={anularFactura}
                    className="btn-danger flex items-center gap-2"
                  >
                    <XCircle size={16} /> Anular
                  </button>
                )}
              </div>

              {/* Inline payment form */}
              {showPago && (
                <div className="bg-blue-50 p-4 rounded-lg border border-blue-200 space-y-3">
                  <h4 className="font-semibold text-blue-800">Nuevo Pago — Saldo: {fmt(selected.saldo)}</h4>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs text-blue-700 mb-1">Valor</label>
                      <input
                        type="number"
                        min="1"
                        max={selected.saldo}
                        value={pagoValor}
                        onChange={e => setPagoValor(e.target.value)}
                        className="input-field"
                        placeholder={`Máx ${fmt(selected.saldo)}`}
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-blue-700 mb-1">Método</label>
                      <select value={pagoMetodo} onChange={e => setPagoMetodo(e.target.value)} className="input-field">
                        {['EFECTIVO', 'NEQUI', 'DAVIPLATA', 'BANCOLOMBIA', 'TRANSFERENCIA'].map(m => <option key={m}>{m}</option>)}
                      </select>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={registrarPago}
                      disabled={savingPago || !pagoValor}
                      className="btn-primary flex items-center gap-2"
                    >
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
    </div>
  )
}
