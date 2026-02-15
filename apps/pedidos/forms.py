from django import forms
from .models import Pedido, ItemPedido, Impresora
from apps.materiales.models import Material # Importamos materiales
from django.contrib.auth import get_user_model
Usuario = get_user_model()

class TailwindModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "rounded border-gray-700 text-[#10b981] focus:ring-[#10b981] bg-gray-900"
            elif isinstance(field.widget, (forms.FileInput, forms.ClearableFileInput)):
                field.widget.attrs["class"] = "w-full text-sm text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-gray-800 file:text-emerald-400 hover:file:bg-gray-700"
            else:
                field.widget.attrs["class"] = "w-full bg-[#0f172a] border border-gray-700 rounded-xl px-4 py-3 text-white outline-none focus:border-[#10b981]"

class PedidoManualForm(TailwindModelForm):
    # Definimos el queryset y personalizamos la etiqueta
    usuario = forms.ModelChoiceField(
        queryset=Usuario.objects.all(),
        empty_label="Seleccione un cliente",
        label="Cliente"
    )
    class Meta:
        model = Pedido
        fields = ['usuario', 'descripcion','estado_pedido']
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Ej: Escultura de dragón personalizada...'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Aquí personalizamos lo que se ve en el select de usuarios
        self.fields['usuario'].label_from_instance = lambda obj: f"{obj.get_full_name_or_user()} - {obj.telefono if obj.telefono else 'Sin Tel.'}"

class ItemPedidoForm(TailwindModelForm):
    # Añadimos el queryset de materiales activos
    material_personalizado = forms.ModelChoiceField(
        queryset=Material.objects.filter(activo=True),
        required=False,
        label="Material para pieza personalizada",
        empty_label="Seleccione un material (Opcional)"
    )

    class Meta:
        model = ItemPedido
        fields = [
            'descripcion', 'material_personalizado', 'cantidad', 
            'gramos_por_unidad', 'precio_unitario', 'variante'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hacemos que estos campos no sean obligatorios para el navegador
        # La lógica de cuál se usa se maneja en el View
        self.fields['descripcion'].required = False
        self.fields['material_personalizado'].required = False
        self.fields['variante'].required = False
        self.fields['gramos_por_unidad'].required = False