const formClienteExpress = document.getElementById('formClienteExpress');
if (formClienteExpress) {
    formClienteExpress.addEventListener('submit', function (e) {
        e.preventDefault();
        const url = this.getAttribute('data-url');
        const formData = new FormData(this);
        fetch(url, {
            method: 'POST',
            body: formData,
            headers: { 'X-CSRFToken': formData.get('csrfmiddlewaretoken') }
        })
            .then(response => {
                return response.json().then(data => {
                    if (!response.ok) {
                        console.error("Errores del formulario:", data.errors);
                        return { success: false, errors: data.errors };
                    }
                    return data;
                });
            })
            .then(data => {
                if (data.success) {
                    const selectCliente = document.querySelector('select[name="usuario"]');
                    if (selectCliente) {
                        const textoOption = `${data.nombre} - ${data.telefono ? data.telefono : 'Sin Tel.'}`;
                        const newOption = new Option(textoOption, data.id, true, true);
                        selectCliente.add(newOption);
                    }
                    cerrarUltimoModal();
                    mostrarToast('success', 'Cliente creado correctamente');
                } else {
                    mostrarToast('error', "Error: " + JSON.stringify(data.errors));
                }
            });
    });
}

document.addEventListener("DOMContentLoaded", () => {
    const inputTelefono = document.querySelector('input[name="telefono"]');
    if (inputTelefono) {
        inputTelefono.addEventListener('input', function (e) {
            let x = e.target.value.replace(/\D/g, '').match(/(\d{0,3})(\d{0,3})(\d{0,4})/);
            e.target.value = !x[2] ? x[1] : x[1] + '-' + x[2] + (x[3] ? '-' + x[3] : '');
        });
        inputTelefono.maxLength = 12;
    }
});

// ==========================================
// GESTIÓN DE ÍTEMS (EDITAR / ELIMINAR)
// ==========================================

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

function abrirModalEditarItem(itemId, url) {
    const wrapper = document.getElementById('modal-editar-item-wrapper');
    if (!wrapper) return;

    wrapper.innerHTML = '';
    fetch(url)
        .then(response => {
            if (!response.ok) throw new Error("Error al cargar el formulario");
            return response.text();
        })
        .then(html => {
            wrapper.innerHTML = html;

            if (typeof htmx !== 'undefined') {
                htmx.process(wrapper);
            }

            const modal = wrapper.querySelector('.modal-overlay');
            if (modal) {
                modal.classList.remove('hidden');
                if (typeof modalStack !== 'undefined') {
                    if (!modal.id) modal.id = 'modalEditarItem';
                    if (!modalStack.includes(modal.id)) {
                        modalStack.push(modal.id);
                    }
                    modal.style.zIndex = 50 + (modalStack.length * 10);
                }
                document.body.style.overflow = 'hidden';
            }
        })
        .catch(err => {
            console.error(err);
            mostrarToast('error', 'No se pudo cargar la edición del ítem');
        });
}

function eliminarItem(itemId) {
    Swal.fire({
        ...swalConfigBase,
        title: '¿Eliminar ítem?',
        html: `Se eliminará este ítem del pedido y se recalcularán los totales.`,
        iconHtml: swalIcons.warningRed,
        confirmButtonText: 'Sí, eliminar',
        showCloseButton: true,
        cancelButtonText: 'Cancelar',
        customClass: {
            ...swalCustomClasses,
            icon: 'border-0'
        }
    }).then((result) => {
        if (result.isConfirmed) {
            fetch(`/administrador/pedidos/item/${itemId}/eliminar/`, {
                method: 'POST',
                headers: { 'X-CSRFToken': getCookie('csrftoken') }
            })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        mostrarToast('success', data.message);
                        setTimeout(() => location.reload(), 500);
                    } else {
                        mostrarToast('error', data.message || 'Error al eliminar');
                    }
                })
                .catch(err => {
                    console.error(err);
                    mostrarToast('error', 'Error de conexión');
                });
        }
    });
}

// ==========================================
// CONTENEDOR / COMPONENTES
// ==========================================

/**
 * Alterna la visibilidad de las filas de componentes de un contenedor.
 * Rota el chevron para indicar estado abierto/cerrado.
 */
function toggleComponentes(itemId) {
    const rows    = document.querySelectorAll(`.comp-rows-${itemId}`);
    const chevron = document.getElementById(`chevron-${itemId}`);
    const btn     = document.getElementById(`toggle-btn-${itemId}`);

    if (!rows.length) return;

    const isCurrentlyHidden = rows[0].classList.contains('hidden');
    
    // Si estaba oculto (true), ahora se va a mostrar (false)
    const shouldShow = isCurrentlyHidden; 

    rows.forEach(row => row.classList.toggle('hidden', !shouldShow));

    if (chevron) {
        chevron.style.transform = shouldShow ? 'rotate(90deg)' : 'rotate(0deg)';
    }

    // --- PERSISTENCIA ---
    // Guardamos "true" si está expandido, "false" si está colapsado
    localStorage.setItem(`tree-state-${itemId}`, shouldShow);
}

document.addEventListener('DOMContentLoaded', () => {
    // Buscamos todos los botones de toggle que tengan el patrón de ID
    const toggleButtons = document.querySelectorAll('[id^="toggle-btn-"]');

    toggleButtons.forEach(btn => {
        // Extraemos el ID numérico del ID del elemento (ej: de "toggle-btn-5" a "5")
        const itemId = btn.id.split('-').pop();
        const savedState = localStorage.getItem(`tree-state-${itemId}`);

        // Si el estado guardado es 'true', forzamos la apertura
        if (savedState === 'true') {
            const rows = document.querySelectorAll(`.comp-rows-${itemId}`);
            const chevron = document.getElementById(`chevron-${itemId}`);

            rows.forEach(row => row.classList.remove('hidden'));
            
            if (chevron) {
                chevron.style.transform = 'rotate(90deg)';
            }
            
            // Opcional: Aplicar estilos de botón activo si los usas
            btn.classList.add('bg-blue-500/20', 'border-blue-500/40');
        }
    });
});

/**
 * Abre el modal de agregar componente apuntando al URL correcto del ítem padre.
 * Actualiza la acción del formulario dinámicamente antes de abrir.
 */
function abrirModalComponente(itemId, url) {
    const form = document.getElementById('formAgregarComponente');
    if (form) {
        form.action = url;
        // Limpiar campos del form para reutilización
        form.reset();
        // Limpiar resultados de búsqueda si los hay
        const searchResults = document.getElementById('search-results-comp');
        if (searchResults) searchResults.innerHTML = '';
        // Ocultar panel de costos
        const panel = form.querySelector('#panel-costos-pers');
        if (panel) panel.classList.add('hidden');
    }
    abrirModal('modalAgregarComponente');
}


// ==========================================
// CATÁLOGO: desglose de precio por variante
// ==========================================
const selectVariante = document.querySelector('#modalItemCatalogo [name="variante"]');
if (selectVariante) {
    selectVariante.addEventListener('change', function () {
        const id = this.value;
        const infoPrecio = document.getElementById('detalle-precio-catalogo');

        if (!id) {
            infoPrecio.textContent = "Seleccione un producto para ver el desglose";
            return;
        }

        fetch(`/administrador/api/variante/${id}/precio/`)
            .then(r => r.json())
            .then(data => {
                const modal = document.getElementById('modalItemCatalogo');

                modal.querySelector('[name="precio_unitario"]').value = data.precio_unitario;
                modal.querySelector('[name="gramos_por_unidad"]').value = data.gramos_por_unidad;

                const base  = data.precio_base.toLocaleString();
                const extra = data.precio_extra.toLocaleString();
                const total = data.precio_unitario.toLocaleString();

                if (data.precio_extra > 0) {
                    infoPrecio.innerHTML = `<span class="text-emerald-400">Precio Base: RD$ ${base}</span> + <span class="text-amber-400">Precio Extra: RD$ ${extra}</span> = <b class="text-white">Precio Total: RD$ ${total}</b>`;
                } else {
                    infoPrecio.innerHTML = `Precio base: <b>RD$ ${base}</b> (Sin cargos extra)`;
                }
            });
    });
}

// ==========================================
// MATERIALES: búsqueda y cálculo de costos
// ==========================================

/**
 * Selecciona un material desde los resultados HTMX.
 * Funciona en cualquier modal activo (personalizado, editar, componente).
 */
function seleccionarMaterial(id, textoCompleto) {
    const modalActivo = document.querySelector('.modal-overlay:not(.hidden)');
    if (!modalActivo) return;

    // Soportar ambos IDs de input de búsqueda
    const inputBusqueda = modalActivo.querySelector('#material-search-input, #material-search-input-comp');
    const inputHidden   = modalActivo.querySelector('input[name="material_personalizado"]');
    const resultados    = modalActivo.querySelector('#search-results, #search-results-editar, #search-results-comp');

    if (inputBusqueda) inputBusqueda.value = textoCompleto;
    if (inputHidden) {
        inputHidden.value = id;
        inputHidden.dispatchEvent(new Event('change', { bubbles: true }));
    }
    if (resultados) resultados.innerHTML = '';

    calcularCostosPersonalizados();

    const nextInput = modalActivo.querySelector('input[name="gramos_por_unidad"]');
    if (nextInput) nextInput.focus();
}

/**
 * Calcula costos estimados y precio sugerido basado en material + gramos + cantidad.
 */
function calcularCostosPersonalizados() {
    const modalActivo = document.querySelector('.modal-overlay:not(.hidden)');
    if (!modalActivo) return;

    const inputHidden       = modalActivo.querySelector('input[name="material_personalizado"]');
    const materialId        = inputHidden ? inputHidden.value : null;
    const gramosInput       = modalActivo.querySelector('input[name="gramos_por_unidad"]');
    const cantidadInput     = modalActivo.querySelector('input[name="cantidad"]');
    const precioUnitarioInput = modalActivo.querySelector('input[name="precio_unitario"]');
    const panel             = modalActivo.querySelector('#panel-costos-pers');

    const gramos   = parseFloat(gramosInput?.value) || 0;
    const cantidad = parseFloat(cantidadInput?.value) || 1;

    if (!materialId || materialId === "" || gramos <= 0) {
        if (panel) panel.classList.add('hidden');
        return;
    }

    fetch(`/administrador/api/materiales/${materialId}/precio/`)
        .then(response => response.json())
        .then(data => {
            if (!modalActivo.isConnected) return;

            const costoGramo     = parseFloat(data.costo_por_gramo || data.costo_gramo);
            const inversionTotal = costoGramo * gramos * cantidad;
            const precioSugerido = costoGramo * gramos * 1.5;

            const elCostoG    = modalActivo.querySelector('#pers-costo-g');
            const elInversion = modalActivo.querySelector('#pers-inversion-total');
            const elSugerido  = modalActivo.querySelector('#pers-sugerido');

            if (elCostoG)    elCostoG.textContent    = `RD$ ${costoGramo.toFixed(2)}`;
            if (elInversion) elInversion.textContent = `RD$ ${inversionTotal.toFixed(2)}`;
            if (elSugerido)  elSugerido.textContent  = `RD$ ${precioSugerido.toFixed(2)}`;

            if (precioUnitarioInput && precioUnitarioInput.dataset.manualEdit !== 'true') {
                precioUnitarioInput.value = precioSugerido.toFixed(2);
            }

            if (panel) panel.classList.remove('hidden');
        })
        .catch(err => console.error('Error calculando costos:', err));
}

// Marcar precio como editado manualmente cuando el usuario escribe
document.addEventListener('input', (e) => {
    if (e.target.name === 'precio_unitario') {
        e.target.dataset.manualEdit = 'true';
    }
});

// Clic en precio sugerido → aplicar al input
document.addEventListener('click', (e) => {
    if (e.target.id === 'pers-sugerido') {
        const modalActivo = e.target.closest('.modal-overlay');
        const precioTexto = e.target.textContent.replace('RD$ ', '').trim();
        const precioInput = modalActivo?.querySelector('input[name="precio_unitario"]');
        if (precioInput) {
            precioInput.value = precioTexto;
            precioInput.dataset.manualEdit = 'false';
            mostrarToast('success', 'Precio sugerido aplicado');
        }
    }
});

// Recalcular al cambiar gramos o cantidad
document.addEventListener('input', (e) => {
    if (e.target.name === 'gramos_por_unidad' || e.target.name === 'cantidad') {
        const modal = e.target.closest('.modal-overlay');
        if (modal) calcularCostosPersonalizados();
    }
});

// Recalcular al cambiar el material (hidden input)
document.addEventListener('change', (e) => {
    if (e.target.name === 'material_personalizado') {
        const id    = e.target.value;
        const modal = e.target.closest('.modal-overlay');
        if (!id || !modal) return;
        fetch(`/administrador/api/materiales/${id}/precio/`)
            .then(r => r.json())
            .then(() => calcularCostosPersonalizados());
    }
});

// ==========================================
// SOLICITUDES: confirmar rechazo
// ==========================================
function confirmarRechazo(url, cliente) {
    Swal.fire({
        ...window.swalConfigBase,
        customClass: window.swalCustomClasses,
        title: '¿Rechazar solicitud?',
        html: `¿Estás seguro de que deseas rechazar la solicitud de <b>${cliente}</b>? Esta acción no se puede deshacer.`,
        iconHtml: window.swalIcons.warningRed,
        confirmButtonText: 'Sí, rechazar',
        cancelButtonText: 'Cancelar',
    }).then((result) => {
        if (result.isConfirmed) {
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = url;

            const csrfInput = document.createElement('input');
            csrfInput.type = 'hidden';
            csrfInput.name = 'csrfmiddlewaretoken';
            csrfInput.value = getCookie('csrftoken');

            form.appendChild(csrfInput);
            document.body.appendChild(form);
            form.submit();
        }
    });
}
// ==========================================
// NOTAS: eliminar nota manual
// ==========================================

const NOTA_LIMITE_MINUTOS = 10;

function confirmarEliminarNota(url, btn) {
    // Verificar en el cliente antes de llamar al servidor
    const createdAt = new Date(btn.getAttribute('data-created'));
    const ahora     = new Date();
    const minutos   = (ahora - createdAt) / 1000 / 60;

    if (minutos > NOTA_LIMITE_MINUTOS) {
        mostrarToast('warning', 'Solo puedes eliminar notas dentro de los primeros 10 minutos.');
        return;
    }

    Swal.fire({
        ...swalConfigBase,
        title: 'Eliminar nota',
        html: 'Esta nota desaparecerá del historial permanentemente.',
        iconHtml: swalIcons.warningRed,
        confirmButtonText: 'Sí, eliminar',
        cancelButtonText: 'Cancelar',
        showCloseButton: true,
        customClass: { ...swalCustomClasses, icon: 'border-0' }
    }).then(result => {
        if (!result.isConfirmed) return;

        const form  = document.createElement('form');
        form.method = 'POST';
        form.action = url;

        const csrf  = document.createElement('input');
        csrf.type   = 'hidden';
        csrf.name   = 'csrfmiddlewaretoken';
        csrf.value  = getCookie('csrftoken');

        form.appendChild(csrf);
        document.body.appendChild(form);
        form.submit();
    });
}

// Desactiva visualmente los botones de notas que ya pasaron los 10 minutos
function actualizarBotonesNota() {
    document.querySelectorAll('.nota-btn-eliminar').forEach(btn => {
        const createdAt = new Date(btn.getAttribute('data-created'));
        const minutos   = (new Date() - createdAt) / 1000 / 60;

        if (minutos > NOTA_LIMITE_MINUTOS) {
            btn.disabled = true;
            btn.classList.add('opacity-30', 'cursor-not-allowed', 'hover:bg-transparent', 'hover:text-red-400');
            btn.title    = 'Tiempo de eliminación expirado (10 min)';
        }
    });
}

// Ejecutar al cargar y cada 30 segundos para actualizar sin recargar
document.addEventListener('DOMContentLoaded', actualizarBotonesNota);
setInterval(actualizarBotonesNota, 30_000);