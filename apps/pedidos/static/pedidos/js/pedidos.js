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
                // Si es 400, igual queremos leer el JSON para ver los errores
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
                    // 1. Seleccionar el cliente en el select
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
    // --- 1. Formateo de Teléfono ---
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

            // Reinicializar HTMX en el contenido nuevo
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
        text: "Esta acción no se puede deshacer.",
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
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                }
            })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        mostrarToast('success', data.message);
                        // Recargar para ver los nuevos totales actualizados hoy
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

                // 1. Asignar valores a los inputs
                modal.querySelector('[name="precio_unitario"]').value = data.precio_unitario;
                modal.querySelector('[name="gramos_por_unidad"]').value = data.gramos_por_unidad;

                // 2. Construir el desglose visualmente
                const base = data.precio_base.toLocaleString();
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

// 1. Lógica de selección del material (Mejorada para Edición)
function seleccionarMaterial(id, textoCompleto) {
    // Buscamos el modal que esté visible actualmente (el de arriba en el stack)
    const modalActivo = document.querySelector('.modal-overlay:not(.hidden)');
    if (!modalActivo) return;

    const inputBusqueda = modalActivo.querySelector('#material-search-input');
    // Buscamos el hidden por nombre si el ID falla o es dinámico
    const inputHidden = modalActivo.querySelector('input[name="material_personalizado"]');
    const resultados = modalActivo.querySelector('#search-results, #search-results-editar');

    if (inputBusqueda) inputBusqueda.value = textoCompleto;
    if (inputHidden) {
        inputHidden.value = id;
        // Disparar evento change manualmente para que otros listeners lo capten
        inputHidden.dispatchEvent(new Event('change', { bubbles: true }));
    }

    if (resultados) resultados.innerHTML = '';

    // Ejecutar cálculos
    calcularCostosPersonalizados();

    // Focus al siguiente campo
    const nextInput = modalActivo.querySelector('input[name="gramos_por_unidad"]');
    if (nextInput) nextInput.focus();
}


/**
 * 2. Función de cálculo de costos y actualización de precio unitario
 */
function calcularCostosPersonalizados() {
    const modalActivo = document.querySelector('.modal-overlay:not(.hidden)');
    if (!modalActivo) return;

    const inputHidden = modalActivo.querySelector('input[name="material_personalizado"]');
    const materialId = inputHidden ? inputHidden.value : null;

    const gramosInput = modalActivo.querySelector('input[name="gramos_por_unidad"]');
    const cantidadInput = modalActivo.querySelector('input[name="cantidad"]');
    const precioUnitarioInput = modalActivo.querySelector('input[name="precio_unitario"]'); // Agregado
    const panel = modalActivo.querySelector('#panel-costos-pers');

    const gramos = parseFloat(gramosInput?.value) || 0;
    const cantidad = parseFloat(cantidadInput?.value) || 1;

    if (!materialId || materialId === "" || gramos <= 0) {
        if (panel) panel.classList.add('hidden');
        return;
    }

    fetch(`/administrador/api/materiales/${materialId}/precio/`)
        .then(response => response.json())
        .then(data => {
            if (!modalActivo.isConnected) return;

            const costoGramo = parseFloat(data.costo_por_gramo || data.costo_gramo);
            const inversionTotal = costoGramo * gramos * cantidad;
            const precioSugerido = (costoGramo * gramos) * 1.5; // Sugerido por unidad

            // Actualizar Etiquetas del Panel
            const elCostoG = modalActivo.querySelector('#pers-costo-g');
            const elInversion = modalActivo.querySelector('#pers-inversion-total');
            const elSugerido = modalActivo.querySelector('#pers-sugerido');

            if (elCostoG) elCostoG.textContent = `RD$ ${costoGramo.toFixed(2)}`;
            if (elInversion) elInversion.textContent = `RD$ ${inversionTotal.toFixed(2)}`;
            if (elSugerido) elSugerido.textContent = `RD$ ${precioSugerido.toFixed(2)}`;

            // Actualizar precio solo si NO fue editado manualmente por el usuario
            if (precioUnitarioInput && precioUnitarioInput.dataset.manualEdit !== 'true') {
                precioUnitarioInput.value = precioSugerido.toFixed(2);
            }

            if (panel) panel.classList.remove('hidden');
        })
        .catch(err => console.error('Error calculando costos:', err));
}

// Marcar precio como "editado manualmente" cuando el usuario escribe
document.addEventListener('input', (e) => {
    if (e.target.name === 'precio_unitario') {
        e.target.dataset.manualEdit = 'true';
    }
});

/**
 * 3. Mejora UX: Permitir que al hacer clic en el precio sugerido se aplique al input
 */
document.addEventListener('click', (e) => {
    if (e.target.id === 'pers-sugerido') {
        const modalActivo = e.target.closest('.modal-overlay');
        const precioTexto = e.target.textContent.replace('RD$ ', '').trim();
        const precioInput = modalActivo?.querySelector('input[name="precio_unitario"]');

        if (precioInput) {
            precioInput.value = precioTexto;
            precioInput.dataset.manualEdit = 'false'; // Reset para que siga auto-actualizando
            mostrarToast('success', 'Precio sugerido aplicado');
        }
    }
});

// Escuchar cambios en CUALQUIER input de gramos o cantidad que esté dentro de un modal
document.addEventListener('input', (e) => {
    if (e.target.name === 'gramos_por_unidad' || e.target.name === 'cantidad') {
        console.log('[Input] Target:', e.target.name);
        console.log('[Input] Modal encontrado:', e.target.closest('.modal-overlay'));
        const modal = e.target.closest('.modal-overlay');
        if (modal) calcularCostosPersonalizados();
    }
});

// Escuchar cambios en el material
document.addEventListener('change', (e) => {
    if (e.target.name === 'material_personalizado') {
        const id = e.target.value;
        const modal = e.target.closest('.modal-overlay');
        if (!id || !modal) return;
        fetch(`/administrador/api/materiales/${id}/precio/`)
            .then(r => r.json())
            .then(data => {
                calcularCostosPersonalizados();
            });
    }
});

function confirmarRechazo(url, cliente) {
    Swal.fire({
        ...window.swalConfigBase, // Tu config de colores y blur
        customClass: window.swalCustomClasses,
        title: '¿Rechazar solicitud?',
        html: `¿Estás seguro de que deseas rechazar la solicitud de <b>${cliente}</b>? Esta acción no se puede deshacer.`,
        iconHtml: window.swalIcons.warningRed, // Usamos tu ícono rojo
        confirmButtonText: 'Sí, rechazar',
        cancelButtonText: 'Cancelar',
    }).then((result) => {
        if (result.isConfirmed) {
            // Creamos un formulario dinámico para hacer el POST
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = url;

            // Añadimos el token CSRF (importante en Django)
            const csrfInput = document.createElement('input');
            csrfInput.type = 'hidden';
            csrfInput.name = 'csrfmiddlewaretoken';
            csrfInput.value = '{{ csrf_token }}'; // Django inyectará esto

            form.appendChild(csrfInput);
            document.body.appendChild(form);
            form.submit();
        }
    });
}