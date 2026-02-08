from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario

@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    # 1. Campos que se verán en el listado principal
    list_display = ('email', 'username', 'first_name', 'last_name', 'rol', 'is_email_verified', 'is_staff')
    
    # 2. Filtros laterales
    list_filter = ('rol', 'is_email_verified', 'is_staff', 'is_superuser', 'is_active')
    
    # 3. Campos por los que se puede buscar
    search_fields = ('email', 'username', 'first_name', 'last_name')
    
    # 4. Orden por defecto
    ordering = ('-date_joined',)

    # 5. Configuración de los formularios de edición (Fieldsets)
    # IMPORTANTE: UserAdmin usa fieldsets para organizar los campos. 
    # Aquí añadimos tus campos personalizados (rol, telefono, etc.)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Información Personal', {'fields': ('first_name', 'last_name', 'username', 'telefono')}),
        ('Roles y Permisos', {
            'fields': ('rol', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Verificación', {'fields': ('is_email_verified', 'last_verification_email')}),
        ('Fechas Importantes', {'fields': ('last_login', 'date_joined')}),
    )

    # 6. Configuración del formulario de creación (cuando das a "Añadir usuario")
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password', 'rol', 'is_email_verified'),
        }),
    )