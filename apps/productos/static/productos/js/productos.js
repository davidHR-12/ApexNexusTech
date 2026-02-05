// --- Previsualización de Imagen Única (Portada) ---
function handleImagePreview(input, previewId, contentId, zoneId) {
    const preview = document.getElementById(previewId);
    const content = document.getElementById(contentId);
    const zone = document.getElementById(zoneId);

    if (input.files && input.files[0]) {
        const reader = new FileReader();
        reader.onload = function (e) {
            preview.src = e.target.result;
            preview.classList.remove('hidden');
            preview.style.opacity = "0.4";

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


// Variable global para persistir archivos
let galeriaFiles = new DataTransfer();

function handleMultiplePreviewsWithDelete(input, containerId, textId) {
    const container = document.getElementById(containerId);

    if (!container || !input.files || input.files.length === 0) return;

    for (let i = 0; i < input.files.length; i++) {
        const file = input.files[i];
        const duplicado = Array.from(galeriaFiles.files).some(f => f.name === file.name && f.size === file.size);

        if (!duplicado) {
            galeriaFiles.items.add(file);
            const reader = new FileReader();

            reader.onload = function (e) {
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

                wrapper.querySelector('.btn-delete').onclick = function () {
                    wrapper.remove();
                    const newDt = new DataTransfer();
                    Array.from(galeriaFiles.files).forEach(f => {
                        if (`${f.name}-${f.size}` !== fileId) newDt.items.add(f);
                    });
                    galeriaFiles = newDt;
                    input.files = galeriaFiles.files;
                    // PASAMOS LOS IDS DINÁMICAMENTE
                    actualizarContadorVisual(containerId, textId);
                };

                container.appendChild(wrapper);
                actualizarContadorVisual(containerId, textId);
            };
            reader.readAsDataURL(file);
        }
    }
    input.files = galeriaFiles.files;
}

function actualizarContadorVisual(containerId, textId) {
    const container = document.getElementById(containerId);
    const galText = document.getElementById(textId);
    if (!container) return;

    const items = container.querySelectorAll('.preview-item');
    const MAX_VISIBLES = 3;

    container.querySelectorAll('.more-indicator').forEach(el => el.remove());

    items.forEach((item, index) => {
        item.style.display = 'block';
        item.classList.remove('hidden');
        const img = item.querySelector('img');
        if (img) img.classList.remove('opacity-40');

        if (index >= MAX_VISIBLES) {
            item.style.display = 'none';
        }
    });

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

    if (galText) {
        galText.innerText = items.length > 0 ? `Ver (${items.length}) / Añadir` : "Añadir más";
    }
}

let imagenesPendientesEliminar = [];

// Las imágenes de galería eliminadas al editar un producto se guardan en un array para ser eliminadas al guardar los cambios
function eliminarImagenProducto(imagenId, wrapperElement) {
    Swal.fire({
        title: '<span class="text-lg font-bold uppercase tracking-widest text-white">¿Eliminar imagen?</span>',
        html: '<p class="text-gray-400 text-sm">La imagen se eliminará al guardar los cambios.</p>',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#ff0000ff',
        cancelButtonColor: '#334155',
        confirmButtonText: 'SÍ, ELIMINAR',
        cancelButtonText: 'CANCELAR',
        background: '#1e293b',
        customClass: {
            popup: 'rounded-3xl border border-gray-800 shadow-2xl',
            confirmButton: 'rounded-xl px-6 py-3 font-bold text-xs uppercase',
            cancelButton: 'rounded-xl px-6 py-3 font-bold text-xs uppercase'
        }
    }).then((result) => {
        if (result.isConfirmed) {

            // Guardamos el ID
            imagenesPendientesEliminar.push(imagenId);

            // Quitamos visualmente la imagen
            const parentElement = wrapperElement.parentElement;
            const parentId = parentElement?.id;

            wrapperElement.remove();

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
// Detectar si se presiona el botón guardar de productos
document.getElementById('btn-Guardar').addEventListener('click', () => {
    eliminarImagenesPendientes();
});

// Función para eliminar las imágenes pendientes
function eliminarImagenesPendientes() {
    if (imagenesPendientesEliminar.length === 0) return;

    const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;

    fetch('/administrador/inventario/productos/api/eliminar-imagenes/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrftoken,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            imagenes: imagenesPendientesEliminar
        })
    })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'ok') {
                imagenesPendientesEliminar = [];
                mostrarToast('success', 'Cambios guardados correctamente');
            }
        });
}


// Abrir modal de editar producto
function abrirEditarProducto(id) {
    const url = `/administrador/inventario/productos/api/${id}/`;

    // Limpiar archivos locales previos
    if (window.galeriaFiles) window.galeriaFiles = new DataTransfer();
    const inputFisico = document.getElementById('input-galeria-edit');
    if (inputFisico) inputFisico.value = "";

    fetch(url)
        .then(response => {
            if (!response.ok) throw new Error('Error al obtener datos');
            return response.json();
        })
        .then(data => {
            const galPreview = document.getElementById('preview-galeria-edit');
            // 1. Limpiar el contenedor pero PRESERVAR el botón de "Añadir"
            const btnAdd = galPreview.querySelector('button');
            galPreview.innerHTML = '';
            if (btnAdd) galPreview.appendChild(btnAdd);

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
                galPreview: document.getElementById('preview-galeria-edit')
            };

            if (elementos.galPreview) elementos.galPreview.innerHTML = '';

            if (elementos.nombre) elementos.nombre.value = data.nombre;
            if (elementos.categoria) elementos.categoria.value = data.categoria_id;
            if (elementos.precio) elementos.precio.value = data.precio_venta;
            if (elementos.peso) elementos.peso.value = data.peso_gramos;
            if (elementos.web) elementos.web.checked = data.mostrar_en_web;
            if (elementos.descripcion) elementos.descripcion.value = data.descripcion || '';

            if (data.imagen_url && elementos.preview) {
                elementos.preview.src = data.imagen_url;
                elementos.preview.classList.remove('hidden');
                if (elementos.content) elementos.content.classList.add('opacity-0');

                // Mostrar el botón de eliminar que acabamos de crear en el HTML
                const btnDel = document.getElementById('btnDeletePortadaEdit');
                if (btnDel) btnDel.classList.remove('hidden');

                // Asegurar que el flag de borrado inicie en "false" (por si abriste otro producto antes)
                const flag = document.getElementById('eliminar_portada_flag_edit');
                if (flag) flag.value = "false";
            } else {
                if (elementos.preview) elementos.preview.classList.add('hidden');
                if (elementos.content) elementos.content.classList.remove('opacity-0');

                // Ocultar botón de eliminar si no hay imagen que borrar
                const btnDel = document.getElementById('btnDeletePortadaEdit');
                if (btnDel) btnDel.classList.add('hidden');
            }

            if (data.imagenes_galeria && elementos.galPreview) {
                data.imagenes_galeria.forEach(imgData => {
                    const wrapper = document.createElement('div');
                    wrapper.className = "preview-item relative group aspect-square animate-in fade-in duration-300";
                    wrapper.innerHTML = `
                        <img src="${imgData.url}" class="w-full h-full object-cover rounded-lg border border-purple-500/20 shadow-sm transition-all">
                        <button type="button" onclick="eliminarImagenProducto('${imgData.id}', this.parentElement)" 
                                class="absolute -top-2 -right-2 bg-red-500 text-white rounded-full w-6 h-6 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all shadow-lg z-50">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                            </svg>
                        </button>
                    `;
                    // Insertar ANTES del botón de añadir
                    if (btnAdd) {
                        galPreview.insertBefore(wrapper, btnAdd);
                    } else {
                        galPreview.appendChild(wrapper);
                    }
                });
            }

            // 3. LLAMADA CORREGIDA: Pasar los IDs del modal de edición
            actualizarContadorVisual('preview-galeria-edit', 'text-galeria-edit');

            if (document.getElementById('formEditarProducto')) {
                document.getElementById('formEditarProducto').action = `/administrador/inventario/productos/${id}/editar/`;
            }

            abrirModal('modalEditarProducto');
        })
        .catch(error => {
            console.error('❌ Error en json:', error);
            mostrarToast('error', 'Error al cargar los datos');
        });
}

// Abrir modal de editar categoría
function abrirEditarCat(id) {
    const url = `/administrador/inventario/productos/categorias/api/${id}/`;

    fetch(url)
        .then(response => response.json())
        .then(data => {
            document.getElementById('edit_cat_nombre_titulo').innerText = `Modificando: ${data.nombre}`;
            document.getElementById('edit_cat_nombre').value = data.nombre;
            document.getElementById('edit_cat_descripcion').value = data.descripcion;

            const preview = document.getElementById('previewEdit');
            const zone = document.getElementById('zoneEdit');
            const btnDelete = document.getElementById('btnDeleteCatEdit');
            const inputHidden = document.getElementById('eliminar_imagen_input');

            // Resetear flag al abrir
            if (inputHidden) inputHidden.value = "false";

            if (data.imagen) {
                preview.src = data.imagen;
                preview.classList.remove('hidden');
                preview.style.opacity = "1";
                if (zone) zone.classList.add('border-solid', 'border-blue-500/60');
                if (btnDelete) btnDelete.classList.remove('hidden');
            } else {
                if (preview) preview.classList.add('hidden');
                if (zone) zone.classList.remove('border-solid', 'border-blue-500/60');
                if (btnDelete) btnDelete.classList.add('hidden');
            }

            document.getElementById('formEditarCategoria').action = `/administrador/inventario/productos/categorias/${id}/editar/`;
            abrirModal('modalEditarCat');
        })
        .catch(error => {
            console.error('Error:', error);
            mostrarToast('error', 'No se pudieron cargar los datos de la categoría');
        });
}

// Confirmar eliminación de categoría
function confirmarEliminarCategoria(id, nombre, redirectUrl) {
    document.getElementById('nombreCatEliminar').innerText = nombre;
    const btn = document.getElementById('btnConfirmarEliminar');

    btn.onclick = function () {
        btn.disabled = true;
        btn.innerHTML = `
            <svg class="animate-spin h-4 w-4 mr-2 inline-block" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg> ELIMINANDO...`;

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
                    mostrarToast('error', data.message);
                    btn.disabled = false;
                    btn.innerText = "SÍ, ELIMINAR";
                }
            })
            .catch(error => {
                console.error('Error:', error);
                mostrarToast('error', 'Error al procesar la solicitud');
                btn.disabled = false;
                btn.innerText = "SÍ, ELIMINAR";
            });
    };

    abrirModal('modalEliminarCategoria');
}

/**
 * Limpia la portada y activa el flag de eliminación para el backend
 */
function limpiarPreviewImagen(previewId, contentId, inputId, flagId) {
    Swal.fire({
        title: '<span class="text-lg font-bold uppercase tracking-widest text-white">¿Quitar Portada?</span>',
        html: '<p class="text-gray-400 text-sm">La imagen se eliminará permanentemente al guardar los cambios.</p>',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#ef4444',
        cancelButtonColor: '#334155',
        confirmButtonText: 'SÍ, QUITAR',
        cancelButtonText: 'CANCELAR',
        background: '#1e293b',
        customClass: {
            popup: 'rounded-3xl border border-gray-800 shadow-2xl',
            confirmButton: 'rounded-xl px-6 py-3 font-bold text-xs uppercase',
            cancelButton: 'rounded-xl px-6 py-3 font-bold text-xs uppercase'
        }
    }).then((result) => {
        if (result.isConfirmed) {
            const preview = document.getElementById(previewId);
            const content = document.getElementById(contentId);
            const input = document.getElementById(inputId);
            const flag = document.getElementById(flagId);

            const zone = preview.parentElement;
            const btnDelete = zone.querySelector('button[id^="btnDelete"]');
            if (preview) { preview.src = ""; preview.classList.add('hidden'); }
            if (content) { content.classList.remove('opacity-0', 'hidden'); }
            if (input) { input.value = ""; }
            if (flag) { flag.value = "true"; } // Esto es lo que lee Django
            if (btnDelete) { btnDelete.classList.add('hidden'); }

            mostrarToast('success', 'Portada marcada para eliminar');
        }
    });
}