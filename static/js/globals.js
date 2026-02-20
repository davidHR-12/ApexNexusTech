function smartRedirect(event, element) {
    const url = element.getAttribute('data-url');
    
    // Detectar si se presiona Ctrl/Cmd/Shift para abrir en nueva pestaña
    if (event.ctrlKey || event.metaKey || event.shiftKey) {
        window.open(url, '_blank');
    } else {
        window.location.href = url;
    }
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

    // Inicializar estado del sidebar si existe
    checkSidebarState();
});

// Referencias a elementos (pueden ser null en páginas públicas)
const btnToggle = document.getElementById('toggleSidebar');
const sidebar = document.getElementById('sidebar');
const overlay = document.getElementById('sidebarOverlay');
const mainContent = document.getElementById('mainContent');
const mobileMenuBtn = document.getElementById('mobileMenuBtn');

function checkSidebarState() {
    // Si no hay sidebar en esta página, no ejecutar nada
    if (!sidebar) return;

    const isMobile = window.innerWidth < 768;
    const savedState = localStorage.getItem('sidebarMini');

    if (!isMobile) {
        if (savedState === 'true') {
            applyMiniState();
        } else {
            applyFullState();
        }
    } else {
        sidebar.classList.add('-translate-x-full');
        sidebar.classList.remove('mini', 'w-20');
        if (mainContent) mainContent.classList.remove('md:ml-20');
    }
}

function applyMiniState() {
    if (!sidebar) return;
    document.documentElement.classList.add('sidebar-is-mini');
    sidebar.classList.add('mini');
    sidebar.classList.remove('w-64');
    sidebar.classList.add('w-20');
    if (mainContent) {
        mainContent.classList.remove('md:ml-64');
        mainContent.classList.add('md:ml-20');
    }
    localStorage.setItem('sidebarMini', 'true');
}

function applyFullState() {
    if (!sidebar) return;
    document.documentElement.classList.remove('sidebar-is-mini');
    sidebar.classList.remove('mini');
    sidebar.classList.remove('w-20');
    sidebar.classList.add('w-64');
    if (mainContent) {
        mainContent.classList.remove('md:ml-20');
        mainContent.classList.add('md:ml-64');
    }
    localStorage.setItem('sidebarMini', 'false');
}

function toggleMenu() {
    if (!sidebar) return;
    const isMobile = window.innerWidth < 768;

    if (isMobile) {
        const isHidden = sidebar.classList.contains('-translate-x-full');
        if (isHidden) {
            sidebar.classList.remove('-translate-x-full');
            if (overlay) overlay.classList.remove('hidden');
            document.body.classList.add('sidebar-open');
        } else {
            sidebar.classList.add('-translate-x-full');
            if (overlay) overlay.classList.add('hidden');
            document.body.classList.remove('sidebar-open');
        }
    } else {
        const isCurrentlyMini = sidebar.classList.contains('mini');
        if (!isCurrentlyMini) {
            applyMiniState();
        } else {
            applyFullState();
        }
    }
}

// Event listeners con Optional Chaining o validación
mobileMenuBtn?.addEventListener('click', toggleMenu);
btnToggle?.addEventListener('click', toggleMenu);
overlay?.addEventListener('click', () => {
    if (sidebar) sidebar.classList.add('-translate-x-full');
    if (overlay) overlay.classList.add('hidden');
    document.body.classList.remove('sidebar-open');
});

window.addEventListener('resize', () => {
    if (!sidebar) return;
    const isMobile = window.innerWidth < 768;

    if (!isMobile) {
        if (overlay) overlay.classList.add('hidden');
        sidebar.classList.remove('-translate-x-full');
        
        if (localStorage.getItem('sidebarMini') === 'true') {
            applyMiniState();
        } else {
            applyFullState();
        }
    } else {
        sidebar.classList.remove('mini', 'w-20');
        sidebar.classList.add('w-64', '-translate-x-full');
        if (mainContent) mainContent.classList.remove('md:ml-20', 'md:ml-64');
    }
});

document.addEventListener('DOMContentLoaded', checkSidebarState);

// ============================================================
//  CONFIGURACIÓN GLOBAL DE SWEETALERT2 (modales de confirmación)
// ============================================================
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

// ============================================================
//  SISTEMA DE TOASTS APILABLES
// ============================================================
function getToastContainer() {
    let container = document.getElementById('toast-stack-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-stack-container';
        container.style.cssText = `
            position: fixed;
            top: 1rem;
            right: 1rem;
            z-index: 99999;
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
            pointer-events: none;
            max-width: 360px;
            width: calc(100vw - 2rem);
        `;
        document.body.appendChild(container);
    }
    return container;
}

const TOAST_CONFIG = {
    success: {
        color: '#10b981',
        bg: 'rgba(16, 185, 129, 0.15)',
        border: 'rgba(16, 185, 129, 0.35)',
        svg: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />'
    },
    error: {
        color: '#ef4444',
        bg: 'rgba(239, 68, 68, 0.15)',
        border: 'rgba(239, 68, 68, 0.35)',
        svg: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />'
    },
    warning: {
        color: '#f59e0b',
        bg: 'rgba(245, 158, 11, 0.15)',
        border: 'rgba(245, 158, 11, 0.35)',
        svg: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />'
    },
    info: {
        color: '#3b82f6',
        bg: 'rgba(59, 130, 246, 0.15)',
        border: 'rgba(59, 130, 246, 0.35)',
        svg: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />'
    }
};

function mostrarToast(type, message, duration = 4000) {
    const sel = TOAST_CONFIG[type] || TOAST_CONFIG.success;
    const container = getToastContainer();

    // ── Crear el elemento toast ──────────────────────────────────
    const toast = document.createElement('div');
    toast.style.cssText = `
        position: relative;
        overflow: hidden;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.75rem;
        padding: 0.75rem 1rem;
        background-color: ${sel.bg};
        border: 1px solid ${sel.border};
        border-radius: 1rem;
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        box-shadow: 0 8px 32px rgba(0,0,0,0.4);
        pointer-events: auto;
        cursor: default;
        opacity: 0;
        transform: translateX(110%);
        transition: opacity 0.35s ease, transform 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
        will-change: opacity, transform;
        min-width: 0;
        width: 100%;
    `;

    toast.innerHTML = `
        <div style="display:flex; align-items:center; gap:0.75rem; min-width:0; flex:1;">
            <div style="color:${sel.color}; flex-shrink:0;">
                <svg width="22" height="22" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    ${sel.svg}
                </svg>
            </div>
            <span style="
                color: #f1f5f9;
                font-size: 0.875rem;
                font-weight: 600;
                letter-spacing: 0.01em;
                line-height: 1.4;
                word-break: break-word;
            ">${message}</span>
        </div>
        <button aria-label="Cerrar" style="
            flex-shrink: 0;
            background: none;
            border: none;
            cursor: pointer;
            color: #64748b;
            padding: 0.2rem;
            border-radius: 0.375rem;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: color 0.2s;
        " onmouseover="this.style.color='#f1f5f9'" onmouseout="this.style.color='#64748b'">
            <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
        </button>
    `;

    // ── Barra de progreso ────────────────────────────────────────
    const progressBar = document.createElement('div');
    progressBar.style.cssText = `
        position: absolute;
        bottom: 0;
        left: 0;
        height: 3px;
        border-radius: 0 0 1rem 1rem;
        background-color: ${sel.color};
        width: 100%;
        transform-origin: left;
        transition: transform ${duration}ms linear;
    `;
    toast.appendChild(progressBar);

    // ── Lógica de cierre ─────────────────────────────────────────
    let autoCloseTimer;
    let remaining = duration;
    let startTime;

    function closeToast() {
        clearTimeout(autoCloseTimer);
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(110%)';
        const h = toast.offsetHeight;
        toast.style.maxHeight = h + 'px';

        setTimeout(() => {
            toast.style.transition = 'opacity 0.3s, transform 0.3s, max-height 0.3s ease, margin 0.3s ease, padding 0.3s ease';
            toast.style.maxHeight = '0';
            toast.style.paddingTop = '0';
            toast.style.paddingBottom = '0';
            toast.style.margin = '0';
            setTimeout(() => { if (toast.parentNode) toast.remove(); }, 320);
        }, 300);
    }

    // Botón X
    toast.querySelector('button').addEventListener('click', closeToast);

    // Pausar al hacer hover
    toast.addEventListener('mouseenter', () => {
        clearTimeout(autoCloseTimer);
        remaining -= Date.now() - startTime;
        progressBar.style.transition = 'none';
    });

    toast.addEventListener('mouseleave', () => {
        progressBar.style.transition = `transform ${remaining}ms linear`;
        progressBar.style.transform = 'scaleX(0)';
        startTime = Date.now();
        autoCloseTimer = setTimeout(closeToast, remaining);
    });

    // ── Insertar y animar ────────────────────────────────────────
    container.appendChild(toast);

    requestAnimationFrame(() => {
        requestAnimationFrame(() => {
            toast.style.opacity = '1';
            toast.style.transform = 'translateX(0)';

            setTimeout(() => {
                progressBar.style.transform = 'scaleX(0)';
                startTime = Date.now();
                autoCloseTimer = setTimeout(closeToast, duration);
            }, 50);
        });
    });
}

// ============================================================
//  GESTIÓN DE MODALES
// ============================================================
let modalStack = [];

function abrirModal(id) {
    const modal = document.getElementById(id);
    if (modal) {
        modal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';

        if (!modalStack.includes(id)) {
            modalStack.push(id);
        }

        modal.style.zIndex = 50 + (modalStack.length * 10);
    }
}

function cerrarUltimoModal() {
    if (modalStack.length > 0) {
        const idParaCerrar = modalStack.pop();
        const modal = document.getElementById(idParaCerrar);
        if (modal) {
            modal.classList.add('hidden');
        }

        if (modalStack.length === 0) {
            document.body.style.overflow = 'auto';
        }
    }
}

function cerrarModales() {
    modalStack.forEach(id => {
        const modal = document.getElementById(id);
        if (modal) modal.classList.add('hidden');
    });
    modalStack = [];
    document.body.style.overflow = 'auto';
}

// Cerrar el último modal con Escape
window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && modalStack.length > 0) {
        cerrarUltimoModal();
    }
});

// Cerrar el último modal al hacer clic fuera
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal-overlay')) {
        if (e.target.id === modalStack[modalStack.length - 1]) {
            cerrarUltimoModal();
        }
    }
});