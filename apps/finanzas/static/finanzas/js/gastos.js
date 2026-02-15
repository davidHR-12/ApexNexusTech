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

  // Limpiar preview de comprobante si existe
  // Usamos el ID del container de preview de creación
  const previewId = 'preview-comprobante-crear';
  const container = document.getElementById(previewId);
  if (container) {
        container.innerHTML = '';
        container.classList.add('hidden');
  }

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

  // CORRECCIÓN: Mostrar el infoBox
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
      // Usar la función global mostrarToast si existe
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
  // CORRECCIÓN: Apuntar al formulario de edición, no al de creación
  const form = document.getElementById('formEditarGasto');
  if (!form) {
    console.error('❌ Form "formEditarGasto" no encontrado');
    return;
  }
  
  // Configurar acción del formulario para edición
  form.action = `/administrador/gastos/editar/${id}/`;
  
  // ===== CAMPOS BÁSICOS =====
  
  // Descripción
  const descripcionInput = form.querySelector('[name="descripcion"]');
  if (descripcionInput) descripcionInput.value = data.descripcion || '';
  
  // Notas
  const notasInput = form.querySelector('[name="notas"]');
  if (notasInput) notasInput.value = data.notas || '';
  
  // Monto
  const montoInput = form.querySelector('[name="monto"]');
  if (montoInput) montoInput.value = data.monto || '';
  
  // Fecha
  const fechaInput = form.querySelector('[name="fecha"]');
  if (fechaInput) fechaInput.value = data.fecha || '';
  
  // Tipo/Categoría
  const selectTipo = form.querySelector('[name="tipo"]');
  if (selectTipo) selectTipo.value = data.tipo || '';
  
  // ===== CAMPOS EXTENDIDOS =====
  
  // Proveedor
  const proveedorInput = form.querySelector('[name="proveedor"]');
  if (proveedorInput) proveedorInput.value = data.proveedor || '';
  
  // Número de Factura
  const facturaInput = form.querySelector('[name="numero_factura"]');
  if (facturaInput) facturaInput.value = data.numero_factura || '';
  
  // Checkbox Recurrente
  const recurrenteCheckbox = form.querySelector('[name="es_recurrente"]');
  if (recurrenteCheckbox) recurrenteCheckbox.checked = data.es_recurrente || false;
  
  // Comprobante Preview (si existe)
  // Nota: data.comprobante es la URL
  if (data.comprobante) {
      mostrarPreviewExistente('preview-comprobante-editar', data.comprobante);
  } else {
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
  
  const inputMonto = form.querySelector('[name="monto"]');
  const inputFecha = form.querySelector('[name="fecha"]');
  const selectTipo = form.querySelector('[name="tipo"]');
  
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
      // Aseguramos que se envíe el valor aunque esté disabled (para visualización)
      // Nota: Realmente se maneja en el submit handler
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
  // 1. Identificar los elementos clave
  const editInfoBox = document.getElementById('edit_info_box');
  const displayInfo = document.getElementById('edit_display_info');
  const displayTipo = document.getElementById('edit_display_type');
  const notaAutomatica = document.getElementById('edit_nota_automatico');
  const btnSubmit = document.getElementById('btnSubmitEditarGasto');

  // 2. Lógica principal: ¿Es automático?
  if (data.es_automatico) {
    // --- MOSTRAR EL INFO BOX ---
    if (editInfoBox) {
      editInfoBox.classList.remove('hidden'); // Se asegura de que sea visible
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
      editInfoBox.classList.add('hidden'); // Desaparece y no ocupa espacio
    }

    if (notaAutomatica) {
      notaAutomatica.classList.add('hidden');
    }

    console.log('ℹ️ UI: Ocultando info (Gasto manual)');
  }

  // 3. Actualizar texto del botón siempre
  if (btnSubmit) {
    btnSubmit.innerText = "Guardar Cambios";
  }
}

// ============================================================================
// MANEJO DE ENVÍO DE FORMULARIOS
// ============================================================================

/**
 * Asegura que los campos readonly se envíen correctamente al servidor.
 * Los inputs readonly no se envían por defecto, así que los habilitamos justo antes de enviar.
 */
document.getElementById('formGasto')?.addEventListener('submit', function() {
  const inputMonto = this.querySelector('[name="monto"]');
  const inputFecha = this.querySelector('[name="fecha"]');
  const selectTipo = this.querySelector('[name="tipo"]');
  
  // Habilitar temporalmente campos readonly para que se envíen
  if (inputMonto?.readOnly) {
    inputMonto.readOnly = false;
  }
  if (inputFecha?.readOnly) {
    inputFecha.readOnly = false;
  }
  if (selectTipo?.disabled) {
    selectTipo.disabled = false;
  }
  
  console.log('✅ Formulario enviando...');
});

// ============================================================================
// UTILIDADES Y PREVIEW DE ARCHIVOS
// ============================================================================

/**
 * Función auxiliar para toggle de checkbox recurrente.
 */
function toggleRecurrente() {
  const checkbox = document.getElementById('es_recurrente') || document.getElementById('edit_es_recurrente');
  if (checkbox?.checked) {
    console.log('✅ Gasto recurrente habilitado');
  } else {
    console.log('⭕ Gasto recurrente deshabilitado');
  }
}

/**
 * Previsualiza el comprobante seleccionado (Imagen o PDF)
 * @param {HTMLInputElement} input - Elemento input file
 * @param {string} previewId - ID del contenedor donde mostrar la preview
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
             // Otro archivo
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
 * Muestra preview de un archivo ya existente (al editar)
 */
function mostrarPreviewExistente(previewId, urlArchivo) {
    const container = document.getElementById(previewId);
    if (!container || !urlArchivo) return;

    // Detectar tipo por extensión simple
    const esImagen = urlArchivo.match(/\.(jpeg|jpg|gif|png|webp)$/i);
    // Extraer nombre del archivo de la URL
    const nombreArchivo = urlArchivo.split('/').pop();
    
    let html = '';
    
    if (esImagen) {
        html = `
            <div class="relative group mt-2 w-full h-20 bg-gray-800 rounded-lg overflow-hidden border border-gray-700">
                <img src="${urlArchivo}" class="w-full h-full object-cover">
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
}