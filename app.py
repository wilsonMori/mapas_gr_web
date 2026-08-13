import streamlit as st
import pandas as pd
from controllers.points_controller import PointsController
from utils.coords_utils import extraer_coordenadas

def main():
    st.title("Mapas GR - Planificación de Rutas")

    archivo = st.file_uploader("Sube tu Excel, las columnas CONTRATO y COORDENADAS deben existir", type=["xlsx"])
    
    if archivo:
        # Avoid reprocessing the file on every interaction by checking the file_id
        if "last_file_id" not in st.session_state or st.session_state["last_file_id"] != archivo.file_id:
            with st.spinner("Procesando archivo reconociendo coordenadas..."):
                df = pd.read_excel(archivo)
                df = extraer_coordenadas(df)
                st.session_state["df"] = df
                st.session_state["last_file_id"] = archivo.file_id
                
                # Reset algorithm states
                st.session_state["algoritmo_aplicado"] = False
                st.session_state.pop("n_dias_anterior", None)
                st.session_state.pop("algoritmo_anterior", None)
                st.session_state.pop("cambios_guardados", None)

        if "df" in st.session_state:
            controller = PointsController(st.session_state["df"])
            controller.run()

if __name__ == "__main__":
    main()
