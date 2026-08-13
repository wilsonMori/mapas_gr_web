import folium
from folium.plugins import Draw, Fullscreen
from streamlit_folium import st_folium
import pandas as pd
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import streamlit as st
import streamlit.components.v1 as components

def inject_draw_css():
    st.markdown("""
    <style>
    .leaflet-draw-actions { z-index: 10000 !important; }
    .leaflet-draw-toolbar { z-index: 10000 !important; }
    .leaflet-top, .leaflet-right { z-index: 10000 !important; }
    .leaflet-control { z-index: 10000 !important; }
    </style>
    """, unsafe_allow_html=True)

def render_colored_map(df, color_by="Dia", key=None, editable=False):
    if color_by not in df.columns:
        st.warning(f"⚠️ La columna '{color_by}' no existe en el DataFrame.")
        return None

#    m = folium.Map(location=[df['Latitud'].mean(), df['Longitud'].mean()], zoom_start=12)
    m = folium.Map(
        location=[df['Latitud'].mean(), df['Longitud'].mean()],
        zoom_start=12,
        tiles="CartoDB positron"   # puedes cambiar a "CartoDB dark_matter" para modo oscuro )
    )

    Fullscreen().add_to(m)

    categorias_unicas = sorted(df[color_by].dropna().unique())

    # 👉 Usar tu paleta de 30 colores 
    paleta_mapa_30 = [
        "#E41A1C",  # Rojo fuerte
        "#377EB8",  # Azul
        "#4DAF4A",  # Verde
        "#FF7F00",  # Naranja
        "#984EA3",  # Morado
        "#A65628",  # Marrón
        "#F781BF",  # Fucsia
        "#00CED1",  # Turquesa fuerte
        "#FFD700",  # Amarillo dorado
        "#1B9E77",  # Verde menta oscuro
 
        "#D95F02",  # Naranja quemado
        "#7570B3",  # Azul violeta
        "#E7298A",  # Rosa intenso
        "#66A61E",  # Verde oliva fuerte
        "#FF0000",  # Rojo puro
        "#000000",  # Negro
        "#00BFFF",  # Azul cielo brillante
        "#228B22",  # Verde bosque
        "#FF6347",  # Tomate
        "#1E90FF",  # Azul vivo

        "#9932CC",  # Morado intenso
        "#FF1493",  # Rosa neón
        "#40E0D0",  # Turquesa claro
        "#FF4500",  # Naranja rojo
        "#32CD32",  # Verde lima 
        "#008080",  # Teal
        "#DC143C",  # Carmesí
        "#4682B4",  # Azul acero
        "#B8860B",  # Mostaza fuerte
        "#00FA9A"   # Verde primavera 
    ]

    # Asignar colores a cada categoría (cíclico si hay más de 30) 
    colores_map = {
        cat: paleta_mapa_30[i % len(paleta_mapa_30)]
        for i, cat in enumerate(categorias_unicas)
    }

    # Normalizar nombres de columnas para encontrar "Contrato"
    normalized_cols = {c.lower().replace(" ", ""): c for c in df.columns}
    col_contrato = next((original for norm, original in normalized_cols.items() if "contrato" in norm), None)

    for cat, color in colores_map.items():
        subset = df[df[color_by] == cat]
        cantidad = len(subset)
        # ✅ Ya no sumamos +1 aquí, porque aplicar_algoritmo lo hace
        grupo = folium.FeatureGroup(name=f"{color_by} {cat} ({cantidad})")

        for _, row in subset.iterrows():
            contrato_text = f"Contrato: {row[col_contrato]}" if col_contrato and pd.notna(row[col_contrato]) else "Contrato: Sin dato"
            popup_text = f"{color_by}: {cat}<br>{contrato_text}"
            folium.CircleMarker(
                [row['Latitud'], row['Longitud']],
                radius=6,
                color=color,
                fill=True,
                popup=popup_text
            ).add_to(grupo)
        grupo.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
 
    if editable:
        Draw(
            export=True,
            position="topleft",
            draw_options={
                "polyline": False,
                "polygon": {
                    "allowIntersection": False,
                    "showArea": True,
                    "shapeOptions": {"color": "#97009c"},
                    "repeatMode": False,
                    "finishOnDoubleClick": True
                },
                "circle": False,
                "rectangle": False,
                "marker": False,
                "circlemarker": False
            },
            edit_options={"edit": True, "remove": True}
        ).add_to(m)

        inject_draw_css()

        # Optimize editable map by limiting returned objects
        return st_folium(
            m, 
            width=700, 
            height=500, 
            key=key, 
            returned_objects=["last_active_drawing", "all_drawings"]
        )

    # For non-editable maps, render static HTML to prevent bidirectional websocket flooding
    components.html(m._repr_html_(), width=700, height=500)
    return None


def render_map(df):
    """
    Mapa inicial con todos los puntos en azul.
    Al hacer clic en un punto se muestra el día y el contrato.
    """
    m = folium.Map(location=[df['Latitud'].mean(), df['Longitud'].mean()], zoom_start=12)
    Fullscreen().add_to(m)

    # Normalizar nombres de columnas para encontrar "Contrato"
    normalized_cols = {c.lower().replace(" ", ""): c for c in df.columns}
    col_contrato = next((original for norm, original in normalized_cols.items() if "contrato" in norm), None)

    for _, row in df.iterrows():
        contrato_text = f"Contrato: {row[col_contrato]}" if col_contrato and pd.notna(row[col_contrato]) else "Contrato: Sin dato"
        # ✅ Ya no sumamos +1 aquí
        dia_val = row['Dia'] if "Dia" in df.columns and pd.notna(row['Dia']) else None
        dia_text = f"Dia: {dia_val}" if dia_val is not None else "Dia: Sin asignar"
        popup_text = f"{dia_text}<br>{contrato_text}"

        folium.CircleMarker(
            [row['Latitud'], row['Longitud']],
            radius=5,
            color="blue",
            fill=True,
            popup=popup_text
        ).add_to(m)

    # Este mapa NO necesita bidireccionalidad
    components.html(m._repr_html_(), width=700, height=500)
    return None
