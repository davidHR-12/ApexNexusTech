from django.contrib import admin
from .models import ReporteGuardado, ConfiguracionDashboard

@admin.register(ReporteGuardado)
class ReporteGuardadoAdmin(admin.ModelAdmin):
    # 1. Columnas de la lista
    list_display = ('nombre', 'tipo', 'usuario', 'fecha_creacion', 'es_publico')
    
    # 2. Filtros y búsqueda
    list_filter = ('tipo', 'es_publico', 'fecha_creacion', 'usuario')
    search_fields = ('nombre', 'descripcion')
    
    # 3. Campos de solo lectura
    readonly_fields = ('fecha_creacion',)

    # 4. Organización del formulario
    fieldsets = (
        ('Información General', {
            'fields': ('nombre', 'tipo', 'descripcion', 'usuario')
        }),
        ('Parámetros Técnicos', {
            'classes': ('collapse',), # Esto hace que la sección sea colapsable
            'fields': ('configuracion',),
            'description': 'Configuración interna del reporte en formato JSON.'
        }),
        ('Visibilidad', {
            'fields': ('es_publico', 'fecha_creacion')
        }),
    )

    def save_model(self, request, obj, form, change):
        """Asigna automáticamente el usuario actual si no se especifica uno"""
        if not obj.usuario_id:
            obj.usuario = request.user
        super().save_model(request, obj, form, change)


@admin.register(ConfiguracionDashboard)
class ConfiguracionDashboardAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'periodo_grafico_ventas', 'mostrar_ventas_dia', 'mostrar_pedidos_pendientes')
    list_filter = ('periodo_grafico_ventas',)
    search_fields = ('usuario__email', 'usuario__first_name')
    
    # Organización por categorías de widgets
    fieldsets = (
        ('Usuario', {
            'fields': ('usuario',)
        }),
        ('Configuración de Visualización', {
            'fields': (
                'periodo_grafico_ventas',
                'mostrar_ventas_dia',
                'mostrar_pedidos_pendientes',
                'mostrar_stock_bajo',
                'mostrar_ultimos_gastos',
                'mostrar_grafico_ventas',
            )
        }),
    )