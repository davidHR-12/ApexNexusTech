// LÓGICA DEL SIDEBAR COLAPSABLE OPTIMIZADA
const btnToggle = document.getElementById('toggleSidebar');
const sidebar = document.getElementById('sidebar');
const overlay = document.getElementById('sidebarOverlay');
const mainContent = document.getElementById('mainContent');
const mobileMenuBtn = document.getElementById('mobileMenuBtn');
const mobileSidebar = document.getElementById('mobileSidebar');
const mobileOverlay = document.getElementById('mobileOverlay');

function checkSidebarState() {
    const isMobile = window.innerWidth < 768;
    const savedState = localStorage.getItem('sidebarMini');

    if (!isMobile) {
        if (savedState === 'true') {
            applyMiniState();
        } else {
            applyFullState(); // Esto asegura que se limpie cualquier clase de inicialización
        }
    } else {
        // En móvil siempre empezamos ocultos
        sidebar.classList.add('-translate-x-full');
        // Limpiamos rastro de mini por si venimos de desktop
        sidebar.classList.remove('mini', 'w-20');
        mainContent.classList.remove('md:ml-20');
    }
}

function applyMiniState() {
    sidebar.classList.add('mini');
    // Sidebar
    sidebar.classList.remove('w-64');
    sidebar.classList.add('w-20');
    // Contenido
    mainContent.classList.remove('md:ml-64');
    mainContent.classList.add('md:ml-20');
    
    localStorage.setItem('sidebarMini', 'true');
}

function applyFullState() {
    // IMPORTANTE: Quitamos la clase de inicialización para que no bloquee más
    document.documentElement.classList.remove('sidebar-is-mini');
    
    sidebar.classList.remove('mini');
    // Sidebar
    sidebar.classList.remove('w-20');
    sidebar.classList.add('w-64');
    // Contenido
    mainContent.classList.remove('md:ml-20');
    mainContent.classList.add('md:ml-64');
    
    localStorage.setItem('sidebarMini', 'false');
}

function toggleMenu() {
    const isMobile = window.innerWidth < 768;

    if (isMobile) {
        // En móvil quitamos/ponemos el translate y mostramos el overlay
        const isHidden = sidebar.classList.contains('-translate-x-full');
        if (isHidden) {
            sidebar.classList.remove('-translate-x-full');
            overlay.classList.remove('hidden');
            document.body.classList.add('sidebar-open');
        } else {
            sidebar.classList.add('-translate-x-full');
            overlay.classList.add('hidden');
            document.body.classList.remove('sidebar-open');
        }
    } else {
        // Lógica de escritorio (Mini/Full)
        const isCurrentlyMini = sidebar.classList.contains('mini');
        if (!isCurrentlyMini) {
            applyMiniState();
            localStorage.setItem('sidebarMini', 'true');
        } else {
            applyFullState();
            localStorage.setItem('sidebarMini', 'false');
        }
    }
}

// Event listeners
mobileMenuBtn?.addEventListener('click', toggleMenu);
btnToggle?.addEventListener('click', toggleMenu);
overlay?.addEventListener('click', () => {
    sidebar.classList.add('-translate-x-full');
    overlay.classList.add('hidden');
    document.body.classList.remove('sidebar-open');
});

window.addEventListener('resize', () => {
    const isMobile = window.innerWidth < 768;

    if (!isMobile) {
        // Desktop
        overlay.classList.add('hidden');
        sidebar.classList.remove('-translate-x-full');
        
        // Restaurar estado según localStorage
        if (localStorage.getItem('sidebarMini') === 'true') {
            applyMiniState();
        } else {
            applyFullState();
        }
    } else {
        // Móvil: Limpiar clases de escritorio para que no estorben
        sidebar.classList.remove('mini', 'w-20');
        sidebar.classList.add('w-64', '-translate-x-full');
        mainContent.classList.remove('md:ml-20', 'md:ml-64');
    }
});

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


let modalStack = [];

// Abrir modal
function abrirModal(id) {
    const modal = document.getElementById(id);
    if (modal) {
        modal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';

        // Agregamos al stack si no estaba ya (evita duplicados)
        if (!modalStack.includes(id)) {
            modalStack.push(id);
        }

        modal.style.zIndex = 50 + (modalStack.length * 10);
    }
}


// Función para cerrar SOLO el modal más reciente
function cerrarUltimoModal() {
    if (modalStack.length > 0) {
        const idParaCerrar = modalStack.pop();
        const modal = document.getElementById(idParaCerrar);
        if (modal) {
            modal.classList.add('hidden');
        }
        
        // Si ya no quedan modales abiertos, devolvemos el scroll al body
        if (modalStack.length === 0) {
            document.body.style.overflow = 'auto';
        }
    }
}

// Cerrar modal
function cerrarModales() {
    modalStack.forEach(id => {
        const modal = document.getElementById(id);
        if (modal) modal.classList.add('hidden');
    });
    modalStack = [];
    document.body.style.overflow = 'auto';
}

// Cerrar SOLO EL ÚLTIMO con Escape
window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && modalStack.length > 0) {
        cerrarUltimoModal();
    }
});

// Cerrar SOLO EL ÚLTIMO al hacer clic fuera
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal-overlay')) {
        // Importante: El overlay que clickeas debe ser el del modal superior
        if (e.target.id === modalStack[modalStack.length - 1]) {
            cerrarUltimoModal();
        }
    }
});
