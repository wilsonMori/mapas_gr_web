import streamlit as st
import pandas as pd
import io
from shapely.geometry import Point, Polygon
from views.map_view import render_colored_map
from views.algorithms import aplicar_algoritmo   # ✅ usar envoltorio genérico

class TecnicosController:
    def __init__(self, df, dia_seleccionado):
        # Filtrar solo los puntos del día seleccionado
        self.df = df[df["Dia"] == dia_seleccionado].copy()
        self.dia = dia_seleccionado

    def run(self):
        st.title(f"👷 Asignación de Técnicos para el Día {self.dia}")

        # Solicitar número de técnicos
        n_tecnicos = st.number_input(
            "Ingrese número de técnicos para este día:",
            min_value=1, step=1, key=f"n_tecnicos_{self.dia}"
        )

        if n_tecnicos > 0:
            st.success("Número de técnicos validado ✅")

            # 👉 Flag para evitar que el algoritmo se ejecute en cada refresco
            if f"algoritmo_tecnicos_aplicado_{self.dia}" not in st.session_state:
                st.session_state[f"algoritmo_tecnicos_aplicado_{self.dia}"] = False

            # Selector de algoritmo
            algoritmo = st.selectbox(
                "Seleccione algoritmo de asignación entre técnicos",
                [
                    "Por zona",
                    "Por proximidad",
                    "Balanceado Preciso",
                    "Capacitado",
                    "Sweep"
                ],
                key=f"algoritmo_tecnicos_{self.dia}"
            )

            # 👉 Aplicar algoritmo solo la primera vez
            if not st.session_state[f"algoritmo_tecnicos_aplicado_{self.dia}"]:
                self.df = aplicar_algoritmo(self.df, algoritmo, n_tecnicos, columna="Tecnico")
                st.session_state["df"].loc[self.df.index, "Tecnico"] = self.df["Tecnico"]
                st.session_state[f"algoritmo_tecnicos_aplicado_{self.dia}"] = True
            else:
                # 👉 Ya se aplicó el algoritmo, refrescar desde el global
                self.df = st.session_state["df"][st.session_state["df"]["Dia"] == self.dia].copy()

            # 👉 Mostrar mapa automático (algoritmo + ediciones)
            st.subheader("🗺️ Distribución por técnicos (algoritmo + ediciones)")
            st.info(f"Algoritmo aplicado: {algoritmo}")
            render_colored_map(self.df, color_by="Tecnico", key=f"map_tecnicos_{self.dia}")

            # 👉 Resumen inicial
            resumen = (
                self.df.groupby("Tecnico")
                .agg(Cantidad_puntos=("Tecnico", "count"))
                .reset_index()
            )
            st.subheader("📊 Resumen por técnico")
            st.table(resumen)

            # 👉 Exportar resumen
            output_resumen = io.BytesIO()
            with pd.ExcelWriter(output_resumen, engine="openpyxl") as writer:
                resumen.to_excel(writer, index=False, sheet_name="Resumen_Tecnicos")
            st.download_button(
                label="📥 Descargar resumen por técnico en Excel",
                data=output_resumen.getvalue(),
                file_name=f"resumen_tecnicos_dia_{self.dia}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            # 👉 Exportar todos los puntos del día con asignación por técnico
            output_excel_tecnicos = io.BytesIO()
            with pd.ExcelWriter(output_excel_tecnicos, engine="openpyxl") as writer:
                self.df.to_excel(writer, index=False, sheet_name="Asignacion_Tecnicos")
            st.download_button(
                label="📥 Descargar puntos asignados por técnico",
                data=output_excel_tecnicos.getvalue(),
                file_name=f"puntos_tecnicos_dia_{self.dia}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            # 👉 Edición manual en mapa
            st.subheader("✏️ Edición manual por técnico")
            output = render_colored_map(self.df, color_by="Tecnico", key=f"map_edit_tecnicos_{self.dia}")

            if output and output.get("last_active_drawing"):
                coords_poly = output["last_active_drawing"]["geometry"]["coordinates"][0]
                polygon = Polygon(coords_poly)

                seleccionados = self.df[self.df.apply(
                    lambda r: polygon.contains(Point(r['Longitud'], r['Latitud'])), axis=1
                )]

                st.success(f"Puntos seleccionados: {len(seleccionados)}")
                st.write(seleccionados)

                if len(seleccionados) > 0:
                    tecnico_manual = st.number_input(
                        "Asignar estos puntos al técnico:",
                        min_value=0, max_value=n_tecnicos-1, step=1,
                        key=f"tecnico_manual_{len(seleccionados)}"
                    )

                    if st.button("💾 Guardar cambios en asignación", key=f"guardar_tecnicos_{len(seleccionados)}"):
                        # 👉 Guardar cambios en el DataFrame global
                        st.session_state["df"].loc[seleccionados.index, "Tecnico"] = int(tecnico_manual)

                        # 👉 Refrescar la copia
                        self.df = st.session_state["df"][st.session_state["df"]["Dia"] == self.dia].copy()

                        st.success("Cambios guardados correctamente ✅")

                        # 👉 Recalcular resumen actualizado
                        resumen = (
                            self.df.groupby("Tecnico")
                            .agg(Cantidad_puntos=("Tecnico", "count"))
                            .reset_index()
                        )
                        st.subheader("📊 Resumen actualizado por técnico")
                        st.table(resumen)

                        # 👉 Renderizar mapa automático (algoritmo + ediciones)
                        st.subheader("🗺️ Distribución por técnicos (actualizada)")
                        render_colored_map(self.df, color_by="Tecnico", key=f"map_tecnicos_{self.dia}_editado")

            # 👉 Mapa final consolidado (siempre visible)
            st.subheader("🗺️ Distribución final por técnicos")
            render_colored_map(st.session_state["df"], color_by="Tecnico", key=f"map_final_tecnicos_{self.dia}")

            # 👉 Botón de descarga de la distribución final por técnicos (todos los puntos del día)
            output_excel_final = io.BytesIO()
            with pd.ExcelWriter(output_excel_final, engine="openpyxl") as writer:
                # Hoja con todos los puntos del día y su técnico asignado
                self.df.to_excel(writer, index=False, sheet_name="Distribucion_Final_Tecnicos")

                # Hoja con resumen por técnico
                resumen_final = (
                    self.df.groupby("Tecnico")
                    .agg(Cantidad_puntos=("Tecnico", "count"))
                    .reset_index()
                )
                resumen_final.to_excel(writer, index=False, sheet_name="Resumen_Tecnicos")

            st.download_button(
                label="📥 Descargar distribución final por técnicos",
                data=output_excel_final.getvalue(),
                file_name=f"distribucion_final_tecnicos_dia_{self.dia}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
