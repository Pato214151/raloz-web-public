#!/usr/bin/env python3
"""
Genera la guía de instalación PDF para RALOZ Web
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.units import inch, cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether
)

# Colores RALOZ
AZUL = HexColor('#1e2ff5')
AZUL_OSCURO = HexColor('#141557')
AZUL_CLARO = HexColor('#dce4ff')
GRIS = HexColor('#6b7280')
VERDE = HexColor('#22c55e')
ROJO = HexColor('#ef4444')
FONDO_CODE = HexColor('#f3f4f6')

styles = getSampleStyleSheet()

# Estilos personalizados
styles.add(ParagraphStyle(
    'TituloRALOZ', parent=styles['Title'],
    fontSize=28, textColor=AZUL, spaceAfter=6
))
styles.add(ParagraphStyle(
    'Subtitulo', parent=styles['Normal'],
    fontSize=14, textColor=GRIS, spaceAfter=20
))
styles.add(ParagraphStyle(
    'PasoTitulo', parent=styles['Heading1'],
    fontSize=18, textColor=AZUL_OSCURO, spaceBefore=20, spaceAfter=10,
    borderWidth=0, borderColor=AZUL, borderPadding=5,
))
styles.add(ParagraphStyle(
    'SubPaso', parent=styles['Heading2'],
    fontSize=14, textColor=AZUL, spaceBefore=14, spaceAfter=8
))
styles.add(ParagraphStyle(
    'Texto', parent=styles['Normal'],
    fontSize=11, leading=16, spaceAfter=8, textColor=HexColor('#374151')
))
styles.add(ParagraphStyle(
    'Codigo', parent=styles['Normal'],
    fontName='Courier', fontSize=10, leading=14,
    backColor=FONDO_CODE, borderWidth=1, borderColor=HexColor('#e5e7eb'),
    borderPadding=8, spaceAfter=10, spaceBefore=6, leftIndent=10
))
styles.add(ParagraphStyle(
    'Alerta', parent=styles['Normal'],
    fontSize=11, leading=16, backColor=HexColor('#fef3c7'),
    borderWidth=1, borderColor=HexColor('#f59e0b'),
    borderPadding=10, spaceAfter=12, spaceBefore=6
))
styles.add(ParagraphStyle(
    'Exito', parent=styles['Normal'],
    fontSize=11, leading=16, backColor=HexColor('#dcfce7'),
    borderWidth=1, borderColor=VERDE,
    borderPadding=10, spaceAfter=12, spaceBefore=6
))
styles.add(ParagraphStyle(
    'Nota', parent=styles['Normal'],
    fontSize=10, leading=14, textColor=GRIS, spaceAfter=6, leftIndent=20
))
styles.add(ParagraphStyle(
    'NumPaso', parent=styles['Normal'],
    fontSize=24, textColor=AZUL, fontName='Helvetica-Bold'
))


def crear_paso(numero, titulo):
    """Crear encabezado de paso numerado"""
    data = [[
        Paragraph(f'{numero}', styles['NumPaso']),
        Paragraph(titulo, styles['PasoTitulo'])
    ]]
    t = Table(data, colWidths=[0.6*inch, 5.5*inch])
    t.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (0,0), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    return t


def build_pdf():
    output_path = '/sessions/gallant-ecstatic-lamport/mnt/raloz_facturacion/web/GUIA_INSTALACION_RALOZ_WEB.pdf'

    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch,
        leftMargin=0.85*inch,
        rightMargin=0.85*inch,
    )

    story = []

    # ═══════════════════════════════════════
    # PORTADA
    # ═══════════════════════════════════════
    story.append(Spacer(1, 1.5*inch))
    story.append(Paragraph('RALOZ COL SAS', styles['TituloRALOZ']))
    story.append(Paragraph('Guia de Instalacion — Version Web', styles['Subtitulo']))
    story.append(Spacer(1, 0.3*inch))
    story.append(HRFlowable(width="100%", thickness=2, color=AZUL))
    story.append(Spacer(1, 0.3*inch))

    story.append(Paragraph(
        'Esta guia te lleva paso a paso desde cero hasta tener RALOZ '
        'funcionando en tu navegador. Solo necesitas Python instalado.',
        styles['Texto']
    ))
    story.append(Spacer(1, 0.2*inch))

    # Resumen de lo que se va a hacer
    resumen_data = [
        ['Que vas a instalar', 'Para que sirve'],
        ['Node.js v20', 'Ejecutar el frontend React'],
        ['PostgreSQL (via Supabase)', 'Base de datos en la nube'],
        ['Dependencias Python (pip)', 'Backend Flask + librerias'],
        ['Dependencias Node (npm)', 'Frontend React + Tailwind'],
        ['Google OAuth (opcional)', 'Login con Gmail'],
    ]
    t = Table(resumen_data, colWidths=[2.5*inch, 3.5*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), AZUL),
        ('TEXTCOLOR', (0,0), (-1,0), white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('GRID', (0,0), (-1,-1), 0.5, HexColor('#e5e7eb')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [white, AZUL_CLARO]),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph(
        '<b>Tiempo estimado:</b> 20-30 minutos',
        styles['Texto']
    ))

    story.append(PageBreak())

    # ═══════════════════════════════════════
    # PASO 1: Instalar Node.js
    # ═══════════════════════════════════════
    story.append(crear_paso('1', 'Instalar Node.js'))

    story.append(Paragraph(
        'Node.js es necesario para ejecutar el frontend React. '
        'Si ya lo tienes instalado, salta al paso 2.',
        styles['Texto']
    ))

    story.append(Paragraph('1.1  Descargar Node.js', styles['SubPaso']))
    story.append(Paragraph(
        'Abre tu navegador y ve a:',
        styles['Texto']
    ))
    story.append(Paragraph(
        'https://nodejs.org/es',
        styles['Codigo']
    ))
    story.append(Paragraph(
        'Descarga la version <b>LTS</b> (la que dice "Recomendado"). '
        'Al momento de esta guia es la v20.',
        styles['Texto']
    ))

    story.append(Paragraph('1.2  Instalar', styles['SubPaso']))
    story.append(Paragraph(
        'Ejecuta el instalador .msi que descargaste. '
        'Dale "Next" a todo, no cambies nada. Deja marcada la opcion '
        '"Add to PATH" (viene marcada por defecto).',
        styles['Texto']
    ))

    story.append(Paragraph('1.3  Verificar', styles['SubPaso']))
    story.append(Paragraph(
        'Abre una nueva ventana de CMD o PowerShell y escribe:',
        styles['Texto']
    ))
    story.append(Paragraph('node --version', styles['Codigo']))
    story.append(Paragraph('npm --version', styles['Codigo']))
    story.append(Paragraph(
        'Si ves numeros como v20.x.x y 10.x.x, esta bien instalado.',
        styles['Exito']
    ))

    # ═══════════════════════════════════════
    # PASO 2: Crear Base de Datos en Supabase
    # ═══════════════════════════════════════
    story.append(crear_paso('2', 'Crear Base de Datos en Supabase (GRATIS)'))

    story.append(Paragraph(
        'Supabase te da PostgreSQL gratis en la nube. Esto reemplaza el SQLite local.',
        styles['Texto']
    ))

    story.append(Paragraph('2.1  Crear cuenta', styles['SubPaso']))
    story.append(Paragraph('https://supabase.com', styles['Codigo']))
    story.append(Paragraph(
        'Haz clic en "Start your project". Puedes registrarte con tu cuenta de GitHub o Gmail.',
        styles['Texto']
    ))

    story.append(Paragraph('2.2  Crear proyecto', styles['SubPaso']))
    story.append(Paragraph(
        'Una vez dentro del dashboard de Supabase:<br/>'
        '- Haz clic en <b>"New Project"</b><br/>'
        '- Nombre: <b>raloz</b><br/>'
        '- Password: <b>Inventate una clave segura y GUARDALA</b><br/>'
        '- Region: <b>South America (Sao Paulo)</b> (la mas cercana a Colombia)<br/>'
        '- Plan: <b>Free</b> (gratis, hasta 500MB)',
        styles['Texto']
    ))

    story.append(Paragraph('2.3  Copiar la URL de conexion', styles['SubPaso']))
    story.append(Paragraph(
        'Cuando el proyecto termine de crearse (1-2 minutos):<br/>'
        '- Ve a <b>Settings</b> (icono de engranaje) en la barra lateral izquierda<br/>'
        '- Clic en <b>"Database"</b><br/>'
        '- Busca la seccion <b>"Connection string"</b><br/>'
        '- Selecciona la pestana <b>"URI"</b><br/>'
        '- Copia esa URL. Se ve asi:',
        styles['Texto']
    ))
    story.append(Paragraph(
        'postgresql://postgres.[TU-REF]:[TU-PASSWORD]@aws-0-sa-east-1.pooler.supabase.com:6543/postgres',
        styles['Codigo']
    ))
    story.append(Paragraph(
        'IMPORTANTE: Reemplaza [TU-PASSWORD] con la clave que pusiste al crear el proyecto. '
        'Guarda esta URL completa, la necesitas en el paso 4.',
        styles['Alerta']
    ))

    story.append(PageBreak())

    # ═══════════════════════════════════════
    # PASO 3: Instalar dependencias del Backend
    # ═══════════════════════════════════════
    story.append(crear_paso('3', 'Instalar dependencias del Backend (Python)'))

    story.append(Paragraph('3.1  Abrir terminal en la carpeta del proyecto', styles['SubPaso']))
    story.append(Paragraph(
        'Abre CMD o PowerShell. Navega hasta la carpeta del proyecto web:',
        styles['Texto']
    ))
    story.append(Paragraph(
        'cd C:\\ruta\\a\\tu\\raloz_facturacion\\web\\backend',
        styles['Codigo']
    ))
    story.append(Paragraph(
        'Reemplaza "C:\\ruta\\a\\tu\\" con la ruta real donde tienes tu carpeta raloz_facturacion.',
        styles['Nota']
    ))

    story.append(Paragraph('3.2  Instalar paquetes Python', styles['SubPaso']))
    story.append(Paragraph('pip install -r requirements.txt', styles['Codigo']))
    story.append(Paragraph(
        'Esto instala Flask, SQLAlchemy, bcrypt, JWT, Google Auth, y todas las dependencias. '
        'Puede tomar 1-3 minutos.',
        styles['Texto']
    ))
    story.append(Paragraph(
        'Si te sale error con psycopg2-binary, intenta: pip install psycopg2-binary '
        'por separado. Si sigue fallando, instala las Build Tools de Visual Studio.',
        styles['Alerta']
    ))

    # ═══════════════════════════════════════
    # PASO 4: Configurar el archivo .env
    # ═══════════════════════════════════════
    story.append(crear_paso('4', 'Configurar variables de entorno (.env)'))

    story.append(Paragraph(
        'Dentro de la carpeta <b>web/backend/</b>, crea un archivo llamado <b>.env</b> '
        '(punto env, sin extension). Puedes copiar el .env.example:',
        styles['Texto']
    ))
    story.append(Paragraph(
        'copy .env.example .env',
        styles['Codigo']
    ))
    story.append(Paragraph(
        'Ahora abre el archivo .env con el Bloc de notas o VS Code y llena estos valores:',
        styles['Texto']
    ))

    env_data = [
        ['Variable', 'Que poner'],
        ['FLASK_ENV', 'development'],
        ['SECRET_KEY', 'Inventate una clave larga, ejemplo: miclaveraloz2024segura'],
        ['JWT_SECRET_KEY', 'Otra clave diferente, ejemplo: jwtraloz2024secreto'],
        ['DATABASE_URL', 'La URL de Supabase que copiaste en el paso 2.3'],
        ['CORS_ORIGINS', 'http://localhost:5173'],
        ['GOOGLE_CLIENT_ID', 'Dejalo vacio por ahora (paso 7)'],
        ['GOOGLE_CLIENT_SECRET', 'Dejalo vacio por ahora (paso 7)'],
    ]
    t = Table(env_data, colWidths=[1.8*inch, 4.2*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), AZUL_OSCURO),
        ('TEXTCOLOR', (0,0), (-1,0), white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('GRID', (0,0), (-1,-1), 0.5, HexColor('#e5e7eb')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [white, AZUL_CLARO]),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(t)

    story.append(PageBreak())

    # ═══════════════════════════════════════
    # PASO 5: Crear tablas e insertar datos
    # ═══════════════════════════════════════
    story.append(crear_paso('5', 'Crear tablas y datos iniciales'))

    story.append(Paragraph(
        'Desde la carpeta web/backend/, ejecuta estos dos comandos:',
        styles['Texto']
    ))
    story.append(Paragraph('flask init-db', styles['Codigo']))
    story.append(Paragraph(
        'Esto crea todas las tablas en tu PostgreSQL de Supabase.',
        styles['Nota']
    ))
    story.append(Paragraph('flask seed', styles['Codigo']))
    story.append(Paragraph(
        'Esto inserta los datos iniciales: metodos de pago (EFECTIVO, NEQUI, etc.), '
        'serie de facturacion, y un usuario admin con password admin123.',
        styles['Nota']
    ))

    story.append(Paragraph(
        'Si ya tienes datos en tu SQLite y quieres migrarlos:',
        styles['Texto']
    ))
    story.append(Paragraph(
        'python scripts/migrar_sqlite_a_postgres.py --sqlite ../../data/usuarios_central.db',
        styles['Codigo']
    ))
    story.append(Paragraph(
        'Este script copia todos tus colegios, productos, facturas, pagos, clientes y stock '
        'de la base SQLite a la nueva PostgreSQL.',
        styles['Exito']
    ))

    # ═══════════════════════════════════════
    # PASO 6: Instalar y levantar el Frontend
    # ═══════════════════════════════════════
    story.append(crear_paso('6', 'Instalar y levantar el Frontend (React)'))

    story.append(Paragraph('6.1  Instalar dependencias', styles['SubPaso']))
    story.append(Paragraph(
        'Abre OTRA ventana de CMD/PowerShell (deja la del backend abierta). '
        'Navega a la carpeta del frontend:',
        styles['Texto']
    ))
    story.append(Paragraph(
        'cd C:\\ruta\\a\\tu\\raloz_facturacion\\web\\frontend',
        styles['Codigo']
    ))
    story.append(Paragraph('npm install', styles['Codigo']))
    story.append(Paragraph(
        'Esto descarga React, Tailwind, Recharts y todas las librerias. '
        'Puede tomar 2-5 minutos la primera vez.',
        styles['Texto']
    ))

    story.append(Paragraph('6.2  Levantar el frontend', styles['SubPaso']))
    story.append(Paragraph('npm run dev', styles['Codigo']))
    story.append(Paragraph(
        'Vas a ver un mensaje que dice: "VITE v6.x.x ready in XXms" y una URL local.',
        styles['Texto']
    ))

    story.append(PageBreak())

    # ═══════════════════════════════════════
    # PASO 7 (Ahora unido): Levantar Backend
    # ═══════════════════════════════════════
    story.append(crear_paso('7', 'Levantar el Backend'))

    story.append(Paragraph(
        'Vuelve a la PRIMERA ventana de CMD (la del backend) y ejecuta:',
        styles['Texto']
    ))
    story.append(Paragraph(
        'cd C:\\ruta\\a\\tu\\raloz_facturacion\\web\\backend<br/>'
        'python run.py',
        styles['Codigo']
    ))
    story.append(Paragraph(
        'Deberias ver: "Running on http://0.0.0.0:5000". El backend esta corriendo.',
        styles['Exito']
    ))

    # ═══════════════════════════════════════
    # PASO 8: Abrir RALOZ Web
    # ═══════════════════════════════════════
    story.append(crear_paso('8', 'Abrir RALOZ en el navegador'))

    story.append(Paragraph(
        'Abre tu navegador (Chrome recomendado) y ve a:',
        styles['Texto']
    ))
    story.append(Paragraph(
        'http://localhost:5173',
        styles['Codigo']
    ))
    story.append(Paragraph(
        'Vas a ver la pantalla de login de RALOZ. Ingresa con:<br/><br/>'
        '<b>Usuario:</b> admin<br/>'
        '<b>Password:</b> admin123<br/><br/>'
        'IMPORTANTE: Cambia la contrasena inmediatamente despues del primer login '
        'yendo al boton de tu perfil.',
        styles['Exito']
    ))

    story.append(PageBreak())

    # ═══════════════════════════════════════
    # PASO 9: Google OAuth (Opcional)
    # ═══════════════════════════════════════
    story.append(crear_paso('9', 'Configurar Login con Google (Opcional)'))

    story.append(Paragraph(
        'Si quieres que los usuarios puedan iniciar sesion con su cuenta de Gmail:',
        styles['Texto']
    ))

    story.append(Paragraph('9.1  Ir a Google Cloud Console', styles['SubPaso']))
    story.append(Paragraph('https://console.cloud.google.com', styles['Codigo']))
    story.append(Paragraph(
        '- Crea un proyecto nuevo (o usa uno existente)<br/>'
        '- Ve a <b>APIs &amp; Services</b> &gt; <b>Credentials</b><br/>'
        '- Clic en <b>"Create Credentials"</b> &gt; <b>"OAuth client ID"</b><br/>'
        '- Application type: <b>Web application</b><br/>'
        '- Nombre: <b>RALOZ Web</b><br/>'
        '- Authorized redirect URIs: agrega <b>http://localhost:5173</b><br/>'
        '- Clic en <b>Create</b>',
        styles['Texto']
    ))

    story.append(Paragraph('9.2  Copiar las credenciales', styles['SubPaso']))
    story.append(Paragraph(
        'Google te dara un <b>Client ID</b> y un <b>Client Secret</b>. '
        'Copia ambos valores.',
        styles['Texto']
    ))

    story.append(Paragraph('9.3  Agregar al .env', styles['SubPaso']))
    story.append(Paragraph(
        'Abre el archivo <b>web/backend/.env</b> y actualiza:',
        styles['Texto']
    ))
    story.append(Paragraph(
        'GOOGLE_CLIENT_ID=tu-client-id-aqui.apps.googleusercontent.com<br/>'
        'GOOGLE_CLIENT_SECRET=tu-client-secret-aqui',
        styles['Codigo']
    ))
    story.append(Paragraph(
        'Tambien crea un archivo <b>web/frontend/.env</b> con:',
        styles['Texto']
    ))
    story.append(Paragraph(
        'VITE_GOOGLE_CLIENT_ID=tu-client-id-aqui.apps.googleusercontent.com',
        styles['Codigo']
    ))
    story.append(Paragraph(
        'Reinicia el backend (Ctrl+C y python run.py de nuevo) '
        'y el frontend (Ctrl+C y npm run dev de nuevo).',
        styles['Alerta']
    ))

    story.append(PageBreak())

    # ═══════════════════════════════════════
    # RESUMEN RAPIDO
    # ═══════════════════════════════════════
    story.append(Paragraph('Resumen Rapido — Comandos Diarios', styles['PasoTitulo']))
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph(
        'Cada vez que quieras usar RALOZ Web, solo necesitas abrir 2 terminales:',
        styles['Texto']
    ))

    story.append(Paragraph('<b>Terminal 1 — Backend:</b>', styles['Texto']))
    story.append(Paragraph(
        'cd web\\backend<br/>'
        'python run.py',
        styles['Codigo']
    ))

    story.append(Paragraph('<b>Terminal 2 — Frontend:</b>', styles['Texto']))
    story.append(Paragraph(
        'cd web\\frontend<br/>'
        'npm run dev',
        styles['Codigo']
    ))

    story.append(Paragraph('<b>Abrir en navegador:</b>', styles['Texto']))
    story.append(Paragraph('http://localhost:5173', styles['Codigo']))

    story.append(Spacer(1, 0.3*inch))
    story.append(HRFlowable(width="100%", thickness=1, color=AZUL))
    story.append(Spacer(1, 0.2*inch))

    # Troubleshooting
    story.append(Paragraph('Problemas Comunes', styles['PasoTitulo']))
    story.append(Spacer(1, 0.1*inch))

    problemas = [
        ['Problema', 'Solucion'],
        ['"pip" no se reconoce', 'Reinstala Python marcando "Add to PATH" en el instalador'],
        ['"node" no se reconoce', 'Reinstala Node.js. Cierra y abre la terminal despues de instalar'],
        ['Error con psycopg2', 'Intenta: pip install psycopg2-binary'],
        ['Error de conexion a BD', 'Verifica la URL en .env. Revisa que el password no tenga caracteres especiales sin escapar'],
        ['La pagina no carga', 'Verifica que AMBAS terminales esten corriendo (backend + frontend)'],
        ['Error CORS', 'Revisa que CORS_ORIGINS en .env tenga http://localhost:5173'],
        ['Login no funciona', 'Ejecuta flask seed para crear el usuario admin'],
        ['Puerto 5000 ocupado', 'Cierra otros programas o cambia el puerto en run.py'],
    ]
    t = Table(problemas, colWidths=[2.2*inch, 3.8*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), ROJO),
        ('TEXTCOLOR', (0,0), (-1,0), white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('GRID', (0,0), (-1,-1), 0.5, HexColor('#e5e7eb')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [white, HexColor('#fef2f2')]),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(t)

    story.append(Spacer(1, 0.4*inch))
    story.append(Paragraph(
        '<b>RALOZ COL SAS</b> — Sistema de Facturacion v1.0.0-beta<br/>'
        'Desarrollado para uniformes escolares en Medellin, Colombia',
        ParagraphStyle('Footer', parent=styles['Normal'],
                       fontSize=9, textColor=GRIS, alignment=TA_CENTER)
    ))

    # Build
    doc.build(story)
    print(f"PDF generado: {output_path}")


if __name__ == '__main__':
    build_pdf()
