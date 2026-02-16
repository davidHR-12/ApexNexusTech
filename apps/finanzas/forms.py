from django import forms
from django.core.exceptions import ValidationError
from decimal import Decimal
from .models import Gasto


# Widget para permitir múltiples archivos en la galería
class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


# Clase base para aplicar estilos de Tailwind rápidamente
class TailwindModelForm(forms.ModelForm):
    """
    Clase base que aplica automáticamente estilos Tailwind a todos los campos.
    Maneja checkboxes, inputs normales, selects, y textareas.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Si el objeto ya existe y es automático, deshabilitamos campos en el FORM
        if self.instance and hasattr(self.instance, 'es_automatico') and self.instance.es_automatico:
            campos_bloqueados = ['monto', 'fecha', 'tipo']
            for campo in campos_bloqueados:
                if campo in self.fields:
                    self.fields[campo].disabled = True # Django ignorará lo que venga del POST
        
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                # Estilos para checkboxes
                field.widget.attrs["class"] = (
                    "rounded border-gray-700 text-[#10b981] focus:ring-[#10b981] bg-gray-900"
                )
            elif isinstance(field.widget, forms.Textarea):
                # Estilos para textareas
                field.widget.attrs["class"] = (
                    "w-full bg-[#0f172a] border border-gray-700 rounded-xl px-4 py-3 text-white outline-none focus:border-[#10b981] font-mono text-sm"
                )
            elif isinstance(field.widget, forms.Select):
                # Estilos para selects
                field.widget.attrs["class"] = (
                    "w-full bg-[#0f172a] border border-gray-700 rounded-xl px-4 py-3 text-white outline-none focus:border-[#10b981] appearance-none"
                )
            else:
                # Estilos para inputs normales (text, number, date, etc.)
                field.widget.attrs["class"] = (
                    "w-full bg-[#0f172a] border border-gray-700 rounded-xl px-4 py-3 text-white outline-none focus:border-[#10b981]"
                )


class GastoForm(TailwindModelForm):
    """
    Formulario para crear y editar gastos.
    
    Incluye validaciones:
    - Monto positivo
    - Fecha no futura
    - Campos requeridos según contexto
    """
    
    class Meta:
        model = Gasto
        fields = ["descripcion", "monto", "fecha", "tipo", "notas"]
        widgets = {
            "fecha": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "w-full bg-[#0f172a] border border-gray-700 rounded-xl px-4 py-3 text-white outline-none focus:border-[#10b981]"
                }
            ),
            "notas": forms.Textarea(
                attrs={
                    "rows": 6,
                    "placeholder": "Notas opcionales...",
                    "class": "w-full bg-[#0f172a] border border-gray-700 rounded-xl px-4 py-3 text-white outline-none focus:border-[#10b981]"
                }
            ),
        }
    
    def clean_monto(self):
        """Valida que el monto sea positivo"""
        monto = self.cleaned_data.get('monto')
        if monto is not None and monto <= 0:
            raise ValidationError("El monto debe ser mayor a 0.")
        return monto
    
    def clean_fecha(self):
        """Valida que la fecha no sea futura"""
        from django.utils import timezone
        fecha = self.cleaned_data.get('fecha')
        if fecha and fecha > timezone.now().date():
            raise ValidationError("La fecha no puede ser futura.")
        return fecha


class GastoFormExtendido(TailwindModelForm):
    """
    Formulario extendido con todos los campos del modelo Gasto.
    Se usa para gastos que requieren más información (comprobantes, facturas, etc.)
    Incluye campo para eliminar comprobante (igual que ProductoForm)
    """
    
    # Campo extra para marcar eliminación de comprobante
    eliminar_comprobante = forms.CharField(
        required=False,
        widget=forms.HiddenInput()
    )
    
    class Meta:
        model = Gasto
        fields = [
            "descripcion", 
            "monto", 
            "fecha", 
            "tipo", 
            "proveedor",
            "numero_factura",
            "comprobante",
            "notas",
            "es_recurrente",
        ]
        widgets = {
            "fecha": forms.DateInput(attrs={"type": "date"}),
            "notas": forms.Textarea(attrs={"rows": 6}),
            "descripcion": forms.TextInput(
                attrs={"placeholder": "Descripción del gasto"}
            ),
            "proveedor": forms.TextInput(
                attrs={"placeholder": "Nombre del proveedor"}
            ),
            "numero_factura": forms.TextInput(
                attrs={"placeholder": "Ej: FAC-2024-001"}
            ),
            "comprobante": forms.FileInput(
                attrs={"accept": "image/*"}
            ),
        }
    
    def clean_monto(self):
        """Valida que el monto sea positivo"""
        monto = self.cleaned_data.get('monto')
        if monto is not None and monto <= 0:
            raise ValidationError("El monto debe ser mayor a 0.")
        return monto
    
    def clean_fecha(self):
        """Valida que la fecha no sea futura"""
        from django.utils import timezone
        fecha = self.cleaned_data.get('fecha')
        if fecha and fecha > timezone.now().date():
            raise ValidationError("La fecha no puede ser futura.")
        return fecha
    
    def clean_comprobante(self):
        comprobante = self.cleaned_data.get('comprobante')
        
        # Si no hay archivo, retornar lo que sea que haya (None o el actual)
        if not comprobante:
            return comprobante

        # VALIDACIÓN CRÍTICA: 
        # Solo validamos el content_type si es un archivo que se está subiendo ahora.
        # Los archivos que ya están en el servidor (al editar) no tienen 'content_type'.
        if hasattr(comprobante, 'content_type'):
            allowed_types = ['image/jpeg', 'image/png','image/webp']
            if comprobante.content_type not in allowed_types:
                raise forms.ValidationError("Solo se permiten archivos JPG, PNG o WEBP.")
            
            # Opcional: Validar tamaño (ej. 5MB)
            if comprobante.size > 5 * 1024 * 1024:
                raise forms.ValidationError("El archivo no debe exceder los 5MB.")

        return comprobante
    
    def save(self, commit=True):
        """
        Guarda el gasto manejando la eliminación del comprobante
        (Similar a ProductoForm.save())
        """
        gasto = super().save(commit=False)
        
        # Si se marcó eliminar comprobante, eliminarlo antes de guardar
        if self.cleaned_data.get('eliminar_comprobante') == 'true':
            if gasto.comprobante:
                gasto.comprobante.delete(save=False)
                gasto.comprobante = None
                print("Comprobante eliminado del gasto")
        
        if commit:
            gasto.save()
        
        return gasto