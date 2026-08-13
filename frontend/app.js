// Detectar la URL del servidor API backend con soporte para file:// y dominios HTTP/HTTPS
function getApiBaseUrl() {
  const isLocalFile = window.location.protocol === 'file:';
  const isLocalHost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' || window.location.hostname === '';
  
  if (isLocalFile || isLocalHost) {
    return 'http://localhost:8000';
  }
  
  // Si está desplegado en un servidor web como almacengr.com
  return `${window.location.protocol}//${window.location.hostname}:8000`;
}

const API_BASE_URL = getApiBaseUrl();

// Paleta de 30 Colores Únicos
const PALETTE_30 = [
  "#E41A1C", "#377EB8", "#4DAF4A", "#FF7F00", "#984EA3", "#A65628", "#F781BF", "#00CED1",
  "#FFD700", "#1B9E77", "#D95F02", "#7570B3", "#E7298A", "#66A61E", "#FF0000", "#000000",
  "#00BFFF", "#228B22", "#FF6347", "#1E90FF", "#9932CC", "#FF1493", "#40E0D0", "#FF4500",
  "#32CD32", "#008080", "#DC143C", "#4682B4", "#B8860B", "#00FA9A"
];

// Estado global de la aplicación
let appState = {
  points: [],
  targetColumn: 'Dia', // 'Dia' o 'Tecnico'
  selectedDayForTech: null,
  lastPolygonDrawn: null,
  isFilteredByDay: false,
  costChart: null
};

// Referencia al Mapa Leaflet y capas
let map = null;
let markersLayerGroup = null;
let drawControl = null;
let drawnItemsLayer = null;

// Inicialización de la App al cargar el DOM
document.addEventListener('DOMContentLoaded', () => {
  initMap();
  initEventListeners();
});

// Inicializar Mapa Leaflet
function initMap() {
  map = L.map('map', {
    center: [-8.0578, -79.022],
    zoom: 12,
    zoomControl: true
  });

  // Capa base elegante CartoDB Positron / Voyager
  L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; <a href="https://carto.com/">CARTO</a>',
    subdomains: 'abcd',
    maxZoom: 19
  }).addTo(map);

  markersLayerGroup = L.layerGroup().addTo(map);

  // Inicializar capa de dibujo de polígonos
  drawnItemsLayer = new L.FeatureGroup();
  map.addLayer(drawnItemsLayer);

  drawControl = new L.Control.Draw({
    draw: {
      polyline: false,
      circle: false,
      rectangle: false,
      marker: false,
      circlemarker: false,
      polygon: {
        allowIntersection: false,
        showArea: true,
        shapeOptions: { color: '#8b5cf6', weight: 2, fillColor: '#8b5cf6', fillOpacity: 0.25 }
      }
    },
    edit: {
      featureGroup: drawnItemsLayer,
      remove: true
    }
  });
  map.addControl(drawControl);

  // Escuchar evento cuando se termina de dibujar un polígono en el mapa
  map.on(L.Draw.Event.CREATED, (e) => {
    drawnItemsLayer.clearLayers();
    const layer = e.layer;
    drawnItemsLayer.addLayer(layer);

    const geoJson = layer.toGeoJSON();
    appState.lastPolygonDrawn = geoJson.geometry.coordinates[0]; // [[lng, lat], ...]
    
    // Contar cuántos puntos caen dentro del polígono dibujado
    const currentPoints = (appState.targetColumn === 'Tecnico' && appState.isFilteredByDay && appState.selectedDayForTech !== null)
      ? appState.points.filter(p => p.Dia === appState.selectedDayForTech)
      : appState.points;

    const selectedCount = currentPoints.filter(pt => {
      const lat = parseFloat(pt.Latitud);
      const lng = parseFloat(pt.Longitud);
      return isPointInPolygon([lng, lat], appState.lastPolygonDrawn);
    }).length;

    // Mostrar el modal emergente con la cantidad de puntos y consulta de día/técnico
    openReassignModal(selectedCount);
  });
}

// Algoritmo de Ray-Casting para detectar si un punto [lng, lat] está dentro del polígono
function isPointInPolygon(point, vs) {
  const x = point[0], y = point[1];
  let inside = false;
  for (let i = 0, j = vs.length - 1; i < vs.length; j = i++) {
    const xi = vs[i][0], yi = vs[i][1];
    const xj = vs[j][0], yj = vs[j][1];
    const intersect = ((yi > y) !== (yj > y))
        && (x < (xj - xi) * (y - yi) / (yj - yi) + xi);
    if (intersect) inside = !inside;
  }
  return inside;
}

// Abrir Modal Emergente de Consulta de Día / Técnico
function openReassignModal(selectedCount) {
  const modal = document.getElementById('modal-reassign');
  const countEl = document.getElementById('modal-points-count');
  const labelEl = document.getElementById('modal-target-label');
  const inputEl = document.getElementById('modal-target-value');

  countEl.innerHTML = `📍 Se han seleccionado <strong style="color:#34d399; font-size:1.15rem;">${selectedCount} puntos</strong> dentro del polígono dibujado.`;
  
  if (appState.targetColumn === 'Tecnico') {
    labelEl.innerText = `¿A qué Técnico deseas asignarlos para el Día ${appState.selectedDayForTech || 1}?`;
    inputEl.value = document.getElementById('tech-number-input').value.trim() || 'Técnico 1';
  } else {
    labelEl.innerText = '¿A qué Día deseas cambiar estos puntos?';
    inputEl.value = document.getElementById('new-day-val').value.trim() || '1';
  }

  modal.style.display = 'flex';
  inputEl.focus();
  inputEl.select();
}

function closeReassignModal() {
  document.getElementById('modal-reassign').style.display = 'none';
}

// Registro de Event Listeners de UI
function initEventListeners() {
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('file-input');

  dropzone.addEventListener('click', () => fileInput.click());
  dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.classList.add('dragover');
  });
  dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('dragover');
    if (e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  });
  fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
      handleFileUpload(e.target.files[0]);
    }
  });

  // Botón Ocultar / Mostrar Panel Lateral
  const btnToggleSidebar = document.getElementById('btn-toggle-sidebar');
  if (btnToggleSidebar) {
    btnToggleSidebar.addEventListener('click', () => {
      const sidebar = document.querySelector('.sidebar');
      sidebar.classList.toggle('collapsed');
      setTimeout(() => {
        if (map) map.invalidateSize();
      }, 320);
    });
  }

  // Botón Ejecutar Algoritmo Días
  document.getElementById('btn-run-days').addEventListener('click', runDaysPartition);

  // Botones del Modal Emergente
  document.getElementById('btn-modal-confirm').addEventListener('click', () => {
    const rawVal = document.getElementById('modal-target-value').value.trim() || '1';
    const numVal = parseInt(rawVal);
    const newValue = isNaN(numVal) ? rawVal : numVal;
    applyPolygonReassign(newValue);
    closeReassignModal();
  });

  document.getElementById('btn-modal-cancel').addEventListener('click', () => {
    drawnItemsLayer.clearLayers();
    appState.lastPolygonDrawn = null;
    closeReassignModal();
  });

  // Permitir presionar la tecla Enter en el input del modal para confirmar rápidamente
  document.getElementById('modal-target-value').addEventListener('keyup', (e) => {
    if (e.key === 'Enter') {
      document.getElementById('btn-modal-confirm').click();
    }
  });

  // Botón Guardar Asignación de Técnico
  const btnSaveTech = document.getElementById('btn-save-tech-assign');
  if (btnSaveTech) {
    btnSaveTech.addEventListener('click', saveTechnicianAssignment);
  }

  // Botón Alternar Filtro por Día / Retornar a Todos los Puntos
  const btnFilterTech = document.getElementById('btn-filter-day-view');
  if (btnFilterTech) {
    btnFilterTech.addEventListener('click', toggleFilterDayForTechniciansView);
  }

  // Cambio de Día a Trabajar
  const selectDayTech = document.getElementById('select-day-tech');
  if (selectDayTech) {
    selectDayTech.addEventListener('change', () => {
      const selectedDay = parseInt(selectDayTech.value);
      if (!isNaN(selectedDay)) {
        appState.selectedDayForTech = selectedDay;
        if (appState.isFilteredByDay) {
          const dayPoints = appState.points.filter(p => p.Dia === selectedDay);
          renderMapPoints(dayPoints, 'Tecnico');
          updateStatsOverlay(dayPoints, 'Tecnico');
        }
      }
    });
  }

  // Botón Exportar Excel
  document.getElementById('btn-export-excel').addEventListener('click', exportToExcel);
}

// Carga de archivo Excel al Backend FastAPI
async function handleFileUpload(file) {
  const formData = new FormData();
  formData.append('file', file);

  const statusEl = document.getElementById('upload-status');
  statusEl.style.display = 'block';
  statusEl.style.color = '#60a5fa';
  statusEl.innerText = '⏳ Procesando archivo y reconociendo coordenadas...';

  try {
    const response = await fetch(`${API_BASE_URL}/api/upload`, {
      method: 'POST',
      body: formData
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || 'Error al subir el archivo');
    }

    const data = await response.json();
    appState.points = data.points;
    appState.targetColumn = 'Dia';
    appState.isFilteredByDay = false;

    statusEl.style.color = '#34d399';
    statusEl.innerHTML = `✅ <strong>${data.total_points}</strong> puntos válidos cargados correctamente.`;

    // Habilitar tarjetas del flujo
    enableCard('card-days');
    enableCard('card-edit');
    setStepActive('step-2');

    renderMapPoints(appState.points, 'Dia');
    updateStatsOverlay(appState.points, 'Dia');
    showToast(`Excel cargado con éxito: ${data.total_points} puntos.`);

  } catch (error) {
    statusEl.style.color = '#ef4444';
    statusEl.innerText = `❌ ${error.message}`;
    showToast(`Error: ${error.message}`, 'error');
  }
}

// Ejecución de Algoritmos por Días
async function runDaysPartition() {
  const nDays = parseInt(document.getElementById('num-days').value) || 5;
  const algo = document.getElementById('algo-days').value;

  try {
    showToast('⏳ Calculando partición por días...');
    const response = await fetch(`${API_BASE_URL}/api/partition`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        points: appState.points,
        n_clusters: nDays,
        algoritmo: algo,
        target_column: 'Dia'
      })
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || 'Error al ejecutar algoritmo');
    }

    const data = await response.json();
    appState.points = data.points;
    appState.targetColumn = 'Dia';
    appState.isFilteredByDay = false;

    renderMapPoints(appState.points, 'Dia');
    updateStatsOverlay(appState.points, 'Dia', data.resumen);

    // Gráfico de convergencia para kms-evolutivo
    if (algo === 'kms-evolutivo' && data.info_extra && data.info_extra.historial_costos) {
      renderCostChart(data.info_extra.historial_costos);
    } else {
      document.getElementById('chart-container').style.display = 'none';
    }

    // Poblar selector de días para técnicos
    populateDaySelectForTechnicians();
    enableCard('card-technicians');
    setStepActive('step-3');
    showToast(`✅ Algoritmo "${algo}" aplicado a ${nDays} días.`);

  } catch (error) {
    showToast(`Error: ${error.message}`, 'error');
  }
}

// Reasignación por Polígono dibujado
async function applyPolygonReassign(targetValue) {
  if (!appState.lastPolygonDrawn) {
    showToast('Dibuja un polígono en el mapa antes de guardar.', 'error');
    return;
  }

  const col = appState.targetColumn;

  try {
    showToast(`⏳ Reasignando puntos en el polígono a ${col}: "${targetValue}"...`);
    const response = await fetch(`${API_BASE_URL}/api/reassign-polygon`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        points: appState.points,
        polygon_coordinates: appState.lastPolygonDrawn,
        new_value: targetValue,
        target_column: col
      })
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || 'Error al reasignar por polígono');
    }

    const data = await response.json();
    appState.points = data.points;

    // Solo filtrar si el usuario explícitamente activó 'isFilteredByDay'
    const pointsToRender = (col === 'Tecnico' && appState.isFilteredByDay && appState.selectedDayForTech !== null)
      ? appState.points.filter(p => p.Dia === appState.selectedDayForTech)
      : appState.points;

    renderMapPoints(pointsToRender, col);
    updateStatsOverlay(pointsToRender, col);

    drawnItemsLayer.clearLayers();
    appState.lastPolygonDrawn = null;

    showToast(`✅ ${data.modified_count} puntos asignados a ${col}: "${targetValue}".`);

  } catch (error) {
    showToast(`Error: ${error.message}`, 'error');
  }
}

// Asignación de Técnico con Botón Guardar
function saveTechnicianAssignment() {
  const selectedDay = parseInt(document.getElementById('select-day-tech').value);
  const techValue = document.getElementById('tech-number-input').value.trim() || 'Técnico 1';

  if (isNaN(selectedDay)) {
    showToast('Selecciona un día válido.', 'error');
    return;
  }

  appState.selectedDayForTech = selectedDay;
  appState.targetColumn = 'Tecnico';

  if (appState.lastPolygonDrawn) {
    applyPolygonReassign(techValue);
  } else {
    let count = 0;
    appState.points.forEach(p => {
      if (p.Dia === selectedDay) {
        p.Tecnico = techValue;
        count++;
      }
    });

    // Mantener todos los puntos visibles salvo que el usuario haya activado explícitamente isFilteredByDay
    const pointsToRender = (appState.isFilteredByDay && appState.selectedDayForTech !== null)
      ? appState.points.filter(p => p.Dia === appState.selectedDayForTech)
      : appState.points;

    renderMapPoints(pointsToRender, 'Tecnico');
    updateStatsOverlay(pointsToRender, 'Tecnico');
    setStepActive('step-4');

    showToast(`✅ Cambios guardados: Puntos del Día ${selectedDay} asignados a "${techValue}".`);
  }
}

// Alternar entre Filtrar por Día y Retornar a Ver Todos los Puntos
function toggleFilterDayForTechniciansView() {
  const btn = document.getElementById('btn-filter-day-view');

  if (appState.isFilteredByDay) {
    // Retornar a la vista general de todos los puntos
    appState.targetColumn = 'Dia';
    appState.selectedDayForTech = null;
    appState.isFilteredByDay = false;

    renderMapPoints(appState.points, 'Dia');
    updateStatsOverlay(appState.points, 'Dia');
    setStepActive('step-2');

    if (btn) {
      btn.innerHTML = '<i class="fa-solid fa-eye"></i> Ver Solo Puntos de Este Día';
      btn.classList.remove('btn-success');
      btn.classList.add('btn-secondary');
    }
    showToast('🌍 Retornado a la vista general de todos los puntos.');

  } else {
    // Filtrar para ver solo el día seleccionado
    const selectedDay = parseInt(document.getElementById('select-day-tech').value);
    if (isNaN(selectedDay)) {
      showToast('Selecciona un día válido.', 'error');
      return;
    }

    appState.selectedDayForTech = selectedDay;
    appState.targetColumn = 'Tecnico';
    appState.isFilteredByDay = true;

    appState.points.forEach(p => {
      if (p.Dia === selectedDay && (p.Tecnico === undefined || p.Tecnico === null)) {
        p.Tecnico = 'Técnico 1';
      }
    });

    const dayPoints = appState.points.filter(p => p.Dia === selectedDay);
    renderMapPoints(dayPoints, 'Tecnico');
    updateStatsOverlay(dayPoints, 'Tecnico');
    setStepActive('step-4');

    if (btn) {
      btn.innerHTML = '<i class="fa-solid fa-earth-americas"></i> Ver Todos los Puntos del Mapa';
      btn.classList.remove('btn-secondary');
      btn.classList.add('btn-success');
    }
    showToast(`👁️ Mostrando solo los puntos del Día ${selectedDay}. Haz clic nuevamente para retornar a ver todos los puntos.`);
  }
}

// Renderizado de Puntos en el Mapa Leaflet
function renderMapPoints(points, colorByColumn) {
  markersLayerGroup.clearLayers();

  if (!points || points.length === 0) return;

  const latLngs = [];

  points.forEach((pt) => {
    const lat = parseFloat(pt.Latitud);
    const lng = parseFloat(pt.Longitud);
    if (isNaN(lat) || isNaN(lng)) return;

    latLngs.push([lat, lng]);

    const catValue = pt[colorByColumn] !== undefined && pt[colorByColumn] !== null ? pt[colorByColumn] : 1;
    
    let catIndex = 0;
    if (typeof catValue === 'number') {
      catIndex = Math.max(0, catValue - 1);
    } else if (typeof catValue === 'string') {
      let hash = 0;
      for (let i = 0; i < catValue.length; i++) {
        hash = catValue.charCodeAt(i) + ((hash << 5) - hash);
      }
      catIndex = Math.abs(hash);
    }

    const color = PALETTE_30[catIndex % PALETTE_30.length];

    const marker = L.circleMarker([lat, lng], {
      radius: 6,
      fillColor: color,
      color: '#ffffff',
      weight: 1,
      opacity: 0.9,
      fillOpacity: 0.85
    });

    const contratoText = pt.Contrato ? `<b>Contrato:</b> ${pt.Contrato}` : 'Sin contrato';
    const popupContent = `
      <div style="font-family:sans-serif; font-size:0.85rem; padding:4px;">
        <strong style="color:${color};">Día ${pt.Dia || 1} | ${colorByColumn}: ${catValue}</strong><br>
        ${contratoText}<br>
        <small style="color:#64748b;">Lat: ${lat.toFixed(5)}, Lng: ${lng.toFixed(5)}</small>
      </div>
    `;
    marker.bindPopup(popupContent);
    markersLayerGroup.addLayer(marker);
  });

  if (latLngs.length > 0) {
    const bounds = L.latLngBounds(latLngs);
    map.fitBounds(bounds, { padding: [30, 30] });
  }
}

// Actualizar Overlay de Estadísticas de Puntos
function updateStatsOverlay(points, colName, resumenBackend = null) {
  const container = document.getElementById('stats-list-container');
  const badge = document.getElementById('total-points-badge');

  badge.innerText = `${points.length} pts`;
  container.innerHTML = '';

  let countsMap = {};
  if (resumenBackend) {
    resumenBackend.forEach(r => {
      countsMap[r[colName]] = r.Cantidad;
    });
  } else {
    points.forEach(p => {
      const val = p[colName] !== undefined && p[colName] !== null ? p[colName] : 'Sin asignar';
      countsMap[val] = (countsMap[val] || 0) + 1;
    });
  }

  Object.keys(countsMap).sort((a,b) => {
    const numA = parseInt(a), numB = parseInt(b);
    if (!isNaN(numA) && !isNaN(numB)) return numA - numB;
    return String(a).localeCompare(String(b));
  }).forEach(cat => {
    let catIndex = 0;
    const catNum = parseInt(cat);
    if (!isNaN(catNum)) {
      catIndex = Math.max(0, catNum - 1);
    } else {
      let hash = 0;
      for (let i = 0; i < cat.length; i++) {
        hash = cat.charCodeAt(i) + ((hash << 5) - hash);
      }
      catIndex = Math.abs(hash);
    }

    const color = PALETTE_30[catIndex % PALETTE_30.length];

    const item = document.createElement('div');
    item.className = 'stats-item';
    item.innerHTML = `
      <div>
        <span class="badge-color" style="background:${color};"></span>
        <span>${colName} ${cat}</span>
      </div>
      <strong>${countsMap[cat]} pts</strong>
    `;
    container.appendChild(item);
  });
}

// Poblador de opciones del Día para sub-partición de técnicos
function populateDaySelectForTechnicians() {
  const select = document.getElementById('select-day-tech');
  if (!select) return;

  select.innerHTML = '';

  const uniqueDays = [...new Set(appState.points.map(p => p.Dia))].filter(d => d !== undefined && d !== null).sort((a,b) => a - b);
  uniqueDays.forEach(d => {
    const opt = document.createElement('option');
    opt.value = d;
    opt.innerText = `Día ${d}`;
    select.appendChild(opt);
  });

  if (uniqueDays.length > 0) {
    appState.selectedDayForTech = uniqueDays[0];
  }
}

// Renderizado del Gráfico de Convergencia del Algoritmo Evolutivo (Chart.js)
function renderCostChart(costHistory) {
  const chartContainer = document.getElementById('chart-container');
  chartContainer.style.display = 'block';

  const ctx = document.getElementById('costChart').getContext('2d');
  
  if (appState.costChart) {
    appState.costChart.destroy();
  }

  appState.costChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: costHistory.map((_, i) => i + 1),
      datasets: [{
        label: 'Costo de la Función Objetivo',
        data: costHistory,
        borderColor: '#10b981',
        backgroundColor: 'rgba(16, 185, 129, 0.1)',
        borderWidth: 2,
        tension: 0.3,
        fill: true,
        pointRadius: 2
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { display: true, ticks: { color: '#64748b', font: { size: 9 } } },
        y: { display: true, ticks: { color: '#64748b', font: { size: 9 } } }
      }
    }
  });
}

// Exportar Distribución Final a Excel
async function exportToExcel() {
  if (!appState.points || appState.points.length === 0) {
    showToast('No hay datos cargados para exportar.', 'error');
    return;
  }

  try {
    showToast('📥 Generando archivo Excel completo...');
    const response = await fetch(`${API_BASE_URL}/api/export`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        points: appState.points,
        target_column: appState.targetColumn
      })
    });

    if (!response.ok) {
      throw new Error('Fallo al descargar el archivo Excel');
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `distribucion_${appState.targetColumn.toLowerCase()}_mapas_gr.xlsx`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);

    showToast('✅ Descarga completada con éxito.');

  } catch (error) {
    showToast(`Error al exportar: ${error.message}`, 'error');
  }
}

// Funciones Auxiliares de UI
function enableCard(cardId) {
  const el = document.getElementById(cardId);
  if (el) {
    el.style.opacity = '1';
    el.style.pointerEvents = 'auto';
  }
}

function setStepActive(stepId) {
  document.querySelectorAll('.step-item').forEach(el => el.classList.remove('active'));
  const activeEl = document.getElementById(stepId);
  if (activeEl) activeEl.classList.add('active');
}

function showToast(message, type = 'info') {
  let toast = document.getElementById('app-toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'app-toast';
    toast.className = 'toast';
    document.body.appendChild(toast);
  }

  toast.style.borderLeftColor = type === 'error' ? '#ef4444' : '#3b82f6';
  toast.innerHTML = `<i class="fa-solid ${type === 'error' ? 'fa-triangle-exclamation' : 'fa-circle-info'}"></i> ${message}`;
  toast.classList.add('show');

  setTimeout(() => {
    toast.classList.remove('show');
  }, 4000);
}
