    // Unificamos la lógica de cierre para esta página
    function cerrarModales() {
        const wrapper = document.getElementById('modal-dinamico-wrapper');
        if (wrapper) wrapper.innerHTML = ''; // Eliminamos el HTML inyectado
        
        document.body.style.overflow = 'auto';
        
        // Cerramos cualquier otro modal estático por si acaso
        document.querySelectorAll('.modal-overlay').forEach(m => {
            m.classList.add('hidden');
        });
    }

    async function abrirModalDinamico(url) {
        // Limpieza preventiva antes de cargar uno nuevo
        cerrarModales(); 

        const wrapper = document.getElementById('modal-dinamico-wrapper');
        try {
            const response = await fetch(url);
            const html = await response.text();
            wrapper.innerHTML = html;
            
            // El modal base inyectado tiene la clase 'modal-overlay'
            const modalElement = wrapper.querySelector('.modal-overlay');
            if (modalElement) {
                modalElement.classList.remove('hidden');
                document.body.style.overflow = 'hidden';
            }
        } catch (error) {
            console.error('Error:', error);
            if (typeof mostrarToast === 'function') {
                mostrarToast('error', 'No se pudo cargar el formulario');
            }
        }
    }
    
    // LÓGICA DE ELIMINAR (Se mantiene igual)
    function confirmarEliminarVariante(id, color, tipo, marca) {
        Swal.fire({
            ...swalConfigBase,
            title: 'Eliminar variante',
            html: `Vas a eliminar la variante <b class="text-white">${marca} ${tipo} ${color}</b>.`,
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
                let urlEliminar = "{% url 'productos:eliminar_variante_json' 0 %}".replace('0', id);
                fetch(urlEliminar, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': '{{ csrf_token }}',
                        'Content-Type': 'application/json'
                    }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        mostrarToast('success', data.message);
                        location.reload(); 
                    } else {
                        mostrarToast('error', data.error);
                    }
                });
            }
        });
    }

    // EVENTOS GLOBALES RE-VINCULADOS
    // Usamos 'keydown' y 'click' para asegurar que llamen a NUESTRA cerrarModales
    window.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') cerrarModales();
    }, true); // El 'true' ayuda a que esta función tenga prioridad

    document.addEventListener('click', (e) => {
        if (e.target.classList.contains('modal-overlay')) {
            cerrarModales();
        }
    }, true);