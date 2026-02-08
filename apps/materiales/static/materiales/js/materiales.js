// ============================================================================
// CONFIGURACIÓN DE SWEETALERT2
// ============================================================================

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


function abrirEditar(id) {
    const url = `/administrador/inventario/materiales/api/${id}/`;

    fetch(url)
        .then(r => r.json())
        .then(data => {
            const costo = document.getElementById('edit_costo');
            const stock = document.getElementById('edit_stock_minimo');
            const nombre = document.getElementById('edit_display_full_name');
            const tipo = document.getElementById('edit_display_tipo');
            const form = document.getElementById('formEditarMaterial');

            // Llenar campos numéricos
            if (costo) costo.value = data.costo_por_gramo;
            if (stock) stock.value = data.stock_minimo;

            // Llenar textos de visualización
            if (nombre) nombre.innerText = data.nombre || '';
            if (tipo) tipo.innerText = data.tipo || '';

            // Actualizar Action del Formulario
            if (form) {
                form.action = `/administrador/inventario/materiales/${id}/editar/`;
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
        .catch(err => console.error("Error al obtener material:", err));
}

function togglePerdida() {
    const section = document.getElementById('seccionPerdida');
    const check = document.getElementById('checkPerdida');
    if (section && check) {
        // "Toggle" la clase 'hidden' basado en si el check NO está marcado
        section.classList.toggle('hidden', !check.checked);
    }
}
// Función para seleccionar un material de la lista de resultados
function seleccionarMaterial(id, textoCompleto) {
    // 1. Ponemos el nombre bonito en el buscador para que el usuario sepa qué eligió
    const inputBusqueda = document.getElementById('material-search-input'); // El ID de tu input hx-get
    if (inputBusqueda) inputBusqueda.value = textoCompleto;

    // 2. Seteamos el ID real en el campo oculto del formulario
    // Asegúrate de que tu EntradaInventarioForm tenga un input hidden con este ID
    const inputHidden = document.getElementById('material-id-hidden');
    if (inputHidden) inputHidden.value = id;

    // 3. Limpiamos la lista de resultados
    const resultados = document.getElementById('search-results');
    if (resultados) resultados.innerHTML = '';
}
function seleccionarAtributo(tipo, nombre) {
    // 1. Setea el valor en el input correspondiente
    const input = document.getElementById(`input-${tipo}`);
    input.value = nombre;

    // 2. Limpia los resultados de HTMX
    document.getElementById(`results-${tipo}`).innerHTML = '';

    // 3. Opcional: Dar foco al siguiente input para agilizar la carga
    if (tipo === 'marca') document.getElementById('input-tipo').focus();
    if (tipo === 'tipo') document.getElementById('input-color').focus();
}

document.addEventListener('click', function (event) {
    // Definimos los IDs de los contenedores de resultados
    const contenedores = ['results-marca', 'results-tipo', 'results-color', 'search-results'];

    contenedores.forEach(id => {
        const resContainer = document.getElementById(id);
        const inputContainer = document.getElementById(`input-${id.split('-')[1]}`);

        // Si el clic no fue en el input ni en el contenedor de resultados, limpiamos
        if (resContainer && !resContainer.contains(event.target) && event.target !== inputContainer) {
            resContainer.innerHTML = '';
        }
    });
});

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
        iconHtml: `
            <div class="w-20 h-20 bg-red-500/10 border border-red-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg class="w-10 h-10 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
                </svg>
            </div>`,
        confirmButtonText: 'Sí, Eliminar',
        cancelButtonText: 'Cancelar',
        customClass: {
            ...swalCustomClasses,
            icon: 'border-0'
        }
    }).then((result) => {
        if (!result.isConfirmed) return;

        fetch(`/administrador/inventario/materiales/${id}/eliminar/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
                'Content-Type': 'application/json'
            }
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Mostramos el toast de éxito
                    mostrarToast('success', data.message);

                    // Esperamos un momento breve para que el usuario vea el toast antes de recargar
                    setTimeout(() => {
                        location.reload();
                    }, 1000);
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