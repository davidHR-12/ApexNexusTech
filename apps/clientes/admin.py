from django.contrib import admin
from .models import PerfilCliente, HistorialCliente

# =============================
# INLINES
# =============================

class HistorialClienteInline(admin.TabularInline):
    """Permite ver y agregar notas de interacción desde el perfil"""
    model = HistorialCliente
    extra = 1
    fields = ('tipo', 'descripcion', 'usuario_registra', 'fecha')
    readonly_fields = ('fecha',)

# =============================
# CONFIGURACIÓN DEL ADMIN
# =============================

@admin.register(PerfilCliente)
class PerfilClienteAdmin(admin.ModelAdmin):
    # 1. Columnas de la lista
    list_display = ('get_email', 'get_nombre', 'empresa', 'ciudad', 'fecha_registro', 'recibir_notificaciones')
    list_filter = ('ciudad', 'recibir_notificaciones', 'fecha_registro')
    search_fields = ('usuario__email', 'usuario__first_name', 'usuario__last_name', 'empresa')
    
    # 2. Integrar el historial en la misma vista
    inlines = [HistorialClienteInline]
    
    # 3. Organización del formulario
    fieldsets = (
        ('Usuario Vinculado', {
            'fields': ('usuario',)
        }),
        ('Información Corporativa', {
            'fields': ('empresa', 'notas')
        }),
        ('Ubicación y Contacto', {
            'fields': ('direccion', 'ciudad', 'codigo_postal')
        }),
        ('Preferencias y Sistema', {
            'fields': ('recibir_notificaciones', 'fecha_registro'),
        }),
    )
    readonly_fields = ('fecha_registro',)

    # Métodos para mostrar datos del Usuario relacionado
    def get_email(self, obj):
        return obj.usuario.email
    get_email.short_description = 'Email'
    get_email.admin_order_field = 'usuario__email'

    def get_nombre(self, obj):
        return f"{obj.usuario.first_name} {obj.usuario.last_name}"
    get_nombre.short_description = 'Nombre completo'

@admin.register(HistorialCliente)
class HistorialClienteAdmin(admin.ModelAdmin):
    list_display = ('cliente', 'tipo', 'fecha', 'usuario_registra')
    list_filter = ('tipo', 'fecha')
    search_fields = ('cliente__usuario__email', 'descripcion')