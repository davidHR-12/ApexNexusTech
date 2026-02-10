// ============================================================================
// CONFIGURACIÓN DE SWEETALERT2
// ============================================================================
function abrirEditar(id) {
    const url = `/administrador/api/materiales/${id}/`;

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
                form.action = `/administrador/materiales/${id}/editar/`;
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

    // Salto automático al siguiente input para velocidad de escritura
    const proximoInput = document.querySelector('input[name="cantidad_gramos"]');
    if (proximoInput) proximoInput.focus();

    document.querySelector('input[name="cantidad_gramos"]').focus();
}

function seleccionarAtributo(tipo, nombre) {
    const input = document.getElementById(`input-${tipo}`);
    if (input) {
        input.value = nombre;
        // Importante: le decimos a HTMX que no busque esto
        input.dispatchEvent(new Event('htmx:abort'));
    }

    // Limpia los resultados
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

// Función para confirmar eliminación de atributos
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
                        // Cerramos modales y recargamos para limpiar la lista principal
                        cerrarModales();
                        setTimeout(() => location.reload(), 800);
                    } else {
                        // Si tiene materiales asociados, la vista devolverá success: false
                        Swal.fire({
                            ...swalConfigBase,
                            title: 'No se puede eliminar',
                            text: data.message,
                            icon: 'error'
                        });
                    }
                })
                .catch(error => mostrarToast('error', 'Error en la solicitud'));
        }
    });
}

function cambiarTab(event, tabId) {
    // 1. Ocultar todos los contenidos
    document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));

    // 2. Resetear todos los botones
    document.querySelectorAll('.tab-btn').forEach(btn => {
        // Quitamos el estado activo
        btn.classList.remove('bg-emerald-600', 'text-white');
        // Devolvemos el estado inactivo
        btn.classList.add('text-gray-500', 'hover:text-gray-300');
    });

    // 3. Mostrar el contenido seleccionado
    document.getElementById(tabId).classList.remove('hidden');

    // 4. Activar el botón clicado
    const activo = event.currentTarget;
    activo.classList.remove('text-gray-500', 'hover:text-gray-300');
    activo.classList.add('bg-emerald-600', 'text-white');
}

// Usamos un objeto global para evitar duplicados
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
                    // Lógica estándar (Bajamos en la lista)
                    currentIndex = (currentIndex + 1 < items.length) ? currentIndex + 1 : 0;
                    window.MaterialesHandlers.actualizarSeleccion(items, currentIndex);
                }
                else if (e.key === 'ArrowUp') {
                    e.preventDefault();
                    // Lógica estándar (Subimos en la lista)
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
                // Quitamos el estilo manual por si acaso
                item.style.backgroundColor = "";
            });

            const activeItem = items[index];
            if (activeItem) {
                activeItem.classList.add('item-active');
                // Forzamos el color con JS para asegurar que se vea
                activeItem.style.backgroundColor = "rgba(37, 99, 235, 0.4)";
                activeItem.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
            }
        }
    };

    // Solo agregamos el evento la PRIMERA vez que se carga el archivo
    document.addEventListener('keydown', window.MaterialesHandlers.keydown);
}