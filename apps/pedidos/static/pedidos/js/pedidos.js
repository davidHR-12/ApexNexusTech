const formClienteExpress = document.getElementById('formClienteExpress');
if (formClienteExpress) {
    formClienteExpress.addEventListener('submit', function(e) {
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
                alert("Error: " + JSON.stringify(data.errors));
                mostrarToast('error', 'Error al crear el cliente');
            }
        });
    });
}

// Bloquear letras en el campo de teléfono
const inputTelefono = document.querySelector('input[name="telefono"]');

if (inputTelefono) {
    inputTelefono.addEventListener('input', function(e) {
        // Solo permite números. Reemplaza cualquier cosa que NO sea 0-9 con vacío.
        this.value = this.value.replace(/[^0-9]/g, '');
    });
}

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

function abrirModalEditarItem(itemId) {
    const wrapper = document.getElementById('modal-editar-item-wrapper');
    if(!wrapper) return;
    
    // Limpiar wrapper por si acaso
    wrapper.innerHTML = '';
    
    fetch(`/administrador/pedidos/item/${itemId}/editar/`)
    .then(response => {
        if(!response.ok) throw new Error("Error al cargar el formulario");
        return response.text();
    })
    .then(html => {
        wrapper.innerHTML = html;
        const modal = wrapper.querySelector('.modal-overlay');
        if(modal) {
             modal.classList.remove('hidden');
             // Push to stack for compatibility with globals.js cerrarUltimoModal
             if(typeof modalStack !== 'undefined') {
                 // Ensure ID exists (modal_base usa {{ modal_id }} que pasamos desde la vista)
                 if(!modal.id) modal.id = 'modalEditarItem';
                 if(!modalStack.includes(modal.id)) {
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
                if(data.success) {
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