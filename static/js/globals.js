// LÓGICA DEL SIDEBAR COLAPSABLE MINI
const btnToggle = document.getElementById('toggleSidebar');
const sidebar = document.getElementById('sidebar');
const overlay = document.getElementById('sidebarOverlay');
const mainContent = document.getElementById('mainContent');

// Verificar si hay un estado guardado en localStorage
function checkSidebarState() {
    const isMobile = window.innerWidth < 768;
    if (!isMobile) {
        const savedState = localStorage.getItem('sidebarMini');
        if (savedState === 'true') {
            sidebar.classList.add('mini');
            document.documentElement.classList.remove('sidebar-mini-init');
            sidebar.style.width = '5rem';
            mainContent.classList.replace('md:ml-64', 'md:ml-20');
        } else {
            // Asegurar que esté expandido si no está guardado como mini
            sidebar.classList.remove('mini');
            sidebar.style.width = '16rem';
        }
    }
}

function toggleMenu() {
    const isMobile = window.innerWidth < 768;

    if (isMobile) {
        // Comportamiento en móvil: Se desliza sobre el contenido
        sidebar.classList.toggle('-translate-x-full');
        overlay.classList.toggle('hidden');
    } else {
        // Comportamiento en escritorio: Minimiza/Expande
        const isCurrentlyMini = sidebar.classList.contains('mini');

        if (!isCurrentlyMini) {
            // Cambiar a modo mini (w-20)
            sidebar.classList.add('mini');
            sidebar.style.width = '5rem'; // 80px
            mainContent.classList.replace('md:ml-64', 'md:ml-20');
            localStorage.setItem('sidebarMini', 'true');
        } else {
            // Volver a modo expandido (w-64)
            sidebar.classList.remove('mini');
            sidebar.style.width = '16rem'; // 256px
            mainContent.classList.replace('md:ml-20', 'md:ml-64');
            localStorage.setItem('sidebarMini', 'false');
        }
    }
}

// Event listeners
if (btnToggle) btnToggle.addEventListener('click', toggleMenu);
if (overlay) overlay.addEventListener('click', toggleMenu);

// Re-ajustar si el usuario cambia el tamaño de la ventana
window.addEventListener('resize', () => {
    const isMobile = window.innerWidth < 768;

    if (!isMobile) {
        // Asegurar que el overlay esté oculto en desktop
        overlay.classList.add('hidden');
        sidebar.classList.remove('-translate-x-full');

        // Mantener el estado mini si estaba activo
        const savedState = localStorage.getItem('sidebarMini');
        if (savedState === 'true' && !sidebar.classList.contains('mini')) {
            sidebar.classList.add('mini');
            sidebar.style.width = '5rem';
            mainContent.classList.replace('md:ml-64', 'md:ml-20');
        } else if (savedState !== 'true' && sidebar.classList.contains('mini')) {
            sidebar.classList.remove('mini');
            sidebar.style.width = '16rem';
            mainContent.classList.replace('md:ml-20', 'md:ml-64');
        }
    } else {
        // En móvil, resetear estilos inline
        sidebar.style.width = '';
        sidebar.classList.remove('mini');
        mainContent.classList.remove('md:ml-20');
        mainContent.classList.add('md:ml-64');
    }
});

// Cargar el estado del sidebar al cargar la página
document.addEventListener('DOMContentLoaded', checkSidebarState);

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
    closeButton: 'text-gray-400 hover:text-white transition-colors focus:outline-none focus:shadow-none border-0 mt-4 mr-4',
    actions: 'pb-4',
    closeButtonHtml: `
      <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
      </svg>`,
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
        </div>`,

    questionBlue: `
    <div class="w-20 h-20 bg-blue-500/10 border border-blue-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
        <svg class="w-10 h-10 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
    </div>`,
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
