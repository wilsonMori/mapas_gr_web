import streamlit as st
import pandas as pd
import io
from models.points_model import PointsModel
from views.map_view import render_map, render_colored_map
from shapely.geometry import Point, Polygon
from sklearn.cluster import KMeans

class PointsController:
    def __init__(self, df):
        self.df = df
        self.model = PointsModel(df)

    def run(self):
        st.title("Planificación de Técnicos GR")

        # Mostrar mapa inicial con todos los puntos
        output = render_map(self.df)

        # Si el usuario dibuja un polígono/círculo
        if output and output.get("last_active_drawing"):
            coords_poly = output["last_active_drawing"]["geometry"]["coordinates"][0]
            polygon = Polygon(coords_poly)

            # Filtrar puntos dentro del polígono
            seleccionados = self.df[self.df.apply(
                lambda r: polygon.contains(Point(r['Longitud'], r['Latitud'])), axis=1
            )]

            st.success(f"Puntos seleccionados: {len(seleccionados)}")
            st.write(seleccionados)

            # 👉 Botón de descarga para puntos seleccionados
            if len(seleccionados) > 0:
                output_excel = io.BytesIO()
                with pd.ExcelWriter(output_excel, engine="openpyxl") as writer:
                    seleccionados.to_excel(writer, index=False, sheet_name="Seleccionados")
                st.download_button(
                    label="📥 Descargar puntos seleccionados en Excel",
                    data=output_excel.getvalue(),
                    file_name="puntos_seleccionados.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

            # Distribuir entre técnicos
            tecnicos = st.number_input("Cantidad de técnicos", min_value=1, value=2)
            if len(seleccionados) > 0:
                clustered = self.model.assign_to_technicians(seleccionados, tecnicos)

                # Mostrar tabla
                st.write(clustered)

                # 👉 Botón de descarga para asignación por técnico
                output_excel2 = io.BytesIO()
                with pd.ExcelWriter(output_excel2, engine="openpyxl") as writer:
                    clustered.to_excel(writer, index=False, sheet_name="Asignación")
                st.download_button(
                    label="📥 Descargar asignación en Excel",
                    data=output_excel2.getvalue(),
                    file_name="asignacion_tecnicos.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

                # Mostrar mapa coloreado por técnico
                render_colored_map(clustered)
