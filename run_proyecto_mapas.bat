@echo off
REM Ir a la carpeta del proyecto
cd C:\Users\LENOVO\Documents\WILSON MORI\mapa\proyecto_mapas

REM Activar el entorno virtual
call mapscon310\Scripts\activate

REM Ejecutar la aplicación con Streamlit
streamlit run app.py

REM Mantener la ventana abierta al terminar
pause
