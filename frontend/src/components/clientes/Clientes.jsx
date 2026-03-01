import { useState, useEffect } from 'react'
import api from '../../services/api'
import toast from 'react-hot-toast'
import { Users, Plus, Search, Edit, X, Eye, Printer, Download } from 'lucide-react'

const fmt = (n) => '$' + Math.round(n || 0).toLocaleString('es-CO')

export default function Clientes() {
  const [clientes, setClientes] = useState([])
  const [buscar, setBuscar] = useState('')
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [showDetail, setShowDetail] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [selectedCliente, setSelectedCliente] = useState(null)
  const [colegios, setColegios] = useState([])
  const [historialCompras, setHistorialCompras] = useState([])
  const [resumenHistorial, setResumenHistorial] = useState(null)
  const [form, setForm] = useState({
    nombre: '', apellidos: '', tipo_documento: 'CC', numero_documento: '', dv: '',
    razon_social: '', telefono: '', celular: '', email: '', direccion: '',
    ciudad: '', departamento: '', codigo_postal: '', pais: 'Colombia',
    id_colegio: '', estudiante_nombre: '', estudiante_grado: '', notas: ''
  })

  useEffect(() => {
    loadColegios()
    loadClientes()
  }, [])

  const loadColegios = async () => {
    try {
      const res = await api.get('/colegios')
      setColegios(res.data.colegios || [])
    } catch (err) {
      console.error('Error cargando colegios:', err)
    }
  }

  const loadClientes = async (q = '') => {
    setLoading(true)
    try {
      const res = await api.get('/clientes', { params: { buscar: q, per_page: 100 } })
      setClientes(res.data.clientes || [])
    } catch {
      toast.error('Error cargando clientes')
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = (e) => {
    e.preventDefault()
    loadClientes(buscar)
  }

  const blankForm = () => ({
    nombre: '', apellidos: '', tipo_documento: 'CC', numero_documento: '', dv: '',
    razon_social: '', telefono: '', celular: '', email: '', direccion: '',
    ciudad: '', departamento: '', codigo_postal: '', pais: 'Colombia',
    id_colegio: '', estudiante_nombre: '', estudiante_grado: '', notas: ''
  })

  const openForm = (cliente = null) => {
    setShowDetail(false) // cerrar modal detalle para que no tape el formulario
    if (cliente) {
      setEditingId(cliente.id_cliente)
      setForm({
        nombre: cliente.nombre || '', apellidos: cliente.apellidos || '',
        tipo_documento: cliente.tipo_documento || 'CC',
        numero_documento: cliente.numero_documento || '', dv: cliente.dv || '',
        razon_social: cliente.razon_social || '',
        telefono: cliente.telefono || '', celular: cliente.celular || '',
        email: cliente.email || '', direccion: cliente.direccion || '',
        ciudad: cliente.ciudad || '', departamento: cliente.departamento || '',
        codigo_postal: cliente.codigo_postal || '', pais: cliente.pais || 'Colombia',
        id_colegio: cliente.id_colegio || '',
        estudiante_nombre: cliente.estudiante_nombre || '',
        estudiante_grado: cliente.estudiante_grado || '',
        notas: cliente.notas || ''
      })
    } else {
      setEditingId(null)
      setForm(blankForm())
    }
    setShowForm(true)
  }

  const guardarCliente = async (e) => {
    e.preventDefault()
    try {
      const datos = { ...form, id_colegio: form.id_colegio || null }
      if (editingId) {
        await api.put(`/clientes/${editingId}`, datos)
        toast.success('Cliente actualizado')
      } else {
        await api.post('/clientes', datos)
        toast.success('Cliente creado')
      }
      setShowForm(false)
      setEditingId(null)
      loadClientes()
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error guardando cliente')
    }
  }

  const verDetalle = async (cliente) => {
    setSelectedCliente(cliente)
    setShowDetail(true)
    try {
      const res = await api.get(`/clientes/${cliente.id_cliente}/historial`)
      setHistorialCompras(res.data.facturas || [])
      setResumenHistorial(res.data.resumen || null)
    } catch {
      toast.error('Error cargando historial')
    }
  }

  const eliminarCliente = async (id, nombre) => {
    if (!confirm(`¿Eliminar cliente "${nombre}"?`)) return
    try {
      await api.delete(`/clientes/${id}`)
      toast.success('Cliente eliminado')
      loadClientes()
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error eliminando cliente')
    }
  }

  const imprimirHistorial = () => {
    if (!selectedCliente) return
    const w = window.open('', '_blank')
    const rows = historialCompras.map(f => `
      <tr>
        <td>${f.numero_factura}</td><td>${f.fecha || ''}</td><td>${f.colegio_nombre || ''}</td>
        <td style="text-align:right">${fmt(f.total)}</td>
        <td style="text-align:right;color:green">${fmt(f.total_abonado)}</td>
        <td style="text-align:right;color:${f.saldo_pendiente > 0 ? 'red' : 'green'}">${fmt(f.saldo_pendiente)}</td>
        <td><span style="color:${f.estado === 'PAGADA' ? 'green' : f.estado === 'ANULADA' ? 'gray' : 'orange'}">${f.estado}</span></td>
      </tr>`).join('')

    w.document.write(`<!DOCTYPE html><html><head><title>Historial - ${selectedCliente.nombre}</title>
      <style>body{font-family:Arial;margin:20px}h2{color:#1976D2;border-bottom:3px solid #FFC107;padding-bottom:8px}
      table{width:100%;border-collapse:collapse;margin:10px 0;font-size:12px}
      th{background:#f5f5f5;padding:6px;border:1px solid #ddd;text-align:left}td{padding:5px 8px;border:1px solid #eee}
      .info{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:15px 0;font-size:13px}
      .kpi{display:inline-block;padding:10px 18px;margin:5px;border-radius:8px;text-align:center}
      @media print{body{margin:10px}}</style></head><body>
      <h2>RALOZ COL SAS - Historial de Cliente</h2>
      <div class="info">
        <div><small>Nombre</small><br><b>${selectedCliente.nombre} ${selectedCliente.apellidos || ''}</b></div>
        <div><small>Documento</small><br><b>${selectedCliente.tipo_documento} ${selectedCliente.numero_documento || ''}${selectedCliente.dv ? '-' + selectedCliente.dv : ''}</b></div>
        <div><small>Teléfono</small><br>${selectedCliente.telefono || '—'}</div>
        <div><small>Email</small><br>${selectedCliente.email || '—'}</div>
        <div><small>Colegio</small><br>${selectedCliente.colegio_nombre || '—'}</div>
        <div><small>Estudiante</small><br>${selectedCliente.estudiante_nombre || '—'} ${selectedCliente.estudiante_grado || ''}</div>
      </div>
      ${resumenHistorial ? `<div>
        <div class="kpi" style="background:#D4EDDA;color:#155724"><small>Total Compras</small><br><b>${fmt(resumenHistorial.total_compras)}</b></div>
        <div class="kpi" style="background:#D1ECF1;color:#0C5460"><small>Total Pagado</small><br><b>${fmt(resumenHistorial.total_pagado)}</b></div>
        <div class="kpi" style="background:#F8D7DA;color:#721C24"><small>Saldo</small><br><b>${fmt(resumenHistorial.saldo_pendiente)}</b></div>
      </div>` : ''}
      <h3>Facturas (${historialCompras.length})</h3>
      <table><thead><tr><th>Factura</th><th>Fecha</th><th>Colegio</th><th>Total</th><th>Pagado</th><th>Saldo</th><th>Estado</th></tr></thead>
      <tbody>${rows}</tbody></table>
      <hr><p style="text-align:center;font-size:11px;color:#999">RALOZ COL SAS</p></body></html>`)
    w.document.close()
    w.print()
  }

  const exportarFacturaElectronica = () => {
    if (!selectedCliente) return
    const c = selectedCliente
    // Fila de datos del cliente
    const clienteRow = [
      c.tipo_documento || 'CC',
      c.numero_documento || '',
      c.dv || '',
      c.nombre || '',
      c.apellidos || '',
      c.razon_social || '',
      c.email || '',
      c.telefono || c.celular || '',
      c.direccion || '',
      c.ciudad || '',
      c.departamento || '',
      c.pais || 'Colombia',
    ]
    // Filas de facturas
    const facturaRows = historialCompras.map(f => [
      f.numero_factura,
      f.fecha || '',
      f.colegio_nombre || '',
      f.total,
      f.total_abonado || 0,
      f.saldo_pendiente || 0,
      f.estado,
    ])

    const clienteHeader = ['tipo_documento','numero_documento','dv','nombre','apellidos','razon_social','email','telefono','direccion','ciudad','departamento','pais']
    const facturaHeader = ['numero_factura','fecha','colegio','total','total_pagado','saldo','estado']

    const csvParts = [
      '=== DATOS CLIENTE ===',
      clienteHeader.join(','),
      clienteRow.map(v => `"${String(v).replace(/"/g, '""')}"`).join(','),
      '',
      '=== FACTURAS ===',
      facturaHeader.join(','),
      ...facturaRows.map(row => row.map(v => `"${String(v).replace(/"/g, '""')}"`).join(',')),
    ]

    const blob = new Blob([csvParts.join('\n')], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `factura_electronica_${c.numero_documento || c.nombre}_${new Date().toISOString().split('T')[0]}.csv`
    a.click()
    URL.revokeObjectURL(url)
    toast.success('Datos exportados para factura electrónica')
  }

  if (loading && clientes.length === 0) {
    return <div className="flex justify-center py-20"><div className="animate-spin h-10 w-10 border-b-2 border-raloz-600 rounded-full"></div></div>
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <h2 className="text-2xl font-bold text-gray-900">Clientes</h2>
        <button onClick={() => openForm()} className="btn-primary flex items-center gap-2"><Plus size={18} /> Nuevo Cliente</button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card"><p className="text-sm text-gray-600">Total Clientes</p><p className="text-3xl font-bold text-raloz-600">{clientes.length}</p></div>
        <div className="card"><p className="text-sm text-gray-600">Con Colegio</p><p className="text-3xl font-bold text-blue-600">{clientes.filter(c => c.id_colegio).length}</p></div>
        <div className="card"><p className="text-sm text-gray-600">Con Documento</p><p className="text-3xl font-bold text-green-600">{clientes.filter(c => c.numero_documento).length}</p></div>
      </div>

      <form onSubmit={handleSearch} className="card flex gap-3 flex-wrap">
        <div className="relative flex-1 min-w-64">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={16} />
          <input type="text" value={buscar} onChange={(e) => setBuscar(e.target.value)} placeholder="Buscar por nombre, teléfono, documento, email..." className="input-field pl-10 w-full" />
        </div>
        <button type="submit" className="btn-primary">Buscar</button>
      </form>

      {clientes.length === 0 ? (
        <div className="card text-center py-12"><Users className="mx-auto text-gray-300 mb-4" size={48} /><p className="text-gray-500">No hay clientes registrados</p></div>
      ) : (
        <div className="card overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50">
                <th className="px-4 py-3 text-left text-gray-600 font-medium">Nombre</th>
                <th className="px-4 py-3 text-left text-gray-600 font-medium">Documento</th>
                <th className="px-4 py-3 text-left text-gray-600 font-medium">Teléfono</th>
                <th className="px-4 py-3 text-left text-gray-600 font-medium">Email</th>
                <th className="px-4 py-3 text-left text-gray-600 font-medium">Colegio</th>
                <th className="px-4 py-3 text-left text-gray-600 font-medium">Estudiante</th>
                <th className="px-4 py-3 text-center text-gray-600 font-medium">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {clientes.map(c => (
                <tr key={c.id_cliente} className="border-b border-gray-50 hover:bg-gray-50">
                  <td className="px-4 py-3"><p className="font-medium text-gray-900">{c.nombre}</p>{c.apellidos && <p className="text-xs text-gray-500">{c.apellidos}</p>}</td>
                  <td className="px-4 py-3 text-gray-700">{c.numero_documento ? `${c.tipo_documento} ${c.numero_documento}${c.dv ? '-' + c.dv : ''}` : '—'}</td>
                  <td className="px-4 py-3 text-gray-700">{c.telefono || c.celular || '—'}</td>
                  <td className="px-4 py-3 text-gray-700 text-xs">{c.email || '—'}</td>
                  <td className="px-4 py-3 text-gray-700 text-xs">{c.colegio_nombre || '—'}</td>
                  <td className="px-4 py-3 text-gray-700 text-xs">{c.estudiante_nombre ? `${c.estudiante_nombre} ${c.estudiante_grado || ''}` : '—'}</td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex justify-center gap-2">
                      <button onClick={() => verDetalle(c)} className="text-blue-600 hover:text-blue-800 p-1" title="Ver detalles"><Eye size={14} /></button>
                      <button onClick={() => openForm(c)} className="text-amber-600 hover:text-amber-800 p-1" title="Editar"><Edit size={14} /></button>
                      <button onClick={() => eliminarCliente(c.id_cliente, c.nombre)} className="text-red-600 hover:text-red-800 p-1" title="Eliminar"><X size={14} /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Modal Crear/Editar */}
      {showForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl p-6 w-full max-w-3xl max-h-[90vh] overflow-y-auto">
            <h3 className="text-lg font-bold mb-4">{editingId ? 'Editar Cliente' : 'Nuevo Cliente'}</h3>
            <form onSubmit={guardarCliente} className="space-y-4">
              <p className="text-sm font-medium text-gray-500 border-b pb-1">Datos Personales</p>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div><label className="block text-sm font-medium mb-1">Nombre *</label><input type="text" required value={form.nombre} onChange={e => setForm({ ...form, nombre: e.target.value })} className="input-field w-full" placeholder="Nombre" /></div>
                <div><label className="block text-sm font-medium mb-1">Apellidos</label><input type="text" value={form.apellidos} onChange={e => setForm({ ...form, apellidos: e.target.value })} className="input-field w-full" placeholder="Apellidos" /></div>
                <div><label className="block text-sm font-medium mb-1">Razón Social</label><input type="text" value={form.razon_social} onChange={e => setForm({ ...form, razon_social: e.target.value })} className="input-field w-full" placeholder="Si es empresa" /></div>
              </div>

              <p className="text-sm font-medium text-gray-500 border-b pb-1">Documento</p>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div><label className="block text-sm font-medium mb-1">Tipo</label>
                  <select value={form.tipo_documento} onChange={e => setForm({ ...form, tipo_documento: e.target.value })} className="input-field w-full">
                    <option value="CC">CC - Cédula</option><option value="CE">CE - Extranjería</option><option value="NIT">NIT</option><option value="PASAPORTE">Pasaporte</option><option value="TI">TI - Tarjeta Id.</option>
                  </select>
                </div>
                <div className="md:col-span-2"><label className="block text-sm font-medium mb-1">Número</label><input type="text" value={form.numero_documento} onChange={e => setForm({ ...form, numero_documento: e.target.value })} className="input-field w-full" /></div>
                <div><label className="block text-sm font-medium mb-1">DV</label><input type="text" value={form.dv} onChange={e => setForm({ ...form, dv: e.target.value })} className="input-field w-full" maxLength={2} /></div>
              </div>

              <p className="text-sm font-medium text-gray-500 border-b pb-1">Contacto</p>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div><label className="block text-sm font-medium mb-1">Teléfono</label><input type="tel" value={form.telefono} onChange={e => setForm({ ...form, telefono: e.target.value })} className="input-field w-full" /></div>
                <div><label className="block text-sm font-medium mb-1">Celular</label><input type="tel" value={form.celular} onChange={e => setForm({ ...form, celular: e.target.value })} className="input-field w-full" /></div>
                <div><label className="block text-sm font-medium mb-1">Email</label><input type="email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} className="input-field w-full" /></div>
              </div>

              <p className="text-sm font-medium text-gray-500 border-b pb-1">Dirección</p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="md:col-span-2"><label className="block text-sm font-medium mb-1">Dirección</label><input type="text" value={form.direccion} onChange={e => setForm({ ...form, direccion: e.target.value })} className="input-field w-full" /></div>
                <div><label className="block text-sm font-medium mb-1">Ciudad</label><input type="text" value={form.ciudad} onChange={e => setForm({ ...form, ciudad: e.target.value })} className="input-field w-full" /></div>
                <div><label className="block text-sm font-medium mb-1">Departamento</label><input type="text" value={form.departamento} onChange={e => setForm({ ...form, departamento: e.target.value })} className="input-field w-full" /></div>
              </div>

              <p className="text-sm font-medium text-gray-500 border-b pb-1">Colegio / Estudiante</p>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div><label className="block text-sm font-medium mb-1">Colegio</label>
                  <select value={form.id_colegio} onChange={e => setForm({ ...form, id_colegio: e.target.value })} className="input-field w-full">
                    <option value="">Seleccionar</option>{colegios.map(c => <option key={c.id_colegio} value={c.id_colegio}>{c.nombre}</option>)}
                  </select>
                </div>
                <div><label className="block text-sm font-medium mb-1">Estudiante</label><input type="text" value={form.estudiante_nombre} onChange={e => setForm({ ...form, estudiante_nombre: e.target.value })} className="input-field w-full" placeholder="Nombre estudiante" /></div>
                <div><label className="block text-sm font-medium mb-1">Grado</label><input type="text" value={form.estudiante_grado} onChange={e => setForm({ ...form, estudiante_grado: e.target.value })} className="input-field w-full" /></div>
              </div>

              <div><label className="block text-sm font-medium mb-1">Notas</label><textarea value={form.notas} onChange={e => setForm({ ...form, notas: e.target.value })} className="input-field w-full" rows={2} /></div>

              <div className="flex gap-3 justify-end pt-4 border-t">
                <button type="button" onClick={() => { setShowForm(false); setEditingId(null) }} className="btn-secondary">Cancelar</button>
                <button type="submit" className="btn-primary">{editingId ? 'Actualizar' : 'Crear'}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal Detalle */}
      {showDetail && selectedCliente && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl p-6 w-full max-w-3xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold">Detalles de Cliente</h3>
              <div className="flex gap-2">
                <button onClick={exportarFacturaElectronica} className="btn-secondary flex items-center gap-1 text-sm" title="Exportar datos para factura electrónica"><Download size={14} /> Exportar</button>
                <button onClick={imprimirHistorial} className="btn-secondary flex items-center gap-1 text-sm"><Printer size={14} /> Imprimir</button>
              </div>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6 pb-4 border-b">
              <div><p className="text-xs text-gray-500">Nombre</p><p className="font-semibold">{selectedCliente.nombre} {selectedCliente.apellidos || ''}</p></div>
              <div><p className="text-xs text-gray-500">Documento</p><p className="font-semibold">{selectedCliente.tipo_documento} {selectedCliente.numero_documento || '—'}{selectedCliente.dv ? '-' + selectedCliente.dv : ''}</p></div>
              <div><p className="text-xs text-gray-500">Teléfono</p><p className="font-semibold">{selectedCliente.telefono || selectedCliente.celular || '—'}</p></div>
              <div><p className="text-xs text-gray-500">Email</p><p className="font-semibold text-sm">{selectedCliente.email || '—'}</p></div>
              <div><p className="text-xs text-gray-500">Colegio</p><p className="font-semibold">{selectedCliente.colegio_nombre || '—'}</p></div>
              <div><p className="text-xs text-gray-500">Estudiante</p><p className="font-semibold">{selectedCliente.estudiante_nombre || '—'} {selectedCliente.estudiante_grado || ''}</p></div>
            </div>

            {resumenHistorial && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
                <div className="bg-blue-50 p-3 rounded text-center"><p className="text-xs text-blue-600">Facturas</p><p className="text-xl font-bold text-blue-700">{resumenHistorial.total_facturas}</p></div>
                <div className="bg-green-50 p-3 rounded text-center"><p className="text-xs text-green-600">Compras</p><p className="text-lg font-bold text-green-700">{fmt(resumenHistorial.total_compras)}</p></div>
                <div className="bg-emerald-50 p-3 rounded text-center"><p className="text-xs text-emerald-600">Pagado</p><p className="text-lg font-bold text-emerald-700">{fmt(resumenHistorial.total_pagado)}</p></div>
                <div className="bg-red-50 p-3 rounded text-center"><p className="text-xs text-red-600">Saldo</p><p className="text-lg font-bold text-red-700">{fmt(resumenHistorial.saldo_pendiente)}</p></div>
              </div>
            )}

            <h4 className="font-semibold mb-3">Historial de Compras</h4>
            {historialCompras.length === 0 ? (
              <p className="text-gray-500 text-sm mb-4">Sin compras registradas</p>
            ) : (
              <div className="overflow-x-auto mb-4">
                <table className="w-full text-sm">
                  <thead><tr className="border-b bg-gray-50">
                    <th className="px-3 py-2 text-left font-medium text-gray-600">Factura</th>
                    <th className="px-3 py-2 text-left font-medium text-gray-600">Fecha</th>
                    <th className="px-3 py-2 text-right font-medium text-gray-600">Total</th>
                    <th className="px-3 py-2 text-right font-medium text-gray-600">Pagado</th>
                    <th className="px-3 py-2 text-right font-medium text-gray-600">Saldo</th>
                    <th className="px-3 py-2 text-center font-medium text-gray-600">Estado</th>
                  </tr></thead>
                  <tbody>
                    {historialCompras.map(f => (
                      <tr key={f.id_factura} className="border-b border-gray-50 hover:bg-gray-50">
                        <td className="px-3 py-2 font-medium text-raloz-600">{f.numero_factura}</td>
                        <td className="px-3 py-2 text-gray-600">{f.fecha}</td>
                        <td className="px-3 py-2 text-right">{fmt(f.total)}</td>
                        <td className="px-3 py-2 text-right text-green-600">{fmt(f.total_abonado)}</td>
                        <td className="px-3 py-2 text-right font-medium text-red-600">{fmt(f.saldo_pendiente)}</td>
                        <td className="px-3 py-2 text-center">
                          <span className={`px-2 py-0.5 rounded text-xs font-medium ${f.estado === 'PAGADA' ? 'bg-green-100 text-green-700' : f.estado === 'ANULADA' ? 'bg-gray-100 text-gray-600' : 'bg-amber-100 text-amber-700'}`}>{f.estado}</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            <div className="flex gap-3 justify-end pt-4 border-t">
              <button onClick={() => setShowDetail(false)} className="btn-secondary">Cerrar</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
