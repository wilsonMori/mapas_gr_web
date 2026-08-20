import sys
import os
import io
import json
import pandas as pd
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from shapely.geometry import Point, Polygon

# Asegurar que el directorio 'backend' esté en el path para importar servicios
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.coords_service import extraer_y_limpiar_coordenadas
from services.algorithm_service import aplicar_algoritmo_particion

app = FastAPI(
    title="Mapas GR API",
    description="API REST Backend para Planificación de Rutas y Asignación Geográfica por Días y Técnicos",
    version="2.0.0"
)

# Permitir peticiones CORS desde cualquier origen (incluyendo GitHub Pages)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Schemas Pydantic
class PointItem(BaseModel):
    point_id: int
    Latitud: float
    Longitud: float
    Contrato: str
    Dia: Optional[Any] = None
    Tecnico: Optional[Any] = None
    extra_fields: Optional[Dict[str, Any]] = None

class PartitionRequest(BaseModel):
    points: List[Dict[str, Any]]
    n_clusters: int
    algoritmo: str
    target_column: str = "Dia"  # "Dia" o "Tecnico"

class PolygonReassignRequest(BaseModel):
    points: List[Dict[str, Any]]
    polygon_coordinates: List[List[float]] # [[lng, lat], ...]
    new_value: Any  # Nuevo Día o Técnico
    target_column: str = "Dia"  # "Dia" o "Tecnico"

class ExportRequest(BaseModel):
    points: List[Dict[str, Any]]
    target_column: str = "Dia"

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "Mapas GR FastAPI Backend"}

@app.post("/api/upload")
async def upload_excel(file: UploadFile = File(...)):
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Formato no soportado. Sube un archivo Excel (.xlsx)")
    
    contents = await file.read()
    try:
        df = pd.read_excel(io.BytesIO(contents))
        df_clean, stats = extraer_y_limpiar_coordenadas(df)
        
        # Convertir a formato dict orient records
        records = df_clean.to_dict(orient="records")
        return {
            "success": True,
            "filename": file.filename,
            "stats": stats,
            "total_points": len(records),
            "points": records
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error procesando archivo Excel: {str(e)}")

@app.post("/api/partition")
def partition_points(payload: PartitionRequest):
    if not payload.points:
        raise HTTPException(status_code=400, detail="Lista de puntos vacía.")
    
    df = pd.DataFrame(payload.points)
    if "Latitud" not in df.columns or "Longitud" not in df.columns:
        raise HTTPException(status_code=400, detail="Los puntos deben contener 'Latitud' y 'Longitud'.")

    try:
        df_part, info_extra = aplicar_algoritmo_particion(
            df=df,
            algoritmo=payload.algoritmo,
            n_clusters=payload.n_clusters,
            columna_destino=payload.target_column
        )

        # Generar resumen
        col = payload.target_column
        resumen = df_part.groupby(col).agg(Cantidad=(col, "count")).reset_index().to_dict(orient="records")

        return {
            "success": True,
            "target_column": payload.target_column,
            "points": df_part.to_dict(orient="records"),
            "resumen": resumen,
            "info_extra": info_extra
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al ejecutar algoritmo: {str(e)}")

@app.post("/api/reassign-polygon")
def reassign_polygon(payload: PolygonReassignRequest):
    if not payload.points or not payload.polygon_coordinates:
        raise HTTPException(status_code=400, detail="Puntos y coordenadas del polígono son requeridos.")
    
    try:
        # Shapely requiere coordenadas como (Longitud, Latitud)
        poly = Polygon(payload.polygon_coordinates)
        df = pd.DataFrame(payload.points)

        modified_count = 0
        col = payload.target_column

        for idx, row in df.iterrows():
            pt = Point(float(row["Longitud"]), float(row["Latitud"]))
            if poly.contains(pt):
                df.at[idx, col] = payload.new_value
                modified_count += 1

        resumen = df.groupby(col).agg(Cantidad=(col, "count")).reset_index().to_dict(orient="records")

        return {
            "success": True,
            "modified_count": modified_count,
            "points": df.to_dict(orient="records"),
            "resumen": resumen
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar selección por polígono: {str(e)}")

@app.post("/api/export")
def export_excel(payload: ExportRequest):
    if not payload.points:
        raise HTTPException(status_code=400, detail="No hay datos para exportar.")

    df = pd.DataFrame(payload.points)
    col = payload.target_column

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Distribucion_Final")

        if col in df.columns:
            resumen = df.groupby(col).agg(Cantidad_puntos=(col, "count")).reset_index()
            resumen.to_excel(writer, index=False, sheet_name="Resumen")

            # Hojas por cada categoría única
            for cat in sorted(df[col].dropna().unique()):
                safe_cat = str(cat).replace(" ", "_")[:25]
                subset = df[df[col] == cat]
                subset.to_excel(writer, index=False, sheet_name=f"{col}_{safe_cat}")

    output.seek(0)
    filename = f"distribucion_{col.lower()}.xlsx"

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
