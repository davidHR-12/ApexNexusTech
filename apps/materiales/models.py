"""
Modelos para la gestión de inventario de materiales de impresión 3D
"""
from django.db import models
from django.core.exceptions import ValidationError
from django.db.models.functions import Lower
from decimal import Decimal

# =============================
# ATRIBUTOS DE MATERIALES
# =============================

class TipoMaterial(models.Model):
    """Tipos de material: PLA, PETG, Resina, ABS, etc."""
    nombre = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Nombre"
    )
    descripcion = models.TextField(
        blank=True,
        help_text="Características y usos del material",
        verbose_name="Descripción"
    )

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Tipo de Material"
        verbose_name_plural = "Tipos de Material"
        ordering = ["nombre"]
        constraints = [
            models.UniqueConstraint(
                Lower('nombre'), 
                name='unique_tipo_nombre_case_insensitive'
            )
        ]


class Marca(models.Model):
    """Marcas de filamento: eSun, Hatchbox, Creality, etc."""
    nombre = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Nombre"
    )
    # posiblemente se pueda eliminar
    pais_origen = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="País de origen"
    )

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Marca"
        verbose_name_plural = "Marcas"
        ordering = ["nombre"]
        constraints = [
            models.UniqueConstraint(
                Lower('nombre'), 
                name='unique_marca_nombre_case_insensitive'
            )
        ]


class Color(models.Model):
    """Colores disponibles: Negro Mate, Rojo Seda, Blanco, etc."""
    nombre = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Nombre"
    )
    # posiblemente se pueda eliminar
    codigo_hex = models.CharField(
        max_length=7,
        blank=True,
        default='#10b981',
        help_text="Código hexadecimal del color (ej: #FF0000)",
        verbose_name="Código Hex"
    )

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Color"
        verbose_name_plural = "Colores"
        ordering = ["nombre"]
        constraints = [
            models.UniqueConstraint(
                Lower('nombre'), 
                name='unique_color_nombre_case_insensitive'
            )
        ]


# =============================
# MATERIAL PRINCIPAL
# =============================

class Material(models.Model):
    """
    Inventario de materiales de impresión.
    Combina tipo, marca y color para identificar un material único.
    """
    tipo = models.ForeignKey(
        TipoMaterial,
        on_delete=models.PROTECT,
        verbose_name="Tipo"
    )
    marca = models.ForeignKey(
        Marca,
        on_delete=models.PROTECT,
        verbose_name="Marca"
    )
    color = models.ForeignKey(
        Color,
        on_delete=models.PROTECT,
        verbose_name="Color"
    )

    # Gestión financiera
    costo_por_gramo = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        verbose_name="Costo por gramo"
    )

    # Gestión de stock
    stock_actual = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Stock actual (gramos)"
    )
    stock_minimo = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=100,
        help_text="Nivel de reorden",
        verbose_name="Stock mínimo (gramos)"
    )

    # Información adicional
    activo = models.BooleanField(
        default=True,
        help_text="Desmarcar para materiales descontinuados",
        verbose_name="Activo"
    )

    # Enlace de compra
    enlace_compra = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Enlace a la tienda para reponer este material (ej: Keitron, Amazon, etc.)",
        verbose_name="Enlace de compra"
    )

    @property
    def necesita_reposicion(self):
        """Verifica si el stock está por debajo del mínimo"""
        return self.stock_actual <= self.stock_minimo

    @property
    def valor_inventario(self):
        """Valor monetario del stock actual (stock_actual × costo_por_gramo)."""
        return (self.stock_actual * self.costo_por_gramo).quantize(Decimal("0.01"))

    def delete(self, *args, **kwargs):
        # Añadimos la opción de forzar el borrado (usado en fusiones)
        force_delete = kwargs.pop('force_delete', False)

        if not force_delete:
            # 1. Impedir si hay stock físico
            if self.stock_actual > 0:
                raise ValidationError(
                    f"No se puede eliminar {self}. Aún tiene {self.stock_actual}g en stock."
                )

            # 2. Impedir si tiene historial (si no es forzado)
            if self.entradainventario_set.exists() or self.consumomaterial_set.exists():
                self.activo = False
                self.save()
                return

        super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.tipo} {self.marca} - {self.color} ({self.stock_actual}g)"

    class Meta:
        verbose_name = "Material"
        verbose_name_plural = "Materiales"
        unique_together = ("tipo", "marca", "color")
        ordering = ["tipo__nombre", "marca__nombre", "color__nombre"]


# =============================
# ENTRADAS DE INVENTARIO
# =============================

class EntradaInventario(models.Model):
    """
    Registro de compras de material.

    Gestión automática:
    - Al crear: Suma stock, crea Gasto, crea Historial
    - Al editar: Recalcula diferencia de stock, actualiza Historial
    - Al borrar: Resta stock agregado, crea Historial de eliminación
    """
    material = models.ForeignKey(
        Material,
        on_delete=models.CASCADE,
        verbose_name="Material"
    )
    cantidad_gramos = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Cantidad (gramos)"
    )
    costo_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Costo total"
    )
    fecha = models.DateField(
        auto_now_add=True,
        verbose_name="Fecha de compra"
    )
    proveedor = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Proveedor"
    )
    numero_factura = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Número de factura"
    )
    notas = models.TextField(
        blank=True,
        verbose_name="Notas"
    )

    def actualizar_stock(self, diferencia):
        """Actualiza el stock del material"""
        self.material.stock_actual += diferencia
        self.material.save()

    def crear_gasto(self):
        """Crea un registro contable de la compra"""
        from apps.finanzas.models import Gasto

        Gasto.objects.create(
            descripcion=f"Compra de {self.cantidad_gramos}g de {str(self.material)}",
            monto=self.costo_total,
            fecha=self.fecha,
            tipo="Compra_Material",
            entrada_inventario=self,
        )

    def crear_historial(self, accion, diferencia=None, old_cantidad=None):
        """Registra el movimiento en el historial"""
        HistorialInventario.objects.create(
            material=self.material,
            entrada=self,
            accion=accion,
            cantidad_nueva=self.cantidad_gramos,
            cantidad_anterior=old_cantidad,
            diferencia=diferencia,
        )

    def save(self, *args, **kwargs):
        # Actualizar costo por gramo del material
        if self.cantidad_gramos > 0:
            nuevo_costo = self.costo_total / self.cantidad_gramos
            self.material.costo_por_gramo = nuevo_costo
            self.material.save()

        if self.pk:  # EDICIÓN
            try:
                old = EntradaInventario.objects.get(pk=self.pk)
                if old.material != self.material:
                    # Si cambió el material, restamos todo al viejo y sumamos todo al nuevo
                    old.material.stock_actual -= old.cantidad_gramos
                    old.material.save()
                    self.material.stock_actual += self.cantidad_gramos
                    self.material.save()
                else:
                    # Si es el mismo material, aplicamos la diferencia
                    diff = self.cantidad_gramos - old.cantidad_gramos
                    if diff != 0:
                        self.actualizar_stock(diff)
                        self.crear_historial(
                            accion="Edición",
                            diferencia=diff,
                            old_cantidad=old.cantidad_gramos,
                        )

                super().save(*args, **kwargs)
            except EntradaInventario.DoesNotExist:
                super().save(*args, **kwargs)

        else:  # NUEVA ENTRADA
            self.actualizar_stock(self.cantidad_gramos)
            super().save(*args, **kwargs)
            self.crear_gasto()
            self.crear_historial(
                accion="Entrada",
                diferencia=self.cantidad_gramos,
                old_cantidad=self.material.stock_actual - self.cantidad_gramos,
            )

    def delete(self, *args, **kwargs):
        """Al borrar, revierte el stock"""
        self.material.stock_actual -= self.cantidad_gramos
        self.material.save()

        self.crear_historial(
            accion="Eliminación",
            diferencia=-self.cantidad_gramos,
            old_cantidad=self.cantidad_gramos,
        )
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"Entrada {self.cantidad_gramos}g - {str(self.material)} ({self.fecha})"

    class Meta:
        verbose_name = "Entrada de Inventario"
        verbose_name_plural = "Entradas de Inventario"
        ordering = ["-fecha"]


# =============================
# HISTORIAL DE MOVIMIENTOS
# =============================

class HistorialInventario(models.Model):
    """
    Auditoría de todos los movimientos de inventario de materiales.
    Registra entradas, ediciones, eliminaciones y consumos.
    """
    ACCIONES = (
        ("Entrada", "Entrada"),
        ("Edición", "Edición"),
        ("Eliminación", "Eliminación"),
        ("Consumo", "Consumo"),
    )

    material = models.ForeignKey(
        Material,
        on_delete=models.CASCADE,
        verbose_name="Material"
    )
    entrada = models.ForeignKey(
        EntradaInventario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Entrada relacionada"
    )
    accion = models.CharField(
        max_length=20,
        choices=ACCIONES,
        verbose_name="Acción"
    )

    cantidad_nueva = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Cantidad nueva"
    )
    cantidad_anterior = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Cantidad anterior"
    )
    diferencia = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Diferencia"
    )

    fecha = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha"
    )

    def __str__(self):
        return f"{self.fecha.date()} - {self.get_accion_display()} ({self.diferencia}g)"

    class Meta:
        verbose_name = "Historial de Inventario"
        verbose_name_plural = "Historial de Inventario"
        ordering = ["-fecha"]


# =============================
# CONSUMO DE MATERIAL
# =============================

class ConsumoMaterial(models.Model):
    """
    Registro de material usado en producción.
    Se vincula a pedidos o producciones internas.
    Resta material del inventario automáticamente.
    """
    # Referencia lazy para evitar dependencias circulares
    pedido = models.ForeignKey(
        'pedidos.Pedido',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Pedido"
    )
    material = models.ForeignKey(
        Material,
        on_delete=models.CASCADE,
        verbose_name="Material"
    )
    gramos_usados = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Gramos usados"
    )
    fecha = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha"
    )
    notas = models.TextField(
        blank=True,
        verbose_name="Notas"
    )

    def ajustar_stock(self, diferencia):
        """
        Ajusta el stock del material.
        Diferencia positiva => devolver stock
        Diferencia negativa => restar stock
        """
        nuevo_stock = self.material.stock_actual + diferencia

        if nuevo_stock < 0:
            raise ValueError(
                f"Stock insuficiente de {str(self.material)}. "
                f"Intento de ajuste: {diferencia}g, stock actual: {self.material.stock_actual}g"
            )

        self.material.stock_actual = nuevo_stock
        self.material.save()

    def crear_historial(self, accion, diferencia, cantidad_anterior):
        """Registra el consumo en el historial"""
        HistorialInventario.objects.create(
            material=self.material,
            entrada=None,
            accion=accion,
            cantidad_nueva=self.material.stock_actual,
            cantidad_anterior=cantidad_anterior,
            diferencia=diferencia,
        )

    def save(self, *args, **kwargs):
        if self.pk:  # EDICIÓN
            old = ConsumoMaterial.objects.get(pk=self.pk)
            diff = self.gramos_usados - old.gramos_usados

            if diff != 0:
                cantidad_anterior = self.material.stock_actual
                self.ajustar_stock(-diff)
                self.crear_historial(
                    accion="Edición",
                    diferencia=-diff,
                    cantidad_anterior=cantidad_anterior,
                )

            super().save(*args, **kwargs)

        else:  # NUEVO CONSUMO
            cantidad_anterior = self.material.stock_actual
            self.ajustar_stock(-self.gramos_usados)
            super().save(*args, **kwargs)
            self.crear_historial(
                accion="Consumo",
                diferencia=-self.gramos_usados,
                cantidad_anterior=cantidad_anterior,
            )

    def delete(self, *args, **kwargs):
        """Al eliminar, devuelve el material al stock"""
        cantidad_anterior = self.material.stock_actual
        self.ajustar_stock(self.gramos_usados)
        self.crear_historial(
            accion="Eliminación",
            diferencia=self.gramos_usados,
            cantidad_anterior=cantidad_anterior,
        )
        super().delete(*args, **kwargs)

    def __str__(self):
        destino = f"Pedido #{self.pedido.id}" if self.pedido else "Producción interna"
        return f"Consumo {self.gramos_usados}g - {str(self.material)} ({destino})"

    class Meta:
        verbose_name = "Consumo de Material"
        verbose_name_plural = "Consumos de Material"
        ordering = ["-fecha"]
