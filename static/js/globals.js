
// Mostrar toast o mensaje dependiendo del tipo
function mostrarToast(type, message) {
    // Definimos la configuración según el tipo
    const config = {
        success: {
            color: '#10b981',
            bg: 'rgba(16, 185, 129, 0.2)',
            border: 'rgba(16, 185, 129, 0.3)',
            svg: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />'
        },
        error: {
            color: '#ef4444',
            bg: 'rgba(239, 68, 68, 0.2)',
            border: 'rgba(239, 68, 68, 0.3)',
            svg: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />'
        },
        warning: {
            color: '#f59e0b',
            bg: 'rgba(245, 158, 11, 0.2)',
            border: 'rgba(245, 158, 11, 0.3)',
            svg: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />'
        }
    };

    const sel = config[type] || config.success;

    const Toast = Swal.mixin({
        toast: true,
        position: 'top',
        showConfirmButton: false,
        timer: 4000,
        background: '#1e293b',
        didOpen: (toast) => {
            toast.style.backdropFilter = 'blur(12px)';
            toast.style.backgroundColor = sel.bg;
            toast.style.border = `1px solid ${sel.border}`;
            toast.style.borderRadius = '1rem';
            
            // Forzamos que el icono nativo de SWAL no aparezca si usamos el nuestro
            const swalIcon = toast.querySelector('.swal2-icon');
            if (swalIcon) swalIcon.style.display = 'none';
        }
    });

    Toast.fire({
        html: `
        <div class="flex items-center gap-3">
            <div style="color: ${sel.color}">
                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    ${sel.svg}
                </svg>
            </div>
            <span class="text-white text-sm font-semibold tracking-wide">${message}</span>
        </div>`
    });
}

// Abrir modal
function abrirModal(id) {
    const modal = document.getElementById(id);
    if (modal) {
        modal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
    }
}

// Cerrar modal
function cerrarModales() {
    const modales = document.querySelectorAll('[id^="modal"]');
    modales.forEach(modal => modal.classList.add('hidden'));
    document.body.style.overflow = 'auto';
}