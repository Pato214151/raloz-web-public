/**
 * Caja diaria: abrir con base, registrar entradas y salidas, y cerrar con el
 * arqueo (diferencia entre lo esperado y lo contado).
 */

import { useState, useEffect } from 'react'
import api from '../../services/api'
import toast from 'react-hot-toast'
import { BookOpen, DollarSign, TrendingUp, TrendingDown, AlertCircle, Plus, Printer, History, X } from 'lucide-react'

const formatMoney = (n) => '$' + Math.round(n || 0).toLocaleString('es-CO')

const METODOS = ['EFECTIVO', 'NEQUI', 'DAVIPLATA', 'BANCOLOMBIA', 'TRANSFERENCIA']

export default function Caja() {
  const [caja, setCaja] = useState(null)
  const [movimientos, setMovimientos] = useState([])
  const [loading, setLoading] = useState(true)
  const [montoInicial, setMontoInicial] = useState('')
  const [montoReal, setMontoReal] = useState('')
  const [observaciones, setObservaciones] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [showMovForm, setShowMovForm] = useState(null)
  const [movForm, setMovForm] = useState({ concepto: '', monto: '', metodo_pago: 'EFECTIVO' })
  const [showHistorial, setShowHistorial] = useState(false)
  const [historial, setHistorial] = useState([])

  useEffect(() => { loadCaja() }, [])

  const loadCaja = async () => {
    setLoading(true)
    try {
      const res = await api.get('/caja/actual')
      setCaja(res.data.caja)
      if (res.data.caja) {
        const movRes = await api.get(`/caja/${res.data.caja.id_caja}/movimientos`)
        setMovimientos(movRes.data.movimientos || [])
      }
    } catch {
      toast.error('Error cargando caja')
    } finally {
      setLoading(false)
    }
  }

  const abrirCaja = async (e) => {
    e.preventDefault()
    try {
      await api.post('/caja/abrir', { monto_inicial: parseFloat(montoInicial) || 0 })
      toast.success('Caja abierta')
      setMontoInicial('')
      setShowForm(false)
      loadCaja()
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error')
    }
  }

  const cerrarCaja = async (e) => {
    e.preventDefault()
    if (!montoReal) { toast.error('Ingresa el monto real'); return }
    try {
      await api.post('/caja/cerrar', {
        monto_real: parseFloat(montoReal),
        observaciones,
      })
      toast.success('Caja cerrada')
      setMontoReal('')
      setObservaciones('')
      loadCaja()
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error')
    }
  }

  const registrarMovimiento = async (e) => {
    e.preventDefault()
    if (!movForm.concepto.trim() || !movForm.monto) {
      toast.error('Completa todos los campos')
      return
    }
    try {
      await api.post('/caja/movimiento', {
        tipo: showMovForm,
        concepto: movForm.concepto,
        monto: parseFloat(movForm.monto),
        metodo_pago: movForm.metodo_pago,
      })
      toast.success(`${showMovForm === 'INGRESO' ? 'Ingreso' : 'Egreso'} registrado`)
      setShowMovForm(null)
      setMovForm({ concepto: '', monto: '', metodo_pago: 'EFECTIVO' })
      loadCaja()
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error')
    }
  }

  const loadHistorial = async () => {
    try {
      const res = await api.get('/caja/historial', { params: { per_page: 50 } })
      setHistorial(res.data.cajas || [])
      setShowHistorial(true)
    } catch {
      toast.error('Error cargando historial')
    }
  }

  const imprimirCaja = () => {
    if (!caja) return
    const w = window.open('', '_blank')
    const movRows = movimientos.map(m => `
      <tr>
        <td>${m.fecha_hora ? m.fecha_hora.split('T')[1]?.slice(0, 5) || m.fecha_hora : ''}</td>
        <td><span style="color:${m.tipo === 'INGRESO' ? 'green' : 'red'};font-weight:bold">${m.tipo}</span></td>
        <td>${m.concepto || m.descripcion || ''}</td>
        <td>${m.metodo_pago || ''}</td>
        <td style="text-align:right;font-weight:bold;color:${m.tipo === 'INGRESO' ? 'green' : 'red'}">${m.tipo === 'INGRESO' ? '+' : '-'}${formatMoney(m.monto || m.valor)}</td>
      </tr>
    `).join('')

    w.document.write(`<!DOCTYPE html><html><head><title>Caja Diaria</title>
      <style>body{font-family:Arial;margin:20px}h2{color:#1976D2;border-bottom:3px solid #FFC107;padding-bottom:8px}
      table{width:100%;border-collapse:collapse;margin:10px 0;font-size:13px}
      th{background:#f5f5f5;padding:6px;border:1px solid #ddd;text-align:left}
      td{padding:5px 8px;border:1px solid #eee}
      .kpi{display:inline-block;padding:12px 20px;margin:5px;border-radius:8px;text-align:center;min-width:120px}
      @media print{body{margin:10px}}</style></head><body>
      <h2>RALOZ COL SAS - Caja Diaria</h2>
      <p>Apertura: ${caja.fecha_apertura || ''} | Usuario: ${caja.usuario_apertura || ''}</p>
      <div>
        <div class="kpi" style="background:#D4EDDA;color:#155724"><b>Ingresos</b><br>${formatMoney(caja.total_ventas)}</div>
        <div class="kpi" style="background:#F8D7DA;color:#721C24"><b>Gastos</b><br>${formatMoney(caja.total_gastos)}</div>
        <div class="kpi" style="background:#D1ECF1;color:#0C5460"><b>Esperado</b><br>${formatMoney(caja.monto_esperado)}</div>
        <div class="kpi" style="background:#FFF3CD;color:#856404"><b>Inicial</b><br>${formatMoney(caja.monto_inicial)}</div>
      </div>
      <h3>Movimientos</h3>
      <table><thead><tr><th>Hora</th><th>Tipo</th><th>Concepto</th><th>Método</th><th>Valor</th></tr></thead>
      <tbody>${movRows}</tbody></table>
      <hr><p style="text-align:center;font-size:11px;color:#999">RALOZ COL SAS</p></body></html>`)
    w.document.close()
    w.print()
  }

  // Calcular efectivo en caja
  const efectivoEnCaja = caja
    ? (caja.monto_inicial || 0) +
      movimientos.filter(m => m.tipo === 'INGRESO' && m.metodo_pago === 'EFECTIVO').reduce((s, m) => s + (m.monto || m.valor || 0), 0) -
      movimientos.filter(m => m.tipo === 'EGRESO' && m.metodo_pago === 'EFECTIVO').reduce((s, m) => s + (m.monto || m.valor || 0), 0)
    : 0

  if (loading) {
    return <div className="flex justify-center py-20"><div className="animate-spin h-10 w-10 border-b-2 border-raloz-600 rounded-full"></div></div>
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900">Caja Diaria</h2>
        <button onClick={loadHistorial} className="btn-secondary flex items-center gap-2 text-sm">
          <History size={16} /> Historial
        </button>
      </div>

      {!caja ? (
        <div className="card">
          <div className="text-center py-12">
            <BookOpen className="mx-auto text-gray-300 mb-4" size={48} />
            <h3 className="text-lg font-semibold text-gray-700 mb-2">No hay caja abierta</h3>
            <p className="text-gray-500 mb-6">Abre una caja para comenzar el turno</p>
            {!showForm ? (
              <button onClick={() => setShowForm(true)} className="btn-primary">Abrir Caja</button>
            ) : (
              <form onSubmit={abrirCaja} className="max-w-sm mx-auto space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-2">Monto Inicial en Efectivo</label>
                  <input type="number" min="0" step="0.01" value={montoInicial} onChange={e => setMontoInicial(e.target.value)}
                    className="input-field w-full" placeholder="0.00" autoFocus />
                </div>
                <div className="flex gap-3">
                  <button type="button" onClick={() => { setShowForm(false); setMontoInicial('') }} className="btn-secondary flex-1">Cancelar</button>
                  <button type="submit" className="btn-success flex-1">Abrir</button>
                </div>
              </form>
            )}
          </div>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Status Bar */}
          <div className="card bg-gradient-to-r from-green-50 to-green-100 border-green-200">
            <div className="flex items-center justify-between flex-wrap gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-green-500 animate-pulse" />
                  <p className="text-sm text-green-700 font-medium">CAJA ABIERTA</p>
                </div>
                <p className="text-xs text-green-600 mt-1">
                  Apertura: {caja.fecha_apertura} | Inicial: {formatMoney(caja.monto_inicial)} | Usuario: {caja.usuario_apertura}
                </p>
              </div>
              <div className="flex gap-2">
                <button onClick={imprimirCaja} className="btn-secondary flex items-center gap-1 text-sm">
                  <Printer size={14} /> Imprimir
                </button>
              </div>
            </div>
          </div>

          {/* KPIs */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div className="card">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs text-gray-600 mb-1">Monto Inicial</p>
                  <p className="text-2xl font-bold text-gray-900">{formatMoney(caja.monto_inicial)}</p>
                </div>
                <DollarSign className="text-blue-500" size={24} />
              </div>
            </div>
            <div className="card">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs text-gray-600 mb-1">Ingresos</p>
                  <p className="text-2xl font-bold text-green-600">{formatMoney(caja.total_ventas)}</p>
                </div>
                <TrendingUp className="text-green-500" size={24} />
              </div>
            </div>
            <div className="card">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs text-gray-600 mb-1">Egresos</p>
                  <p className="text-2xl font-bold text-red-600">{formatMoney(caja.total_gastos)}</p>
                </div>
                <TrendingDown className="text-red-500" size={24} />
              </div>
            </div>
            <div className="card">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs text-gray-600 mb-1">Esperado</p>
                  <p className="text-2xl font-bold text-blue-600">{formatMoney(caja.monto_esperado)}</p>
                </div>
                <AlertCircle className="text-amber-500" size={24} />
              </div>
            </div>
            <div className="card bg-green-50">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs text-green-700 mb-1">Efectivo en Caja</p>
                  <p className="text-2xl font-bold text-green-700">{formatMoney(efectivoEnCaja)}</p>
                </div>
                <DollarSign className="text-green-600" size={24} />
              </div>
            </div>
          </div>

          {/* Desglose + Movimientos */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="card">
              <h3 className="font-semibold mb-4">Desglose</h3>
              <div className="space-y-3">
                <div className="flex justify-between items-center pb-3 border-b">
                  <span className="text-gray-600">Monto Inicial</span>
                  <span className="font-semibold">{formatMoney(caja.monto_inicial)}</span>
                </div>
                <div className="flex justify-between items-center pb-3 border-b">
                  <span className="text-gray-600">+ Ingresos</span>
                  <span className="font-semibold text-green-600">+{formatMoney(caja.total_ventas)}</span>
                </div>
                <div className="flex justify-between items-center pb-3 border-b">
                  <span className="text-gray-600">- Egresos</span>
                  <span className="font-semibold text-red-600">-{formatMoney(caja.total_gastos)}</span>
                </div>
                <div className="flex justify-between items-center bg-blue-50 p-3 rounded font-bold">
                  <span>Esperado en Caja</span>
                  <span className="text-blue-600">{formatMoney(caja.monto_esperado)}</span>
                </div>
              </div>
            </div>

            {/* Movimientos con botones de registro */}
            <div className="card">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold">Movimientos</h3>
                <div className="flex gap-2">
                  <button onClick={() => setShowMovForm('INGRESO')} className="bg-green-500 hover:bg-green-600 text-white px-3 py-1.5 rounded text-xs font-medium flex items-center gap-1">
                    <Plus size={12} /> Ingreso
                  </button>
                  <button onClick={() => setShowMovForm('EGRESO')} className="bg-red-500 hover:bg-red-600 text-white px-3 py-1.5 rounded text-xs font-medium flex items-center gap-1">
                    <Plus size={12} /> Gasto
                  </button>
                </div>
              </div>
              {movimientos.length === 0 ? (
                <p className="text-sm text-gray-500">Sin movimientos registrados</p>
              ) : (
                <div className="space-y-2 max-h-72 overflow-y-auto">
                  {movimientos.map(m => (
                    <div key={m.id_movimiento} className="flex justify-between items-center py-2 border-b text-sm">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-bold ${
                            m.tipo === 'INGRESO' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                          }`}>{m.tipo}</span>
                          <span className="text-xs text-gray-400">{m.metodo_pago}</span>
                        </div>
                        <p className="text-xs text-gray-600 truncate mt-0.5">{m.concepto || m.descripcion}</p>
                      </div>
                      <p className={`font-semibold ml-2 ${m.tipo === 'INGRESO' ? 'text-green-600' : 'text-red-600'}`}>
                        {m.tipo === 'INGRESO' ? '+' : '-'}{formatMoney(m.monto || m.valor)}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Cerrar Caja */}
          <div className="card bg-gradient-to-r from-amber-50 to-orange-50 border-amber-200">
            <h3 className="text-lg font-semibold mb-4">Cerrar Caja</h3>
            <form onSubmit={cerrarCaja} className="space-y-4">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-2">Monto Real Contado</label>
                  <input type="number" min="0" step="0.01" value={montoReal} onChange={e => setMontoReal(e.target.value)}
                    className="input-field w-full" placeholder="Ingresa el dinero contado..." />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">Observaciones</label>
                  <input type="text" value={observaciones} onChange={e => setObservaciones(e.target.value)}
                    className="input-field w-full" placeholder="Notas opcionales..." />
                </div>
              </div>

              {montoReal && (
                <div className="p-3 bg-white rounded border-l-4 border-blue-500">
                  <p className="text-sm text-gray-600 mb-2">Diferencia:</p>
                  <p className={`text-2xl font-bold ${
                    Math.abs(parseFloat(montoReal) - (caja.monto_esperado || 0)) < 0.01
                      ? 'text-green-600'
                      : parseFloat(montoReal) > (caja.monto_esperado || 0)
                      ? 'text-blue-600'
                      : 'text-red-600'
                  }`}>
                    {parseFloat(montoReal) > (caja.monto_esperado || 0) ? '+' : ''}
                    {formatMoney(parseFloat(montoReal) - (caja.monto_esperado || 0))}
                    {Math.abs(parseFloat(montoReal) - (caja.monto_esperado || 0)) < 0.01 && ' (Cuadra)'}
                  </p>
                </div>
              )}

              <button type="submit" className="btn-danger w-full lg:w-auto">Cerrar Caja</button>
            </form>
          </div>
        </div>
      )}

      {/* Modal Registrar Movimiento */}
      {showMovForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl p-6 w-full max-w-md">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold">
                {showMovForm === 'INGRESO' ? 'Registrar Ingreso' : 'Registrar Gasto'}
              </h3>
              <button onClick={() => setShowMovForm(null)} className="text-gray-400 hover:text-gray-600">
                <X size={20} />
              </button>
            </div>
            <form onSubmit={registrarMovimiento} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Concepto *</label>
                <input type="text" required value={movForm.concepto} onChange={e => setMovForm({ ...movForm, concepto: e.target.value })}
                  className="input-field w-full" placeholder="Descripción del movimiento" autoFocus />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Monto *</label>
                <input type="number" required min="1" step="0.01" value={movForm.monto}
                  onChange={e => setMovForm({ ...movForm, monto: e.target.value })}
                  className="input-field w-full" placeholder="0.00" />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Método de Pago</label>
                <select value={movForm.metodo_pago} onChange={e => setMovForm({ ...movForm, metodo_pago: e.target.value })} className="input-field w-full">
                  {METODOS.map(m => <option key={m}>{m}</option>)}
                </select>
              </div>
              <div className="flex gap-3 justify-end pt-4 border-t">
                <button type="button" onClick={() => setShowMovForm(null)} className="btn-secondary">Cancelar</button>
                <button type="submit" className={showMovForm === 'INGRESO' ? 'btn-success' : 'btn-danger'}>
                  Registrar {showMovForm === 'INGRESO' ? 'Ingreso' : 'Gasto'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal Historial */}
      {showHistorial && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl p-6 w-full max-w-3xl max-h-[80vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold">Historial de Cajas Cerradas</h3>
              <button onClick={() => setShowHistorial(false)} className="text-gray-400 hover:text-gray-600">
                <X size={20} />
              </button>
            </div>
            {historial.length === 0 ? (
              <p className="text-gray-500 text-center py-8">No hay cajas cerradas</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b bg-gray-50">
                      <th className="px-3 py-2 text-left font-medium text-gray-600">Fecha</th>
                      <th className="px-3 py-2 text-left font-medium text-gray-600">Usuario</th>
                      <th className="px-3 py-2 text-right font-medium text-gray-600">Inicial</th>
                      <th className="px-3 py-2 text-right font-medium text-gray-600">Ingresos</th>
                      <th className="px-3 py-2 text-right font-medium text-gray-600">Gastos</th>
                      <th className="px-3 py-2 text-right font-medium text-gray-600">Esperado</th>
                      <th className="px-3 py-2 text-right font-medium text-gray-600">Real</th>
                      <th className="px-3 py-2 text-right font-medium text-gray-600">Diferencia</th>
                    </tr>
                  </thead>
                  <tbody>
                    {historial.map(c => (
                      <tr key={c.id_caja} className="border-b border-gray-50 hover:bg-gray-50">
                        <td className="px-3 py-2 text-gray-900">{c.fecha_apertura?.split('T')[0] || c.fecha_apertura}</td>
                        <td className="px-3 py-2 text-gray-600">{c.usuario_apertura}</td>
                        <td className="px-3 py-2 text-right">{formatMoney(c.monto_inicial)}</td>
                        <td className="px-3 py-2 text-right text-green-600">{formatMoney(c.total_ventas)}</td>
                        <td className="px-3 py-2 text-right text-red-600">{formatMoney(c.total_gastos)}</td>
                        <td className="px-3 py-2 text-right font-medium">{formatMoney(c.monto_esperado)}</td>
                        <td className="px-3 py-2 text-right font-medium">{formatMoney(c.monto_real)}</td>
                        <td className={`px-3 py-2 text-right font-bold ${
                          (c.diferencia || 0) >= 0 ? 'text-green-600' : 'text-red-600'
                        }`}>{formatMoney(c.diferencia)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
