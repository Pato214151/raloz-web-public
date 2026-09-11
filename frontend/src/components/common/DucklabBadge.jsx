// Sello "Hecho por Ducklab" — marca de agua fija abajo-izquierda.
// Sin dependencias externas (SVG y estilos inline).
export default function DucklabBadge() {
  return (
    <a
      href="https://mi-pagina-web-two-lilac.vercel.app"
      target="_blank"
      rel="noopener noreferrer"
      aria-label="Hecho por Ducklab"
      // En celular la barra inferior ocupa ese rincón: el sello quedaba
      // ENCIMA del botón "Inicio" (z-index 9999) y lo volvía intocable.
      className="hidden lg:inline-flex"
      style={{
        position: 'fixed',
        left: 14,
        bottom: 14,
        zIndex: 9999,
        alignItems: 'center',
        gap: 6,
        padding: '5px 10px 5px 5px',
        borderRadius: 999,
        background: 'rgba(0,0,0,0.55)',
        backdropFilter: 'blur(6px)',
        textDecoration: 'none',
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        transition: 'transform 0.2s ease, background 0.2s ease',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.transform = 'translateY(-2px)'
        e.currentTarget.style.background = 'rgba(0,0,0,0.75)'
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.transform = 'translateY(0)'
        e.currentTarget.style.background = 'rgba(0,0,0,0.55)'
      }}
    >
      <span
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: 20,
          height: 20,
          borderRadius: 6,
          background: 'linear-gradient(135deg, #ef4444, #b91c1c)',
        }}
      >
        <svg viewBox="0 0 24 24" width="12" height="12" fill="none" aria-hidden="true">
          <ellipse cx="12.6" cy="15.4" rx="7.6" ry="4.2" fill="#ffffff" />
          <circle cx="8.4" cy="9.4" r="4.5" fill="#ffffff" />
          <path d="M12 7.7 L18.6 8.4 c0.9 0.1 0.9 1.3 0 1.4 L12 10.7 Z" fill="#ffffff" />
          <circle cx="9.7" cy="8.6" r="1.05" fill="#8a1212" />
        </svg>
      </span>
      <span style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.02em', color: '#fff' }}>
        Ducklab
      </span>
    </a>
  )
}
