import numpy as np
import pandas as pd
import random
from sklearn.cluster import KMeans

def evaluate_cost_fast(coords, asignaciones, n_dias, cantidades, alpha=1.0, beta=3.0, gamma=2.0):
    dispersion = 0.0
    ranges = []
    
    for d in range(n_dias):
        mask = (asignaciones == d)
        if not np.any(mask):
            dispersion += 1.0
        else:
            sub = coords[mask]
            min_lat, max_lat = sub[:, 0].min(), sub[:, 0].max()
            min_lon, max_lon = sub[:, 1].min(), sub[:, 1].max()
            dispersion += float((max_lat - min_lat) * (max_lon - min_lon))
            ranges.append((min_lon, max_lon))

    # Sobrelapamiento en longitud
    ranges.sort(key=lambda x: x[0])
    overlap = 0.0
    for i in range(len(ranges) - 1):
        r1 = ranges[i][1]
        l2 = ranges[i+1][0]
        if l2 < r1:
            overlap += (r1 - l2)

    # Conteo de desbalance por día
    counts = np.bincount(asignaciones[asignaciones >= 0], minlength=n_dias)
    desbalance = 0
    for d, esp in enumerate(cantidades):
        cnt = counts[d] if d < len(counts) else 0
        desbalance += abs(esp - cnt)

    unassigned_penalty = np.sum(asignaciones == -1) * 5.0
    return float(alpha * dispersion + beta * overlap + gamma * desbalance + unassigned_penalty)

def asignar_por_kmeans_evolutivo(df, cantidades, n_generations=20, population_size=10,
                                 alpha=1.0, beta=3.0, gamma=2.0, mutation_sigma=0.001):
    df = df.copy()
    n_dias = len(cantidades)
    coords = df[["Latitud", "Longitud"]].values.astype(float)

    if len(coords) < n_dias:
        df["Dia"] = 0
        return df, {"mejor_costo": 0.0, "historial_costos": [0.0]}

    kmeans = KMeans(n_clusters=n_dias, n_init=5, random_state=42)
    labels_init = kmeans.fit_predict(coords)
    centroids = kmeans.cluster_centers_

    population = []
    for _ in range(population_size):
        noise = np.random.normal(0, mutation_sigma, size=centroids.shape)
        population.append(centroids + noise)

    best_asignaciones = labels_init
    best_cost = evaluate_cost_fast(coords, labels_init, n_dias, cantidades, alpha, beta, gamma)
    history = [best_cost]

    # Ejecución genéticas pura vectorizada en NumPy (Ultra-rápida)
    for gen in range(n_generations):
        scored = []
        for c_matrix in population:
            # Matriz de distancias vectorizadas (N, K)
            dists = np.linalg.norm(coords[:, np.newaxis, :] - c_matrix[np.newaxis, :, :], axis=2)
            asignaciones = np.argmin(dists, axis=1)

            cost = evaluate_cost_fast(coords, asignaciones, n_dias, cantidades, alpha, beta, gamma)
            scored.append((c_matrix, cost, asignaciones))

        scored.sort(key=lambda x: x[1])
        elites = scored[:max(1, population_size // 4)]

        if elites[0][1] < best_cost:
            best_cost = elites[0][1]
            best_asignaciones = elites[0][2]
        history.append(float(best_cost))

        new_pop = [e[0] for e in elites]
        while len(new_pop) < population_size:
            parent = random.choice(elites)[0]
            child = parent + np.random.normal(0, mutation_sigma, size=parent.shape)
            new_pop.append(child)
        population = new_pop

    df["Dia"] = best_asignaciones
    return df, {"mejor_costo": float(best_cost), "historial_costos": history}
