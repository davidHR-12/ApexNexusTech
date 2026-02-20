// ============================================================================
// FUNCIONES ESPECÍFICAS PARA BÚSQUEDA DE MATERIALES EN VARIANTES
// ============================================================================

/**
 * Selecciona un material desde los resultados de búsqueda y actualiza el formset.
 * 
 * @param {string} fieldIndex - Índice del campo en el formset (0, 1, 2...).
 * @param {string} materialId - ID del material seleccionado.
 * @param {string} materialNombre - Nombre completo del material para mostrar.
 */
function seleccionarMaterialVariante(fieldIndex, materialId, materialNombre) {
    // 1. Actualizar el select oculto de Django
    const selectMaterial = document.querySelector(`select[name="detalles_material-${fieldIndex}-material"]`);
    if (selectMaterial) {
        selectMaterial.value = materialId;
    }

    // 2. Actualizar el input de búsqueda visual
    const searchInput = document.getElementById(`material-search-${fieldIndex}`);
    if (searchInput) {
        searchInput.value = materialNombre; // <-- Aquí ponemos el texto
        
        // Opcional: Cambiar el estilo para indicar que ya está seleccionado
        searchInput.classList.remove('border-gray-700');
        searchInput.classList.add('border-emerald-500', 'bg-emerald-500/10', 'text-emerald-400');
    }

    // 3. Limpiar los resultados de búsqueda para que desaparezca la lista
    const resultadosDiv = document.getElementById(`resultados-material-${fieldIndex}`);
    if (resultadosDiv) {
        resultadosDiv.innerHTML = '';
    }

    // 5. Enfocar el siguiente campo (gramos) para agilizar la entrada de datos
    const gramosInput = document.querySelector(`input[name="detalles_material-${fieldIndex}-gramos_usados"]`);
    if (gramosInput) {
        setTimeout(() => gramosInput.focus(), 100);
    }
}


// Escuchamos todos los eventos de entrada en el documento
document.addEventListener('input', function (event) {
    // Verificamos si el cambio viene de un input de búsqueda de materiales
    if (event.target.classList.contains('material-search-input')) {
        const input = event.target;
        const index = input.getAttribute('data-field-index');
        
        // Si el usuario borró el texto, reseteamos estilos y valores
        if (input.value === '') {
            resetInputMaterial(index);
        }
    }
});

function resetInputMaterial(fieldIndex) {
    const searchInput = document.getElementById(`material-search-${fieldIndex}`);
    // Buscamos el select oculto por nombre, ya que los IDs a veces fallan en formsets dinámicos
    const selectMaterial = document.querySelector(`select[name="detalles_material-${fieldIndex}-material"]`);

    if (searchInput) {
        searchInput.classList.remove('border-emerald-500', 'bg-emerald-500/10', 'text-emerald-400');
        searchInput.classList.add('border-gray-700');
    }

    if (selectMaterial) {
        selectMaterial.value = '';
    }
}

/**
 * Limpia la selección de material de un campo específico, reseteando los inputs.
 * 
 * @param {string} fieldIndex - Índice del campo a limpiar.
 */
function limpiarSeleccionMaterial(fieldIndex) {
    // Limpiar el valor del select oculto
    const selectMaterial = document.querySelector(`select[name="detalles_material-${fieldIndex}-material"]`);
    if (selectMaterial) {
        selectMaterial.value = '';
    }

    // Resetear el input de búsqueda
    const searchInput = document.getElementById(`material-search-${fieldIndex}`);
    if (searchInput) {
        searchInput.value = '';
        searchInput.classList.remove('border-emerald-500/50', 'bg-emerald-500/5');
        searchInput.classList.add('border-gray-700');
    }

    // Ocultar el indicador de selección
    const selectedDiv = document.getElementById(`material-selected-${fieldIndex}`);
    if (selectedDiv) {
        selectedDiv.classList.add('hidden');
    }
}

/**
 * Event Listener Global: Oculta los resultados de búsqueda cuando se hace clic fuera de ellos.
 */
document.addEventListener('click', function (e) {
    // Si el clic NO es en un input de búsqueda ni en el contenedor de resultados
    if (!e.target.closest('.material-search-input') && !e.target.closest('[id^="resultados-material-"]')) {
        // Ocultar todos los contenedores de resultados activos
        document.querySelectorAll('[id^="resultados-material-"]').forEach(div => {
            div.innerHTML = '';
        });
    }
});

// ============================================================================
// FUNCIONES PARA EL MANEJO DE MODALES Y COOKIES
// ============================================================================

/**
 * Obtiene el valor de una cookie por su nombre (ej. csrftoken).
 * 
 * @param {string} name - El nombre de la cookie a buscar.
 * @returns {string|null} El valor de la cookie o null si no existe.
 */
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

/**
 * Cierra cualquier modal abierto (dinámico o estático) 
 * y restaura el scroll de la página.
 * Renombrado para no sobrescribir la función global del layout.
 */
function limpiarModalesDinamicos() {
    const wrapper = document.getElementById('modal-dinamico-wrapper');
    if (wrapper) wrapper.innerHTML = ''; // Limpiar contenido del modal dinámico

    document.body.style.overflow = 'auto'; // Restaurar scroll

    // Cerrar otros modales estáticos si existen
    document.querySelectorAll('.modal-overlay').forEach(m => {
        m.classList.add('hidden');
    });
}

/**
 * Abre un modal dinámico cargando su contenido desde una URL.
 * Inyecta el HTML y reactiva los scripts necesarios (como la búsqueda de materiales).
 * 
 * @param {string} url - La URL de la vista que retorna el HTML del modal.
 */
async function abrirModalDinamico(url) {
    limpiarModalesDinamicos(); // Asegurar limpieza previa

    const wrapper = document.getElementById('modal-dinamico-wrapper');
    try {
        const response = await fetch(url);
        const html = await response.text();
        wrapper.innerHTML = html;

        const modalElement = wrapper.querySelector('.modal-overlay');
        if (modalElement) {
            modalElement.classList.remove('hidden');
            document.body.style.overflow = 'hidden'; // Bloquear scroll del body
            
            // --- INTEGRACIÓN CON GLOBALS.JS ---
            // Aseguramos que el modal tenga un ID
            if (!modalElement.id) {
                modalElement.id = 'modal-dinamico-' + Date.now();
            }
            
            // Empujamos al stack global para que cerrarUltimoModal() funcione
            if (typeof modalStack !== 'undefined') {
                if (!modalStack.includes(modalElement.id)) {
                    modalStack.push(modalElement.id);
                }
                // Actualizar z-index
                modalElement.style.zIndex = 50 + (modalStack.length * 10);
            }
            // ----------------------------------

            const modalContainer = modalElement.querySelector('div');
            if (modalContainer) {
                // Ajustar ancho del modal para mejor visualización
                modalContainer.classList.remove('max-w-md', 'max-w-lg');
                modalContainer.classList.add('max-w-2xl');
            }
        }

        // Inicializar la lógica interactiva del formulario dentro del modal
        inicializarScriptsModal();

    } catch (error) {
        console.error('Error al abrir modal:', error);
        if (typeof mostrarToast === 'function') {
            mostrarToast('error', 'No se pudo cargar el formulario');
        }
    }
}

function cerrarModalDinamico() {
    const modal = document.getElementById('modal-container');
    if (modal) {
        modal.classList.add('hidden');
        document.body.style.overflow = ''; // Restaurar scroll
        
        // Limpiar el contenido
        modal.innerHTML = '';
        
        // Quitar del stack global
        if (typeof modalStack !== 'undefined') {
            modalStack.pop();
        }
    }
}

// ============================================================================
// LÓGICA DEL FORMSET (AÑADIR/ELIMINAR MATERIALES)
// ============================================================================

/**
 * Actualiza la numeración visual de los materiales y gestiona el estado del botón "Añadir".
 */
function actualizarNumeracionMateriales() {
    const filas = document.querySelectorAll('.material-form-row');
    const contador = document.getElementById('contador-materiales');
    const btnAdd = document.getElementById('add-material');

    // Obtener límite de materiales (default: 10)
    const maxMateriales = btnAdd ? parseInt(btnAdd.dataset.maxMaterials) || 10 : 10;
    
    // Actualizar contador visual
    if (contador) {
        contador.textContent = `${filas.length} / ${maxMateriales} materiales`;
    }

    // Bloquear o desbloquear botón según el límite
    if (btnAdd) {
        if (filas.length >= maxMateriales) {
            btnAdd.disabled = true;
            btnAdd.classList.add('opacity-50', 'cursor-not-allowed', 'grayscale');
            btnAdd.innerHTML = 'Límite de materiales alcanzado';
        } else {
            btnAdd.disabled = false;
            btnAdd.classList.remove('opacity-50', 'cursor-not-allowed', 'grayscale');
            btnAdd.innerHTML = `
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-width="2" stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"></path>
                </svg>
                Añadir otro material`;
        }
    }

    // Actualizar índices visuales (1, 2, 3...)
    filas.forEach((fila, index) => {
        const numeroSpan = fila.querySelector('.material-number');
        if (numeroSpan) numeroSpan.textContent = index + 1;
    });

    // Mostrar u ocultar botones de eliminar (mínimo 1 fila requerida)
    const botonesEliminar = document.querySelectorAll('.eliminar-material');
    botonesEliminar.forEach(btn => {
        filas.length > 1 ? btn.classList.remove('hidden') : btn.classList.add('hidden');
    });
}

/**
 * Configura la delegación de eventos para eliminar filas de materiales.
 */
function configurarEliminacionMaterial() {
    document.addEventListener('click', function (e) {
        if (e.target.closest('.eliminar-material')) {
            const fila = e.target.closest('.material-form-row');
            const filas = document.querySelectorAll('.material-form-row');

            // Evitar eliminar si es el único elemento
            if (filas.length <= 1) return;

            // Animación de salida
            fila.style.opacity = '0';
            fila.style.transform = 'translateX(-20px)';

            setTimeout(() => {
                fila.remove();
                actualizarNumeracionMateriales();
                actualizarIndicesFormset();
            }, 200);
        }
    });
}

/**
 * Recalcula los atributos 'name', 'id' y atributos HTMX de los inputs del formset
 * para mantener la secuencia correcta (0, 1, 2...) tras añadir o eliminar filas.
 */
function actualizarIndicesFormset() {
    const totalFormsInput = document.getElementById('id_detalles_material-TOTAL_FORMS');
    const filas = document.querySelectorAll('.material-form-row');

    filas.forEach((fila, index) => {
        // Actualizar inputs y selects del formset de Django
        fila.querySelectorAll('input, select').forEach(input => {
            input.name = input.name.replace(/-\d+-/, `-${index}-`);
            input.id = input.id.replace(/-\d+-/, `-${index}-`);
        });
        
        // Actualizar atributos HTMX para asegurar que la búsqueda funcione en la fila correcta
        const searchInput = fila.querySelector('.material-search-input');
        if (searchInput) {
            searchInput.setAttribute('hx-target', `#resultados-material-${index}`);
            searchInput.setAttribute('data-field-index', index);
            searchInput.id = `material-search-${index}`; // Asegura que el ID también cambie
        }
        
        // Actualizar IDs de contenedores relacionados (resultados, selección, texto)
        const resultadosDiv = fila.querySelector('[id^="resultados-material-"]');
        if (resultadosDiv) resultadosDiv.id = `resultados-material-${index}`;
        
        const selectedDiv = fila.querySelector('[id^="material-selected-"]');
        if (selectedDiv) selectedDiv.id = `material-selected-${index}`;
        
    });

    // Actualizar el contador total de formularios para Django
    if (totalFormsInput) {
        totalFormsInput.value = filas.length;
    }
    
    // Re-procesar HTMX después de actualizar el DOM
    if (typeof htmx !== 'undefined') {
        filas.forEach(fila => htmx.process(fila));
    }
}

/**
 * Inicializa los scripts y eventos del modal, incluyendo la lógica de HTMX 
 * y la funcionalidad para añadir nuevos materiales dinámicamente.
 */
function inicializarScriptsModal() {
    const btnAddMaterial = document.getElementById('add-material');
    if (!btnAddMaterial) return;

    actualizarNumeracionMateriales();
    configurarEliminacionMaterial();

    // Activar HTMX en las filas existentes (necesario al cargar el modal)
    if (typeof htmx !== 'undefined') {
        const filasExistentes = document.querySelectorAll('.material-form-row');
        filasExistentes.forEach(fila => {
            htmx.process(fila);
        });
    }

    // Reemplazar el botón para asegurar que no haya event listeners duplicados
    const nuevoBtn = btnAddMaterial.cloneNode(true);
    btnAddMaterial.parentNode.replaceChild(nuevoBtn, btnAddMaterial);

    // Event Listener para añadir nueva fila
    nuevoBtn.addEventListener('click', function () {
        const filasActuales = document.querySelectorAll('.material-form-row').length;
        const maxPermitido = parseInt(this.dataset.maxMaterials) || 12;

        if (filasActuales >= maxPermitido) {
            if (typeof mostrarToast === 'function') {
                mostrarToast('error', `Máximo de ${maxPermitido} materiales permitidos`);
            }
            return;
        }

        let totalFormsInput = document.getElementById('id_detalles_material-TOTAL_FORMS');
        if (!totalFormsInput) return;

        let formIdx = parseInt(totalFormsInput.value);
        let allForms = document.querySelectorAll('.material-form-row');

        if (allForms.length === 0) return;

        // Clonar la última fila para usarla como template
        let lastForm = allForms[allForms.length - 1];
        let newForm = lastForm.cloneNode(true);

        // Limpiar y actualizar la nueva fila con el nuevo índice
        newForm.querySelectorAll('input, select, div, label').forEach(element => {
            // Actualizar IDs
            if (element.id) {
                element.id = element.id.replace(/-\d+/, `-${formIdx}`);
            }

            // Actualizar Names
            if (element.name) {
                element.name = element.name.replace(/-\d+-/, `-${formIdx}-`);
            }

            // Actualizar HTMX targets e índices
            if (element.hasAttribute('hx-target')) {
                element.setAttribute('hx-target', `#resultados-material-${formIdx}`);
            }
            if (element.hasAttribute('data-field-index')) {
                element.setAttribute('data-field-index', formIdx);
            }

            // Resetear valores de inputs
            if (element.tagName === 'INPUT' && element.type !== 'hidden') {
                element.value = '';
            }
            if (element.tagName === 'SELECT') {
                element.selectedIndex = 0;
            }
        });

        // Resetear estado visual de búsqueda
        const searchInput = newForm.querySelector('.material-search-input');
        if (searchInput) {
            searchInput.classList.remove('border-emerald-500/50', 'bg-emerald-500/5');
            searchInput.classList.add('border-gray-700');
        }

        const selectedDiv = newForm.querySelector('[id^="material-selected-"]');
        if (selectedDiv) {
            selectedDiv.classList.add('hidden');
        }

        const resultadosDiv = newForm.querySelector('[id^="resultados-material-"]');
        if (resultadosDiv) {
            resultadosDiv.innerHTML = '';
        }

        // Insertar la nueva fila en el DOM
        let materialList = document.getElementById('material-list');
        if (!materialList) return;

        materialList.appendChild(newForm);

        // Actualizar contador total
        totalFormsInput.value = formIdx + 1;

        actualizarNumeracionMateriales();

        // Procesar HTMX en la nueva fila
        if (typeof htmx !== 'undefined') {
            htmx.process(newForm);
        }

        // Scroll y foco automático
        setTimeout(() => {
            newForm.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            const newSearchInput = newForm.querySelector('.material-search-input');
            if (newSearchInput) {
                newSearchInput.focus();
            }
        }, 100);
    });
}

/*
 * Configura la petición de HTMX globalmente para los inputs de material.
 * Así evitamos el error de "null value" al borrar filas.
 */
document.body.addEventListener('htmx:configRequest', function(evt) {
    // Si el elemento que dispara es un buscador de materiales
    if (evt.target.classList.contains('material-search-input')) {
        const fieldIndex = evt.target.getAttribute('data-field-index');
        const queryValue = evt.target.value;
        
        // Inyectamos los valores dinámicamente en la petición
        evt.detail.parameters['field_index'] = fieldIndex;
        evt.detail.parameters['q'] = queryValue;
    }
});

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

// ============================================================================
// FUNCIONES DE GESTIÓN DE VARIANTES Y EVENTOS GLOBALES
// ============================================================================

/**
 * Solicita confirmación y elimina una variante vía POST.
 * 
 * @param {HTMLElement} buttonElement - El botón que disparó la acción.
 */
function confirmarEliminarVariante(buttonElement) {
    const nombre = buttonElement.dataset.nombre;
    const urlEliminar = buttonElement.dataset.urlEliminar;

    Swal.fire({
        ...swalConfigBase,
        title: 'Eliminar variante',
        html: `Vas a eliminar la variante <b class="text-white">${nombre}</b>.`,
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
            fetch(urlEliminar, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'Content-Type': 'application/json'
                }
            })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        mostrarToast('success', data.message);
                        location.reload();
                    } else {
                        mostrarToast('error', data.error);
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    mostrarToast('error', 'Error al eliminar la variante');
                });
        }
    });
}

/**
 * Cambia la imagen principal del visor de productos.
 * 
 * @param {string} url - URL de la nueva imagen a mostrar.
 */
function cambiarVisor(url) {
    const mainImg = document.getElementById('main-image');
    const placeholder = document.getElementById('image-placeholder');

    if (mainImg) {
        mainImg.src = url;
        mainImg.classList.remove('hidden');
    }

    if (placeholder) {
        placeholder.classList.add('hidden');
    }
}

/**
 * Abre el modal de variantes desactivadas
 */
function abrirArchivoVariantes(productoId) {
    const contenedor = document.querySelector('#modalArchivoVariantes .custom-scrollbar');
    if (contenedor) contenedor.innerHTML = '<div class="text-center py-10 text-gray-500">Cargando archivo...</div>';
    
    // El endpoint debe devolver un partial HTML con la lista de variantes activa=False
    fetch(`/administrador/productos/${productoId}/variantes-archivadas/`)
        .then(response => response.text())
        .then(html => {
            contenedor.innerHTML = html;
            abrirModal('modalArchivoVariantes');
        })
        .catch(err => mostrarToast('error', 'Error al cargar el archivo de variantes'));
}

/**
 * Reactiva una variante individual
 */
function reactivarVariante(id) {
    fetch(`/administrador/productos/variante/${id}/toggle-activo/`, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCookie('csrftoken') }
    })
    .then(response => {
        // Si el servidor responde con 500 o 404, lanzamos error para el catch
        if (!response.ok) {
            return response.json().then(err => { throw new Error(err.error || 'Error interno') });
        }
        return response.json();
    })
    .then(data => {
        if(data.success) {
            mostrarToast('success', 'Variante reactivada');
            location.reload();
        }
    })
    .catch(error => {
        console.error('Error:', error);
        mostrarToast('error', 'No se pudo reactivar: ' + error.message);
    });
}

/**
 * Selecciona o deselecciona todos los checkboxes de variantes
 */
function toggleSelectAllVariantes(source) {
    const checkboxes = document.querySelectorAll('input[name="variantes_ids"]');
    checkboxes.forEach(cb => {
        cb.checked = source.checked;
    });
    // Actualizamos el botón de acción masiva y el contador
    toggleBatchButtonVariantes();
}

/**
 * Modifica ligeramente la función actual para que el checkbox 
 * "master" se desmarque si quitas uno individual
 */
function toggleBatchButtonVariantes() {
    const totalCheckboxes = document.querySelectorAll('input[name="variantes_ids"]');
    const checkedCheckboxes = document.querySelectorAll('input[name="variantes_ids"]:checked');
    const selectAll = document.getElementById('selectAllVariantes');
    const container = document.getElementById('batchActionVariantes');
    const countSpan = document.getElementById('selectedCountVariantes');
    
    // Si desmarcamos uno manual, el "Seleccionar todos" debe desmarcarse
    if (selectAll) {
        selectAll.checked = (totalCheckboxes.length === checkedCheckboxes.length);
    }

    if (checkedCheckboxes.length > 0) {
        container.classList.remove('hidden');
        countSpan.innerText = checkedCheckboxes.length;
    } else {
        container.classList.add('hidden');
    }
}

function reactivarMultiplesVariantes() {
    const ids = Array.from(document.querySelectorAll('input[name="variantes_ids"]:checked')).map(cb => cb.value);
    
    fetch('/administrador/productos/variantes/reactivar-multiples/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ ids: ids })
    })
    .then(response => response.json())
    .then(data => {
        if(data.success) {
            mostrarToast('success', data.message);
            location.reload();
        }
    });
}

/**
 * Función mejorada para el switch de la tabla principal
 */
function toggleVarianteEstado(varianteId) {
    fetch(`/administrador/productos/variante/${varianteId}/toggle-activo/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const msg = data.nuevo_estado ? 'Variante activada' : 'Variante desactivada';
            mostrarToast(data.nuevo_estado ? 'success' : 'info', msg);
            
            // Recargamos para que desaparezca de la lista de "Activas" si se desactivó
            setTimeout(() => location.reload(), 1000);
        }
    });
}