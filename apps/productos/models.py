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
        verbose_name="Orden",
        blank=True,
        null=True
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
        """Calcula el costo basado en la variante por defecto (la primera)"""
        primera_variante = self.variantes.first()
        if primera_variante:
            return primera_variante.costo_materiales
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
    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        related_name="variantes",
        verbose_name="Producto"
    )
    materiales_consumidos = models.ManyToManyField(
        "materiales.Material",
        through='VarianteMaterialDetalle',
        related_name="variantes_que_lo_usan"
    )
    stock_disponible = models.IntegerField(default=0, verbose_name="Stock disponible")
    precio_adicional = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Sobreprecio respecto al precio base",
        verbose_name="Precio adicional"
    )
    codigo_sku = models.CharField(max_length=50, blank=True, unique=True, null=True, verbose_name="SKU")
    activa = models.BooleanField(default=True, verbose_name="Activa")

    @property
    def precio_final(self):
        return self.producto.precio_venta + self.precio_adicional

    @property
    def costo_materiales(self):
        """Calcula el costo sumando todos los materiales del detalle"""
        total = sum(d.gramos_usados * d.material.costo_por_gramo for d in self.detalles_material.all())
        return Decimal(total).quantize(Decimal("0.01"))

    @property
    def costo_produccion_total(self):
        """Suma costo de materiales + costo estimado de energía"""
        # Calculamos costo de energía: (Tiempo en horas * Consumo Promedio Kw * Precio Kwh)
        # Por ahora, para no complicar, usamos solo materiales o una fórmula simple:
        costo_energia_estimado = self.producto.tiempo_impresion_horas * Decimal("2.5") # Ejemplo: RD$2.5 por hora
        return self.costo_materiales + costo_energia_estimado

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs) # Guardamos primero para tener ID si es nuevo
        
        if not self.codigo_sku:
            # Para el SKU, tomamos el nombre del primer material disponible
            primer_detalle = self.detalles_material.first()
            if primer_detalle:
                material_slug = slugify(f"{primer_detalle.material.color.nombre}-{primer_detalle.material.tipo.nombre}")
                self.codigo_sku = f"{self.producto.slug}-{material_slug}"[:50]
                # Guardamos de nuevo para actualizar el SKU
                super().save(update_fields=['codigo_sku'])

    def __str__(self):
        # Muestra algo como: "Cráneo T-Rex (Rojo, Dorado)"
        materiales = ", ".join([d.material.color.nombre for d in self.detalles_material.all()])
        return f"{self.producto.nombre} ({materiales if materiales else 'Sin materiales'})"

    @classmethod
    def obtener_materiales_normalizados(cls, detalles_material):
        """
        Extrae y normaliza los materiales de un formset o QuerySet.
        Retorna lista ordenada de tuplas (material_id, gramos)
        """
        materiales = []
        for detalle in detalles_material:
            if isinstance(detalle, dict):  # Vienen del formset
                if detalle and not detalle.get("DELETE"):
                    mat = detalle.get("material")
                    gramos = detalle.get("gramos_usados")
                    if mat and gramos:
                        materiales.append((mat.id, Decimal(str(gramos))))
            else:  # Vienen de la BD
                if detalle.material and detalle.gramos_usados:
                    materiales.append((detalle.material.id, Decimal(str(detalle.gramos_usados))))
        materiales.sort()
        return materiales

    def tiene_duplicado_en_producto(self):
        """
        Verifica si ya existe otra variante en el mismo producto
        con exactamente los mismos materiales y gramos.
        Útil antes de crear una nueva variante.
        """
        materiales_nuevos = self.obtener_materiales_normalizados(
            self.detalles_material.all()
        )
        
        if not materiales_nuevos:
            return False
        
        variantes_existentes = self.producto.variantes.prefetch_related(
            "detalles_material__material"
        ).exclude(pk=self.pk)  # Excluir la variante actual en caso de edición
        
        for variante_ex in variantes_existentes:
            materiales_existentes = self.obtener_materiales_normalizados(
                variante_ex.detalles_material.all()
            )
            if materiales_nuevos == materiales_existentes:
                return True
        
        return False

    class Meta:
        verbose_name = "Variante de Producto"
        verbose_name_plural = "Variantes de Productos"
        ordering = ["producto__nombre"]


class VarianteMaterialDetalle(models.Model):
    """

    Modelo intermedio para definir cuántos gramos de qué material 

    usa una variante específica.

    """
    variante = models.ForeignKey(VarianteProducto, on_delete=models.CASCADE, related_name="detalles_material")
    material = models.ForeignKey("materiales.Material", on_delete=models.CASCADE)
    gramos_usados = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        verbose_name = "Detalle de Material de Variante"
        unique_together = ('variante', 'material')

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
    fecha = models.DateTimeField(auto_now_add=True, verbose_name="Fecha")
    observaciones = models.TextField(blank=True, verbose_name="Observaciones")

    @property
    def costo_total_produccion(self):
        """Costo total basado en la receta de la variante"""
        return (self.variante.costo_materiales * self.cantidad_producida).quantize(Decimal("0.01"))

    def save(self, *args, **kwargs):
        nueva = self.pk is None
        if nueva:
            # 1. Validar stock de TODOS los materiales definidos en la variante
            detalles = self.variante.detalles_material.all()
            if not detalles.exists():
                raise ValueError(f"La variante {self.variante} no tiene materiales configurados.")

            for detalle in detalles:
                total_necesario = detalle.gramos_usados * self.cantidad_producida
                if detalle.material.stock_actual < total_necesario:
                    raise ValueError(
                        f"Stock insuficiente de {detalle.material}. "
                        f"Necesitas {total_necesario}g y hay {detalle.material.stock_actual}g."
                    )

            super().save(*args, **kwargs)

            # 2. Registrar el consumo de cada material en la app materiales
            from apps.materiales.models import ConsumoMaterial
            for detalle in detalles:
                total_usado = detalle.gramos_usados * self.cantidad_producida
                ConsumoMaterial.objects.create(
                    material=detalle.material,
                    gramos_usados=total_usado,
                    notas=f"Producción stock: {self.cantidad_producida}x {self.variante}"
                )

            # 3. Aumentar stock de la variante
            self.variante.stock_disponible += self.cantidad_producida
            self.variante.save()
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return f"Producción {self.cantidad_producida}x {self.variante} ({self.fecha.date()})"

    class Meta:
        verbose_name = "Producción Interna"
        verbose_name_plural = "Producciones Internas"
        ordering = ["-fecha"]
