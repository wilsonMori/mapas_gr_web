import streamlit as st
import pandas as pd
from controllers.points_controller import PointsController
from utils.coords_utils import extraer_coordenadas

def main():
    st.title("Mapas GR - Planificación de Técnicos")

    archivo = st.file_uploader("Sube tu Excel con coordenadas", type=["xlsx"])
    if archivo:
        df = pd.read_excel(archivo)
        df = extraer_coordenadas(df)
        controller = PointsController(df)
        controller.run()

if __name__ == "__main__":
    main()
