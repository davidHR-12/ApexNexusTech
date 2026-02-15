/**
 * Logica para el Dashboard de Finanzas
 * Maneja gráficos con Chart.js y actualización de KPIs
 */

let chartGastosMes = null;
let chartGastosPorTipo = null; // Reservado para futuro uso si se implementa
let datosGastos = {};
let datosPorTipo = {}; // Reservado

document.addEventListener('DOMContentLoaded', cargarDatos);

/**
 * Cargar datos del backend
 */
async function cargarDatos() {
  try {
    // URL definida en el HTML como variable global o data-url
    // Buscamos el contenedor principal que tiene el data-url
    const container = document.querySelector('[data-url-gastos]');
    if (!container) return;
    
    const url = container.dataset.urlGastos;
    const response = await fetch(url);
    datosGastos = await response.json();
    
    calcularKPIs();
    actualizarGrafico();
    llenarTabla();
    llenarResumenTipo();
    
  } catch (error) {
    console.error('Error cargando datos:', error);
    // Usar sistema de notificaciones si existe, sino alert
    if (typeof mostrarToast === 'function') {
        mostrarToast('error', 'Error al cargar los datos de gastos');
    } else {
        alert('Error al cargar los datos de gastos');
    }
  }
}

/**
 * Calcular y mostrar KPIs
 */
function calcularKPIs() {
  if (!datosGastos.totales || datosGastos.totales.length === 0) return;

  const totalGastos = datosGastos.totales.reduce((a, b) => a + b, 0);
  // Copia para no mutar original y ordenar descendente
  const mayores = [...datosGastos.totales].sort((a, b) => b - a);
  const promedio = totalGastos / datosGastos.totales.length;

  actualizarTextoID('kpiTotalGastos', `-RD$ ${formatoMoneda(totalGastos)}`);
  actualizarTextoID('kpiCountGastos', `${datosGastos.totales.length} meses`);
  actualizarTextoID('kpiPromedioDiario', `-RD$ ${formatoMoneda(promedio)}`);
  actualizarTextoID('kpiMesesData', datosGastos.meses.length);

  if (datosGastos.meses.length > 0) {
    const mayorMonto = mayores[0];
    // Encontrar el índice original de este monto para obtener el mes
    const mayorIndex = datosGastos.totales.indexOf(mayorMonto);
    actualizarTextoID('kpiMayorMes', `-RD$ ${formatoMoneda(mayorMonto)}`);
    actualizarTextoID('kpiMayorMesNombre', datosGastos.meses[mayorIndex]);
  }
}

/**
 * Actualizar gráfico según filtros
 */
async function actualizarGrafico() {
  const filterTipo = document.getElementById('filterTipo').value;
  const filterTodos = document.getElementById('filterTodos').checked;
  const container = document.querySelector('[data-url-gastos]');
  const urlBase = container ? container.dataset.urlGastos : '';

  let datos = datosGastos.totales;

  if (filterTipo && !filterTodos && urlBase) {
    try {
      const response = await fetch(`${urlBase}?tipo=${filterTipo}`);
      const datosFiltered = await response.json();
      datos = datosFiltered.totales;
    } catch (error) {
      console.error('Error al filtrar:', error);
    }
  }

  renderizarGraficoLinea(datosGastos.meses, datos);
}

/**
 * Renderizar gráfico de línea
 */
function renderizarGraficoLinea(meses, datos) {
  const canvas = document.getElementById('chartGastosMes');
  if (!canvas) return;
  
  const ctx = canvas.getContext('2d');

  if (chartGastosMes) {
    chartGastosMes.destroy();
  }

  chartGastosMes = new Chart(ctx, {
    type: 'line',
    data: {
      labels: meses.map(m => {
        const [año, mes] = m.split('-');
        // Crear fecha localmente sin timezone issues simples
        const date = new Date(año, mes - 1);
        return date.toLocaleString('es-DO', { month: 'short', year: '2-digit' });
      }),
      datasets: [{
        label: 'Gastos Mensuales',
        data: datos,
        borderColor: '#ef4444',
        backgroundColor: 'rgba(239, 68, 68, 0.1)',
        tension: 0.4,
        fill: true,
        pointRadius: 5,
        pointBackgroundColor: '#ef4444',
        pointBorderColor: '#fff',
        pointBorderWidth: 2,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: '#d1d5db' } },
        tooltip: {
            callbacks: {
                label: function(context) {
                    return 'RD$ ' + formatoMoneda(context.parsed.y);
                }
            }
        }
      },
      scales: {
        y: {
          ticks: {
            color: '#9ca3af',
            callback: value => 'RD$ ' + formatoMoneda(value)
          },
          grid: { color: 'rgba(107, 114, 128, 0.1)' }
        },
        x: {
          ticks: { color: '#9ca3af' },
          grid: { color: 'rgba(107, 114, 128, 0.1)' }
        }
      }
    }
  });
}

/**
 * Llenar tabla de desglose por mes
 */
function llenarTabla() {
  const tbody = document.getElementById('tablaMesesBody');
  if (!tbody) return;

  const totalGeneral = datosGastos.totales.reduce((a, b) => a + b, 0);
  let html = '';
  // Iteramos para calcular variación respecto al mes anterior en el loop
  // Nota: datosGastos.totales asume orden cronológico
  
  datosGastos.meses.forEach((mes, idx) => {
    const monto = datosGastos.totales[idx];
    const porcentaje = totalGeneral > 0 ? ((monto / totalGeneral) * 100).toFixed(1) : 0;
    
    let variacionHTML = '<span class="text-gray-500">-</span>';
    
    if (idx > 0) {
        const montoAnterior = datosGastos.totales[idx - 1];
        if (montoAnterior !== 0) {
            const variacion = ((monto - montoAnterior) / montoAnterior) * 100;
            const simbolo = variacion > 0 ? '↑' : variacion < 0 ? '↓' : '→';
            const color = variacion > 0 ? 'text-red-400' : (variacion < 0 ? 'text-green-400' : 'text-gray-400');
            variacionHTML = `<span class="${color} font-bold text-xs">${simbolo} ${Math.abs(variacion).toFixed(1)}%</span>`;
        }
    }

    html += `
      <tr class="hover:bg-gray-800/40 transition-colors border-b border-gray-800/50 last:border-0">
        <td class="p-4 text-gray-300 font-medium">${mes}</td>
        <td class="p-4 text-right font-mono text-white">-RD$ ${formatoMoneda(monto)}</td>
        <td class="p-4 text-right text-gray-400 text-sm">${porcentaje}%</td>
        <td class="p-4 text-right">${variacionHTML}</td>
      </tr>
    `;
  });

  tbody.innerHTML = html;
}

/**
 * Llenar resumen por tipo
 */
function llenarResumenTipo() {
  const resumen = document.getElementById('resumenPorTipo');
  if (!resumen) return;

  const tipos = [
    { key: 'Mantenimiento', label: 'Mantenimiento', color: '#6b7280' },
    { key: 'Energia', label: 'Energía', color: '#eab308' },
    { key: 'Compra_Material', label: 'Compra Material', color: '#3b82f6' },
    { key: 'Herramientas', label: 'Herramientas', color: '#f97316' },
    { key: 'Servicios', label: 'Servicios', color: '#a855f7' },
    { key: 'Otro', label: 'Otro', color: '#6366f1' },
  ];

  let html = '';
  
  // Calcular totales por tipo desde los datos recibidos
  // La API devuelve: "por_tipo": { "Energia": {"2024-01": 500, ...}, ... }
  
  tipos.forEach(tipo => {
    let totalTipo = 0;
    
    if (datosGastos.por_tipo && datosGastos.por_tipo[tipo.key]) {
        // Sumar todos los valores mensuales para este tipo
        const montos = Object.values(datosGastos.por_tipo[tipo.key]);
        totalTipo = montos.reduce((a, b) => a + parseFloat(b), 0);
    }
    
    // Solo mostrar si tiene gastos > 0 (opcional, pero limpia la UI)
    // O mostrar 0.00 para que se vea que existen las categorías
    
    html += `
      <div class="flex items-center justify-between p-3 bg-gray-800/40 rounded-xl border border-gray-700/30 hover:bg-gray-800/60 transition-colors">
        <div class="flex items-center gap-3">
          <div class="w-2.5 h-2.5 rounded-full shadow-sm" style="background-color: ${tipo.color}"></div>
          <span class="text-gray-300 text-sm font-medium">${tipo.label}</span>
        </div>
        <span class="text-white font-mono text-sm font-bold">-RD$ ${formatoMoneda(totalTipo)}</span>
      </div>
    `;
  });

  resumen.innerHTML = html;
}

/**
 * Exportar datos a CSV
 */
function exportarDatos() {
  if (!datosGastos.meses || datosGastos.meses.length === 0) {
      alert("No hay datos para exportar");
      return;
  }

  let csv = 'Mes,Total Gastos\n';
  datosGastos.meses.forEach((mes, idx) => {
    // Negativo para indicar egreso
    csv += `${mes},-${datosGastos.totales[idx].toFixed(2)}\n`;
  });

  const blob = new Blob([csv], { type: 'text/csv' });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `gastos_mensuales_${new Date().toISOString().split('T')[0]}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.URL.revokeObjectURL(url);
}

// --- Helpers ---

function formatoMoneda(valor) {
    if (valor === undefined || valor === null) return "0.00";
    return Number(valor).toLocaleString('es-DO', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function actualizarTextoID(id, texto) {
    const el = document.getElementById(id);
    if (el) el.textContent = texto;
}
