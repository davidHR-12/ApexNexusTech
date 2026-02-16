// ============================================================================
// GESTIÓN DE GASTOS - CREAR NUEVO
// ============================================================================

/**
 * Prepara el modal para registrar un nuevo gasto.
 * Resetea el formulario y configura los campos en modo "crear".
 */
function prepararNuevoGasto(urlCrear) {
  const form = document.getElementById('formGasto');
  if (!form) {
    console.error('❌ Form con ID "formGasto" no encontrado');
    return;
  }
  
  form.reset();
  form.action = urlCrear;

  // Limpiar preview
  const container = document.getElementById('preview-comprobante-crear');
  if (container) {
    container.innerHTML = '';
    container.classList.add('hidden');
  }

  // Resetear flag de eliminación
  const eliminarFlag = document.getElementById('eliminar_comprobante');
  if (eliminarFlag) eliminarFlag.value = 'false';

  // Establecer fecha actual
  const inputFecha = form.querySelector('[name="fecha"]');
  if (inputFecha) {
    const hoy = new Date().toISOString().split('T')[0];
    inputFecha.value = hoy;
    inputFecha.readOnly = false;
  }

  // Resetear selectores de categoría
  const selectTipo = document.getElementById('selectTipoGasto');
  if (selectTipo) {
    selectTipo.disabled = false;
  }

  // Resetear campos de monto y habilitar edición
  const inputMonto = form.querySelector('[name="monto"]');
  if (inputMonto) {
    inputMonto.readOnly = false;
    inputMonto.classList.remove('opacity-50');
  }

  // Actualizar títulos y mensajes informativos
  const infoText = document.getElementById('infoTextGasto');
  const btnSubmit = document.getElementById('btnSubmitGasto');
  
  if (infoText) infoText.innerHTML = "<b>Nota:</b> Si registras una compra desde inventario, el gasto se genera automáticamente.";
  if (btnSubmit) btnSubmit.innerText = "Confirmar";

  // Mostrar el infoBox
  const infoBox = document.getElementById('infoBoxGasto');
  if (infoBox) infoBox.classList.remove('hidden');

  // Habilitar todos los campos para crear
  const inputs = form.querySelectorAll('input, select, textarea');
  inputs.forEach(i => {
    i.readOnly = false;
    i.disabled = false;
    i.classList.remove('opacity-50');
  });

  // Mostrar modal en modo crear
  abrirModal('modalNuevoGasto');
}

// ============================================================================
// GESTIÓN DE GASTOS - EDITAR
// ============================================================================

/**
 * Abre el modal de edición cargando los datos del gasto desde la API.
 * Aplica restricciones según si el gasto es automático o manual.
 */
function abrirEditarGasto(id) {
  // Obtener datos del gasto desde la API
  fetch(`/administrador/gastos/api/${id}/`)
    .then(response => {
      if (!response.ok) throw new Error(`Error ${response.status}: ${response.statusText}`);
      return response.json();
    })
    .then(data => {
      console.log('✅ Datos del gasto cargados:', data);
      
      // Llenar campos del formulario
      rellenarFormularioGasto(id, data);
      
      // Aplicar restricciones según tipo de gasto
      aplicarRestriccionesGasto(data.es_automatico);
      
      // Actualizar UI según tipo
      actualizarUIEdicionGasto(data);
      
      // Abrir modal en modo edición
      abrirModal('modalEditarGasto');
    })
    .catch(error => {
      console.error('❌ Error al cargar gasto:', error);
      if (typeof mostrarToast === 'function') {
        mostrarToast('error', 'Error al cargar los datos del gasto');
      } else {
        alert('Error al cargar los datos del gasto');
      }
    });
}


/**
 * Rellena los campos del formulario con los datos del gasto.
 * Soporta tanto campos básicos como extendidos.
 */
function rellenarFormularioGasto(id, data) {
  // Apuntar al formulario de edición
  const form = document.getElementById('formEditarGasto');
  if (!form) {
    console.error('❌ Form "formEditarGasto" no encontrado');
    return;
  }
  
  // Configurar acción del formulario para edición
  form.action = `/administrador/gastos/editar/${id}/`;
  
  // ===== CAMPOS BÁSICOS =====
  
  // Descripción - usar ID correcto: edit_descripcion
  const descripcionInput = document.getElementById('edit_descripcion');
  if (descripcionInput) {
    descripcionInput.value = data.descripcion || '';
    console.log('✅ Descripción:', data.descripcion);
  }
  
  // Notas - usar ID correcto: edit_notas
  const notasInput = document.getElementById('edit_notas');
  if (notasInput) {
    notasInput.value = data.notas || '';
    console.log('✅ Notas:', data.notas);
  }
  
  // Monto - usar ID correcto: edit_monto
  const montoInput = document.getElementById('edit_monto');
  if (montoInput) {
    montoInput.value = data.monto || '';
    console.log('✅ Monto:', data.monto);
  }
  
  // Fecha - usar ID correcto: edit_fecha
  const fechaInput = document.getElementById('edit_fecha');
  if (fechaInput) {
    fechaInput.value = data.fecha || '';
    console.log('✅ Fecha:', data.fecha);
  }
  
  // Tipo/Categoría - usar ID correcto: edit_selectTipoGasto
  const selectTipo = document.getElementById('edit_selectTipoGasto');
  if (selectTipo) {
    selectTipo.value = data.tipo || '';
    console.log('✅ Tipo:', data.tipo);
  }
  
  // ===== CAMPOS EXTENDIDOS =====
  
  // Proveedor - usar ID correcto: edit_proveedor
  const proveedorInput = document.getElementById('edit_proveedor');
  if (proveedorInput) {
    proveedorInput.value = data.proveedor || '';
    console.log('✅ Proveedor:', data.proveedor);
  }
  
  // Número de Factura - usar ID correcto: edit_numero_factura
  const facturaInput = document.getElementById('edit_numero_factura');
  if (facturaInput) {
    facturaInput.value = data.numero_factura || '';
    console.log('✅ Número factura:', data.numero_factura);
  }
  
  // Checkbox Recurrente - usar ID correcto: edit_es_recurrente
  const recurrenteCheckbox = document.getElementById('edit_es_recurrente');
  if (recurrenteCheckbox) {
    recurrenteCheckbox.checked = data.es_recurrente || false;
    console.log('✅ Checkbox recurrente establecido a:', data.es_recurrente);
  } else {
    console.warn('⚠️ Checkbox edit_es_recurrente NO encontrado en el DOM');
  }

  // ===== COMPROBANTE PREVIEW CON OPCIÓN DE ELIMINAR =====
  const eliminarFlag = document.getElementById('edit_eliminar_comprobante');
  if (eliminarFlag) {
    eliminarFlag.value = 'false'; // Resetear flag
  }

  if (data.comprobante) {
    console.log('📎 Comprobante encontrado:', data.comprobante);
    mostrarPreviewComprobanteConEliminar('preview-comprobante-editar', data.comprobante);
  } else {
    // Limpiar preview si no hay comprobante
    const container = document.getElementById('preview-comprobante-editar');
    if (container) {
      container.innerHTML = '';
      container.classList.add('hidden');
    }
  }

  console.log('✅ Campos del formulario de edición rellenados');
}

/**
 * Aplica restricciones de edición según si el gasto es automático.
 * - Automático: bloquea monto, fecha y tipo
 * - Manual: permite editar todos los campos
 */
function aplicarRestriccionesGasto(esAutomatico) {
  const form = document.getElementById('formEditarGasto');
  if (!form) return;
  
  // Usar IDs correctos
  const inputMonto = document.getElementById('edit_monto');
  const inputFecha = document.getElementById('edit_fecha');
  const selectTipo = document.getElementById('edit_selectTipoGasto');
  
  if (esAutomatico) {
    // GASTO AUTOMÁTICO: bloquear campos críticos
    if (inputMonto) {
      inputMonto.readOnly = true;
      inputMonto.classList.add('opacity-50');
    }
    
    if (inputFecha) {
      inputFecha.readOnly = true;
      inputFecha.classList.add('opacity-50');
    }
    
    if (selectTipo) {
      selectTipo.disabled = true;
      selectTipo.classList.add('opacity-50');
    }
    
    console.log('🔒 Restricciones aplicadas: gasto automático');
  } else {
    // GASTO MANUAL: permitir edición completa
    if (inputMonto) {
      inputMonto.readOnly = false;
      inputMonto.classList.remove('opacity-50');
    }
    
    if (inputFecha) {
      inputFecha.readOnly = false;
      inputFecha.classList.remove('opacity-50');
    }
    
    if (selectTipo) {
      selectTipo.disabled = false;
      selectTipo.classList.remove('opacity-50');
    }
    
    console.log('✅ Todos los campos habilitados: gasto manual');
  }
}

/**
 * Actualiza los títulos, subtítulos e información del modal según el tipo de gasto.
 */
function actualizarUIEdicionGasto(data) {
  // Identificar los elementos clave
  const editInfoBox = document.getElementById('edit_info_box');
  const displayInfo = document.getElementById('edit_display_info');
  const displayTipo = document.getElementById('edit_display_type');
  const notaAutomatica = document.getElementById('edit_nota_automatico');
  const btnSubmit = document.getElementById('btnSubmitEditarGasto');

  // Lógica principal: ¿Es automático?
  if (data.es_automatico) {
    // --- MOSTRAR EL INFO BOX ---
    if (editInfoBox) {
      editInfoBox.classList.remove('hidden');
    }

    if (displayInfo) {
      displayInfo.innerText = 'Gasto Automático (Vinculado a Inventario)';
    }

    if (displayTipo) {
      displayTipo.innerHTML = '<span class="text-blue-400">No puedes editar Monto, Categoría o Fecha de este gasto.</span>';
    }

    if (notaAutomatica) {
      notaAutomatica.classList.remove('hidden');
    }

    console.log('ℹ️ UI: Mostrando info de gasto automático');

  } else {
    // --- OCULTAR EL INFO BOX POR COMPLETO ---
    if (editInfoBox) {
      editInfoBox.classList.add('hidden');
    }

    if (notaAutomatica) {
      notaAutomatica.classList.add('hidden');
    }

    console.log('ℹ️ UI: Ocultando info (Gasto manual)');
  }

  // Actualizar texto del botón siempre
  if (btnSubmit) {
    btnSubmit.innerText = "Guardar Cambios";
  }
}

// ============================================================================
// MANEJO DE ENVÍO DE FORMULARIOS
// ============================================================================

/**
 * Manejador unificado para el envío de formularios de gastos.
 * Habilita campos bloqueados justo antes del envío para que Django reciba los datos.
 */
function manejarEnvioGasto(e) {
    const form = e.currentTarget;
    const fields = form.querySelectorAll('[name="monto"], [name="fecha"], [name="tipo"]');
    
    fields.forEach(f => {
        f.readOnly = false;
        f.disabled = false;
    });
    
    console.log(`✅ Formulario ${form.id} preparado y enviando...`);
}

// Escuchar ambos formularios
document.getElementById('formGasto')?.addEventListener('submit', manejarEnvioGasto);
document.getElementById('formEditarGasto')?.addEventListener('submit', manejarEnvioGasto);

// ============================================================================
// UTILIDADES Y PREVIEW DE ARCHIVOS
// ============================================================================

/**
 * Función corregida para toggle de checkbox recurrente.
 */
function toggleRecurrente(element) {
  if (!element) {
    console.warn('⚠️ toggleRecurrente() llamado sin elemento');
    return;
  }
  
  const estaChecked = element.checked;
  
  if (estaChecked) {
    console.log('✅ Gasto recurrente habilitado');
  } else {
    console.log('⭕ Gasto recurrente deshabilitado');
  }
}

/**
 * Previsualiza el comprobante seleccionado (Imagen o PDF)
 */
function previsualizarComprobante(input, previewId) {
    const container = document.getElementById(previewId);
    if (!container || !input.files || !input.files[0]) return;

    const file = input.files[0];
    const reader = new FileReader();

    reader.onload = function(e) {
        let html = '';
        
        if (file.type.startsWith('image/')) {
            // Es una imagen
            html = `
                <div class="relative group mt-2 w-full h-32 bg-gray-800 rounded-lg overflow-hidden border border-gray-700">
                    <img src="${e.target.result}" class="w-full h-full object-cover">
                    <div class="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                        <p class="text-white text-xs font-bold">${file.name}</p>
                    </div>
                </div>
            `;
        } else {
             // Otro tipo de archivo
             html = `
                <div class="relative group mt-2 w-full p-3 bg-gray-800 rounded-lg border border-gray-700 flex items-center gap-3">
                    <div class="bg-blue-500/20 p-2 rounded-lg text-blue-500">
                        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
                    </div>
                    <div class="flex-1 min-w-0">
                        <p class="text-sm font-medium text-gray-200 truncate">${file.name}</p>
                    </div>
                </div>
            `;
        }

        container.innerHTML = html;
        container.classList.remove('hidden');
    }
    
    reader.readAsDataURL(file);
}

/**
 * Limpia la selección del input file y la preview
 */
function limpiarSeleccionArchivo(inputId, previewId) {
    const input = document.getElementById(inputId);
    const container = document.getElementById(previewId);
    
    if (input) input.value = '';
    
    if (container) {
        container.innerHTML = '';
        container.classList.add('hidden');
    }
}

/**
 * ✅ Muestra preview de un archivo existente CON BOTÓN DE ELIMINAR usando SweetAlert2
 * @param {string} previewId - ID del contenedor de preview
 * @param {string} urlArchivo - URL del archivo existente
 */
function mostrarPreviewComprobanteConEliminar(previewId, urlArchivo) {
    const container = document.getElementById(previewId);
    if (!container || !urlArchivo) {
      console.warn('⚠️ No se puede mostrar preview: container o URL faltando', { previewId, urlArchivo });
      return;
    }

    // Detectar tipo por extensión
    const esImagen = urlArchivo.match(/\.(jpeg|jpg|gif|png|webp)$/i);
    const nombreArchivo = urlArchivo.split('/').pop();
    
    let html = '';
    
    if (esImagen) {
        html = `
            <div class="relative group mt-2 w-full bg-gray-800 rounded-lg overflow-hidden border border-gray-700">
                <img src="${urlArchivo}" class="w-full h-24 object-cover" onerror="console.error('Error cargando imagen:', this.src)">
                <div class="absolute inset-0 bg-black/70 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                    <a href="${urlArchivo}" target="_blank" 
                       class="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs rounded-lg font-bold transition-colors">
                        Ver
                    </a>
                    <button type="button" 
                            onclick="confirmarEliminarComprobante()"
                            class="px-3 py-1.5 bg-red-600 hover:bg-red-500 text-white text-xs rounded-lg font-bold transition-colors">
                        Eliminar
                    </button>
                </div>
            </div>
            <p class="text-[10px] text-gray-500 mt-1 italic">Archivo actual • Pasa el cursor para ver opciones</p>
        `;
    } else {
         html = `
            <div class="relative group mt-2 w-full p-3 bg-gray-800 rounded-lg border border-gray-700">
                <div class="flex items-center gap-3">
                    <div class="bg-blue-500/20 p-2 rounded-lg text-blue-500">
                        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z">
                            </path>
                        </svg>
                    </div>
                    <div class="flex-1 min-w-0">
                        <a href="${urlArchivo}" target="_blank" 
                           class="text-sm font-medium text-blue-400 hover:text-blue-300 truncate underline block">
                            ${nombreArchivo}
                        </a>
                    </div>
                    <button type="button" 
                            onclick="confirmarEliminarComprobante()"
                            class="px-3 py-1.5 bg-red-600 hover:bg-red-500 text-white text-xs rounded-lg font-bold transition-colors">
                        Eliminar
                    </button>
                </div>
            </div>
            <p class="text-[10px] text-gray-500 mt-1 italic">Archivo actual</p>
        `;
    }

    container.innerHTML = html;
    container.classList.remove('hidden');
    console.log('✅ Preview del comprobante mostrado con opción de eliminar:', nombreArchivo);
}

/**
 * ✅ Confirma y ejecuta eliminación de comprobante usando SweetAlert2 (estilo productos.js)
 */
function confirmarEliminarComprobante() {
    // Configuración base de SweetAlert2 (igual que productos.js)
    const swalConfigBase = {
        background: '#1e293b',
        color: '#fff',
        showCancelButton: true,
        reverseButtons: true,
        buttonsStyling: false,
        showClass: { popup: '', backdrop: '' },
        hideClass: { popup: '', backdrop: '' },
        backdrop: 'rgba(0, 0, 0, 0.5)',
        didOpen: () => {
            const container = Swal.getContainer();
            if (container) container.style.backdropFilter = 'blur(4px)';
        }
    };

    const swalCustomClasses = {
        popup: 'bg-[#1e293b] border border-gray-800 rounded-2xl shadow-2xl',
        title: 'text-xl font-bold text-white',
        htmlContainer: 'text-gray-300',
        confirmButton: 'bg-red-600 hover:bg-red-700 text-white font-bold text-xs uppercase px-6 py-3 rounded-xl transition-colors mx-2',
        cancelButton: 'bg-slate-700 hover:bg-slate-600 text-white font-bold text-xs uppercase px-6 py-3 rounded-xl transition-colors mx-2',
        actions: 'pb-4'
    };

    // Icono personalizado (estilo productos.js)
    const iconoEliminar = `
        <div class="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-red-500/10">
            <svg class="h-6 w-6 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
        </div>
    `;

    Swal.fire({
        ...swalConfigBase,
        title: '¿QUITAR COMPROBANTE?',
        html: '<p class="text-gray-400 text-sm">El archivo se eliminará permanentemente al guardar los cambios.</p>',
        iconHtml: iconoEliminar,
        confirmButtonText: 'SÍ, ELIMINAR',
        cancelButtonText: 'CANCELAR',
        showCloseButton: true,
        customClass: {
            ...swalCustomClasses,
            icon: 'border-0'
        }
    }).then((result) => {
        if (result.isConfirmed) {
            ejecutarEliminacionComprobante();
        }
    });
}

/**
 * ✅ Ejecuta la eliminación marcando el flag y mostrando mensaje visual
 */
function ejecutarEliminacionComprobante() {
    const eliminarFlag = document.getElementById('edit_eliminar_comprobante');
    const container = document.getElementById('preview-comprobante-editar');
    const inputFile = document.getElementById('edit_comprobante');

    // Marcar flag de eliminación
    if (eliminarFlag) {
        eliminarFlag.value = 'true';
        console.log('✅ Flag de eliminación activado');
    }

    // Mostrar mensaje visual de advertencia
    if (container) {
        container.innerHTML = `
            <div class="mt-2 p-3 bg-orange-500/10 border border-orange-500/20 rounded-lg">
                <p class="text-orange-400 text-xs font-bold flex items-center gap-2">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                    El comprobante se eliminará al guardar los cambios
                </p>
            </div>
        `;
        container.classList.remove('hidden');
    }

    // Resetear input file por si tenía algo seleccionado
    if (inputFile) {
        inputFile.value = '';
    }

    // Toast de confirmación
    if (typeof mostrarToast === 'function') {
        mostrarToast('success', 'Comprobante marcado para eliminar');
    }

    console.log('🗑️ Comprobante marcado para eliminar');
}

/**
 * ✅ LEGACY: Mantener para compatibilidad con código existente
 * Función original sin botón de eliminar (usada en creación y gasto_detalle.html)
 */
function mostrarPreviewExistente(previewId, urlArchivo) {
    const container = document.getElementById(previewId);
    if (!container || !urlArchivo) {
      console.warn('⚠️ No se puede mostrar preview: container o URL faltando', { previewId, urlArchivo });
      return;
    }

    const esImagen = urlArchivo.match(/\.(jpeg|jpg|gif|png|webp)$/i);
    const nombreArchivo = urlArchivo.split('/').pop();
    
    let html = '';
    
    if (esImagen) {
        html = `
            <div class="relative group mt-2 w-full h-20 bg-gray-800 rounded-lg overflow-hidden border border-gray-700">
                <img src="${urlArchivo}" class="w-full h-full object-cover" onerror="console.error('Error cargando imagen:', this.src)">
                <div class="absolute inset-0 bg-black/50 flex items-center justify-center">
                    <a href="${urlArchivo}" target="_blank" class="text-white text-xs underline hover:text-blue-300">Ver original</a>
                </div>
            </div>
            <p class="text-[10px] text-gray-500 mt-1 italic">Archivo actual</p>
        `;
    } else {
         html = `
            <div class="relative group mt-2 w-full p-3 bg-gray-800 rounded-lg border border-gray-700 flex items-center gap-3">
                <div class="bg-blue-500/20 p-2 rounded-lg text-blue-500">
                    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
                </div>
                <div class="flex-1 min-w-0">
                    <a href="${urlArchivo}" target="_blank" class="text-sm font-medium text-blue-400 hover:text-blue-300 truncate underline">${nombreArchivo}</a>
                </div>
            </div>
            <p class="text-[10px] text-gray-500 mt-1 italic">Archivo actual</p>
        `;
    }

    container.innerHTML = html;
    container.classList.remove('hidden');
    console.log('✅ Preview del comprobante mostrado:', nombreArchivo);
}