import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import LocateControl

# Lista de coordenadas
puntos = [
    {"lat": -8.0578, "lon": -79.022, "nombre": "Punto A"},
    {"lat": -8.0580, "lon": -79.022, "nombre": "Punto B"},
    {"lat": -8.0581, "lon": -79.0215, "nombre": "Punto C"},
    {"lat": -8.0582, "lon": -79.022, "nombre": "Punto D"},
]

# Crear mapa centrado en el primer punto
m = folium.Map(location=[puntos[0]["lat"], puntos[0]["lon"]], zoom_start=18)

# Agregar todos los puntos
coords = []
for p in puntos:
    coords.append([p["lat"], p["lon"]])
    link = f"https://www.google.com/maps?q={p['lat']},{p['lon']}"
    folium.CircleMarker(
        location=[p["lat"], p["lon"]],
        radius=6,
        color="blue",
        fill=True,
        fill_color="blue",
        popup=f"<b>{p['nombre']}</b><br><a href='{link}' target='_blank'>Ir al sitio</a>",
        tooltip=p["nombre"]
    ).add_to(m)

# Dibujar línea que conecta los puntos
folium.PolyLine(coords, color="red", weight=2.5, opacity=1).add_to(m)

# Agregar control de geolocalización
LocateControl(auto_start=True).add_to(m)

# Mostrar mapa en Streamlit
st.title("Mapa estilo My Maps con ubicación actual")
st_folium(m, width=700, height=500)
