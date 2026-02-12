// ============================================================================
// GESTIÓN DE COLORES
// ============================================================================

// Sincronizar el input type="color" con el div de previsualización
document.addEventListener('input', function(e) {
    if (e.target && e.target.name === 'color_hex') {
        console.log('🎨 Color cambiado:', e.target.value);
        
        // Para el modal de CREAR
        const previewCrear = document.getElementById('color-preview');
        if (previewCrear) {
            previewCrear.style.backgroundColor = e.target.value;
            console.log('✅ Preview actualizado (crear)');
        }
        
        // Para el modal de EDITAR
        const previewEditar = document.getElementById('edit_color_preview');
        if (previewEditar) {
            previewEditar.style.backgroundColor = e.target.value;
            console.log('✅ Preview actualizado (editar)');
        }
    }
});

// Función para cuando el usuario selecciona un color del autocompletado (AJAX)
function seleccionarColor(nombre, hex) {
    const inputNombre = document.getElementById('input-color');
    const inputHex = document.getElementById('input-color-hex');
    const preview = document.getElementById('color-preview');

    // 1. Asignar el nombre al campo de texto
    if (inputNombre) inputNombre.value = nombre;

    // 2. Asignar el valor HEX al input color y disparar el evento input
    if (inputHex) {
        inputHex.value = hex;
        inputHex.disabled = true; 
        inputHex.parentElement.classList.add('pointer-events-none', 'opacity-70');
        // Importante: forzamos el evento 'input' para que otros listeners (como el de previsualización) reaccionen
        inputHex.dispatchEvent(new Event('input', { bubbles: true }));
    }
    if (preview) {
        preview.style.backgroundColor = hex;
        preview.classList.add('ring-2', 'ring-blue-500');
        // Cambiamos el icono a un candado
        preview.innerHTML = `
            <svg class="w-4 h-4 text-white mix-blend-difference" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clip-rule="evenodd" />
            </svg>`;
    }
    
    // 3. Limpiar los resultados
    const results = document.getElementById('results-color');
    if (results) results.innerHTML = '';

    // 4. Salto de foco al costo
    const costoInput = document.querySelector('input[name="costo_por_gramo"]');
    if (costoInput) costoInput.focus();
}

// Si el usuario empieza a escribir manualmente, desbloqueamos y reseteamos
document.getElementById('input-color')?.addEventListener('input', function() {
    const inputHex = document.getElementById('input-color-hex');
    const preview = document.getElementById('color-preview');
    
    if (inputHex && inputHex.disabled) {
        inputHex.disabled = false;
        inputHex.parentElement.classList.remove('pointer-events-none', 'opacity-70');
        inputHex.value = "#10b981";
        
        if (preview) {
            preview.style.backgroundColor = "#10b981";
            preview.classList.remove('ring-2', 'ring-blue-500');
            // Restaurar icono original del gotero
            preview.innerHTML = `
                <svg class="w-4 h-4 text-white mix-blend-difference opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.172-1.172a4 4 0 115.656 5.656L10 17.657" />
                </svg>`;
        }
    }
});

// Función para: "negro mate" -> "Negro mate"
function aplicarCapitalize(text) {
    if (!text) return "";
    // Solo capitalizamos la primera letra del string total
    return text.charAt(0).toUpperCase() + text.slice(1).toLowerCase();
}

// 1. Lógica para MARCA y COLOR (Primera letra Mayúscula)
['input-marca', 'input-color'].forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;

    el.addEventListener('input', function(e) {
        const start = this.selectionStart; // Guardar posición del cursor
        this.value = aplicarCapitalize(this.value);
        this.setSelectionRange(start, start); // Restaurar posición del cursor
    });
});

// 2. Lógica para TIPO (Todo Mayúsculas: PLA, PETG)
const inputTipo = document.getElementById('input-tipo');
if (inputTipo) {
    inputTipo.addEventListener('input', function(e) {
        const start = this.selectionStart;
        this.value = this.value.toUpperCase();
        this.setSelectionRange(start, start);
    });
}
// Asegurar que los datos bloqueados se envíen al servidor
document.getElementById('formCrearMaterial')?.addEventListener('submit', function() {
    const inputHex = document.getElementById('input-color-hex');
    if (inputHex) {
        inputHex.disabled = false; // Lo habilitamos justo al enviar
    }
});
// ============================================================================
// EDITAR MATERIAL
// ============================================================================

function abrirEditar(id) {
    const url = `/administrador/api/materiales/${id}/`;

    fetch(url)
        .then(r => r.json())
        .then(data => {
            console.log('📦 Datos del material:', data);
            
            const costo = document.getElementById('edit_costo');
            const stock = document.getElementById('edit_stock_minimo');
            const nombre = document.getElementById('edit_display_full_name');
            const tipo = document.getElementById('edit_display_tipo');
            const form = document.getElementById('formEditarMaterial');

            const colorNombreSpan = document.getElementById('edit_display_color_nombre');
            const inputHex = document.getElementById('edit_color_hex_input');
            const preview = document.getElementById('edit_color_preview');

            // Llenar campos numéricos
            if (costo) costo.value = data.costo_por_gramo;
            if (stock) stock.value = data.stock_minimo;

            // Llenar textos de visualización
            if (nombre) nombre.innerText = data.nombre || '';
            if (tipo) tipo.innerText = data.tipo || '';

            if (colorNombreSpan) {
                // 'color_nombre' debe venir en tu respuesta JSON de la API
                colorNombreSpan.innerText = `"${data.color_nombre || 'Color sin asignar'}"`;
            }
            // ✅ ASIGNAR EL COLOR
            if (inputHex && data.color_hex) {
                inputHex.value = data.color_hex;
                console.log('🎨 Color hex asignado al input:', data.color_hex);
            }
            if (preview && data.color_hex) {
                preview.style.backgroundColor = data.color_hex;
                console.log('✅ Preview actualizado con color:', data.color_hex);
            }

            // Actualizar Action del Formulario
            if (form) {
                form.action = `/administrador/materiales/${id}/editar/`;
                console.log('📝 Form action actualizado:', form.action);
            }

            // Resetear el checkbox de pérdida al abrir (por seguridad UX)
            const checkPerdida = document.getElementById('checkPerdida');
            const seccionPerdida = document.getElementById('seccionPerdida');
            if (checkPerdida) {
                checkPerdida.checked = false;
                if (seccionPerdida) seccionPerdida.classList.add('hidden');
            }

            abrirModal('modalEditarMaterial');
        })
        .catch(err => console.error("❌ Error al obtener material:", err));
}

function togglePerdida() {
    const section = document.getElementById('seccionPerdida');
    const check = document.getElementById('checkPerdida');
    if (section && check) {
        section.classList.toggle('hidden', !check.checked);
    }
}

// ============================================================================
// SELECCIÓN DE MATERIALES Y ATRIBUTOS
// ============================================================================

function seleccionarMaterial(id, textoCompleto) {
    const inputBusqueda = document.getElementById('material-search-input');
    if (inputBusqueda) inputBusqueda.value = textoCompleto;

    const inputHidden = document.getElementById('material-id-hidden');
    if (inputHidden) inputHidden.value = id;

    const resultados = document.getElementById('search-results');
    if (resultados) resultados.innerHTML = '';

    const proximoInput = document.querySelector('input[name="cantidad_gramos"]');
    if (proximoInput) proximoInput.focus();
}

function seleccionarAtributo(tipo, nombre) {
    const input = document.getElementById(`input-${tipo}`);
    if (input) {
        input.value = nombre;
        input.dispatchEvent(new Event('htmx:abort'));
    }

    const resContainer = document.getElementById(`results-${tipo}`);
    if (resContainer) resContainer.innerHTML = '';

    // Salto de foco inteligente
    if (tipo === 'marca') {
        document.getElementById('input-tipo').focus();
    } else if (tipo === 'tipo') {
        document.getElementById('input-color').focus();
    } else if (tipo === 'color') {
        const costoInput = document.querySelector('input[name="costo_por_gramo"]');
        if (costoInput) costoInput.focus();
    }
}

// Cerrar resultados al hacer clic fuera
document.addEventListener('click', function (event) {
    const contenedores = ['results-marca', 'results-tipo', 'results-color', 'search-results'];

    contenedores.forEach(id => {
        const resContainer = document.getElementById(id);
        const inputContainer = document.getElementById(`input-${id.split('-')[1]}`);

        if (resContainer && !resContainer.contains(event.target) && event.target !== inputContainer) {
            resContainer.innerHTML = '';
        }
    });
});

// ============================================================================
// ELIMINACIÓN
// ============================================================================

function confirmarEliminarMaterial(id, nombre) {
    Swal.fire({
        ...swalConfigBase,
        title: 'Eliminar Material',
        html: `
            <div class="text-center">
                <p class="text-gray-300 mb-2">Estás por eliminar:</p>
                <p class="text-white font-semibold text-lg">${nombre}</p>
                <p class="text-gray-400 text-sm mt-3 border-t border-gray-700/50 pt-3">Si tiene historial, no se eliminara, en cambio se desactivará automáticamente.</p>
            </div>`,
        iconHtml: swalIcons.warningRed,
        confirmButtonText: 'Sí, Eliminar',
        cancelButtonText: 'Cancelar',
        showCloseButton: true,
        customClass: {
            ...swalCustomClasses,
            icon: 'border-0'
        }
    }).then((result) => {
        if (!result.isConfirmed) return;

        fetch(`/administrador/materiales/${id}/eliminar/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
                'Content-Type': 'application/json'
            }
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    mostrarToast('success', data.message);
                    setTimeout(() => location.reload(), 1000);
                } else {
                    Swal.close();
                    mostrarToast('error', data.message || 'Error al eliminar el material');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                Swal.close();
                mostrarToast('error', 'Error al procesar la solicitud');
            });
    });
}

function confirmarEliminarAtributo(tipo, id, nombre) {
    Swal.fire({
        ...swalConfigBase,
        title: '¿Eliminar Atributo?',
        html: `<p class="text-gray-300">¿Estás seguro de eliminar <b>${nombre}</b> de la lista de ${tipo}?</p>
               <p class="text-red-400 text-[10px] mt-2 font-bold uppercase">Esta acción no se puede deshacer</p>`,
        iconHtml: swalIcons.warningRed,
        confirmButtonText: 'Sí, Eliminar',
        cancelButtonText: 'Cancelar',
        showCloseButton: true,
        customClass: {
            ...swalCustomClasses,
            icon: 'border-0'
        }
    }).then((result) => {
        if (result.isConfirmed) {
            fetch(`/administrador/materiales/atributos/${tipo}/${id}/eliminar/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
                    'Content-Type': 'application/json'
                }
            })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        mostrarToast('success', data.message);
                        cerrarModales();
                        setTimeout(() => location.reload(), 800);
                    } else {
                        Swal.fire({
                            ...swalConfigBase,
                            title: 'No se puede eliminar',
                            text: data.message,
                            iconHtml: swalIcons.warningRed,
                            confirmButtonText: 'Entendido',
                            showCloseButton: true,
                            showCancelButton: false,
                            customClass: {
                                ...swalCustomClasses,
                                icon: 'border-0'
                            }
                        });
                    }
                })
                .catch(error => mostrarToast('error', 'Error en la solicitud'));
        }
    });
}

// ============================================================================
// TABS
// ============================================================================

function cambiarTab(event, tabId) {
    document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));

    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('bg-emerald-600', 'text-white');
        btn.classList.add('text-gray-500', 'hover:text-gray-300');
    });

    document.getElementById(tabId).classList.remove('hidden');

    const activo = event.currentTarget;
    activo.classList.remove('text-gray-500', 'hover:text-gray-300');
    activo.classList.add('bg-emerald-600', 'text-white');
}

// ============================================================================
// NAVEGACIÓN CON TECLADO
// ============================================================================

if (typeof window.MaterialesHandlers === 'undefined') {
    window.MaterialesHandlers = {
        keydown: function (e) {
            const target = e.target;
            if (target.tagName === 'INPUT' && target.hasAttribute('hx-target')) {

                if (['ArrowUp', 'ArrowDown', 'Enter', 'Tab'].includes(e.key)) {
                    if (e.key !== 'Tab') e.stopPropagation();
                }

                const selector = target.getAttribute('hx-target');
                const container = document.querySelector(selector);
                if (!container) return;

                const items = container.querySelectorAll('.resultado-item');
                if (items.length === 0) return;

                let currentIndex = Array.from(items).findIndex(item => item.classList.contains('item-active'));

                if (e.key === 'ArrowDown') {
                    e.preventDefault();
                    currentIndex = (currentIndex + 1 < items.length) ? currentIndex + 1 : 0;
                    window.MaterialesHandlers.actualizarSeleccion(items, currentIndex);
                }
                else if (e.key === 'ArrowUp') {
                    e.preventDefault();
                    currentIndex = (currentIndex <= 0) ? items.length - 1 : currentIndex - 1;
                    window.MaterialesHandlers.actualizarSeleccion(items, currentIndex);
                }
                else if (e.key === 'Enter' || e.key === 'Tab') {
                    if (currentIndex >= 0) {
                        e.preventDefault();
                        items[currentIndex].click();
                    }
                }
            }
        },
        actualizarSeleccion: function (items, index) {
            items.forEach(item => {
                item.classList.remove('item-active');
                item.style.backgroundColor = "";
            });

            const activeItem = items[index];
            if (activeItem) {
                activeItem.classList.add('item-active');
                activeItem.style.backgroundColor = "rgba(37, 99, 235, 0.4)";
                activeItem.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
            }
        }
    };

    document.addEventListener('keydown', window.MaterialesHandlers.keydown);
}