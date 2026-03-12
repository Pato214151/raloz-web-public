import { useState, useEffect } from 'react'
import api from '../../services/api'
import toast from 'react-hot-toast'
import { CreditCard, Search, RefreshCw, Edit, Trash2, Printer } from 'lucide-react'

const fmt = (n) => '$' + Math.round(n || 0).toLocaleString('es-CO')
const METODOS = ['EFECTIVO', 'NEQUI', 'DAVIPLATA', 'BANCOLOMBIA', 'TRANSFERENCIA']

export default function Pagos() {
  const [buscar, setBuscar] = useState('')
  const [facturasPendientes, setFacturasPendientes] = useState([])
  const [factura, setFactura] = useState(null)
  const [pagosFactura, setPagosFactura] = useState([])
  const [valor, setValor] = useState('')
  const [metodo, setMetodo] = useState('EFECTIVO')
  const [fechaPago, setFechaPago] = useState(new Date().toISOString().split('T')[0])
  const [saving, setSaving] = useState(false)
  const [loading, setLoading] = useState(true)
  const [editingPago, setEditingPago] = useState(null)

  useEffect(() => { loadPendientes() }, [])

  const loadPendientes = async () => {
    setLoading(true)
    try {
      const res = await api.get('/facturas', { params: { estado: 'PENDIENTE', per_page: 200 } })
      setFacturasPendientes(res.data.facturas || [])
    } catch {
      toast.error('Error cargando facturas pendientes')
    } finally {
      setLoading(false)
    }
  }

  const seleccionarFactura = async (f) => {
    try {
      const res = await api.get(`/facturas/${f.id_factura}`)
      setFactura(res.data.factura)
      const pagosRes = await api.get('/pagos', { params: { id_factura: f.id_factura, per_page: 100 } })
      setPagosFactura(pagosRes.data.pagos || [])
    } catch {
      toast.error('Error cargando factura')
    }
  }

  const buscarFactura = async () => {
    if (!buscar.trim()) return
    try {
      const res = await api.get('/facturas', { params: { buscar, per_page: 10 } })
      if (res.data.facturas?.length > 0) {
        seleccionarFactura(res.data.facturas[0])
      } else {
        toast.error('Factura no encontrada')
        setFactura(null)
      }
    } catch {
      toast.error('Error buscando factura')
    }
  }

  const registrarPago = async () => {
    if (!factura || !valor) return
    setSaving(true)
    try {
      await api.post('/pagos', {
        id_factura: factura.id_factura,
        valor: parseFloat(valor),
        metodo_pago: metodo,
        fecha_pago: fechaPago,
      })
      toast.success('Pago registrado')
      setValor('')
      await seleccionarFactura(factura)
      loadPendientes()
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error registrando pago')
    } finally {
      setSaving(false)
    }
  }

  const eliminarPago = async (idPago) => {
    if (!confirm('¿Eliminar este pago?')) return
    try {
      await api.delete(`/pagos/${idPago}`)
      toast.success('Pago eliminado')
      await seleccionarFactura(factura)
      loadPendientes()
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error')
    }
  }

  const guardarEdicionPago = async () => {
    if (!editingPago) return
    try {
      await api.put(`/pagos/${editingPago.id_pago}`, {
        valor: parseFloat(editingPago.valor),
        metodo_pago: editingPago.metodo_pago,
        fecha_pago: editingPago.fecha_pago,
      })
      toast.success('Pago actualizado')
      setEditingPago(null)
      await seleccionarFactura(factura)
      loadPendientes()
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error')
    }
  }

  const saldo = factura ? (factura.saldo_pendiente ?? (factura.total - (factura.total_abonado || 0))) : 0
  const totalPendienteGlobal = facturasPendientes.reduce((s, f) => s + (f.saldo_pendiente || 0), 0)

  const imprimirRecibo = (pago) => {
    const w = window.open('', '_blank')
    w.document.write(`<!DOCTYPE html><html><head><title>Recibo de Pago</title>
      <style>body{font-family:Arial;margin:20px;max-width:400px;margin:auto}
      h2{color:#1976D2;text-align:center;border-bottom:3px solid #FFC107;padding-bottom:8px}
      .info{margin:15px 0}.row{display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #eee}
      .total{font-size:24px;text-align:center;color:#2e7d32;font-weight:bold;margin:20px 0;padding:15px;background:#e8f5e9;border-radius:8px}
      @media print{body{margin:10px}}</style></head><body>
      <h2>RALOZ COL SAS</h2><h3 style="text-align:center;color:#666">Recibo de Pago</h3>
      <div class="info">
        <div class="row"><span>Factura:</span><b>${factura?.numero_factura || ''}</b></div>
        <div class="row"><span>Cliente:</span><b>${factura?.cliente_nombre || ''}</b></div>
        <div class="row"><span>Fecha Pago:</span><b>${pago.fecha_pago || ''}</b></div>
        <div class="row"><span>Método:</span><b>${pago.metodo_pago}</b></div>
      </div>
      <div class="total">${fmt(pago.valor)}</div>
      <div class="info">
        <div class="row"><span>Total Factura:</span><span>${fmt(factura?.total)}</span></div>
        <div class="row"><span>Total Pagado:</span><span style="color:green">${fmt(factura?.total_abonado)}</span></div>
        <div class="row"><span>Saldo:</span><b style="color:${saldo > 0 ? 'red' : 'green'}">${fmt(saldo)}</b></div>
      </div>
      <hr><p style="text-align:center;font-size:10px;color:#999">RALOZ COL SAS - Gracias por su pago</p></body></html>`)
    w.document.close()
    w.print()
  }

  const filteredPendientes = buscar.trim()
    ? facturasPendientes.filter(f =>
        f.numero_factura?.toLowerCase().includes(buscar.toLowerCase()) ||
        f.cliente_nombre?.toLowerCase().includes(buscar.toLowerCase())
      )
    : facturasPendientes

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900">Pagos / Abonos</h2>
        <button onClick={loadPendientes} className="btn-secondary flex items-center gap-2 text-sm">
          <RefreshCw size={14} /> Actualizar
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card">
          <p className="text-sm text-gray-600">Facturas Pendientes</p>
          <p className="text-3xl font-bold text-amber-600">{facturasPendientes.length}</p>
        </div>
        <div className="card">
          <p className="text-sm text-gray-600">Total Saldo Pendiente</p>
          <p className="text-3xl font-bold text-red-600">{fmt(totalPendienteGlobal)}</p>
        </div>
        <div className="card">
          <p className="text-sm text-gray-600">Factura Seleccionada</p>
          <p className="text-xl font-bold text-raloz-600">{factura?.numero_factura || '—'}</p>
        </div>
      </div>

      {/* Búsqueda */}
      <div className="flex gap-3">
        <input value={buscar} onChange={e => setBuscar(e.target.value)} onKeyDown={e => e.key === 'Enter' && buscarFactura()}
          className="input-field flex-1" placeholder="Buscar factura o cliente..." />
        <button onClick={buscarFactura} className="btn-primary flex items-center gap-2">
          <Search size={18} /> Buscar
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Lista de Facturas Pendientes */}
        <div className="card">
          <h3 className="font-semibold mb-3">Facturas con Saldo Pendiente</h3>
          {loading ? (
            <div className="flex justify-center py-8"><div className="animate-spin h-8 w-8 border-b-2 border-raloz-600 rounded-full"></div></div>
          ) : filteredPendientes.length === 0 ? (
            <p className="text-gray-500 text-center py-8">No hay facturas pendientes</p>
          ) : (
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {filteredPendientes.map(f => (
                <div key={f.id_factura} onClick={() => seleccionarFactura(f)}
                  className={`p-3 rounded-lg border cursor-pointer transition-all hover:shadow ${
                    factura?.id_factura === f.id_factura ? 'border-raloz-500 bg-raloz-50 shadow' : 'border-gray-200 hover:border-gray-300'
                  }`}>
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-sm">{f.numero_factura}</p>
                      <p className="text-xs text-gray-600">{f.cliente_nombre}</p>
                      <p className="text-xs text-gray-400">{f.colegio_nombre}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-xs text-gray-500">Total: {fmt(f.total)}</p>
                      <p className="font-bold text-red-600 text-sm">Saldo: {fmt(f.saldo_pendiente)}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Detalle + Formulario */}
        <div className="space-y-4">
          {factura ? (
            <>
              {/* Info Factura */}
              <div className="card">
                <h3 className="text-lg font-semibold mb-3">{factura.numero_factura}</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between"><span className="text-gray-500">Cliente</span><span className="font-medium">{factura.cliente_nombre}</span></div>
                  <div className="flex justify-between"><span className="text-gray-500">Total</span><span className="font-bold">{fmt(factura.total)}</span></div>
                  <div className="flex justify-between"><span className="text-gray-500">Pagado</span><span className="text-green-600 font-medium">{fmt(factura.total_abonado)}</span></div>
                  <div className="flex justify-between border-t pt-2">
                    <span className="text-gray-700 font-medium">Saldo</span>
                    <span className={`font-bold text-lg ${saldo > 0 ? 'text-red-600' : 'text-green-600'}`}>{fmt(saldo)}</span>
                  </div>
                </div>
              </div>

              {/* Historial de Pagos */}
              {pagosFactura.length > 0 && (
                <div className="card">
                  <h4 className="font-semibold mb-3 text-sm">Pagos Realizados</h4>
                  <div className="space-y-2">
                    {pagosFactura.map(p => (
                      <div key={p.id_pago} className="flex items-center justify-between p-2 bg-gray-50 rounded text-sm">
                        {editingPago?.id_pago === p.id_pago ? (
                          <div className="flex items-center gap-2 flex-1 flex-wrap">
                            <input type="number" value={editingPago.valor} onChange={e => setEditingPago({ ...editingPago, valor: e.target.value })}
                              className="input-field w-24 text-sm" />
                            <select value={editingPago.metodo_pago} onChange={e => setEditingPago({ ...editingPago, metodo_pago: e.target.value })}
                              className="input-field text-sm">
                              {METODOS.map(m => <option key={m}>{m}</option>)}
                            </select>
                            <button onClick={guardarEdicionPago} className="text-green-600 hover:text-green-800 text-xs font-medium">Guardar</button>
                            <button onClick={() => setEditingPago(null)} className="text-gray-400 hover:text-gray-600 text-xs">Cancelar</button>
                          </div>
                        ) : (
                          <>
                            <div>
                              <p className="font-medium text-green-600">{fmt(p.valor)}</p>
                              <p className="text-xs text-gray-400">{p.fecha_pago} · {p.metodo_pago}</p>
                            </div>
                            <div className="flex gap-1">
                              <button onClick={() => imprimirRecibo(p)} className="text-blue-500 hover:text-blue-700 p-1" title="Imprimir recibo">
                                <Printer size={13} />
                              </button>
                              <button onClick={() => setEditingPago({ ...p })} className="text-amber-500 hover:text-amber-700 p-1" title="Editar">
                                <Edit size={13} />
                              </button>
                              <button onClick={() => eliminarPago(p.id_pago)} className="text-red-500 hover:text-red-700 p-1" title="Eliminar">
                                <Trash2 size={13} />
                              </button>
                            </div>
                          </>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Formulario Nuevo Pago */}
              {saldo > 0 && (
                <div className="card border-green-200 bg-green-50">
                  <h4 className="font-semibold mb-3">Nuevo Pago</h4>
                  <div className="space-y-3">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Valor</label>
                      <input type="number" min="1" max={saldo} value={valor} onChange={e => setValor(e.target.value)}
                        className="input-field" placeholder={`Máximo ${fmt(saldo)}`} />
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Método</label>
                        <select value={metodo} onChange={e => setMetodo(e.target.value)} className="input-field">
                          {METODOS.map(m => <option key={m}>{m}</option>)}
                        </select>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Fecha</label>
                        <input type="date" value={fechaPago} onChange={e => setFechaPago(e.target.value)} className="input-field" />
                      </div>
                    </div>
                    <button onClick={registrarPago} disabled={saving || !valor} className="btn-success w-full flex items-center justify-center gap-2">
                      <CreditCard size={18} /> {saving ? 'Registrando...' : 'Registrar Pago'}
                    </button>
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="card text-center py-12">
              <CreditCard className="mx-auto text-gray-300 mb-4" size={48} />
              <p className="text-gray-500">Selecciona una factura para registrar pagos</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
