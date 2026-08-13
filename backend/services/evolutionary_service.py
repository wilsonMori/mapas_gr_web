import numpy as np
import pandas as pd
import random
from sklearn.cluster import KMeans

def day_bbox_area(group):
    if group.empty:
        return 0.0
    lat_range = group["Latitud"].max() - group["Latitud"].min()
    lon_range = group["Longitud"].max() - group["Longitud"].min()
    return float(lat_range * lon_range)

def sector_overlap_longitude(df):
    ranges = []
    for dia in sorted(df["Dia"].unique()):
        g = df[df["Dia"] == dia]
        if g.empty:
            continue
        ranges.append((dia, g["Longitud"].min(), g["Longitud"].max()))
    ranges.sort(key=lambda x: x[1])

    overlap = 0.0
    for i in range(len(ranges) - 1):
        _, l1, r1 = ranges[i]
        _, l2, r2 = ranges[i+1]
        if l2 < r1:
            overlap += (r1 - l2)
    return float(overlap)

def evaluate_cost(df, cantidades, alpha=1.0, beta=3.0, gamma=2.0):
    dispersion = 0.0
    for dia in range(len(cantidades)):
        g = df[df["Dia"] == dia]
        if g.empty:
            dispersion += 1.0
        else:
            dispersion += day_bbox_area(g)

    cruce = sector_overlap_longitude(df)
    counts = df[df["Dia"] != -1]["Dia"].value_counts().to_dict()
    desbalance = 0
    for dia, esperado in enumerate(cantidades):
        desbalance += abs(esperado - counts.get(dia, 0))

    unassigned_penalty = len(df[df["Dia"] == -1]) * 5.0
    return float(alpha * dispersion + beta * cruce + gamma * desbalance + unassigned_penalty)

def asignar_por_kmeans_evolutivo(df, cantidades, n_generations=40, population_size=16,
                                 alpha=1.0, beta=3.0, gamma=2.0, mutation_sigma=0.001):
    df = df.copy()
    n_dias = len(cantidades)
    coords = df[["Latitud", "Longitud"]].values

    kmeans = KMeans(n_clusters=n_dias, n_init=10, random_state=42)
    df["Dia"] = kmeans.fit_predict(coords)
    centroids = kmeans.cluster_centers_

    population = []
    for _ in range(population_size):
        noise = np.random.normal(0, mutation_sigma, size=centroids.shape)
        population.append(centroids + noise)

    best_df, best_cost = None, float("inf")
    history = []

    for gen in range(n_generations):
        scored = []
        for c_matrix in population:
            asignaciones = []
            for i, row in df.iterrows():
                dists = np.linalg.norm(c_matrix - np.array([row["Latitud"], row["Longitud"]]), axis=1)
                asignaciones.append(int(np.argmin(dists)))
            df["Dia"] = asignaciones

            cost = evaluate_cost(df, cantidades, alpha, beta, gamma)
            scored.append((c_matrix, cost, df.copy()))

        scored.sort(key=lambda x: x[1])
        elites = scored[:max(1, population_size // 4)]

        if elites[0][1] < best_cost:
            best_cost = elites[0][1]
            best_df = elites[0][2]
        history.append(float(best_cost))

        new_pop = [e[0] for e in elites]
        while len(new_pop) < population_size:
            parent = random.choice(elites)[0]
            child = parent + np.random.normal(0, mutation_sigma, size=parent.shape)
            new_pop.append(child)
        population = new_pop

    return best_df, {"mejor_costo": float(best_cost), "historial_costos": history}
