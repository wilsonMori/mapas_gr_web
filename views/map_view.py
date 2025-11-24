import folium
from folium.plugins import Draw, Fullscreen
from streamlit_folium import st_folium

def render_map(df):
    """
    Mapa inicial con todos los puntos en azul.
    Al hacer clic en un punto se muestra el Número de Contrato de Suministro.
    """
    m = folium.Map(location=[df['Latitud'].mean(), df['Longitud'].mean()], zoom_start=12)
    Fullscreen().add_to(m)  # Pantalla completa

    for _, row in df.iterrows():
        folium.CircleMarker(
            [row['Latitud'], row['Longitud']],
            radius=5,
            color="blue",
            fill=True,
            popup=f"Contrato: {row['Número de Contrato de Suministro']}"
        ).add_to(m)

    Draw(export=True).add_to(m)
    return st_folium(m, width=700, height=500)


def render_colored_map(df):
    """
    Mapa coloreado por técnico con leyenda.
    Cada técnico tiene su color y se muestra el total de puntos asignados.
    """
    m = folium.Map(location=[df['Latitud'].mean(), df['Longitud'].mean()], zoom_start=12)
    Fullscreen().add_to(m)

    # Paleta de colores para técnicos
    colores = ["red", "green", "purple", "orange", "brown", "blue", "darkred", "cadetblue"]
    tecnicos_unicos = sorted(df['Tecnico'].unique())

    # Añadir puntos coloreados
    for _, row in df.iterrows():
        color = colores[row['Tecnico'] % len(colores)]
        folium.CircleMarker(
            [row['Latitud'], row['Longitud']],
            radius=6,
            color=color,
            fill=True,
            popup=f"Contrato: {row['Número de Contrato de Suministro']} | Técnico {row['Tecnico']}"
        ).add_to(m)

    # Contar puntos por técnico
    conteo = df['Tecnico'].value_counts().sort_index()

    # Construir HTML de la leyenda con colores aplicados al texto
    leyenda_html = """
    <div style='position: fixed; 
                bottom: 50px; left: 50px; width: 260px; height: auto; 
                background-color: #f9f9f9; z-index:9999; 
                padding: 12px; border:2px solid #444; font-size:14px;
                box-shadow: 2px 2px 6px rgba(0,0,0,0.3);'>
        <b>🗂️ Distribución de Puntos</b><br>
    """
    for t in tecnicos_unicos:
        color = colores[t % len(colores)]
        total = conteo[t]
        leyenda_html += f"""
        <div style='margin-top:6px; color:{color}; font-weight:bold;'>
            <span style='background:{color};width:14px;height:14px;display:inline-block;border-radius:50%;margin-right:6px;'></span>
            Técnico {t} — {total} puntos
        </div>
        """

    leyenda_html += "</div>"
    m.get_root().html.add_child(folium.Element(leyenda_html))

    return st_folium(m, width=700, height=500)
