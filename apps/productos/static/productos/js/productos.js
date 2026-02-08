// ============================================================================
// PRODUCTOS.JS - Gestión de Productos e Imágenes
// ============================================================================

// ----------------------------------------------------------------------------
// VARIABLES GLOBALES
// ----------------------------------------------------------------------------

/**
 * DataTransfer para persistir archivos de galería entre interacciones
 * Permite mantener los archivos seleccionados aunque el input se reinicie
 */
let galeriaFiles = new DataTransfer();

/**
 * Array de IDs de imágenes marcadas para eliminar
 * Se envían al backend cuando el usuario guarda los cambios
 */
let imagenesPendientesEliminar = [];


// ----------------------------------------------------------------------------
// CONFIGURACIÓN DE SWEETALERT2
// ----------------------------------------------------------------------------

/**
 * Configuración base reutilizable para todos los modales de SweetAlert2
 */
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

/**
 * Clases CSS personalizadas para los elementos de SweetAlert2
 */
const swalCustomClasses = {
    popup: 'bg-[#1e293b] border border-gray-800 rounded-2xl shadow-2xl',
    title: 'text-xl font-bold text-white',
    htmlContainer: 'text-gray-300',
    confirmButton: 'bg-red-600 hover:bg-red-700 text-white font-bold text-xs uppercase px-6 py-3 rounded-xl transition-colors mx-2',
    cancelButton: 'bg-slate-700 hover:bg-slate-600 text-white font-bold text-xs uppercase px-6 py-3 rounded-xl transition-colors mx-2',
    actions: 'pb-4'
};


// ----------------------------------------------------------------------------
// FUNCIONES DE PREVISUALIZACIÓN DE IMÁGENES
// ----------------------------------------------------------------------------

/**
 * Maneja la previsualización de una imagen única (portada)
 * 
 * @param {HTMLInputElement} input - Input file que contiene la imagen
 * @param {string} previewId - ID del elemento <img> donde mostrar la preview
 * @param {string} contentId - ID del contenedor de contenido a ocultar
 * @param {string} zoneId - ID de la zona de drop para aplicar estilos
 */
function handleImagePreview(input, previewId, contentId, zoneId) {
    const preview = document.getElementById(previewId);
    const content = document.getElementById(contentId);
    const zone = document.getElementById(zoneId);

    if (input.files && input.files[0]) {
        const reader = new FileReader();
        reader.onload = function (e) {
            // Mostrar la imagen de preview
            preview.src = e.target.result;
            preview.classList.remove('hidden');
            preview.style.opacity = "0.4";

            // Aplicar estilos visuales
            if (zone) zone.classList.add('border-solid', 'border-blue-500/60');
            if (content) {
                const pText = content.querySelector('p');
                if (pText) {
                    pText.innerText = "Nueva imagen seleccionada";
                    pText.classList.replace('text-gray-400', 'text-blue-400');
                }
            }
        }
        reader.readAsDataURL(input.files[0]);
    }
}

/**
 * Maneja la previsualización múltiple de imágenes con opción de eliminar
 * Usa un DataTransfer global para persistir archivos
 * 
 * @param {HTMLInputElement} input - Input file (múltiple)
 * @param {string} containerId - ID del contenedor donde mostrar las previews
 * @param {string} textId - ID del texto que muestra el contador de imágenes
 */
function handleMultiplePreviewsWithDelete(input, containerId, textId) {
    const container = document.getElementById(containerId);

    if (!container || !input.files || input.files.length === 0) return;

    // Procesar cada archivo seleccionado
    for (let i = 0; i < input.files.length; i++) {
        const file = input.files[i];

        // Verificar duplicados (mismo nombre y tamaño)
        const duplicado = Array.from(galeriaFiles.files).some(
            f => f.name === file.name && f.size === file.size
        );

        if (!duplicado) {
            // Añadir archivo al DataTransfer global
            galeriaFiles.items.add(file);

            const reader = new FileReader();
            reader.onload = function (e) {
                // Crear wrapper para la imagen
                const wrapper = document.createElement('div');
                wrapper.className = "preview-item relative group aspect-square animate-in fade-in zoom-in duration-300";

                const fileId = `${file.name}-${file.size}`;
                wrapper.dataset.fileId = fileId;

                wrapper.innerHTML = `
                    <img src="${e.target.result}" class="w-full h-full object-cover rounded-lg border border-purple-500/50 shadow-md">
                    <button type="button" class="btn-delete absolute -top-2 -right-2 bg-red-500 hover:bg-red-600 text-white rounded-full w-6 h-6 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all shadow-lg z-50">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                        </svg>
                    </button>
                `;

                // Configurar botón de eliminar
                wrapper.querySelector('.btn-delete').onclick = function () {
                    wrapper.remove();

                    // Reconstruir DataTransfer sin este archivo
                    const newDt = new DataTransfer();
                    Array.from(galeriaFiles.files).forEach(f => {
                        if (`${f.name}-${f.size}` !== fileId) {
                            newDt.items.add(f);
                        }
                    });
                    galeriaFiles = newDt;
                    input.files = galeriaFiles.files;

                    actualizarContadorVisual(containerId, textId);
                };

                container.appendChild(wrapper);
                actualizarContadorVisual(containerId, textId);
            };
            reader.readAsDataURL(file);
        }
    }

    // Actualizar el input con todos los archivos acumulados
    input.files = galeriaFiles.files;
}

/**
 * Actualiza el contador visual de imágenes y aplica lógica de "+N más"
 * Muestra máximo 3 imágenes, las demás quedan ocultas con un indicador
 * 
 * @param {string} containerId - ID del contenedor de previews
 * @param {string} textId - ID del texto contador
 */
function actualizarContadorVisual(containerId, textId) {
    const container = document.getElementById(containerId);
    const galText = document.getElementById(textId);

    if (!container) return;

    const items = container.querySelectorAll('.preview-item');
    const MAX_VISIBLES = 3;

    // Eliminar indicadores previos de "+N más"
    container.querySelectorAll('.more-indicator').forEach(el => el.remove());

    // Mostrar/ocultar items según el límite
    items.forEach((item, index) => {
        item.style.display = 'block';
        item.classList.remove('hidden');

        const img = item.querySelector('img');
        if (img) img.classList.remove('opacity-40');

        if (index >= MAX_VISIBLES) {
            item.style.display = 'none';
        }
    });

    // Si hay más imágenes que el límite, mostrar indicador "+N"
    if (items.length > MAX_VISIBLES) {
        const lastVisible = items[MAX_VISIBLES - 1];
        const extraCount = items.length - MAX_VISIBLES;

        const badge = document.createElement('div');
        badge.className = "more-indicator absolute inset-0 bg-gray-900/80 rounded-lg flex flex-col items-center justify-center border border-purple-500/50 pointer-events-none z-10";
        badge.innerHTML = `<span class="text-white font-bold text-xl">+${extraCount + 1}</span>`;

        const imgTarget = lastVisible.querySelector('img');
        if (imgTarget) imgTarget.classList.add('opacity-40');

        lastVisible.appendChild(badge);
    }

    // Actualizar texto contador
    if (galText) {
        galText.innerText = items.length > 0
            ? `Ver (${items.length}) / Añadir`
            : "Añadir más";
    }
}


// ----------------------------------------------------------------------------
// FUNCIONES DE ELIMINACIÓN DE IMÁGENES
// ----------------------------------------------------------------------------

/**
 * Marca una imagen de galería para eliminar (no se elimina hasta guardar)
 * CORRECCIÓN: Ahora recibe el elemento wrapper directamente
 * 
 * @param {string} imagenId - ID de la imagen en la base de datos
 * @param {HTMLElement} wrapperElement - Elemento DOM que contiene la imagen
 */
function eliminarImagenProducto(imagenId, wrapperElement) {


    Swal.fire({
        ...swalConfigBase,
        title: '¿ELIMINAR IMAGEN?',
        html: '<p class="text-gray-400 text-sm">La imagen se eliminará al guardar los cambios.</p>',
        iconHtml: swalIcons.deleteProduct,
        confirmButtonText: 'SÍ, ELIMINAR',
        cancelButtonText: 'CANCELAR',
        customClass: {
            ...swalCustomClasses,
            icon: 'border-0'
        }
    }).then((result) => {
        if (result.isConfirmed) {


            // Añadir a la lista de pendientes
            imagenesPendientesEliminar.push(imagenId);


            // Obtener el contenedor padre para actualizar el contador
            const parentElement = wrapperElement.parentElement;
            const parentId = parentElement?.id;



            // Remover del DOM
            wrapperElement.remove();

            // Actualizar contador visual
            if (parentId) {
                const textId = parentId === 'preview-galeria-edit'
                    ? 'text-galeria-edit'
                    : 'text-galeria-nuevo';
                actualizarContadorVisual(parentId, textId);
            }

            mostrarToast('success', 'Imagen marcada para eliminar');
        }
    });
}

/**
 * Elimina las imágenes pendientes en el backend
 * Se ejecuta cuando el usuario guarda los cambios del producto
 * CORRECCIÓN: Mejor manejo de errores y logging
 */
function eliminarImagenesPendientes() {


    if (imagenesPendientesEliminar.length === 0) {

        return Promise.resolve(); // Retornar Promise para mejor control de flujo
    }



    const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;

    return fetch('/administrador/inventario/productos/api/eliminar-imagenes/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrftoken,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            imagenes: imagenesPendientesEliminar
        })
    })
        .then(res => {

            if (!res.ok) {
                throw new Error(`Error HTTP: ${res.status}`);
            }
            return res.json();
        })
        .then(data => {


            if (data.status === 'ok' || data.success) {

                imagenesPendientesEliminar = []; // Limpiar array
                return true;
            } else {

                mostrarToast('error', data.message || 'Error al eliminar imágenes');
                return false;
            }
        })
        .catch(error => {

            mostrarToast('error', 'Error de conexión al eliminar imágenes');
            return false;
        });
}

/**
 * Limpia la previsualización de portada y activa flag de eliminación
 * 
 * @param {string} previewId - ID del elemento <img> de preview
 * @param {string} contentId - ID del contenedor a mostrar
 * @param {string} inputId - ID del input file a limpiar
 * @param {string} flagId - ID del input hidden que indica si eliminar
 */
function limpiarPreviewImagen(previewId, contentId, inputId, flagId) {
    Swal.fire({
        ...swalConfigBase,
        title: '¿QUITAR PORTADA?',
        html: '<p class="text-gray-400 text-sm">La imagen se eliminará permanentemente al guardar los cambios.</p>',
        iconHtml: swalIcons.deleteProduct,
        confirmButtonText: 'SÍ, QUITAR',
        cancelButtonText: 'CANCELAR',
        customClass: {
            ...swalCustomClasses,
            icon: 'border-0',
            confirmButton: swalCustomClasses.confirmButton
                .replace('bg-red-600', 'bg-amber-600')
                .replace('hover:bg-red-700', 'hover:bg-amber-700')
        }
    }).then((result) => {
        if (result.isConfirmed) {
            const preview = document.getElementById(previewId);
            const content = document.getElementById(contentId);
            const input = document.getElementById(inputId);
            const flag = document.getElementById(flagId);

            const zone = preview?.parentElement;
            const btnDelete = zone?.querySelector('button[id^="btnDelete"]');

            // Limpiar preview y restablecer estado
            if (preview) {
                preview.src = "";
                preview.classList.add('hidden');
            }
            if (content) {
                content.classList.remove('opacity-0', 'hidden');
            }
            if (input) {
                input.value = "";
            }
            if (flag) {
                flag.value = "true"; // Marcar para eliminar en backend
            }
            if (btnDelete) {
                btnDelete.classList.add('hidden');
            }

            mostrarToast('success', 'Portada marcada para eliminar');
        }
    });
}


// ----------------------------------------------------------------------------
// FUNCIONES DE MODALES (PRODUCTOS)
// ----------------------------------------------------------------------------

/**
 * Abre el modal de edición de producto y carga sus datos
 * CORRECCIÓN: Limpia el array de imágenes pendientes al abrir
 * 
 * @param {number|string} id - ID del producto a editar
 */
function abrirEditarProducto(id) {
    const url = `/administrador/inventario/productos/api/${id}/`;



    // 1. Limpiar archivos locales previos
    galeriaFiles = new DataTransfer();
    const inputFisico = document.getElementById('input-galeria-edit');
    if (inputFisico) inputFisico.value = "";

    // CORRECCIÓN CRÍTICA: Limpiar array de imágenes pendientes al abrir un nuevo producto
    imagenesPendientesEliminar = [];


    fetch(url)
        .then(response => {
            if (!response.ok) throw new Error('Error al obtener datos');
            return response.json();
        })
        .then(data => {


            // 2. Obtener referencias a elementos del DOM
            const galPreview = document.getElementById('preview-galeria-edit');

            const elementos = {
                nombre: document.getElementById('edit_prod_nombre'),
                categoria: document.getElementById('edit_prod_categoria'),
                precio: document.getElementById('edit_prod_precio'),
                peso: document.getElementById('edit_prod_peso'),
                web: document.getElementById('edit_prod_web'),
                descripcion: document.getElementById('edit_prod_desc'),
                form: document.getElementById('formEditarProducto'),
                preview: document.getElementById('previewEdit'),
                content: document.getElementById('contentEdit'),
                galPreview: galPreview
            };

            // 3. Limpiar galería PRESERVANDO estructura
            if (galPreview) {
                // Guardar referencia al botón de añadir ANTES de limpiar
                const btnAdd = galPreview.querySelector('button[onclick*="input-galeria-edit"]');

                // Limpiar TODO el contenedor
                galPreview.innerHTML = '';

                // Restaurar el botón si existía
                if (btnAdd) {
                    galPreview.appendChild(btnAdd);
                }
            }

            // 4. Rellenar campos del formulario
            if (elementos.nombre) elementos.nombre.value = data.nombre;
            if (elementos.categoria) elementos.categoria.value = data.categoria_id;
            if (elementos.precio) elementos.precio.value = data.precio_venta;
            if (elementos.peso) elementos.peso.value = data.peso_gramos;
            if (elementos.web) elementos.web.checked = data.mostrar_en_web;
            if (elementos.descripcion) elementos.descripcion.value = data.descripcion || '';

            // 5. Manejar imagen de portada
            if (data.imagen_url && elementos.preview) {
                elementos.preview.src = data.imagen_url;
                elementos.preview.classList.remove('hidden');
                if (elementos.content) elementos.content.classList.add('opacity-0');

                const btnDel = document.getElementById('btnDeletePortadaEdit');
                if (btnDel) btnDel.classList.remove('hidden');

                // Resetear flag de eliminación
                const flag = document.getElementById('eliminar_portada_flag_edit');
                if (flag) flag.value = "false";
            } else {
                if (elementos.preview) elementos.preview.classList.add('hidden');
                if (elementos.content) elementos.content.classList.remove('opacity-0');

                const btnDel = document.getElementById('btnDeletePortadaEdit');
                if (btnDel) btnDel.classList.add('hidden');
            }

            // 6. Cargar imágenes de galería
            if (data.imagenes_galeria && galPreview) {


                // Obtener referencia actualizada al botón de añadir
                const btnAdd = galPreview.querySelector('button[onclick*="input-galeria-edit"]');

                data.imagenes_galeria.forEach(imgData => {
                    const wrapper = document.createElement('div');
                    wrapper.className = "preview-item relative group aspect-square animate-in fade-in duration-300";

                    // CORRECCIÓN: Pasar this.parentElement correctamente
                    wrapper.innerHTML = `
                        <img src="${imgData.url}" class="w-full h-full object-cover rounded-lg border border-purple-500/20 shadow-sm transition-all">
                        <button type="button" 
                                onclick="eliminarImagenProducto('${imgData.id}', this.parentElement)" 
                                class="absolute -top-2 -right-2 bg-red-500 hover:bg-red-600 text-white rounded-full w-6 h-6 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all shadow-lg z-50">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                            </svg>
                        </button>
                    `;

                    // Insertar SOLO si el botón existe y está en el DOM
                    if (btnAdd && btnAdd.parentNode === galPreview) {
                        galPreview.insertBefore(wrapper, btnAdd);
                    } else {
                        // Si no hay botón, simplemente añadir al final
                        galPreview.appendChild(wrapper);
                    }
                });
            }

            // 7. Actualizar contador visual
            actualizarContadorVisual('preview-galeria-edit', 'text-galeria-edit');

            // 8. Configurar action del formulario
            if (elementos.form) {
                elementos.form.action = `/administrador/inventario/productos/${id}/editar/`;
            }

            // 9. Abrir el modal
            abrirModal('modalEditarProducto');
        })
        .catch(error => {

            mostrarToast('error', 'Error al cargar los datos del producto');
        });
}


// ----------------------------------------------------------------------------
// FUNCIONES DE MODALES (CATEGORÍAS)
// ----------------------------------------------------------------------------

/**
 * Abre el modal de edición de categoría y carga sus datos
 * 
 * @param {number|string} id - ID de la categoría a editar
 */
function abrirEditarCat(id) {
    const url = `/administrador/inventario/productos/categorias/api/${id}/`;

    fetch(url)
        .then(response => {
            if (!response.ok) throw new Error('Error al obtener datos');
            return response.json();
        })
        .then(data => {
            // Actualizar título del modal
            const titulo = document.getElementById('edit_cat_nombre_titulo');
            if (titulo) titulo.innerText = `Modificando: ${data.nombre}`;

            // Rellenar campos
            const inputNombre = document.getElementById('edit_cat_nombre');
            const inputDesc = document.getElementById('edit_cat_descripcion');
            if (inputNombre) inputNombre.value = data.nombre;
            if (inputDesc) inputDesc.value = data.descripcion;

            // Manejar imagen de portada
            const preview = document.getElementById('previewEdit');
            const zone = document.getElementById('zoneEdit');
            const btnDelete = document.getElementById('btnDeleteCatEdit');
            const inputHidden = document.getElementById('eliminar_imagen_input');

            // Resetear flag de eliminación
            if (inputHidden) inputHidden.value = "false";

            if (data.imagen) {
                if (preview) {
                    preview.src = data.imagen;
                    preview.classList.remove('hidden');
                    preview.style.opacity = "1";
                }
                if (zone) zone.classList.add('border-solid', 'border-blue-500/60');
                if (btnDelete) btnDelete.classList.remove('hidden');
            } else {
                if (preview) preview.classList.add('hidden');
                if (zone) zone.classList.remove('border-solid', 'border-blue-500/60');
                if (btnDelete) btnDelete.classList.add('hidden');
            }

            // Configurar action del formulario
            const form = document.getElementById('formEditarCategoria');
            if (form) {
                form.action = `/administrador/inventario/productos/categorias/${id}/editar/`;
            }

            abrirModal('modalEditarCat');
        })
        .catch(error => {

            mostrarToast('error', 'No se pudieron cargar los datos de la categoría');
        });
}

/**
 * Confirma y ejecuta la eliminación de una categoría
 * 
 * @param {number|string} id - ID de la categoría
 * @param {string} nombre - Nombre de la categoría para mostrar en confirmación
 * @param {string} redirectUrl - URL a donde redirigir tras eliminar
 */
function confirmarEliminarCategoria(id, nombre, redirectUrl) {
    Swal.fire({
        ...swalConfigBase,
        title: 'Eliminar Categoría',
        html: `
            <div class="text-center">
                <p class="text-gray-300 mb-2">Estás por eliminar:</p>
                <p class="text-white font-semibold text-lg">${nombre}</p>
                <p class="text-gray-400 text-sm mt-3 border-t border-gray-700/50 pt-3">Esta acción no se puede deshacer y los productos dentro de esta categoria se moveran a Sin Categorizar   .</p>
            </div>`,
        iconHtml: swalIcons.warningRed,
        confirmButtonText: 'Sí, Eliminar',
        cancelButtonText: 'Cancelar',
        customClass: {
            ...swalCustomClasses,
            icon: 'border-0'
        }
    }).then((result) => {
        if (result.isConfirmed) {
            // Mostrar modal de carga
            Swal.fire({
                ...swalConfigBase,
                title: 'Eliminando...',
                html: `
                    <div class="py-4">
                        <svg class="animate-spin h-10 w-10 mx-auto text-red-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                    </div>`,
                showConfirmButton: false,
                allowOutsideClick: false,
                customClass: { popup: swalCustomClasses.popup }
            });

            // Ejecutar eliminación
            fetch(`/administrador/inventario/productos/categorias/${id}/eliminar/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
                    'Content-Type': 'application/json'
                }
            })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        window.location.href = redirectUrl;
                    } else {
                        Swal.close();
                        mostrarToast('error', data.message || 'Error al eliminar la categoría');
                    }
                })
                .catch(error => {

                    Swal.close();
                    mostrarToast('error', 'Error al procesar la solicitud');
                });
        }
    });
}


// ----------------------------------------------------------------------------
// EVENT LISTENERS Y MANEJO DE GUARDADO
// ----------------------------------------------------------------------------

/**
 * Intercepta el submit del formulario para eliminar imágenes antes de enviar
 * CORRECCIÓN: Ahora espera a que se eliminen las imágenes antes de continuar
 */
document.addEventListener('DOMContentLoaded', function () {
    const formEditar = document.getElementById('formEditarProducto');

    if (formEditar) {


        formEditar.addEventListener('submit', function (e) {


            // Si hay imágenes pendientes de eliminar
            if (imagenesPendientesEliminar.length > 0) {
                e.preventDefault(); // Detener el submit


                // Eliminar imágenes primero
                eliminarImagenesPendientes().then(() => {

                    // Ahora sí enviar el formulario
                    formEditar.submit();
                });
            } else {

            }
        });
    }
});

/**
 * ALTERNATIVA: Detectar clic en botón guardar
 * Si prefieres usar un botón específico en lugar del submit del form
 */
const btnGuardar = document.getElementById('btn-Guardar');
if (btnGuardar) {


    btnGuardar.addEventListener('click', function (e) {


        if (imagenesPendientesEliminar.length > 0) {
            e.preventDefault();


            eliminarImagenesPendientes().then((success) => {
                if (success) {

                    const form = document.getElementById('formEditarProducto');
                    if (form) form.submit();
                }
            });
        }
    });
}


// ============================================================================
// FIN DE PRODUCTOS.JS
// ============================================================================