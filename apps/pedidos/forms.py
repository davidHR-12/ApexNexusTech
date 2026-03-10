from django import forms
from .models import Pedido, ItemPedido
from apps.materiales.models import Material
from django.contrib.auth import get_user_model
from apps.core.utils import TailwindModelForm

Usuario = get_user_model()

class PedidoManualForm(TailwindModelForm):
    """Formulario simplificado: El estado siempre empieza en 'En_Espera'"""
    usuario = forms.ModelChoiceField(
        queryset=Usuario.objects.all(),
        empty_label="Seleccione un cliente",
        label="Cliente",
    )

    class Meta:
        model = Pedido
        fields = ["usuario", "descripcion"]
        widgets = {
            "descripcion": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": "Ej: Escultura de dragón personalizada...",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["usuario"].label_from_instance = (
            lambda obj: f"{obj.get_full_name_or_user()} - {obj.telefono if obj.telefono else 'Sin Tel.'}"
        )


class ItemCatalogoForm(TailwindModelForm):
    """Formulario para agregar items del catálogo a un pedido"""

    class Meta:
        model = ItemPedido
        fields = ["variante", "cantidad", "precio_unitario", "gramos_por_unidad"]
        widgets = {
            "gramos_por_unidad": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["variante"].required = True
        self.fields["variante"].empty_label = "Seleccione un producto del catálogo"
        self.fields["variante"].label_from_instance = self.label_variante_detallada

        # En modo edición, bloquea la variante y los gramos para evitar inconsistencias
        if self.instance and self.instance.pk:
            self.fields["variante"].disabled = True
            self.fields["gramos_por_unidad"].disabled = True

    def label_variante_detallada(self, obj):
        """Genera una etiqueta detallada para cada variante mostrando materiales, precio y stock"""
        detalles = obj.detalles_material.all()
        materiales_list = [
            f"{d.material.tipo.nombre} {d.material.color.nombre}" for d in detalles
        ]
        str_materiales = (
            ", ".join(materiales_list) if materiales_list else "Sin materiales"
        )
        precio = f"RD$ {obj.precio_final:,.2f}"
        stock = int(obj.stock_disponible)
        return f"{obj.producto.nombre} - ({str_materiales}) - {precio} | Stock: {stock}"

    def clean(self):
        """Valida que haya suficiente stock disponible para la cantidad solicitada"""
        cleaned_data = super().clean()
        variante = cleaned_data.get("variante")
        cantidad = cleaned_data.get("cantidad")

        if variante and cantidad:
            if variante.stock_disponible < cantidad:
                self.add_error(
                    "variante",
                    f"No hay suficientes piezas en stock. Disponibles: {int(variante.stock_disponible)}, Solicitadas: {cantidad}.",
                )

        return cleaned_data


class ItemPersonalizadoForm(TailwindModelForm):
    """Formulario para crear items personalizados con materiales específicos"""

    material_personalizado = forms.ModelChoiceField(
        queryset=Material.objects.filter(activo=True),
        required=True,
        label="Material",
        empty_label="Seleccione el material a usar",
        widget=forms.HiddenInput(attrs={'id': 'material-id-hidden'})
    )

    class Meta:
        model = ItemPedido
        fields = [
            "descripcion",
            "material_personalizado",
            "gramos_por_unidad",
            "precio_unitario",
        ]
        widgets = {
            # Asegura explícitamente que sea un input de texto visible
            "gramos_por_unidad": forms.NumberInput(attrs={
                "placeholder": "Ej: 100",
                "class": "w-full bg-[#0f172a] border border-gray-700 rounded-xl px-4 py-3 text-white outline-none focus:border-[#10b981] transition-all",
                "step": "0.1",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Filtra solo materiales activos con stock y optimiza la consulta
        self.fields["material_personalizado"].queryset = Material.objects.filter(
            activo=True
        ).select_related("tipo", "marca", "color")

        # Muestra el stock disponible en el select de materiales
        self.fields["material_personalizado"].label_from_instance = lambda obj: (
            f"{obj.tipo} {obj.marca} - {obj.color} (Disponible: {obj.stock_actual}g)"
        )

        self.fields["descripcion"].required = True
        self.fields["descripcion"].widget.attrs["placeholder"] = "Ej: Engranaje motor 12mm"
        self.fields["gramos_por_unidad"].required = True
        self.fields["gramos_por_unidad"].widget.attrs["placeholder"] = "Ej: 100"
        self.fields["precio_unitario"].required = True
        self.fields["precio_unitario"].initial = None
        self.fields["precio_unitario"].widget.attrs["placeholder"] = "Ej: 100"
        self.fields["gramos_por_unidad"].initial = None

    def clean(self):
        """Valida que haya suficiente material en stock y que el precio sea válido"""
        cleaned_data = super().clean()
        precio = cleaned_data.get("precio_unitario")
        if precio is not None and precio <= 0:
            self.add_error("precio_unitario", "El precio debe ser mayor a 0.")

        return cleaned_data

class ItemContenedorForm(TailwindModelForm):
    """
    Formulario para crear el ítem contenedor (producto final visible para el cliente).
    Solo requiere nombre/descripción — el precio y los gramos se calculan
    automáticamente a partir de los componentes de producción.
    """
    class Meta:
        model   = ItemPedido
        fields  = ['descripcion', 'cantidad']
        widgets = {
            'descripcion': forms.TextInput(attrs={
                'placeholder': 'Ej: Casco de Iron Man',
                'autofocus': True,
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['descripcion'].label  = 'Nombre del producto final'
        self.fields['descripcion'].required = True
        self.fields['cantidad'].initial   = 1
        self.fields['cantidad'].label     = 'Cantidad de unidades'


class ComponenteItemForm(TailwindModelForm):
    """
    Formulario para agregar un componente de producción a un ítem contenedor.
    Contiene los datos técnicos: material, gramos, precio, cantidad.
    """
    material_personalizado = forms.ModelChoiceField(
        queryset=Material.objects.filter(activo=True),
        required=True,
        label='Material',
        empty_label='Seleccione el material',
        widget=forms.HiddenInput(attrs={'id': 'comp-material-id-hidden'}),
    )

    class Meta:
        model  = ItemPedido
        fields = [
            'descripcion',
            'material_personalizado',
            'gramos_por_unidad',
            'precio_unitario',
        ]
        widgets = {
            'descripcion': forms.TextInput(attrs={
                'placeholder': 'Ej: Parte roja — ABS',
            }),
            'gramos_por_unidad': forms.NumberInput(attrs={
                'placeholder': 'Ej: 200',
            }),
            'precio_unitario': forms.NumberInput(attrs={
                'placeholder': 'Ej: 350',
            }),
            'cantidad': forms.NumberInput(attrs={
                'placeholder': '1',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['material_personalizado'].queryset = Material.objects.filter(
            activo=True
        ).select_related('tipo', 'marca', 'color')
        self.fields['material_personalizado'].label_from_instance = (
            lambda obj: f"{obj.tipo} {obj.marca} — {obj.color}  (Stock: {obj.stock_actual}g)"
        )
        self.fields['descripcion'].required = True
        self.fields['descripcion'].label    = 'Nombre del componente'
        self.fields['gramos_por_unidad'].required = True
        self.fields['precio_unitario'].required    = True

    def clean_precio_unitario(self):
        precio = self.cleaned_data.get('precio_unitario')
        if precio is not None and precio <= 0:
            raise forms.ValidationError('El precio debe ser mayor a 0.')
        return precio