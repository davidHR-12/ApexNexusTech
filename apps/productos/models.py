"""
Modelos para la gestión de productos y catálogo
"""
from django.db import models
from django.utils.text import slugify
from decimal import Decimal


# =============================
# CATEGORÍAS
# =============================

class Categoria(models.Model):
    """Categorías de productos para organizar el catálogo"""
    nombre = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Nombre"
    )
    descripcion = models.TextField(
        blank=True,
        null=True,
        help_text="Breve descripción de los productos en esta categoría",
        verbose_name="Descripción"
    )
    imagen = models.ImageField(
        upload_to="categorias/",
        null=True,
        blank=True,
        verbose_name="Imagen"
    )
    slug = models.SlugField(
        unique=True,
        blank=True,
        verbose_name="Slug"
    )
    orden = models.IntegerField(
        default=0,
        help_text="Orden de aparición en el catálogo",
        verbose_name="Orden"
    )
    activa = models.BooleanField(
        default=True,
        verbose_name="Activa"
    )

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nombre)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"
        ordering = ["orden", "nombre"]


# =============================
# PRODUCTOS
# =============================

def get_default_categoria():
    """Función helper para categoría por defecto"""
    obj, created = Categoria.objects.get_or_create(
        nombre="Sin Categorizar",
        defaults={
            'descripcion': 'Categoría para productos sin clasificación.',
            'orden': 9999
        }
    )
    return obj.pk


class Producto(models.Model):
    """
    Producto o pieza imprimible.
    Puede tener múltiples variantes (diferentes colores/materiales).
    """
    nombre = models.CharField(
        max_length=200,
        verbose_name="Nombre"
    )
    slug = models.SlugField(
        unique=True,
        blank=True,
        verbose_name="Slug"
    )
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.SET_DEFAULT,
        default=get_default_categoria,
        related_name="productos",
        verbose_name="Categoría"
    )
    descripcion = models.TextField(
        blank=True,
        verbose_name="Descripción"
    )
    precio_venta = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Precio de venta"
    )
    imagen = models.ImageField(
        upload_to="productos/",
        null=True,
        blank=True,
        verbose_name="Imagen principal"
    )

    # Datos técnicos para cálculos
    material_base = models.ForeignKey(
        "materiales.Material",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Material por defecto para estimaciones",
        verbose_name="Material base"
    )
    peso_gramos = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Peso (gramos)"
    )
    tiempo_impresion_horas = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        help_text="Tiempo estimado de impresión",
        verbose_name="Tiempo de impresión (horas)"
    )

    # Configuración del catálogo
    mostrar_en_web = models.BooleanField(
        default=False,
        verbose_name="Mostrar en web"
    )
    destacado = models.BooleanField(
        default=False,
        help_text="Aparecerá en la página principal",
        verbose_name="Destacado"
    )
    activo = models.BooleanField(
        default=True,
        verbose_name="Activo"
    )

    # Metadata
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de creación"
    )
    fecha_modificacion = models.DateTimeField(
        auto_now=True,
        verbose_name="Última modificación"
    )

    @property
    def stock_total(self):
        """Suma el stock de todas las variantes"""
        return sum(v.stock_disponible for v in self.variantes.all())

    @property
    def costo_produccion(self):
        """Calcula el costo estimado de producción"""
        if self.material_base and self.peso_gramos:
            return Decimal(
                self.material_base.costo_por_gramo * self.peso_gramos
            ).quantize(Decimal("0.01"))
        return Decimal("0.00")

    @property
    def margen_ganancia(self):
        """Calcula el margen de ganancia"""
        costo = self.costo_produccion
        if costo > 0:
            return ((self.precio_venta - costo) / costo * 100).quantize(Decimal("0.01"))
        return Decimal("0.00")

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nombre)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Producto/Pieza"
        verbose_name_plural = "Productos/Piezas"
        ordering = ["-fecha_creacion"]


# =============================
# VARIANTES DE PRODUCTOS
# =============================

class VarianteProducto(models.Model):
    """
    Variantes de un producto (diferentes colores/materiales).
    Ejemplo: "Soporte de celular" en PLA Negro, PLA Rojo, PETG Azul.
    """
    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        related_name="variantes",
        verbose_name="Producto"
    )
    material = models.ForeignKey(
        "materiales.Material",
        on_delete=models.PROTECT,
        verbose_name="Material"
    )
    stock_disponible = models.IntegerField(
        default=0,
        verbose_name="Stock disponible"
    )
    precio_adicional = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Sobreprecio respecto al precio base del producto",
        verbose_name="Precio adicional"
    )
    codigo_sku = models.CharField(
        max_length=50,
        blank=True,
        unique=True,
        null=True,
        verbose_name="SKU"
    )
    activa = models.BooleanField(
        default=True,
        verbose_name="Activa"
    )

    @property
    def precio_final(self):
        """Precio total de esta variante"""
        return self.producto.precio_venta + self.precio_adicional

    def save(self, *args, **kwargs):
        # Auto-generar SKU si no existe
        if not self.codigo_sku:
            # Incluimos la marca para evitar colisiones entre marcas del mismo color
            marca = self.material.marca.nombre.lower().replace(' ', '-')
            color = self.material.color.nombre.lower().replace(' ', '-')
            tipo = self.material.tipo.nombre.lower().replace(' ', '-')
        
            nuevo_sku = f"{self.producto.slug}-{marca}-{color}-{tipo}"
        
            # Si el SKU es muy largo, lo cortamos, pero aseguramos unicidad
            self.codigo_sku = nuevo_sku[:50]
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.producto.nombre} ({self.material.color})"

    class Meta:
        verbose_name = "Variante de Producto"
        verbose_name_plural = "Variantes de Productos"
        unique_together = ("producto", "material")
        ordering = ["producto__nombre", "material__color__nombre"]


# =============================
# GALERÍA DE IMÁGENES
# =============================

class ImagenProducto(models.Model):
    """Imágenes adicionales del producto (galería)"""
    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        related_name="imagenes",
        verbose_name="Producto"
    )
    imagen = models.ImageField(
        upload_to="productos/galeria/",
        verbose_name="Imagen"
    )
    orden = models.IntegerField(
        default=0,
        help_text="Orden en que aparecerán las fotos",
        verbose_name="Orden"
    )
    descripcion = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Descripción"
    )

    def __str__(self):
        return f"Imagen de {self.producto.nombre}"

    class Meta:
        verbose_name = "Imagen de Producto"
        verbose_name_plural = "Galería de Imágenes"
        ordering = ["producto", "orden"]


# =============================
# PRODUCCIÓN INTERNA
# =============================

class ProduccionInterna(models.Model):
    """
    Registro de producción para stock.
    Permite fabricar productos por adelantado.
    """
    variante = models.ForeignKey(
        VarianteProducto,
        on_delete=models.CASCADE,
        related_name="producciones",
        verbose_name="Variante"
    )
    cantidad_producida = models.PositiveIntegerField(
        help_text="Cantidad de piezas impresas para stock",
        verbose_name="Cantidad producida"
    )
    material = models.ForeignKey(
        "materiales.Material",
        on_delete=models.PROTECT,
        help_text="Material usado para esta producción",
        verbose_name="Material"
    )
    gramos_por_pieza = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Consumo de material por unidad",
        verbose_name="Gramos por pieza"
    )
    fecha = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha"
    )
    observaciones = models.TextField(
        blank=True,
        verbose_name="Observaciones"
    )

    @property
    def gramos_totales(self):
        """Total de gramos consumidos en esta producción"""
        return self.cantidad_producida * self.gramos_por_pieza

    @property
    def costo_material(self):
        """Costo total del material usado"""
        return Decimal(self.gramos_totales * self.material.costo_por_gramo).quantize(Decimal("0.01"))

    def save(self, *args, **kwargs):
        nueva = self.pk is None

        # Validar stock de material antes de guardar
        gramos_totales = self.cantidad_producida * self.gramos_por_pieza
        if nueva and self.material.stock_actual < gramos_totales:
            raise ValueError(
                f"Stock insuficiente de {self.material}. "
                f"Necesitas {gramos_totales}g y solo hay {self.material.stock_actual}g."
            )

        super().save(*args, **kwargs)

        if nueva:
            # Registrar consumo de material
            from apps.materiales.models import ConsumoMaterial
            ConsumoMaterial.objects.create(
                pedido=None,
                material=self.material,
                gramos_usados=gramos_totales,
                notas=f"Producción interna: {self.cantidad_producida}x {self.variante}"
            )

            # Aumentar stock de la variante
            self.variante.stock_disponible += self.cantidad_producida
            self.variante.save()

    def __str__(self):
        return f"Producción {self.cantidad_producida}x {self.variante} ({self.fecha.date()})"

    class Meta:
        verbose_name = "Producción Interna"
        verbose_name_plural = "Producciones Internas"
        ordering = ["-fecha"]
