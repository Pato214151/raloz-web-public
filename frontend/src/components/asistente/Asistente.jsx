import { useState, useRef, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import api from '../../services/api'
import {
  Sparkles, Send, Plus, Copy, RotateCcw, Check, AlertTriangle,
  ShoppingCart, Users, BookOpen, BarChart3, Boxes, ClipboardList,
  Loader2, Clock, ChevronRight,
} from 'lucide-react'

// ── Branding RALOZ ──
const NAVY = '#071E49'
const YELLOW = '#FFD84D'
const STORAGE_KEY = 'raloz_asistente_chat'

// Chips del estado vacío (mandan un comando de arranque al asistente)
const ATAJOS = [
  { id: 'ventas',     label: 'Ventas',     icon: ShoppingCart, prompt: '¿Cuánto hemos vendido hoy?' },
  { id: 'inventario', label: 'Inventario', icon: Boxes,        prompt: '¿Qué prendas tienen stock bajo?' },
  { id: 'pedidos',    label: 'Pedidos',    icon: ClipboardList, prompt: '¿Qué pedidos están pendientes?' },
  { id: 'clientes',   label: 'Clientes',   icon: Users,        prompt: '¿Qué clientes tienen saldo pendiente?' },
  { id: 'caja',       label: 'Caja',       icon: BookOpen,     prompt: '¿Cómo va la caja hoy?' },
  { id: 'reportes',   label: 'Reportes',   icon: BarChart3,    prompt: 'Dame un resumen de ventas del mes' },
]

const SUGERENCIAS = [
  '¿Cuánto vendimos hoy?',
  'Stock de camisa talla 10',
  'Clientes con saldo pendiente',
  'Pedidos listos para entregar',
]

// Texto con **negritas** y saltos de línea (sin mostrar los asteriscos)
function renderRich(texto) {
  return String(texto).split('\n').map((linea, i) => (
    <div key={i} style={{ minHeight: linea ? undefined : 6 }}>
      {linea.split(/(\*\*[^*]+\*\*)/g).map((parte, j) =>
        parte.startsWith('**') && parte.endsWith('**')
          ? <strong key={j} className="font-semibold">{parte.slice(2, -2)}</strong>
          : parte
      )}
    </div>
  ))
}

// Movimiento legible para ajustar_stock
function movimientoTxt(a) {
  if (a.modo === 'sumar') return `+${a.cantidad}`
  if (a.modo === 'restar') return `−${a.cantidad}`
  return `= ${a.cantidad}`
}

// ── Tarjeta de confirmación (elegante, sin aspecto de log) ──
function TarjetaConfirmar({ accion, estado, onConfirmar, onCancelar }) {
  const enviando = estado === 'enviando'
  let titulo = 'Confirmar acción'
  let filas = []
  if (accion.tipo === 'ajustar_stock') {
    titulo = 'Actualizar inventario'
    filas = [
      ['Producto', accion.prenda],
      ['Colegio · Talla', `${accion.colegio} · ${accion.talla}`],
      ['Movimiento', movimientoTxt(accion)],
    ]
  } else if (accion.tipo === 'cambiar_estado_pedido') {
    titulo = 'Actualizar pedido'
    filas = [['Pedido', accion.factura], ['Nuevo estado', (accion.descripcion || '').split(': ').pop()]]
  } else if (accion.tipo === 'crear_tarea') {
    titulo = 'Crear recordatorio'
    filas = [['Recordar', accion.titulo], ...(accion.fecha ? [['Fecha', accion.fecha]] : [])]
  } else if (accion.tipo === 'fijar_costo') {
    titulo = 'Fijar costo'
    filas = [
      ['Producto', accion.prenda],
      ['Colegio', accion.colegio],
      ['Costo', '$' + Math.round(accion.costo || 0).toLocaleString('es-CO')],
    ]
  } else if (accion.tipo === 'revertir') {
    titulo = 'Deshacer cambio'
    filas = [['Se revertirá', (accion.descripcion || '').replace(/^Deshacer:\s*/, '')]]
  } else {
    filas = [['Acción', accion.descripcion]]
  }

  return (
    <div className="mt-2 rounded-2xl border border-[#E7EBF1] bg-white overflow-hidden"
      style={{ boxShadow: '0 1px 2px rgba(7,30,73,.04), 0 8px 24px rgba(7,30,73,.06)' }}>
      <div className="flex items-center gap-2 px-4 py-2.5 border-b border-[#E7EBF1]"
        style={{ background: '#FFFBEB' }}>
        <span className="w-1.5 h-1.5 rounded-full" style={{ background: YELLOW }} />
        <span className="text-[13px] font-semibold text-[#10213F]">{titulo}</span>
      </div>
      <div className="px-4 py-3 space-y-2">
        {filas.map(([k, v]) => (
          <div key={k} className="flex items-center justify-between gap-3 text-[13.5px]">
            <span className="text-[#718096]">{k}</span>
            <span className="font-semibold text-[#10213F] text-right truncate max-w-[62%]">{v || '—'}</span>
          </div>
        ))}
      </div>
      <div className="flex items-center gap-2 px-4 pb-3">
        {estado === 'hecha' ? (
          <span className="flex items-center gap-1.5 text-[13px] font-semibold text-emerald-600">
            <Check size={15} /> Hecho
          </span>
        ) : estado === 'cancelada' ? (
          <span className="text-[13px] text-[#718096]">Cancelada</span>
        ) : (
          <>
            <button onClick={onConfirmar} disabled={enviando}
              className="flex-1 py-2 rounded-xl text-white text-[13.5px] font-semibold transition-opacity disabled:opacity-60"
              style={{ background: NAVY }}>
              {enviando ? 'Confirmando…' : 'Confirmar'}
            </button>
            <button onClick={onCancelar} disabled={enviando}
              className="px-4 py-2 rounded-xl text-[13.5px] font-medium text-[#718096] border border-[#E7EBF1] hover:bg-[#F7F8FA]">
              Cancelar
            </button>
          </>
        )}
      </div>
    </div>
  )
}

// ── Burbuja de usuario ──
function BurbujaUsuario({ texto }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[85%] rounded-2xl rounded-br-md px-4 py-2.5 text-[14px] leading-relaxed text-white whitespace-pre-wrap"
        style={{ background: NAVY }}>
        {texto}
      </div>
    </div>
  )
}

// Quita emojis de estado al inicio del texto (para que no parezca log)
const limpiarPrefijo = (t) => String(t || '').replace(/^\s*[✅✔️☑️🎉👍]+\s*/u, '')

// ── Resultado de una acción (tarjeta de éxito limpia, sin aspecto de log) ──
function ResultadoRaloz({ texto }) {
  return (
    <div className="flex gap-3">
      <div className="w-8 h-8 rounded-xl flex items-center justify-center shrink-0 mt-0.5" style={{ background: NAVY }}>
        <Sparkles size={16} color={YELLOW} />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-[12px] font-semibold text-[#718096] mb-1">RALOZ</p>
        <div className="inline-flex items-center gap-2 rounded-xl border border-emerald-100 bg-emerald-50 px-3 py-2">
          <Check size={15} className="text-emerald-600 shrink-0" />
          <span className="text-[13.5px] text-[#10213F]">{limpiarPrefijo(texto)}</span>
        </div>
      </div>
    </div>
  )
}

const cop = (n) => '$' + Math.round(Number(n || 0)).toLocaleString('es-CO')

// ── Tarjetas de datos estructurados (inventario, métricas…) ──
function TarjetasDatos({ datos }) {
  const r = datos?.resultado || {}
  if (datos?.tipo === 'buscar_prenda' && r.encontrado && Array.isArray(r.prendas)) {
    return (
      <div className="mt-2 grid gap-2">
        {r.prendas.slice(0, 4).map((p, i) => {
          const tallas = Object.entries(p.stock_por_talla || {}).filter(([, q]) => q > 0)
          const total = p.stock_total ?? tallas.reduce((s, [, q]) => s + q, 0)
          return (
            <div key={i} className="rounded-2xl border border-[#E7EBF1] bg-white p-3.5" style={{ boxShadow: '0 1px 2px rgba(7,30,73,.04)' }}>
              <div className="flex items-start justify-between gap-3">
                <p className="text-[14px] font-semibold text-[#10213F]">{p.prenda}</p>
                <span className={`shrink-0 inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-full ${
                  total > 0 ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-600'
                }`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${total > 0 ? 'bg-emerald-500' : 'bg-red-500'}`} />
                  {total > 0 ? 'Disponible' : 'Agotado'}
                </span>
              </div>
              <p className="text-[13px] text-[#718096] mt-0.5">{total} unidad{total === 1 ? '' : 'es'} en total</p>
              {tallas.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mt-2">
                  {tallas.map(([t, q]) => (
                    <span key={t} className="text-[11.5px] font-medium text-[#10213F] bg-[#F7F8FA] border border-[#E7EBF1] rounded-lg px-2 py-0.5">
                      Talla {t} · <b>{q}</b>
                    </span>
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </div>
    )
  }
  if (datos?.tipo === 'movimientos' && r.encontrado && Array.isArray(r.movimientos)) {
    const signo = { SALIDA: '−', ENTRADA: '+', AJUSTE: '=' }
    const col = { SALIDA: 'text-red-600', ENTRADA: 'text-emerald-600', AJUSTE: 'text-amber-600' }
    return (
      <div className="mt-2 rounded-2xl border border-[#E7EBF1] bg-white p-3.5 max-w-md" style={{ boxShadow: '0 1px 2px rgba(7,30,73,.04)' }}>
        <p className="text-[14px] font-semibold text-[#10213F] mb-2">{r.prenda}{r.talla ? ` · Talla ${r.talla}` : ''} — Movimientos</p>
        <div className="space-y-2">
          {r.movimientos.map((m, i) => (
            <div key={i} className="flex items-center justify-between gap-2 text-[12.5px]">
              <div className="min-w-0">
                <span className={`font-semibold ${col[m.tipo] || 'text-[#10213F]'}`}>{signo[m.tipo] || ''}{m.cantidad}</span>
                <span className="text-[#718096]"> · T{m.talla}{m.stock_antes != null ? ` · ${m.stock_antes}→${m.stock_despues}` : ` → ${m.stock_despues}`}</span>
                {(m.referencia || m.motivo) && <span className="text-[#718096]"> · {m.referencia || m.motivo}</span>}
              </div>
              <span className="text-[11px] text-[#718096] shrink-0">
                {m.usuario}{m.fecha ? ' · ' + new Date(m.fecha + (m.fecha.endsWith('Z') ? '' : 'Z')).toLocaleDateString('es-CO', { day: '2-digit', month: 'short' }) : ''}
              </span>
            </div>
          ))}
        </div>
      </div>
    )
  }
  if (datos?.tipo === 'buscar_factura' && r.encontrado) {
    const badge = r.estado === 'PAGADA' ? 'bg-emerald-50 text-emerald-700'
      : r.estado === 'ANULADA' ? 'bg-gray-100 text-gray-600' : 'bg-amber-50 text-amber-700'
    return (
      <div className="mt-2 rounded-2xl border border-[#E7EBF1] bg-white p-3.5 max-w-md" style={{ boxShadow: '0 1px 2px rgba(7,30,73,.04)' }}>
        <div className="flex items-start justify-between gap-3">
          <p className="text-[14px] font-semibold text-[#10213F]">Factura {r.numero_factura}</p>
          <span className={`shrink-0 text-[11px] font-semibold px-2 py-0.5 rounded-full ${badge}`}>{r.estado}</span>
        </div>
        {(r.cliente || r.fecha) && <p className="text-[12.5px] text-[#718096] mt-0.5">{[r.cliente, r.fecha].filter(Boolean).join(' · ')}</p>}
        <div className="flex gap-4 mt-2 text-[13px]">
          <span className="text-[#10213F]">Total <b>{cop(r.total)}</b></span>
          {r.saldo_pendiente > 0
            ? <span className="text-red-600">Saldo <b>{cop(r.saldo_pendiente)}</b></span>
            : <span className="text-emerald-600 font-medium">Sin saldo</span>}
        </div>

        {/* Descuento de inventario (leído del kardex) + stock actual */}
        {Array.isArray(r.detalles) && r.detalles.length > 0 && (
          <div className="mt-3 pt-3 border-t border-[#E7EBF1]">
            {r.descontado_inventario !== undefined && (
              <span className={`inline-flex items-center gap-1 text-[11.5px] font-semibold px-2 py-0.5 rounded-full mb-2 ${
                r.descontado_inventario >= r.unidades_pedido ? 'bg-emerald-50 text-emerald-700'
                  : r.descontado_inventario > 0 ? 'bg-amber-50 text-amber-700' : 'bg-red-50 text-red-600'
              }`}>
                <span className={`w-1.5 h-1.5 rounded-full ${
                  r.descontado_inventario >= r.unidades_pedido ? 'bg-emerald-500'
                    : r.descontado_inventario > 0 ? 'bg-amber-500' : 'bg-red-500'}`} />
                {r.descontado_inventario >= r.unidades_pedido
                  ? 'Inventario descontado ✓'
                  : r.descontado_inventario > 0
                  ? `Descontó ${r.descontado_inventario}/${r.unidades_pedido} (resto a fabricación)`
                  : 'No descontó del inventario'}
              </span>
            )}
            <div className="space-y-1.5">
              {r.detalles.map((d, i) => (
                <div key={i} className="flex items-center justify-between gap-2 text-[12.5px]">
                  <span className="text-[#10213F] truncate">{d.prenda} · T{d.talla} · x{d.cantidad}</span>
                  <span className="shrink-0 text-[#718096]">
                    {d.stock_antes != null
                      ? <span className="text-emerald-600 font-medium">{d.stock_antes} → {d.stock_despues} (−{d.descontado})</span>
                      : d.descontado > 0
                      ? <span className="text-emerald-600 font-medium">salió {d.descontado} · quedan {d.stock_actual}</span>
                      : <span className="text-red-600 font-medium">no salió · quedan {d.stock_actual}</span>}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    )
  }
  if (datos?.tipo === 'pedidos_cliente' && r.encontrado && Array.isArray(r.pedidos)) {
    return (
      <div className="mt-2 grid gap-2 max-w-md">
        {r.pedidos.slice(0, 5).map((p, i) => (
          <div key={i} className="rounded-xl border border-[#E7EBF1] bg-white p-3">
            <div className="flex items-center justify-between gap-3">
              <span className="text-[13px] font-semibold text-[#10213F]">{p.referencia}</span>
              <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-[#F7F8FA] text-[#718096]">{p.estado}</span>
            </div>
            <div className="flex items-center justify-between mt-1 text-[12px]">
              <span className="text-[#718096]">{p.fecha ? new Date(p.fecha).toLocaleDateString('es-CO', { day: '2-digit', month: 'short' }) : ''}</span>
              <span className="font-semibold text-[#10213F]">{cop(p.total)}</span>
            </div>
          </div>
        ))}
      </div>
    )
  }
  if (datos?.tipo === 'top_productos' && r.encontrado && Array.isArray(r.productos)) {
    const medalla = ['🥇', '🥈', '🥉']
    const maxU = Math.max(...r.productos.map(p => p.unidades || 0), 1)
    return (
      <div className="mt-2 rounded-2xl border border-[#E7EBF1] bg-white p-3.5 max-w-lg" style={{ boxShadow: '0 1px 2px rgba(7,30,73,.04)' }}>
        <p className="text-[13px] font-semibold text-[#10213F] mb-2">Más vendidas <span className="text-[#718096] font-normal">· {r.periodo}</span></p>
        <div className="space-y-2">
          {r.productos.map((p, i) => (
            <div key={i}>
              <div className="flex items-center justify-between gap-2 text-[13px]">
                <span className="text-[#10213F] truncate">{medalla[i] || `${i + 1}.`} {p.prenda}</span>
                <span className="shrink-0 text-[#718096]"><b className="text-[#10213F]">{p.unidades}</b> uds · {cop(p.total)}</span>
              </div>
              <div className="h-1.5 rounded-full bg-[#F7F8FA] mt-1 overflow-hidden">
                <div className="h-full rounded-full" style={{ width: `${Math.round((p.unidades / maxU) * 100)}%`, background: NAVY }} />
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }
  if (datos?.tipo === 'ventas_periodo' && (r.total !== undefined)) {
    return (
      <div className="mt-2 grid grid-cols-2 gap-2 max-w-sm">
        <div className="rounded-2xl border border-[#E7EBF1] bg-white p-3.5">
          <p className="text-[11.5px] text-[#718096]">Total vendido</p>
          <p className="text-[18px] font-bold text-[#10213F] mt-0.5">{cop(r.total)}</p>
        </div>
        <div className="rounded-2xl border border-[#E7EBF1] bg-white p-3.5">
          <p className="text-[11.5px] text-[#718096]">Facturas</p>
          <p className="text-[18px] font-bold text-[#10213F] mt-0.5">{r.facturas ?? 0}</p>
        </div>
        <p className="col-span-2 text-[11px] text-[#718096] px-1">{r.desde} → {r.hasta}</p>
      </div>
    )
  }
  if (datos?.tipo === 'simular_precio' && r.encontrado) {
    const sube = (r.porcentaje || 0) >= 0
    return (
      <div className="mt-2 rounded-2xl border border-[#E7EBF1] bg-white p-3.5 max-w-lg" style={{ boxShadow: '0 1px 2px rgba(7,30,73,.04)' }}>
        <div className="flex items-center justify-between gap-3 mb-2">
          <p className="text-[13px] font-semibold text-[#10213F]">
            Simulación <span className="text-[#718096] font-normal">· precio {sube ? '+' : ''}{r.porcentaje}%</span>
          </p>
          <span className="text-[10.5px] font-semibold px-2 py-0.5 rounded-full bg-[#FFF7DB] text-[#8A6D00]">Escenario · no aplicado</span>
        </div>
        <div className="space-y-2">
          {(r.items || []).map((it, i) => {
            const mejora = it.margen_nuevo - it.margen_actual
            return (
              <div key={i} className="rounded-xl border border-[#E7EBF1] bg-[#F7F8FA] p-2.5">
                <div className="flex items-center justify-between gap-2 text-[12.5px]">
                  <span className="text-[#10213F] font-medium truncate">{it.prenda} <span className="text-[#718096]">· T{it.talla_grupo}</span></span>
                  <span className="shrink-0 text-[#718096]">
                    {cop(it.precio_actual)} <span className="text-[#10213F] font-semibold">→ {cop(it.precio_nuevo)}</span>
                  </span>
                </div>
                <div className="flex items-center justify-between gap-2 text-[11.5px] mt-1">
                  <span className="text-[#718096]">Margen {it.margen_actual}% <span className="text-[#10213F] font-semibold">→ {it.margen_nuevo}%</span>
                    <span className={`ml-1 font-semibold ${mejora >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>({mejora >= 0 ? '+' : ''}{mejora} pts)</span>
                  </span>
                  <span className="text-[#718096]">Util. {cop(it.utilidad_actual)} → <b className="text-[#10213F]">{cop(it.utilidad_nueva)}</b></span>
                </div>
              </div>
            )
          })}
        </div>
        {r.sin_costo > 0 && (
          <p className="text-[11px] text-amber-600 mt-2">⚠️ {r.sin_costo} referencia{r.sin_costo === 1 ? '' : 's'} sin costo cargado — no se pueden simular.</p>
        )}
        {r.nota && <p className="text-[11px] text-[#718096] mt-1.5">{r.nota}</p>}
      </div>
    )
  }
  if (datos?.tipo === 'bitacora' && r.encontrado && Array.isArray(r.acciones)) {
    return (
      <div className="mt-2 rounded-2xl border border-[#E7EBF1] bg-white p-3.5 max-w-lg" style={{ boxShadow: '0 1px 2px rgba(7,30,73,.04)' }}>
        <p className="text-[13px] font-semibold text-[#10213F] mb-2">Últimos cambios</p>
        <div className="space-y-2">
          {r.acciones.map((a, i) => (
            <div key={i} className="flex items-start justify-between gap-3 text-[12.5px]">
              <div className="min-w-0">
                <p className="text-[#10213F] truncate">{a.descripcion || a.tipo}</p>
                <p className="text-[11px] text-[#718096]">
                  #{a.id_accion} · {a.usuario || '—'}
                  {a.fecha ? ' · ' + new Date(a.fecha + (a.fecha.endsWith('Z') ? '' : 'Z')).toLocaleDateString('es-CO', { day: '2-digit', month: 'short' }) : ''}
                </p>
              </div>
              <div className="flex items-center gap-1.5 shrink-0">
                {a.resultado === 'REVERTIDA'
                  ? <span className="text-[10.5px] font-semibold px-2 py-0.5 rounded-full bg-[#EDEFF4] text-[#6A778F]">revertida</span>
                  : a.verificado
                  ? <span className="text-[10.5px] font-semibold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700">✓ verificado</span>
                  : <span className="text-[10.5px] font-semibold px-2 py-0.5 rounded-full bg-amber-50 text-amber-700">sin verificar</span>}
                {a.reversible && a.resultado !== 'REVERTIDA' && (
                  <span className="text-[10.5px] font-medium px-2 py-0.5 rounded-full border border-[#E7EBF1] text-[#718096]">reversible</span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }
  return null
}

// ── Mensaje de RALOZ ──
function MensajeRaloz({ m, onConfirmar, onCancelar, onCopiar, onRegenerar, puedeRegenerar }) {
  return (
    <div className="flex gap-3">
      <div className="w-8 h-8 rounded-xl flex items-center justify-center shrink-0 mt-0.5" style={{ background: NAVY }}>
        <Sparkles size={16} color={YELLOW} />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-[12px] font-semibold text-[#718096] mb-1">RALOZ</p>
        <div className={`text-[14px] leading-relaxed ${m.error ? 'text-red-600' : 'text-[#10213F]'}`}>
          {m.error
            ? <div className="flex items-start gap-2"><AlertTriangle size={15} className="mt-0.5 shrink-0" />{m.texto}</div>
            : renderRich(m.texto)}
        </div>

        {m.datos && <TarjetasDatos datos={m.datos} />}

        {m.accion && (
          <TarjetaConfirmar accion={m.accion} estado={m.accionEstado}
            onConfirmar={onConfirmar} onCancelar={onCancelar} />
        )}

        {/* Acciones de la respuesta */}
        {!m.error && !m.accion && (
          <div className="flex items-center gap-1 mt-1.5 opacity-0 hover:opacity-100 focus-within:opacity-100 transition-opacity">
            <button onClick={onCopiar} title="Copiar respuesta"
              className="p-1.5 rounded-lg text-[#718096] hover:bg-[#F7F8FA]"><Copy size={13} /></button>
            {puedeRegenerar && (
              <button onClick={onRegenerar} title="Regenerar"
                className="p-1.5 rounded-lg text-[#718096] hover:bg-[#F7F8FA]"><RotateCcw size={13} /></button>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default function Asistente() {
  const navigate = useNavigate()
  const { usuario } = useAuth()
  const [mensajes, setMensajes] = useState(() => {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]') } catch { return [] }
  })
  const [input, setInput] = useState('')
  const [cargando, setCargando] = useState(false)
  const finRef = useRef(null)
  const taRef = useRef(null)

  useEffect(() => { finRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [mensajes, cargando])
  useEffect(() => {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(mensajes.slice(-40))) } catch { /* lleno */ }
  }, [mensajes])

  const nuevaConversacion = () => {
    setMensajes([])
    try { localStorage.removeItem(STORAGE_KEY) } catch { /* ignore */ }
    taRef.current?.focus()
  }

  const llamar = useCallback(async (pregunta) => {
    setCargando(true)
    try {
      const res = await api.post('/asistente/preguntar', { pregunta }, { timeout: 130000 })
      setMensajes((m) => [...m, { rol: 'bot', texto: res.data.respuesta, accion: res.data.accion || null, datos: res.data.datos || null }])
    } catch (err) {
      const data = err?.response?.data || {}
      let msg = data.code === 'sin_config'
        ? 'El asistente aún no está activo: falta configurar la llave GEMINI_API_KEY en el servidor (Render → Environment).'
        : data.error || 'No pude responder ahora. Intenta de nuevo en un momento.'
      if (data.detalle && data.code !== 'ocupado') msg += `\n\nDetalle técnico: ${data.detalle}`
      setMensajes((m) => [...m, { rol: 'bot', texto: msg, error: true }])
    } finally { setCargando(false) }
  }, [])

  const preguntar = (texto) => {
    const pregunta = (texto ?? input).trim()
    if (!pregunta || cargando) return
    setInput('')
    setMensajes((m) => [...m, { rol: 'user', texto: pregunta }])
    llamar(pregunta)
  }

  const regenerar = () => {
    if (cargando) return
    const ultUser = [...mensajes].reverse().find(m => m.rol === 'user')
    if (ultUser) llamar(ultUser.texto)
  }

  const confirmarAccion = async (idx) => {
    const accion = mensajes[idx]?.accion
    if (!accion) return
    setMensajes((m) => m.map((x, i) => (i === idx ? { ...x, accionEstado: 'enviando' } : x)))
    try {
      const res = await api.post('/asistente/ejecutar', accion, { timeout: 60000 })
      setMensajes((m) => {
        const upd = m.map((x, i) => (i === idx ? { ...x, accionEstado: 'hecha' } : x))
        return [...upd, { rol: 'bot', texto: res.data.mensaje || 'Listo, cambio aplicado.', resultado: true }]
      })
    } catch (err) {
      const msg = err?.response?.data?.error || 'No pude ejecutar la acción.'
      setMensajes((m) => {
        const upd = m.map((x, i) => (i === idx ? { ...x, accionEstado: 'error' } : x))
        return [...upd, { rol: 'bot', texto: msg, error: true }]
      })
    }
  }

  const cancelarAccion = (idx) =>
    setMensajes((m) => m.map((x, i) => (i === idx ? { ...x, accionEstado: 'cancelada' } : x)))

  const copiar = (t) => { try { navigator.clipboard?.writeText(t) } catch { /* noop */ } }

  const hoy = new Date().toLocaleDateString('es-CO', { day: 'numeric', month: 'long', year: 'numeric' })
  const rolLabel = { administrador: 'Administrador', vendedor: 'Vendedor', cajero: 'Cajero' }[usuario?.rol] || usuario?.rol
  const ultimoBotIdx = mensajes.map(m => m.rol).lastIndexOf('bot')
  const actividad = mensajes.filter(m => m.resultado).slice(-4).reverse()
  const vacio = mensajes.length === 0

  return (
    <div className="grid lg:grid-cols-[minmax(0,1fr)_310px] gap-5 h-[calc(100dvh-168px)] lg:h-[calc(100vh-96px)]">

      {/* ══ Columna principal ══ */}
      <div className="flex flex-col min-h-0 min-w-0 bg-white rounded-2xl border border-[#E7EBF1]"
        style={{ boxShadow: '0 1px 2px rgba(7,30,73,.04)' }}>

        {/* Header */}
        <div className="flex items-center justify-between gap-3 px-5 py-4 border-b border-[#E7EBF1]">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0" style={{ background: NAVY }}>
              <Sparkles size={20} color={YELLOW} />
            </div>
            <div className="min-w-0">
              <h1 className="text-[16px] font-bold text-[#10213F] leading-tight">Asistente RALOZ</h1>
              <p className="text-[12.5px] text-[#718096] leading-tight">Tu copiloto operativo</p>
            </div>
          </div>
          <button onClick={nuevaConversacion}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-[13px] font-medium text-[#10213F] border border-[#E7EBF1] hover:bg-[#F7F8FA] transition-colors">
            <Plus size={15} /> <span className="hidden sm:inline">Nueva conversación</span>
          </button>
        </div>

        {/* Conversación */}
        <div className="flex-1 overflow-y-auto px-5 py-5">
          {vacio ? (
            <div className="h-full flex flex-col items-center justify-center text-center max-w-md mx-auto">
              <div className="w-14 h-14 rounded-2xl flex items-center justify-center mb-4" style={{ background: NAVY }}>
                <Sparkles size={26} color={YELLOW} />
              </div>
              <h2 className="text-[19px] font-bold text-[#10213F]">¿En qué puedo ayudarte?</h2>
              <p className="text-[13.5px] text-[#718096] mt-1 mb-6">
                Pregúntame por ventas, inventario, pedidos, clientes o caja.
              </p>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 w-full">
                {ATAJOS.map(a => (
                  <button key={a.id} onClick={() => preguntar(a.prompt)}
                    className="flex flex-col items-center gap-2 px-3 py-4 rounded-xl border border-[#E7EBF1] bg-white hover:border-[#071E49]/25 hover:bg-[#F7F8FA] transition-all">
                    <a.icon size={20} className="text-[#071E49]" />
                    <span className="text-[13px] font-medium text-[#10213F]">{a.label}</span>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="flex flex-col gap-5 max-w-3xl mx-auto">
              {mensajes.map((m, i) => (
                m.rol === 'user'
                  ? <BurbujaUsuario key={i} texto={m.texto} />
                  : m.resultado
                  ? <ResultadoRaloz key={i} texto={m.texto} />
                  : <MensajeRaloz key={i} m={m}
                      onConfirmar={() => confirmarAccion(i)}
                      onCancelar={() => cancelarAccion(i)}
                      onCopiar={() => copiar(m.texto)}
                      onRegenerar={regenerar}
                      puedeRegenerar={i === ultimoBotIdx && !m.resultado} />
              ))}
              {cargando && (
                <div className="flex gap-3 items-center">
                  <div className="w-8 h-8 rounded-xl flex items-center justify-center shrink-0" style={{ background: NAVY }}>
                    <Sparkles size={16} color={YELLOW} />
                  </div>
                  <span className="flex items-center gap-2 text-[13.5px] text-[#718096]">
                    <Loader2 size={14} className="animate-spin" /> RALOZ está analizando…
                  </span>
                </div>
              )}
              <div ref={finRef} />
            </div>
          )}
        </div>

        {/* Input fijo */}
        <div className="border-t border-[#E7EBF1] p-3">
          {/* Atajos siempre a mano (para no tener que subir) */}
          <div className="flex gap-1.5 overflow-x-auto scrollbar-thin pb-2 -mx-1 px-1">
            {ATAJOS.map(a => (
              <button key={a.id} onClick={() => preguntar(a.prompt)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-[#E7EBF1] text-[12.5px] font-medium text-[#10213F] hover:bg-[#F7F8FA] whitespace-nowrap shrink-0 transition-colors">
                <a.icon size={13} className="text-[#071E49]" /> {a.label}
              </button>
            ))}
          </div>
          <form onSubmit={(e) => { e.preventDefault(); preguntar() }}
            className="flex items-end gap-2 rounded-2xl border border-[#E7EBF1] bg-[#F7F8FA] px-3 py-2 focus-within:border-[#071E49]/30 transition-colors">
            <textarea
              ref={taRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); preguntar() } }}
              rows={1}
              placeholder="Pregunta al asistente…"
              className="flex-1 bg-transparent resize-none outline-none text-[14px] text-[#10213F] placeholder-[#718096] py-1.5 max-h-32"
            />
            <button type="submit" disabled={cargando || !input.trim()}
              title="Enviar"
              className="w-10 h-10 rounded-xl flex items-center justify-center text-white shrink-0 transition-opacity disabled:opacity-40"
              style={{ background: NAVY }}>
              {cargando ? <Loader2 size={17} className="animate-spin" /> : <Send size={17} />}
            </button>
          </form>
          <p className="text-[11px] text-[#718096] mt-1.5 px-1">Enter para enviar · Shift + Enter para nueva línea</p>
        </div>
      </div>

      {/* ══ Panel derecho ══ */}
      <aside className="hidden lg:flex flex-col gap-4 overflow-y-auto pr-0.5">
        {/* Acciones rápidas */}
        <Panel titulo="Acciones rápidas" icon={Sparkles}>
          <div className="grid grid-cols-1 gap-1.5">
            <AccionRail icon={Boxes}         label="Consultar stock"   onClick={() => preguntar('¿Qué prendas tienen stock bajo?')} />
            <AccionRail icon={ShoppingCart}  label="Nueva venta"       onClick={() => navigate('/ventas?tab=nueva')} />
            <AccionRail icon={Users}         label="Buscar cliente"    onClick={() => navigate('/clientes')} />
            <AccionRail icon={BarChart3}     label="Ver ventas hoy"    onClick={() => preguntar('¿Cuánto hemos vendido hoy?')} />
            <AccionRail icon={ClipboardList} label="Pedidos pendientes" onClick={() => preguntar('¿Qué pedidos están pendientes?')} />
            <AccionRail icon={BookOpen}      label="Resumen de caja"   onClick={() => preguntar('¿Cómo va la caja hoy?')} />
          </div>
        </Panel>

        {/* Actividad reciente */}
        {actividad.length > 0 && (
          <Panel titulo="Actividad reciente" icon={Clock}>
            <div className="flex flex-col gap-2.5">
              {actividad.map((a, i) => (
                <div key={i} className="flex items-start gap-2">
                  <Check size={14} className="text-emerald-500 mt-0.5 shrink-0" />
                  <p className="text-[12.5px] text-[#10213F] leading-snug">{a.texto}</p>
                </div>
              ))}
            </div>
          </Panel>
        )}

        {/* Contexto del sistema */}
        <Panel titulo="Contexto del sistema" icon={ClipboardList}>
          <div className="space-y-2.5 text-[13px]">
            <FilaCtx k="Fecha" v={hoy} />
            <FilaCtx k="Usuario" v={usuario?.usuario} />
            <FilaCtx k="Rol" v={rolLabel} />
          </div>
          <button onClick={() => navigate('/finanzas')}
            className="mt-3 flex items-center gap-1 text-[12.5px] font-medium text-[#071E49] hover:opacity-80">
            Ver métricas del día <ChevronRight size={13} />
          </button>
        </Panel>

        {/* Sugerencias */}
        <Panel titulo="Sugerencias" icon={Sparkles}>
          <div className="flex flex-col gap-1.5">
            {SUGERENCIAS.map(s => (
              <button key={s} onClick={() => preguntar(s)}
                className="text-left text-[12.5px] text-[#10213F] px-3 py-2 rounded-lg border border-[#E7EBF1] hover:bg-[#F7F8FA] transition-colors">
                {s}
              </button>
            ))}
          </div>
        </Panel>
      </aside>
    </div>
  )
}

function Panel({ titulo, icon: Icon, children }) {
  return (
    <div className="bg-white rounded-2xl border border-[#E7EBF1] p-4" style={{ boxShadow: '0 1px 2px rgba(7,30,73,.04)' }}>
      <div className="flex items-center gap-2 mb-3">
        <Icon size={15} className="text-[#071E49]" />
        <h3 className="text-[13px] font-bold text-[#10213F]">{titulo}</h3>
      </div>
      {children}
    </div>
  )
}

function AccionRail({ icon: Icon, label, onClick }) {
  return (
    <button onClick={onClick}
      className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] font-medium text-[#10213F] hover:bg-[#F7F8FA] transition-colors text-left">
      <Icon size={15} className="text-[#718096] shrink-0" /> {label}
    </button>
  )
}

function FilaCtx({ k, v }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-[#718096]">{k}</span>
      <span className="font-semibold text-[#10213F] truncate max-w-[60%] text-right">{v || '—'}</span>
    </div>
  )
}
