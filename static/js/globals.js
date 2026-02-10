
// LÓGICA DEL SIDEBAR RESPONSIVO
const btnToggle = document.getElementById('toggleSidebar');
const sidebar = document.getElementById('sidebar');
const overlay = document.getElementById('sidebarOverlay');

function toggleMenu() {
    sidebar.classList.toggle('-translate-x-full');
    overlay.classList.toggle('hidden');
}

btnToggle.addEventListener('click', toggleMenu);
overlay.addEventListener('click', toggleMenu);


window.swalConfigBase = window.swalConfigBase || {
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

window.swalCustomClasses = window.swalCustomClasses || {
    popup: 'bg-[#1e293b] border border-gray-800 rounded-2xl shadow-2xl relative', 
    title: 'text-xl font-bold text-white',
    htmlContainer: 'text-gray-300',
    confirmButton: 'px-4 py-3 rounded-xl border border-red-500 text-white bg-red-500 hover:bg-red-600 transition-all font-bold text-sm mx-2',
    cancelButton: 'px-4 py-3 rounded-xl border border-gray-700 text-gray-400 hover:bg-gray-800 transition-all font-bold text-sm mx-2',
    closeButton: 'absolute top-6 right-6 text-gray-400 hover:text-white transition-colors border-0 focus:shadow-none outline-none',
    actions: 'pb-4',
    closeButtonHtml: `<div class="absolute top-6 right-6 text-gray-400 hover:text-white transition-colors z-20">
      <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
      </svg>
    </div>`,
};

window.swalIcons = window.swalIcons || {
    // Icono de Peligro/Eliminar (Rojo)
    warningRed: `
        <div class="w-20 h-20 bg-red-500/10 border border-red-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg class="w-10 h-10 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
            </svg>
        </div>`,

    successGreen: `
        <div class="w-20 h-20 bg-emerald-500/10 border border-emerald-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg class="w-10 h-10 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
            </svg>
        </div>`,

    deleteProduct: `
        <div class="w-20 h-20 bg-amber-500/10 border border-amber-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg class="w-10 h-10 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-4v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
            </svg>
        </div>`
};

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
        timer: 6000,
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

// Cerrar modales con la tecla Escape
window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        cerrarModales();
    }
});

// Cerrar modales al hacer clic fuera de ellos
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal-overlay')) {
        cerrarModales();
    }
});
