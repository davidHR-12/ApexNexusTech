/**
 * Dashboard de Finanzas — Gastos
 */

let chartGastosMes     = null;
let chartGastosPorTipo = null;
let datosGastos        = {};

document.addEventListener("DOMContentLoaded", () => {
  cargarDatos();
  registrarFiltros();
});

// ════════════════════════════════════════════════════════
// CARGA INICIAL
// ════════════════════════════════════════════════════════
async function cargarDatos() {
  const container = document.querySelector("[data-url-gastos]");
  if (!container) return;

  try {
    const response = await fetch(container.dataset.urlGastos);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    datosGastos = await response.json();

    calcularKPIs();
    actualizarGraficoLinea();
    renderizarGraficoPastel();
    llenarTabla();
    llenarResumenTipo();
  } catch (error) {
    console.error("Error cargando datos:", error);
    mostrarError("No se pudieron cargar los datos del dashboard.");
  }
}

// ════════════════════════════════════════════════════════
// FILTROS (listeners separados del HTML)
// ════════════════════════════════════════════════════════
function registrarFiltros() {
  const chkTodos   = document.getElementById("filterTodos");
  const selTipo    = document.getElementById("filterTipo");

  chkTodos?.addEventListener("change", () => {
    if (chkTodos.checked) selTipo.value = "";
    actualizarGraficoLinea();
  });

  selTipo?.addEventListener("change", () => {
    if (selTipo.value) chkTodos.checked = false;
    else chkTodos.checked = true;
    actualizarGraficoLinea();
  });
}

// ════════════════════════════════════════════════════════
// KPIs
// ════════════════════════════════════════════════════════
function calcularKPIs() {
  const { meses, totales } = datosGastos;
  if (!totales || totales.length === 0) return;

  const totalGastos = totales.reduce((a, b) => a + b, 0);
  const promedio    = totalGastos / totales.length;

  // Índice real del mes con mayor gasto (evita bug con indexOf en duplicados)
  let mayorIndex = 0;
  totales.forEach((v, i) => { if (v > totales[mayorIndex]) mayorIndex = i; });

  setText("kpiTotalGastos",    `-RD$ ${fmt(totalGastos)}`);
  setText("kpiCountGastos",    `${totales.length} meses`);
  setText("kpiPromedioDiario", `-RD$ ${fmt(promedio)}`);
  setText("kpiMesesData",      meses.length);
  setText("kpiMayorMes",       `-RD$ ${fmt(totales[mayorIndex])}`);
  setText("kpiMayorMesNombre", formatMes(meses[mayorIndex]));
}

// ════════════════════════════════════════════════════════
// GRÁFICO DE LÍNEA
// ════════════════════════════════════════════════════════
function actualizarGraficoLinea() {
  if (!datosGastos.meses) return;   // datos aún no cargados

  const selTipo  = document.getElementById("filterTipo");
  const chkTodos = document.getElementById("filterTodos");
  const tipo     = selTipo?.value || "";

  let datos;
  if (!tipo || chkTodos?.checked) {
    datos = datosGastos.totales;
  } else {
    datos = datosGastos.meses.map(mes =>
      datosGastos.por_tipo?.[tipo]?.[mes] ?? 0
    );
  }

  const canvas = document.getElementById("chartGastosMes");
  if (!canvas) return;

  const sinDatos = !datos || datos.every(v => v === 0);
  mostrarMensajeSinDatos("chartGastosMes", sinDatos);

  if (chartGastosMes) chartGastosMes.destroy();
  if (sinDatos) return;

  chartGastosMes = new Chart(canvas.getContext("2d"), {
    type: "line",
    data: {
      labels: datosGastos.meses.map(formatMes),
      datasets: [{
        label: "Gastos RD$",
        data: datos,
        borderColor: "#ef4444",
        backgroundColor: "rgba(239,68,68,0.1)",
        tension: 0.4,
        fill: true,
        pointRadius: 4,
        pointBackgroundColor: "#ef4444",
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: { label: ctx => `-RD$ ${fmt(ctx.parsed.y)}` },
        },
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: { color: "#9ca3af", callback: v => "-RD$ " + fmt(v) },
          grid:  { color: "rgba(255,255,255,0.05)" },
        },
        x: {
          ticks: { color: "#9ca3af" },
          grid:  { display: false },
        },
      },
    },
  });
}

// ════════════════════════════════════════════════════════
// GRÁFICO DE PASTEL
// ════════════════════════════════════════════════════════
function renderizarGraficoPastel() {
  const canvas = document.getElementById("chartGastosPorTipo");
  if (!canvas) return;

  const COLORES = ["#6b7280","#eab308","#3b82f6","#f97316","#a855f7","#6366f1"];
  const labels  = [];
  const valores  = [];

  Object.entries(datosGastos.por_tipo || {}).forEach(([tipo, meses]) => {
    const total = Object.values(meses).reduce((a, b) => a + b, 0);
    if (total > 0) {
      labels.push(tipo.replace("_", " "));
      valores.push(total);
    }
  });

  const sinDatos = valores.length === 0;
  mostrarMensajeSinDatos("chartGastosPorTipo", sinDatos);

  if (chartGastosPorTipo) chartGastosPorTipo.destroy();
  if (sinDatos) return;

  chartGastosPorTipo = new Chart(canvas.getContext("2d"), {
    type: "doughnut",
    data: {
      labels,
      datasets: [{
        data: valores,
        backgroundColor: COLORES.slice(0, valores.length),
        borderWidth: 0,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: "bottom", labels: { color: "#d1d5db" } },
        tooltip: {
          callbacks: { label: ctx => `-RD$ ${fmt(ctx.parsed)}` },
        },
      },
      cutout: "70%",
    },
  });
}

// ════════════════════════════════════════════════════════
// TABLA POR MES
// ════════════════════════════════════════════════════════
function llenarTabla() {
  const tbody = document.getElementById("tablaMesesBody");
  if (!tbody) return;

  const { meses, totales } = datosGastos;

  if (!meses || meses.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="4" class="p-8 text-center text-gray-500 italic">
          No se han registrado gastos en el periodo seleccionado.
        </td>
      </tr>`;
    return;
  }

  const totalGeneral = totales.reduce((a, b) => a + b, 0);

  tbody.innerHTML = meses.map((mes, idx) => {
    const monto      = totales[idx];
    const porcentaje = totalGeneral > 0 ? ((monto / totalGeneral) * 100).toFixed(1) : "0.0";

    let variacionHTML = '<span class="text-gray-500">—</span>';
    if (idx > 0 && totales[idx - 1] !== 0) {
      const pct     = ((monto - totales[idx - 1]) / totales[idx - 1]) * 100;
      const simbolo = pct > 0 ? "↑" : pct < 0 ? "↓" : "→";
      const color   = pct > 0 ? "text-red-400" : pct < 0 ? "text-green-400" : "text-gray-400";
      variacionHTML = `<span class="${color} font-bold text-xs">${simbolo} ${Math.abs(pct).toFixed(1)}%</span>`;
    }

    return `
      <tr class="hover:bg-gray-800/40 transition-colors border-b border-gray-800/50 last:border-0">
        <td class="p-4 text-gray-300 font-medium">${formatMes(mes)}</td>
        <td class="p-4 text-right font-mono text-white">-RD$ ${fmt(monto)}</td>
        <td class="p-4 text-right text-gray-400 text-sm">${porcentaje}%</td>
        <td class="p-4 text-right">${variacionHTML}</td>
      </tr>`;
  }).join("");
}

// ════════════════════════════════════════════════════════
// RESUMEN POR TIPO
// ════════════════════════════════════════════════════════
function llenarResumenTipo() {
  const resumen = document.getElementById("resumenPorTipo");
  if (!resumen) return;

  const TIPOS = [
    { key: "Mantenimiento",   label: "Mantenimiento",   color: "#6b7280" },
    { key: "Energia",         label: "Energía",         color: "#eab308" },
    { key: "Compra_Material", label: "Compra Material", color: "#3b82f6" },
    { key: "Herramientas",    label: "Herramientas",    color: "#f97316" },
    { key: "Servicios",       label: "Servicios",       color: "#a855f7" },
    { key: "Otro",            label: "Otro",            color: "#6366f1" },
  ];

  resumen.innerHTML = TIPOS.map(({ key, label, color }) => {
    const totalTipo = Object.values(datosGastos.por_tipo?.[key] || {})
      .reduce((a, b) => a + parseFloat(b), 0);

    return `
      <div class="flex items-center justify-between p-3 bg-gray-800/40 rounded-xl border border-gray-700/30 hover:bg-gray-800/60 transition-colors">
        <div class="flex items-center gap-3">
          <div class="w-2.5 h-2.5 rounded-full" style="background-color:${color}"></div>
          <span class="text-gray-300 text-sm font-medium">${label}</span>
        </div>
        <span class="text-white font-mono text-sm font-bold">-RD$ ${fmt(totalTipo)}</span>
      </div>`;
  }).join("");
}

// ════════════════════════════════════════════════════════
// HELPERS
// ════════════════════════════════════════════════════════

/** Formatea número como moneda dominicana */
function fmt(valor) {
  if (valor == null) return "0.00";
  return Number(valor).toLocaleString("es-DO", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

/** Convierte "2024-01" → "Ene. 2024" */
function formatMes(mesStr) {
  if (!mesStr) return mesStr;
  const [year, month] = mesStr.split("-");
  return new Date(year, month - 1).toLocaleString("es-DO", {
    month: "short",
    year:  "numeric",
  });
}

function setText(id, texto) {
  const el = document.getElementById(id);
  if (el) el.textContent = texto;
}

function mostrarError(msg) {
  // Reutiliza SweetAlert2 si está disponible, si no usa alert
  if (typeof Swal !== "undefined") {
    Swal.fire({ icon: "error", title: "Error", text: msg, background: "#1e293b", color: "#fff" });
  } else {
    alert(msg);
  }
}

/** Muestra u oculta overlay "sin datos" sobre un canvas */
function mostrarMensajeSinDatos(canvasId, mostrar) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;

  const container = canvas.parentElement;
  let msgDiv = container.querySelector(".no-data-message");

  if (mostrar) {
    canvas.style.opacity = "0.1";
    if (!msgDiv) {
      msgDiv = document.createElement("div");
      msgDiv.className = "no-data-message absolute inset-0 flex flex-col items-center justify-center bg-gray-900/40 backdrop-blur-sm rounded-xl z-10";
      msgDiv.innerHTML = `
        <div class="text-gray-500 flex flex-col items-center">
          <svg class="w-12 h-12 mb-2 opacity-20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
          </svg>
          <span class="text-sm font-medium uppercase tracking-widest opacity-50">Sin datos disponibles</span>
        </div>`;
      container.appendChild(msgDiv);
    }
  } else {
    canvas.style.opacity = "1";
    msgDiv?.remove();
  }
}