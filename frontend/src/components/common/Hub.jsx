import { useSearchParams } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'

/**
 * Hub: una sola pantalla-centro con pestañas contextuales.
 * Reúne funciones relacionadas SIN cambiar los componentes existentes:
 * cada pestaña monta su componente solo cuando está activa.
 *
 * tabs = [{ id, label, icon, element, roles? }]
 * La pestaña activa se guarda en la URL (?tab=id) → back del navegador y
 * enlaces directos funcionan.
 */
export default function Hub({ tabs }) {
  const { usuario } = useAuth()
  const [params, setParams] = useSearchParams()

  const visibles = tabs.filter(t => !t.roles || t.roles.includes(usuario?.rol))
  if (visibles.length === 0) return null

  const activo = visibles.find(t => t.id === params.get('tab')) || visibles[0]

  const irA = (id) => {
    const p = new URLSearchParams(params)
    p.set('tab', id)
    setParams(p, { replace: false })
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Barra de pestañas */}
      <div className="flex items-center gap-1 overflow-x-auto scrollbar-thin -mx-1 px-1
                      border-b border-gray-200">
        {visibles.map(t => {
          const on = t.id === activo.id
          return (
            <button
              key={t.id}
              onClick={() => irA(t.id)}
              className={`relative flex items-center gap-1.5 px-3.5 py-2.5 text-[13px] font-semibold
                          whitespace-nowrap transition-colors ${
                on ? 'text-slate-900' : 'text-gray-400 hover:text-gray-600'
              }`}
            >
              {t.icon ? <t.icon size={15} className={on ? 'text-amber-500' : ''} /> : null}
              {t.label}
              {on && <span className="absolute left-2 right-2 -bottom-px h-0.5 rounded-full bg-amber-400" />}
            </button>
          )
        })}
      </div>

      {/* Contenido de la pestaña activa */}
      <div key={activo.id}>{activo.element}</div>
    </div>
  )
}
