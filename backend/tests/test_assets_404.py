"""
Un archivo del build que ya no existe debe dar 404, no index.html.

Tras un despliegue, el navegador que tenía el panel abierto sigue pidiendo
los .js de la versión anterior. Si Flask le responde index.html, el navegador
recibe HTML donde espera JavaScript, falla por MIME type y la pantalla queda
en blanco sin explicación para quien está atendiendo.
"""
from app import es_archivo_del_build


def test_chunk_viejo_se_trata_como_archivo():
    assert es_archivo_del_build('assets/Dashboard-lZGU60Ej.js')
    assert es_archivo_del_build('assets/index-D6kdSv-J.css')
    assert es_archivo_del_build('algo.js')


def test_rutas_de_la_app_no_se_confunden():
    """/finanzas y /gastos son vistas de la SPA: deben servir index.html."""
    for ruta in ('', 'finanzas', 'gastos', 'asistente', 'mi-dia'):
        assert not es_archivo_del_build(ruta)
