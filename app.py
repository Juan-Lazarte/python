import os
import uuid
from flask import Flask, render_template, request, redirect, url_for, flash
import geopandas as gpd
from shapely.geometry import Polygon, LineString, MultiLineString, Point
import plotly.graph_objs as go

app = Flask(__name__)
app.secret_key = 'mi_clave_secreta'  # Necesaria para usar mensajes flash

# Aumentamos el tamaño máximo permitido a 150 MB
app.config['MAX_CONTENT_LENGTH'] = 150 * 1024 * 1024  # 150 MB

# Configuración de la carpeta de subida
UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'dxf_file' not in request.files:
            flash('No se encontró el campo para el archivo.')
            return redirect(request.url)
        file = request.files['dxf_file']
        if file.filename == '':
            flash('No se seleccionó ningún archivo.')
            return redirect(request.url)
        if file:
            filename = f"{uuid.uuid4().hex}_{file.filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            try:
                gdf_topografia = gpd.read_file(file_path, driver="DXF")
            except Exception as e:
                flash(f"No se pudo cargar el archivo DXF: {e}")
                os.remove(file_path)
                return redirect(request.url)
            
            vertices = [
                (241591.91, 8346384.83),
                (244210.10, 8346803.62),
                (245442.26, 8343979.28),
                (243056.61, 8343144.50)
            ]
            poligono_recorte = Polygon(vertices)
            
            gdf_filtrado = gdf_topografia.clip(poligono_recorte)
            
            topografia_trazos = []
            puntos_topo_x = []
            puntos_topo_y = []
            
            for _, row in gdf_filtrado.iterrows():
                geom = row['geometry']
                if geom is None:
                    continue
                if isinstance(geom, LineString):
                    x, y = geom.xy
                    topografia_trazos.append(go.Scattergl(
                        x=list(x), y=list(y), mode='lines',
                        line=dict(color='gray', width=1), showlegend=False
                    ))
                elif isinstance(geom, MultiLineString):
                    for line in geom.geoms:
                        x, y = line.xy
                        topografia_trazos.append(go.Scattergl(
                            x=list(x), y=list(y), mode='lines',
                            line=dict(color='gray', width=1), showlegend=False
                        ))
                elif isinstance(geom, Point):
                    puntos_topo_x.append(geom.x)
                    puntos_topo_y.append(geom.y)
            
            if puntos_topo_x and puntos_topo_y:
                topografia_trazos.append(go.Scattergl(
                    x=puntos_topo_x, y=puntos_topo_y, mode='markers',
                    marker=dict(size=4, color='gray'), showlegend=False
                ))
            
            fig = go.Figure(data=topografia_trazos)
            fig.update_layout(
                title="Topografía Filtrada (DXF) sin contorno adicional",
                xaxis=dict(range=[241591, 245442.26], visible=False, showgrid=False, zeroline=False),
                yaxis=dict(range=[8343000, 8347000], visible=False, showgrid=False, zeroline=False),
                height=1400, width=1400, showlegend=False,
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)'
            )
            
            graph_html = fig.to_html(full_html=False)
            os.remove(file_path)
            
            return render_template('display.html', graph_html=graph_html)
    
    return render_template('index.html')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))  # Usa el puerto de Railway o 5000 por defecto
    app.run(host='0.0.0.0', port=port, debug=True)