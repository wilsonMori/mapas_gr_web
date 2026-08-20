import sys
import os
import webbrowser
import threading
import time
import uvicorn
from fastapi.staticfiles import StaticFiles
from main import app

# Rutas para PyInstaller (empaquetado)
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
else:
    # Subimos un nivel (de backend a proyecto_mapas)
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

frontend_path = os.path.join(base_path, 'frontend')

# Montamos la carpeta frontend en la ruta principal para servir index.html
app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")

def open_browser():
    # Esperamos 2 segundos a que el servidor de FastAPI encienda
    time.sleep(2)
    print("Abriendo el navegador...")
    webbrowser.open("http://localhost:8000")

if __name__ == "__main__":
    print("Iniciando Sistema de Almacén GR (Local)...")
    # Lanzar el navegador en segundo plano
    threading.Thread(target=open_browser, daemon=True).start()
    # Iniciar el servidor local
    uvicorn.run(app, host="127.0.0.1", port=8000)
