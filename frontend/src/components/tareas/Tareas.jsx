import { useState, useEffect } from 'react'
import { useAuth } from '../../context/AuthContext'
import api from '../../services/api'
import toast from 'react-hot-toast'
import {
  CheckSquare, Square, Plus, Trash2, ClipboardList,
  Calendar, User, ChevronDown, ChevronUp, AlertCircle, Flag
} from 'lucide-react'

const PRIORIDAD_CONFIG = {
  ALTA:  { label: 'Alta',  color: 'bg-red-100 text-red-700',    dot: 'bg-red-500' },
  MEDIA: { label: 'Media', color: 'bg-amber-100 text-amber-700', dot: 'bg-amber-400' },
  BAJA:  { label: 'Baja',  color: 'bg-gray-100 text-gray-500',   dot: 'bg-gray-400' },
}

const HOY = new Date().toISOString().split('T')[0]

function estaVencida(fecha) {
  if (!fecha) return false
  return fecha < HOY
}

function badgeAsignado(nombre) {
  if (!nombre) return <span className="text-xs text-gray-400 italic">Todos</span>
  return (
    <span className="inline-flex items-center gap-1 text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full">
      <User size={11} /> {nombre}
    </span>
  )
}

export default function Tareas() {
  const { usuario } = useAuth()
  const esAdmin = usuario?.rol === 'administrador'

  const [tareas, setTareas] = useState([])
  const [usuarios, setUsuarios] = useState([])
  const [loading, setLoading] = useState(true)
  const [filtroPendientes, setFiltroPendientes] = useState(false)
  const [mostrarForm, setMostrarForm] = useState(false)
  const [form, setForm] = useState({ titulo: '', descripcion: '', fecha_vencimiento: '', asignada_a: '', prioridad: 'MEDIA' })
  const [guardando, setGuardando] = useState(false)

  useEffect(() => {
    cargar()
    if (esAdmin) cargarUsuarios()
  }, [filtroPendientes])

  async function cargar() {
    setLoading(true)
    try {
      const params = filtroPendientes ? '?pendientes=true' : ''
      const { data } = await api.get(`/tareas${params}`)
      setTareas(data)
    } catch {
      toast.error('Error cargando tareas')
    } finally {
      setLoading(false)
    }
  }

  async function cargarUsuarios() {
    try {
      const { data } = await api.get('/tareas/usuarios')
      setUsuarios(data)
    } catch { /* silencioso */ }
  }

  async function crearTarea() {
    if (!form.titulo.trim()) { toast.error('Escribe un título'); return }
    setGuardando(true)
    try {
      await api.post('/tareas', {
        titulo: form.titulo.trim(),
        descripcion: form.descripcion.trim() || null,
        prioridad: form.prioridad || 'MEDIA',
        fecha_vencimiento: form.fecha_vencimiento || null,
        asignada_a: form.asignada_a ? parseInt(form.asignada_a) : null,
      })
      toast.success('Tarea creada')
      setForm({ titulo: '', descripcion: '', fecha_vencimiento: '', asignada_a: '', prioridad: 'MEDIA' })
      setMostrarForm(false)
      cargar()
    } catch (e) {
      toast.error(e.response?.data?.error || 'Error al crear tarea')
    } finally {
      setGuardando(false)
    }
  }

  async function toggleCompletar(id) {
    try {
      const { data } = await api.patch(`/tareas/${id}/completar`)
      setTareas(prev => prev.map(t => t.id_tarea === id ? data : t))
    } catch {
      toast.error('Error actualizando tarea')
    }
  }

  async function eliminar(id) {
    if (!confirm('¿Eliminar esta tarea?')) return
    try {
      await api.delete(`/tareas/${id}`)
      setTareas(prev => prev.filter(t => t.id_tarea !== id))
      toast.success('Tarea eliminada')
    } catch {
      toast.error('Error eliminando tarea')
    }
  }

  const pendientes = tareas.filter(t => !t.completada)
  const completadas = tareas.filter(t => t.completada)

  return (
    <div className="max-w-2xl mx-auto space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <ClipboardList size={24} className="text-raloz-600" />
          <div>
            <h1 className="text-xl font-bold text-gray-900">Tareas</h1>
            <p className="text-xs text-gray-500">
              {pendientes.length} pendiente{pendientes.length !== 1 ? 's' : ''}
              {completadas.length > 0 && ` · ${completadas.length} completada${completadas.length !== 1 ? 's' : ''}`}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setFiltroPendientes(v => !v)}
            className={`text-xs px-3 py-1.5 rounded-lg border transition-colors ${
              filtroPendientes
                ? 'bg-amber-50 border-amber-300 text-amber-700'
                : 'border-gray-200 text-gray-500 hover:bg-gray-50'
            }`}
          >
            {filtroPendientes ? 'Ver todas' : 'Solo pendientes'}
          </button>

          {esAdmin && (
            <button
              onClick={() => setMostrarForm(v => !v)}
              className="btn-primary flex items-center gap-1.5 text-sm"
            >
              <Plus size={16} />
              Nueva tarea
            </button>
          )}
        </div>
      </div>

      {/* Formulario nueva tarea (admin) */}
      {esAdmin && mostrarForm && (
        <div className="bg-white border border-raloz-200 rounded-xl p-4 space-y-3 shadow-sm">
          <h3 className="font-semibold text-gray-800 text-sm">Nueva tarea</h3>

          <input
            className="input-field w-full"
            placeholder="Título de la tarea *"
            value={form.titulo}
            onChange={e => setForm({ ...form, titulo: e.target.value })}
            onKeyDown={e => e.key === 'Enter' && crearTarea()}
          />

          <textarea
            className="input-field w-full resize-none"
            rows={2}
            placeholder="Descripción (opcional)"
            value={form.descripcion}
            onChange={e => setForm({ ...form, descripcion: e.target.value })}
          />

          <div className="flex gap-2">
            <div className="flex-1">
              <label className="block text-xs text-gray-500 mb-1">Prioridad</label>
              <div className="flex gap-1">
                {['ALTA', 'MEDIA', 'BAJA'].map(p => {
                  const cfg = PRIORIDAD_CONFIG[p]
                  return (
                    <button key={p} type="button"
                      onClick={() => setForm({ ...form, prioridad: p })}
                      className={`flex-1 py-1.5 text-xs font-medium rounded-lg border-2 transition-colors ${
                        form.prioridad === p ? `${cfg.color} border-current` : 'border-gray-200 text-gray-400 hover:border-gray-300'
                      }`}>
                      {cfg.label}
                    </button>
                  )
                })}
              </div>
            </div>
            <div className="flex-1">
              <label className="block text-xs text-gray-500 mb-1">Fecha límite (opcional)</label>
              <input
                type="date"
                className="input-field w-full"
                value={form.fecha_vencimiento}
                onChange={e => setForm({ ...form, fecha_vencimiento: e.target.value })}
              />
            </div>
            <div className="flex-1">
              <label className="block text-xs text-gray-500 mb-1">Asignar a</label>
              <select
                className="input-field w-full"
                value={form.asignada_a}
                onChange={e => setForm({ ...form, asignada_a: e.target.value })}
              >
                <option value="">Todos</option>
                {usuarios.map(u => (
                  <option key={u.id_usuario} value={u.id_usuario}>
                    {u.usuario} ({u.rol})
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="flex gap-2 pt-1">
            <button
              onClick={crearTarea}
              disabled={guardando}
              className="btn-primary text-sm"
            >
              {guardando ? 'Guardando...' : 'Crear tarea'}
            </button>
            <button
              onClick={() => { setMostrarForm(false); setForm({ titulo: '', descripcion: '', fecha_vencimiento: '', asignada_a: '', prioridad: 'MEDIA' }) }}
              className="btn-secondary text-sm"
            >
              Cancelar
            </button>
          </div>
        </div>
      )}

      {/* Lista de tareas */}
      {loading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-raloz-600" />
        </div>
      ) : tareas.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <ClipboardList size={40} className="mx-auto mb-3 opacity-40" />
          <p className="text-sm">No hay tareas {filtroPendientes ? 'pendientes' : ''}</p>
          {esAdmin && <p className="text-xs mt-1">Crea la primera con el botón "Nueva tarea"</p>}
        </div>
      ) : (
        <div className="space-y-2">
          {/* Pendientes */}
          {pendientes.map(t => (
            <TareaCard
              key={t.id_tarea}
              tarea={t}
              esAdmin={esAdmin}
              onToggle={toggleCompletar}
              onEliminar={eliminar}
            />
          ))}

          {/* Separador completadas */}
          {completadas.length > 0 && !filtroPendientes && (
            <>
              <div className="flex items-center gap-2 pt-2">
                <div className="flex-1 h-px bg-gray-200" />
                <span className="text-xs text-gray-400">Completadas ({completadas.length})</span>
                <div className="flex-1 h-px bg-gray-200" />
              </div>
              {completadas.map(t => (
                <TareaCard
                  key={t.id_tarea}
                  tarea={t}
                  esAdmin={esAdmin}
                  onToggle={toggleCompletar}
                  onEliminar={eliminar}
                />
              ))}
            </>
          )}
        </div>
      )}
    </div>
  )
}

function TareaCard({ tarea, esAdmin, onToggle, onEliminar }) {
  const [expandida, setExpandida] = useState(false)
  const vencida = !tarea.completada && estaVencida(tarea.fecha_vencimiento)

  return (
    <div className={`bg-white rounded-xl border transition-all ${
      tarea.completada
        ? 'border-gray-100 opacity-60'
        : vencida
          ? 'border-red-200 bg-red-50/30'
          : 'border-gray-200 hover:border-raloz-200'
    }`}>
      <div className="flex items-start gap-3 p-3.5">
        {/* Checkbox */}
        <button
          onClick={() => onToggle(tarea.id_tarea)}
          className={`mt-0.5 flex-shrink-0 transition-colors ${
            tarea.completada ? 'text-green-500' : 'text-gray-300 hover:text-raloz-500'
          }`}
        >
          {tarea.completada
            ? <CheckSquare size={20} />
            : <Square size={20} />
          }
        </button>

        {/* Contenido */}
        <div className="flex-1 min-w-0">
          <p className={`text-sm font-medium leading-snug ${
            tarea.completada ? 'line-through text-gray-400' : 'text-gray-800'
          }`}>
            {tarea.titulo}
          </p>

          {/* Meta */}
          <div className="flex flex-wrap items-center gap-2 mt-1.5">
            {!tarea.completada && tarea.prioridad && tarea.prioridad !== 'MEDIA' && (() => {
              const cfg = PRIORIDAD_CONFIG[tarea.prioridad] || PRIORIDAD_CONFIG.MEDIA
              return (
                <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full ${cfg.color}`}>
                  <Flag size={9} /> {cfg.label}
                </span>
              )
            })()}
            {tarea.fecha_vencimiento && (
              <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full ${
                tarea.completada
                  ? 'bg-gray-100 text-gray-400'
                  : vencida
                    ? 'bg-red-100 text-red-600'
                    : 'bg-amber-50 text-amber-700'
              }`}>
                {vencida && !tarea.completada && <AlertCircle size={10} />}
                <Calendar size={10} />
                {new Date(tarea.fecha_vencimiento + 'T12:00:00').toLocaleDateString('es-CO', { day: 'numeric', month: 'short' })}
              </span>
            )}
            {badgeAsignado(tarea.asignada_a_nombre)}
            {tarea.completada && tarea.completada_por_nombre && (
              <span className="text-xs text-gray-400">✓ {tarea.completada_por_nombre}</span>
            )}
          </div>

          {/* Descripción expandible */}
          {tarea.descripcion && (
            <>
              <button
                onClick={() => setExpandida(v => !v)}
                className="mt-1.5 flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600"
              >
                {expandida ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                {expandida ? 'Ocultar' : 'Ver detalle'}
              </button>
              {expandida && (
                <p className="mt-1.5 text-xs text-gray-500 leading-relaxed bg-gray-50 rounded-lg p-2.5">
                  {tarea.descripcion}
                </p>
              )}
            </>
          )}
        </div>

        {/* Acciones admin */}
        {esAdmin && (
          <button
            onClick={() => onEliminar(tarea.id_tarea)}
            className="flex-shrink-0 text-gray-300 hover:text-red-400 transition-colors p-1"
            title="Eliminar tarea"
          >
            <Trash2 size={15} />
          </button>
        )}
      </div>
    </div>
  )
}
