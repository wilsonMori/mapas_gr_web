import pandas as pd
import re

def procesar_coordenada_individual(coordenada_str):
    if pd.isna(coordenada_str):
        return None, None
    coordenada_str = str(coordenada_str).strip()
    if not coordenada_str:
        return None, None

    coordenada_str = re.sub(r'\s*,\s*', ' ', coordenada_str)
    coordenada_str = re.sub(r'\s+', ' ', coordenada_str)
    partes = coordenada_str.split()

    if len(partes) >= 2:
        try:
            lat = float(partes[0])
            lon = float(partes[1])
            return lat, lon
        except ValueError:
            return None, None
    return None, None

def extraer_y_limpiar_coordenadas(df: pd.DataFrame):
    df_clean = df.copy()
    columnas_lower = {col.lower().strip(): col for col in df_clean.columns}

    if 'coordenadas' in columnas_lower:
        col_real = columnas_lower['coordenadas']
        coords = df_clean[col_real].apply(procesar_coordenada_individual)
        df_clean['Latitud'] = [c[0] for c in coords]
        df_clean['Longitud'] = [c[1] for c in coords]
    elif 'ubicación' in columnas_lower or 'ubicacion' in columnas_lower:
        col_real = columnas_lower.get('ubicación') or columnas_lower.get('ubicacion')
        coords = df_clean[col_real].apply(procesar_coordenada_individual)
        df_clean['Latitud'] = [c[0] for c in coords]
        df_clean['Longitud'] = [c[1] for c in coords]
    elif 'latitud' in columnas_lower and 'longitud' in columnas_lower:
        lat_col = columnas_lower['latitud']
        lon_col = columnas_lower['longitud']
        df_clean['Latitud'] = pd.to_numeric(df_clean[lat_col], errors='coerce')
        df_clean['Longitud'] = pd.to_numeric(df_clean[lon_col], errors='coerce')
    else:
        raise ValueError("No se encontraron columnas de coordenadas válidas (CONTRATO / COORDENADAS / LATITUD / LONGITUD)")

    original_count = len(df_clean)
    df_clean = df_clean.dropna(subset=['Latitud', 'Longitud'])
    validos_count = len(df_clean)

    # Identificar columna contrato si existe
    col_contrato = next((col for col in df_clean.columns if 'contrato' in col.lower()), None)
    if col_contrato:
        df_clean['Contrato'] = df_clean[col_contrato].astype(str)
    else:
        df_clean['Contrato'] = [f"Item {i+1}" for i in range(len(df_clean))]

    df_clean = df_clean.reset_index(drop=True)
    df_clean['point_id'] = df_clean.index.astype(int)

    return df_clean, {
        "total_original": original_count,
        "total_validos": validos_count,
        "eliminados": original_count - validos_count
    }
