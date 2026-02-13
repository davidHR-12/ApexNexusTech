/**
 * Obtiene el valor de una cookie por su nombre, útil para recuperar el CSRF token.
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
 * y restaura el comportamiento del scroll en el cuerpo de la página.
 */
function cerrarModales() {
    const wrapper = document.getElementById('modal-dinamico-wrapper');
    if (wrapper) wrapper.innerHTML = ''; // Limpiar contenido del modal dinámico

    document.body.style.overflow = 'auto';

    // Cerrar otros modales estáticos si los hubiera
    document.querySelectorAll('.modal-overlay').forEach(m => {
        m.classList.add('hidden');
    });
}

/**
 * Abre un modal dinámico cargando su contenido desde una URL específica.
 * Inyecta el HTML recibido y reactiva los scripts necesarios.
 * @param {string} url - La URL de la vista que retorna el HTML del modal.
 */
async function abrirModalDinamico(url) {
    cerrarModales(); // Asegurar limpieza previa

    const wrapper = document.getElementById('modal-dinamico-wrapper');
    try {
        const response = await fetch(url);
        const html = await response.text();
        wrapper.innerHTML = html;

        const modalElement = wrapper.querySelector('.modal-overlay');
        if (modalElement) {
            modalElement.classList.remove('hidden');
            document.body.style.overflow = 'hidden';
            const modalContainer = modalElement.querySelector('div'); 
            if (modalContainer) {
                // Eliminamos anchos pequeños y aplicamos uno más grande
                modalContainer.classList.remove('max-w-md', 'max-w-lg');
                modalContainer.classList.add('max-w-2xl'); // Esto le dará ~896px
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

/**
 * Actualiza la numeración visual de los materiales listados 
 * y controla el estado (habilitado/deshabilitado) del botón "Añadir".
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

    // Actualizar números de índice visuales (1, 2, 3...)
    filas.forEach((fila, index) => {
        const numeroSpan = fila.querySelector('.material-number');
        if (numeroSpan) numeroSpan.textContent = index + 1;
    });

    // Mostrar u ocultar botones de eliminar (mínimo 1 requerido)
    const botonesEliminar = document.querySelectorAll('.eliminar-material');
    botonesEliminar.forEach(btn => {
        filas.length > 1 ? btn.classList.remove('hidden') : btn.classList.add('hidden');
    });
}

/**
 * Configura el event listener para manejar la eliminación de filas de materiales.
 * Utiliza delegación de eventos.
 */
function configurarEliminacionMaterial() {
    document.addEventListener('click', function(e) {
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
 * Recalcula los atributos 'name' e 'id' de los inputs del formset de Django
 * para mantener la secuencia correcta (0, 1, 2...) tras añadir o eliminar filas.
 */
function actualizarIndicesFormset() {
    const totalFormsInput = document.getElementById('id_detalles_material-TOTAL_FORMS');
    const filas = document.querySelectorAll('.material-form-row');
    
    filas.forEach((fila, index) => {
        fila.querySelectorAll('input, select').forEach(input => {
            // Reemplazar el índice en el nombre e ID (ej: -0- -> -1-)
            input.name = input.name.replace(/-\d+-/, `-${index}-`);
            input.id = input.id.replace(/-\d+-/, `-${index}-`);
        });
    });
    
    if (totalFormsInput) {
        totalFormsInput.value = filas.length;
    }
}

/**
 * Inicializa los controladores y eventos necesarios cuando se abre el modal,
 * incluyendo la lógica para añadir nuevos materiales dinámicamente.
 */
function inicializarScriptsModal() {
    const btnAddMaterial = document.getElementById('add-material');
    if (!btnAddMaterial) return;

    actualizarNumeracionMateriales();
    configurarEliminacionMaterial();
    
    // Clonar para limpiar eventos previos y asignar el nuevo
    const nuevoBtn = btnAddMaterial.cloneNode(true);
    btnAddMaterial.parentNode.replaceChild(nuevoBtn, btnAddMaterial);
    
    nuevoBtn.addEventListener('click', function() {
        const filasActuales = document.querySelectorAll('.material-form-row').length;
        const maxPermitido = parseInt(this.dataset.maxMaterials) || 10;

        // Validar límite máximo
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
        
        // Clonar la última fila para crear una nueva
        let lastForm = allForms[allForms.length - 1];
        let newForm = lastForm.cloneNode(true);
        
        // Limpiar valores de los inputs clonados y asignar nuevos índices
        newForm.querySelectorAll('input, select').forEach(input => {
            input.name = input.name.replace(/-\d+-/, `-${formIdx}-`);
            input.id = input.id.replace(/-\d+-/, `-${formIdx}-`);
            input.value = '';
        });
        
        let materialList = document.getElementById('material-list');
        if (!materialList) return;
        
        materialList.appendChild(newForm);
        
        totalFormsInput.value = formIdx + 1;
        
        actualizarNumeracionMateriales();
        
        setTimeout(() => {
            newForm.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }, 100);
    });
}

/**
 * Solicita confirmación al usuario para eliminar una variante.
 * Si se confirma, realiza la petición POST al servidor.
 * @param {HTMLElement} buttonElement - El botón que disparó la acción (contiene datos de la variante).
 */
function confirmarEliminarVariante(buttonElement) {
    const id = buttonElement.dataset.varianteId;
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

function cambiarVisor(url) {
    const mainImg = document.getElementById('main-image');
    const placeholder = document.getElementById('image-placeholder');

    if (mainImg) {
        mainImg.src = url;
        mainImg.classList.remove('hidden'); // Muestra la imagen si estaba oculta
    }

    if (placeholder) {
        placeholder.classList.add('hidden'); // Oculta el texto de "Sin imagen"
    }
}

/* Eventos Globales */
window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') cerrarModales();
}, true);

document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal-overlay')) {
        cerrarModales();
    }
}, true);