import { useState } from 'react'
import api from '../../services/api'
import toast from 'react-hot-toast'
import { CreditCard, Search } from 'lucide-react'

export default function Pagos() {
  const [buscar, setBuscar] = useState('')
  const [factura, setFactura] = useState(null)
  const [valor, setValor] = useState('')
  const [metodo, setMetodo] = useState('EFECTIVO')
  const [saving, setSaving] = useState(false)

  const buscarFactura = async () => {
    if (!buscar.trim()) return
    try {
      const res = await api.get('/facturas', { params: { buscar, per_page: 1 } })
      if (res.data.facturas?.length > 0) {
        const detRes = await api.get(`/facturas/${res.data.facturas[0].id_factura}`)
        setFactura(detRes.data.factura)
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
      })
      toast.success('Pago registrado')
      // Recargar factura
      const res = await api.get(`/facturas/${factura.id_factura}`)
      setFactura(res.data.factura)
      setValor('')
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error registrando pago')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">Registrar Pago</h2>

      <div className="flex gap-3">
        <input value={buscar} onChange={e => setBuscar(e.target.value)} onKeyDown={e => e.key === 'Enter' && buscarFactura()}
          className="input-field flex-1" placeholder="Número de factura o nombre..." />
        <button onClick={buscarFactura} className="btn-primary flex items-center gap-2">
          <Search size={18} /> Buscar
        </button>
      </div>

      {factura && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="card">
            <h3 className="text-lg font-semibold mb-4">{factura.numero_factura}</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between"><span className="text-gray-500">Cliente</span><span>{factura.cliente_nombre}</span></div>
              <div className="flex justify-between"><span className="text-gray-500">Total</span><span className="font-bold">${Math.round(factura.total).toLocaleString('es-CO')}</span></div>
              <div className="flex justify-between"><span className="text-gray-500">Pagado</span><span className="text-green-600">${Math.round(factura.total_pagado).toLocaleString('es-CO')}</span></div>
              <div className="flex justify-between border-t pt-2"><span className="text-gray-700 font-medium">Saldo</span><span className="text-red-600 font-bold text-lg">${Math.round(factura.saldo).toLocaleString('es-CO')}</span></div>
            </div>
          </div>

          {factura.saldo > 0 && (
            <div className="card">
              <h3 className="text-lg font-semibold mb-4">Nuevo Pago</h3>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Valor</label>
                  <input type="number" min="1" max={factura.saldo} value={valor} onChange={e => setValor(e.target.value)} className="input-field" placeholder={`Máximo $${Math.round(factura.saldo).toLocaleString('es-CO')}`} />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Método</label>
                  <select value={metodo} onChange={e => setMetodo(e.target.value)} className="input-field">
                    {['EFECTIVO', 'NEQUI', 'DAVIPLATA', 'BANCOLOMBIA', 'TRANSFERENCIA'].map(m => <option key={m}>{m}</option>)}
                  </select>
                </div>
                <button onClick={registrarPago} disabled={saving || !valor} className="btn-success w-full flex items-center justify-center gap-2">
                  <CreditCard size={18} /> {saving ? 'Registrando...' : 'Registrar Pago'}
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
