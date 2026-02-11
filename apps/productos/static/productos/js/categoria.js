// ============================================================================
// CATEGORIAS.JS - Gestión de Categorías
// ============================================================================

/**
 * Abre el modal de edición de categoría y carga sus datos vía API
 * @param {number|string} id - ID de la categoría a editar
 */
function abrirEditarCat(id) {
    const url = `/administrador/api/categorias/${id}/`;

    fetch(url)
        .then(response => {
            if (!response.ok) throw new Error('Error al obtener datos');
            return response.json();
        })
        .then(data => {
            // Configurar action del formulario
            const form = document.getElementById('formEditarCategoria');
            if (form) {
                form.action = `/administrador/categorias/${id}/editar/`;
            }
            // Actualizar título del modal
            const titulo = document.getElementById('edit_cat_nombre_titulo');
            if (titulo) titulo.innerText = `Modificando: ${data.nombre}`;

            // Rellenar campos
            const inputNombre = document.getElementById('edit_cat_nombre');
            const inputDesc = document.getElementById('edit_cat_descripcion');
            if (inputNombre) inputNombre.value = data.nombre;
            if (inputDesc) inputDesc.value = data.descripcion;

            const inputOrden = document.getElementById('edit_cat_orden');
            if (inputOrden) {
                // Usamos Number() para asegurar que sea un dígito y || 0 por si viene null
                const valorOrden = (data.orden !== undefined && data.orden !== null) ? data.orden : 0;
                inputOrden.value = valorOrden;
            }
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

            abrirModal('modalEditarCat');
        })
        .catch(error => {
            mostrarToast('error', 'No se pudieron cargar los datos de la categoría');
        });
}

/**
 * Confirma y ejecuta la eliminación de una categoría con SweetAlert2
 */
function confirmarEliminarCategoria(id, nombre, redirectUrl) {
    Swal.fire({
        ...swalConfigBase,
        title: 'Eliminar Categoría',
        html: `
            <div class="text-center">
                <p class="text-gray-300 mb-2">Estás por eliminar:</p>
                <p class="text-white font-semibold text-lg">${nombre}</p>
                <p class="text-gray-400 text-sm mt-3 border-t border-gray-700/50 pt-3">Esta acción no se puede deshacer y los productos se moverán a "Sin Categorizar".</p>
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
        if (result.isConfirmed) {
            fetch(`/administrador/categorias/${id}/eliminar/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
                }
            })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        window.location.href = redirectUrl;
                    } else {
                        mostrarToast('error', data.message || 'Error al eliminar');
                    }
                })
                .catch(() => {
                    mostrarToast('error', 'Ocurrió un error en el servidor');
                });
        }
    });
}