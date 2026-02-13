from django import forms
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from decimal import Decimal, InvalidOperation
from .models import Categoria, Producto, ProduccionInterna, VarianteProducto, ImagenProducto, VarianteMaterialDetalle
from apps.materiales.models import Material
from django.forms import inlineformset_factory
import logging

# --- WIDGETS ---


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result


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

# --- FORMULARIOS ---


class ProductoForm(TailwindModelForm):
    imagenes_galeria = MultipleFileField(
        required=False, label="Imágenes de galería")
    
    eliminar_portada = forms.BooleanField(
        required=False, 
        initial=False, 
        widget=forms.HiddenInput()
    )

    class Meta:
        model = Producto
        fields = [
            "nombre", "categoria", "descripcion", "precio_venta",
            "peso_gramos", "imagen", "mostrar_en_web", "destacado", "activo"
        ]
        widgets = {"descripcion": forms.Textarea(attrs={"rows": 2})}

    def _limpiar_decimal(self, valor):
        if isinstance(valor, str):
            valor = valor.replace(",", "")
        try:
            return abs(Decimal(valor))
        except (InvalidOperation, TypeError, ValueError):
            return Decimal("0.00")

    def clean_precio_venta(self):
        return self._limpiar_decimal(self.cleaned_data.get("precio_venta"))

    def clean_peso_gramos(self):
        return self._limpiar_decimal(self.cleaned_data.get("peso_gramos"))

    def save(self, commit=True):
        producto = super().save(commit=False)
        producto.slug = slugify(producto.nombre)
        if self.cleaned_data.get('eliminar_portada'):
            if producto.imagen:
                producto.imagen.delete(save=False)
                producto.imagen = None
        if commit:
            producto.save()
            imagenes = self.cleaned_data.get('imagenes_galeria')
            if imagenes:
                for f in imagenes:
                    ImagenProducto.objects.create(producto=producto, imagen=f)
        return producto


class CategoriaForm(TailwindModelForm):
    # Campo extra que no está en el modelo pero usaremos para la lógica
    eliminar_imagen = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = Categoria
        fields = ["nombre", "descripcion", "imagen", "orden", "activa"]
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        # Si el usuario marcó eliminar imagen, la borramos físicamente
        if self.cleaned_data.get('eliminar_imagen') == 'true':
            if instance.imagen:
                instance.imagen.delete(save=False)
                instance.imagen = None
        print("orden", self.cleaned_data.get("orden"))
        
        if commit:
            instance.save()
        return instance


class VarianteProductoForm(TailwindModelForm):
    """
    Nota: El material se gestiona a través de VarianteMaterialDetalle (Inlines o Formsets)
    """
    class Meta:
        model = VarianteProducto
        fields = ["stock_disponible",
                  "precio_adicional", "activa", "codigo_sku"]


class VarianteMaterialDetalleForm(TailwindModelForm):
    class Meta:
        model = VarianteMaterialDetalle
        fields = ["material", "gramos_usados"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["material"].queryset = Material.objects.filter(
            stock_actual__gt=0).select_related("marca", "color", "tipo")


MaterialDetalleFormSet = inlineformset_factory(
    VarianteProducto, 
    VarianteMaterialDetalle,
    form=VarianteMaterialDetalleForm,
    extra=1,      # Empieza con un espacio para 1 material
    can_delete=True,
    min_num=1,    # Al menos debe tener 1 material
    validate_min=True
)


class ProduccionInternaForm(TailwindModelForm):
    class Meta:
        model = ProduccionInterna
        fields = ["variante", "cantidad_producida", "observaciones"]
        widgets = {"observaciones": forms.Textarea(attrs={"rows": 2})}

    def clean(self):
        cd = super().clean()
        variante = cd.get("variante")
        cantidad = cd.get("cantidad_producida")

        if variante and cantidad:
            for detalle in variante.detalles_material.all():
                total_necesario = detalle.gramos_usados * cantidad
                if detalle.material.stock_actual < total_necesario:
                    raise ValidationError(
                        f"Stock insuficiente de {detalle.material}. Necesitas {total_necesario}g.")
        return cd
