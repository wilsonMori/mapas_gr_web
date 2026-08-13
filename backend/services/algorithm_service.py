import pandas as pd
import numpy as np
import random
from sklearn.cluster import KMeans
from sklearn.metrics import pairwise_distances
from geopy.distance import geodesic
from services.evolutionary_service import asignar_por_kmeans_evolutivo

def aplicar_algoritmo_particion(df: pd.DataFrame, algoritmo: str, n_clusters: int, columna_destino="Dia"):
    df = df.copy()

    if algoritmo == "Por zona":
        df = asignar_por_zona(df, n_clusters)
        info_extra = {}
    elif algoritmo == "Por proximidad":
        df = distribucion_por_proximidad(df, n_clusters)
        info_extra = {}
    elif algoritmo == "Balanceado Preciso":
        df = asignar_balanceado_preciso(df, n_clusters)
        info_extra = {}
    elif algoritmo == "Capacitado":
        df = asignar_capacitado(df, n_clusters)
        info_extra = {}
    elif algoritmo == "Sweep":
        df = asignar_sweep(df, n_clusters)
        info_extra = {}
    elif algoritmo == "kms-evolutivo":
        total_puntos = len(df)
        sugerido = int(np.floor(total_puntos / n_clusters))
        cantidades = [sugerido] * n_clusters
        cantidades[-1] += total_puntos - sum(cantidades)
        
        df, info_extra = asignar_por_kmeans_evolutivo(df, cantidades)
    else:
        df = asignar_por_zona(df, n_clusters)
        info_extra = {}

    # Convertir días/técnicos de 0-indexed a 1-indexed (salvo -1 sin asignar)
    if "Dia" in df.columns:
        df["Dia"] = df["Dia"].apply(lambda x: int(x) + 1 if x != -1 else -1)

    if columna_destino != "Dia":
        df[columna_destino] = df["Dia"]
        df.drop(columns=["Dia"], errors="ignore", inplace=True)

    return df, info_extra

def asignar_por_zona(df, n_clusters, random_state=42):
    df = df.copy()
    if len(df) < n_clusters:
        df["Dia"] = 0
        return df

    coords = df[["Latitud", "Longitud"]].values
    kmeans = KMeans(n_clusters=n_clusters, random_state=random_state)
    labels = kmeans.fit_predict(coords)
    df["Dia"] = labels.astype(int)
    return df

def distribucion_por_proximidad(df, n_clusters):
    df = df.copy()
    coords = df[['Latitud', 'Longitud']].values
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    df['Dia'] = kmeans.fit_predict(coords)

    orden_clusters = (
        df.groupby("Dia")[["Latitud", "Longitud"]]
        .mean()
        .sort_values(by=["Latitud", "Longitud"])
        .index.tolist()
    )
    mapping = {cluster: i for i, cluster in enumerate(orden_clusters)}
    df['Dia'] = df['Dia'].map(mapping).astype(int)
    return df

def asignar_balanceado_preciso(df, n_clusters, max_iter=100):
    df = df.copy()
    coords = df[['Latitud', 'Longitud']].values
    n_points = len(coords)
    target_size = n_points // n_clusters
    extra = n_points % n_clusters

    centroides = coords[np.random.choice(n_points, n_clusters, replace=False)]
    asignaciones = np.full(n_points, -1)

    for _ in range(max_iter):
        dist = pairwise_distances(coords, centroides)
        asignaciones[:] = -1
        usados = set()

        for dia in range(n_clusters):
            candidatos = np.argsort(dist[:, dia])
            count = 0
            limite = target_size + (1 if dia < extra else 0)
            for idx in candidatos:
                if asignaciones[idx] == -1 and count < limite:
                    asignaciones[idx] = dia
                    usados.add(idx)
                    count += 1

        for dia in range(n_clusters):
            sub_coords = coords[asignaciones == dia]
            if len(sub_coords) > 0:
                centroides[dia] = sub_coords.mean(axis=0)

    for idx in np.where(asignaciones == -1)[0]:
        distancias = pairwise_distances([coords[idx]], centroides)[0]
        asignaciones[idx] = np.argmin(distancias)

    df['Dia'] = asignaciones.astype(int)
    return df

def asignar_capacitado(df, n_clusters):
    df = df.copy()
    coords = df[['Latitud', 'Longitud']].values
    n_points = len(coords)
    capacidad = max(1, n_points // n_clusters)

    centroides = coords[np.random.choice(n_points, n_clusters, replace=False)]
    asignaciones = np.full(n_points, -1)

    for idx, punto in enumerate(coords):
        distancias = [geodesic(punto, c).meters for c in centroides]
        orden = np.argsort(distancias)
        for dia in orden:
            if (asignaciones == dia).sum() < capacidad:
                asignaciones[idx] = dia
                break

    # Sobrantes si existen
    for idx in np.where(asignaciones == -1)[0]:
        asignaciones[idx] = random.randint(0, n_clusters - 1)

    df['Dia'] = asignaciones.astype(int)
    return df

def asignar_sweep(df, n_clusters, esquina="NO"):
    df = df.copy()
    n_points = len(df)
    target_size = n_points // n_clusters
    extra = n_points % n_clusters

    if esquina == "NO":
        df = df.sort_values(by=["Latitud", "Longitud"], ascending=[False, True])
    elif esquina == "NE":
        df = df.sort_values(by=["Latitud", "Longitud"], ascending=[False, False])
    elif esquina == "SO":
        df = df.sort_values(by=["Latitud", "Longitud"], ascending=[True, True])
    elif esquina == "SE":
        df = df.sort_values(by=["Latitud", "Longitud"], ascending=[True, False])

    df["Dia"] = -1
    usados = set()

    for dia in range(n_clusters):
        limite = target_size + (1 if dia < extra else 0)
        candidatos = df[~df.index.isin(usados)].copy()

        if len(candidatos) <= limite:
            df.loc[candidatos.index, "Dia"] = dia
            break

        punto_inicio = candidatos.iloc[0][["Latitud", "Longitud"]].values
        candidatos["distancia"] = candidatos.apply(
            lambda r: geodesic(punto_inicio, (r["Latitud"], r["Longitud"])).meters,
            axis=1
        )

        seleccionados = candidatos.nsmallest(limite, "distancia")
        df.loc[seleccionados.index, "Dia"] = dia
        usados.update(seleccionados.index)

    return df
