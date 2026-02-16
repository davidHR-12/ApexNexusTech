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

    // Limpiar wrapper por si acaso
    wrapper.innerHTML = '';
    console.log(url);
    fetch(url)
        .then(response => {
            if (!response.ok) throw new Error("Error al cargar el formulario");
            return response.text();
        })
        .then(html => {
            wrapper.innerHTML = html;
            const modal = wrapper.querySelector('.modal-overlay');
            if (modal) {
                modal.classList.remove('hidden');
                // Push to stack for compatibility with globals.js cerrarUltimoModal
                if (typeof modalStack !== 'undefined') {
                    // Ensure ID exists (modal_base usa {{ modal_id }} que pasamos desde la vista)
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
    selectVariante.addEventListener('change', function() {
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

// --- LÓGICA PARA MODAL PERSONALIZADO ---
// Variable global para el precio
let precioGramoPers = 0;

function calcularSugeridoPersonalizado(contenedor) {
    // Buscamos los elementos DENTRO del contenedor (puede ser el modal de crear o el de editar)
    const inputGramos = contenedor.querySelector('[name="gramos_por_unidad"]');
    const inputCant = contenedor.querySelector('[name="cantidad"]');
    const inputPrecioVenta = contenedor.querySelector('[name="precio_unitario"]');
    
    // Los spans suelen estar fuera o tener IDs únicos
    const spanCostoG = document.getElementById('pers-costo-g');
    const spanInversionTotal = document.getElementById('pers-inversion-total');
    const spanSugerido = document.getElementById('pers-sugerido');
    const panelCostos = document.getElementById('panel-costos-pers');

    const gramos = parseFloat(inputGramos?.value) || 0;
    const cantidad = parseInt(inputCant?.value) || 1;
    
    if (gramos > 0 && precioGramoPers > 0) {
        const costoUnidad = gramos * precioGramoPers;
        const inversionTotal = costoUnidad * cantidad;
        const sugerido = (costoUnidad * 1.5).toFixed(2);
        
        if(spanCostoG) spanCostoG.innerText = `RD$ ${precioGramoPers.toFixed(2)}`;
        if(spanInversionTotal) spanInversionTotal.innerText = `RD$ ${inversionTotal.toFixed(2)}`;
        if(spanSugerido) spanSugerido.innerText = `RD$ ${sugerido}`;
        
        panelCostos?.classList.remove('hidden');
        if (inputPrecioVenta) inputPrecioVenta.value = sugerido;
    }
}

// Escuchar cambios en CUALQUIER input de gramos o cantidad que esté dentro de un modal
document.addEventListener('input', (e) => {
    if (e.target.name === 'gramos_por_unidad' || e.target.name === 'cantidad') {
        const modal = e.target.closest('.modal-overlay');
        if (modal) calcularSugeridoPersonalizado(modal);
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
                precioGramoPers = parseFloat(data.costo_por_gramo);
                calcularSugeridoPersonalizado(modal);
            });
    }
});