/**
 * Logica para el Dashboard de Finanzas
 */

let chartGastosMes = null;
let chartGastosPorTipo = null;
let datosGastos = {};

document.addEventListener('DOMContentLoaded', cargarDatos);

async function cargarDatos() {
  try {
    const container = document.querySelector('[data-url-gastos]');
    if (!container) return;
    
    const url = container.dataset.urlGastos;
    const response = await fetch(url);
    datosGastos = await response.json();
    
    calcularKPIs();
    actualizarGrafico(); // Esto dibuja la línea
    renderizarGraficoPastel(); // Añadido: Dibuja el pastel al cargar
    llenarTabla();
    llenarResumenTipo();
    
  } catch (error) {
    console.error('Error cargando datos:', error);
    alert('Error al cargar los datos de gastos');
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
 * Lógica de Filtrado
 */
function actualizarGrafico() {
  const filterTipo = document.getElementById('filterTipo').value;
  const filterTodos = document.getElementById('filterTodos');
  
  if (filterTipo) filterTodos.checked = false;

  let datosParaGrafica = [];

  if (filterTodos.checked || !filterTipo) {
    datosParaGrafica = datosGastos.totales;
  } else {
    datosParaGrafica = datosGastos.meses.map(mes => {
        return (datosGastos.por_tipo[filterTipo] && datosGastos.por_tipo[filterTipo][mes]) 
               ? datosGastos.por_tipo[filterTipo][mes] : 0;
    });
  }

  // CORRECCIÓN: Aquí debe llamar a la función de LINEA, no la de pastel
  renderizarGraficoLinea(datosGastos.meses, datosParaGrafica);
}

/**
 * Gráfico de Línea (Tendencia Mensual) - ¡ESTA FALTABA!
 */
function renderizarGraficoLinea(meses, datos) {
  const canvas = document.getElementById('chartGastosMes');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');

  if (chartGastosMes) chartGastosMes.destroy();

  chartGastosMes = new Chart(ctx, {
    type: 'line',
    data: {
      labels: meses.map(m => {
        // Formatear mes para que se vea mejor (Ej: "Jan 24")
        const [year, month] = m.split('-');
        return new Date(year, month - 1).toLocaleString('es-DO', { month: 'short', year: '2-digit' });
      }),
      datasets: [{
        label: 'Gastos RD$',
        data: datos,
        borderColor: '#ef4444', // Rojo
        backgroundColor: 'rgba(239, 68, 68, 0.1)',
        tension: 0.4,
        fill: true,
        pointRadius: 4,
        pointBackgroundColor: '#ef4444'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (context) => `RD$ ${formatoMoneda(context.parsed.y)}`
          }
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: { color: '#9ca3af', callback: v => 'RD$ ' + formatoMoneda(v) },
          grid: { color: 'rgba(255, 255, 255, 0.05)' }
        },
        x: {
          ticks: { color: '#9ca3af' },
          grid: { display: false }
        }
      }
    }
  });
}

/**
 * Gráfico de Pastel (Categorías)
 */
function renderizarGraficoPastel() {
    const canvas = document.getElementById('chartGastosPorTipo');
    if (!canvas) return;

    const labels = [];
    const valores = [];
    const colores = ['#6b7280', '#eab308', '#3b82f6', '#f97316', '#a855f7', '#6366f1'];

    Object.keys(datosGastos.por_tipo).forEach(tipo => {
        const total = Object.values(datosGastos.por_tipo[tipo]).reduce((a, b) => a + b, 0);
        if (total > 0) {
            labels.push(tipo.replace('_', ' '));
            valores.push(total);
        }
    });

    const tieneDatos = valores.length > 0;
    mostrarMensajeSinDatos('chartGastosPorTipo', !tieneDatos);

    if (!tieneDatos) {
        if (chartGastosPorTipo) chartGastosPorTipo.destroy();
        return;
    }
    
    if (chartGastosPorTipo) chartGastosPorTipo.destroy();
    chartGastosPorTipo = new Chart(canvas.getContext('2d'), {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{ data: valores, backgroundColor: colores, borderWidth: 0 }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { position: 'bottom', labels: { color: '#d1d5db' } } },
            cutout: '70%'
        }
    });
}

/**
 * Llenar tabla de desglose por mes
 */
function llenarTabla() {
  const tbody = document.getElementById('tablaMesesBody');
  if (!tbody) return;


  if (!datosGastos.meses || datosGastos.meses.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="4" class="p-8 text-center text-gray-500 italic">
                    No se han registrado gastos en el periodo seleccionado.
                </td>
            </tr>
        `;
        return;
    }
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

/**
 * Helper para mostrar mensaje cuando no hay datos en los gráficos
 */
function mostrarMensajeSinDatos(canvasId, mostrar) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;

    const container = canvas.parentElement;
    let msgDiv = container.querySelector('.no-data-message');

    if (mostrar) {
        if (!msgDiv) {
            msgDiv = document.createElement('div');
            msgDiv.className = 'no-data-message absolute inset-0 flex flex-col items-center justify-center bg-gray-900/40 backdrop-blur-sm rounded-xl z-10 transition-all';
            msgDiv.innerHTML = `
                <div class="text-gray-500 flex flex-col items-center">
                    <svg class="w-12 h-12 mb-2 opacity-20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <span class="text-sm font-medium uppercase tracking-widest opacity-50">No hay datos disponibles</span>
                </div>
            `;
            container.appendChild(msgDiv);
        }
        canvas.style.opacity = '0.1'; // Atenuamos el gráfico si existe
    } else {
        if (msgDiv) msgDiv.remove();
        canvas.style.opacity = '1';
    }
}