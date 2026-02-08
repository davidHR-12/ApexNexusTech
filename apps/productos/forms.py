from django import forms
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from decimal import Decimal, InvalidOperation
from .models import Categoria, Producto, ProduccionInterna, VarianteProducto, ImagenProducto
from apps.materiales.models import Material

# Widget para permitir múltiples archivos
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

# --- CLASE BASE ---
class TailwindModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "rounded border-gray-700 text-[#10b981] focus:ring-[#10b981] bg-gray-900"
            # Ajuste para que el input de archivo no se vea raro
            elif isinstance(field.widget, (forms.FileInput, forms.ClearableFileInput)):
                field.widget.attrs["class"] = "w-full text-sm text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-gray-800 file:text-emerald-400 hover:file:bg-gray-700"
            else:
                field.widget.attrs["class"] = "w-full bg-[#0f172a] border border-gray-700 rounded-xl px-4 py-3 text-white outline-none focus:border-[#10b981]"

# --- PRODUCTO ---
class ProductoForm(TailwindModelForm):
    # Campo virtual para subir varias imágenes a la vez en la galería
    imagenes_galeria = MultipleFileField(
        required=False,
        label="Imágenes de galería"
    )

    class Meta:
        model = Producto
        fields = [
            "nombre", "categoria", "descripcion", "precio_venta",
            "material_base", "peso_gramos", "imagen", "mostrar_en_web",
        ]
        widgets = {"descripcion": forms.Textarea(attrs={"rows": 2})}

    def clean_imagenes_galeria(self):
        # Buscamos directamente en FILES para asegurar que capturamos todo lo del JS
        archivos = self.files.getlist('imagenes_galeria')
        return archivos

    def clean_precio_venta(self):
        return self._limpiar_decimal(self.cleaned_data.get("precio_venta"))

    def clean_peso_gramos(self):
        return self._limpiar_decimal(self.cleaned_data.get("peso_gramos"))

    def _limpiar_decimal(self, valor):
        """Lógica centralizada para quitar comas y asegurar positivos"""
        if isinstance(valor, str):
            valor = valor.replace(",", "")
        try:
            return abs(Decimal(valor))
        except (InvalidOperation, TypeError, ValueError):
            raise ValidationError("Formato numérico inválido.")

    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre')
        nuevo_slug = slugify(nombre)
        
        # Verificamos si ya existe otro producto con el mismo slug
        # Excluimos el producto actual por si estamos editando
        exists = Producto.objects.filter(slug=nuevo_slug).exclude(pk=self.instance.pk).exists()
        
        if exists:
            raise ValidationError(
                f"Ya existe un producto con un nombre similar (genera el slug: '{nuevo_slug}'). "
                "Por favor, elige un nombre más específico."
            )
            
        return nombre

    def save(self, commit=True):
        producto = super().save(commit=False)
        producto.slug = slugify(producto.nombre)
        
        if self.data.get("eliminar_portada_flag") == "true":
            if producto.imagen:
                producto.imagen.delete(save=False)
                producto.imagen = None

        if commit:
            producto.save()
            # 3. Guardar las imágenes usando la lista que limpiamos en el paso 2
            imagenes = self.cleaned_data.get('imagenes_galeria')
            if imagenes:
                for f in imagenes:
                    ImagenProducto.objects.create(producto=producto, imagen=f)
        
        return producto

# --- CATEGORÍA ---
class CategoriaForm(TailwindModelForm):
    class Meta:
        model = Categoria
        fields = ["nombre", "descripcion", "imagen"]

    def save(self, commit=True):
        categoria = super().save(commit=False)
        categoria.slug = slugify(categoria.nombre)
        
        if self.data.get("eliminar_imagen") == "true" and not self.files.get("imagen"):
            if categoria.imagen:
                categoria.imagen.delete(save=False)
                categoria.imagen = None
                
        if commit:
            categoria.save()
        return categoria

# --- VARIANTE ---
class VarianteProductoForm(TailwindModelForm):
    class Meta:
        model = VarianteProducto
        fields = ["material", "stock_disponible", "precio_adicional"]

    def __init__(self, *args, **kwargs):
        self.producto = kwargs.pop("producto", None)
        super().__init__(*args, **kwargs)

        if self.producto:
            materiales_ya_usados = self.producto.variantes.values_list("material_id", flat=True)
            self.fields["material"].queryset = (
                Material.objects.exclude(id__in=materiales_ya_usados)
                .filter(stock_actual__gt=0)
                .select_related("marca", "color", "tipo")
            )
            self.fields["material"].label_from_instance = (
                lambda obj: f"{obj.marca.nombre} {obj.tipo.nombre} - {obj.color.nombre} ({obj.stock_actual}g)"
            )

    def clean(self):
        cd = super().clean()
        material = cd.get("material")
        if self.producto and material:
            if VarianteProducto.objects.filter(producto=self.producto, material=material).exists():
                raise ValidationError("Esta variante ya existe para este producto.")
        return cd

# --- PRODUCCIÓN ---
class ProduccionInternaForm(TailwindModelForm):
    class Meta:
        model = ProduccionInterna
        fields = ["variante", "cantidad_producida", "material", "gramos_por_pieza", "observaciones"]
        widgets = {"observaciones": forms.Textarea(attrs={"rows": 2})}

    def clean(self):
        cd = super().clean()
        material = cd.get("material")
        cantidad = cd.get("cantidad_producida")
        gramos = cd.get("gramos_por_pieza")
        
        if material and cantidad and gramos:
            total = cantidad * gramos
            if material.stock_actual < total:
                raise ValidationError(f"Stock insuficiente. Necesitas {total}g y solo hay {material.stock_actual}g.")
        return cd