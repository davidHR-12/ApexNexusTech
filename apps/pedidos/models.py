"""
Modelos para la gestión de pedidos y cotizaciones
"""
from django.db import models
from django.conf import settings
from decimal import Decimal


# =============================
# SOLICITUDES DE COTIZACIÓN
# =============================

class SolicitudCotizacion(models.Model):
    """
    Solicitud de cotización iniciada por un cliente.
    Puede convertirse en un pedido una vez cotizada y aceptada.
    """
    ESTADOS = (
        ("Pendiente", "Pendiente de revisión"),
        ("Cotizada", "Cotización enviada"),
        ("Aceptada", "Aceptada por cliente"),
        ("Rechazada", "Rechazada"),
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="solicitudes_cotizacion",
        verbose_name="Cliente"
    )
    descripcion = models.TextField(
        help_text="Descripción del producto a cotizar",
        verbose_name="Descripción"
    )
    imagen_referencia = models.ImageField(
        upload_to="pedidos/referencias/",
        blank=True,
        null=True,
        verbose_name="Imagen de referencia"
    )
    enlace_referencia = models.URLField(
        blank=True,
        null=True,
        help_text="Link a un modelo 3D o referencia",
        verbose_name="Enlace de referencia"
    )
    dimensiones_aprox = models.CharField(
        max_length=100,
        help_text="Ej: 10x10x5 cm",
        blank=True,
        verbose_name="Dimensiones aproximadas"
    )
    estado = models.CharField(
        max_length=15,
        choices=ESTADOS,
        default="Pendiente",
        verbose_name="Estado"
    )
    fecha_solicitud = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de solicitud"
    )

    # Respuesta del admin
    precio_cotizado = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Precio cotizado"
    )
    tiempo_estimado = models.CharField(
        max_length=100,
        blank=True,
        help_text="Ej: 2-3 días hábiles",
        verbose_name="Tiempo estimado"
    )
    notas_admin = models.TextField(
        blank=True,
        verbose_name="Notas del administrador"
    )
    fecha_respuesta = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de respuesta"
    )

    def __str__(self):
        return f"Solicitud #{self.id} - {self.usuario.email} ({self.get_estado_display()})"

    class Meta:
        verbose_name = "Solicitud de Cotización"
        verbose_name_plural = "Solicitudes de Cotización"
        ordering = ["-fecha_solicitud"]


# =============================
# PEDIDOS
# =============================

class Pedido(models.Model):
    """
    Pedido confirmado de impresión 3D.
    Puede originarse de una solicitud de cotización o directamente del catálogo.
    """
    ESTADOS_PEDIDO = (
        ("En_Espera", "En espera de pago"),
        ("Confirmado", "Confirmado - Pendiente de producción"),
        ("En_Produccion", "En producción"),
        ("Listo", "Listo para entrega"),
        ("Entregado", "Entregado"),
        ("Cancelado", "Cancelado"),
    )

    # Relación con cliente
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pedidos",
        verbose_name="Cliente"
    )

    # Relación opcional con solicitud de cotización
    solicitud = models.OneToOneField(
        SolicitudCotizacion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Solicitud de cotización"
    )

    # Detalles del pedido
    descripcion = models.TextField(
        help_text="Descripción del pedido",
        verbose_name="Descripción"
    )

    # Datos técnicos
    peso_estimado_g = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Peso estimado (gramos)"
    )
    tiempo_estimado_h = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Tiempo estimado (horas)"
    )

    # Costos
    precio_kwh_usado = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=15.00,
        help_text="Costo de energía por kWh",
        verbose_name="Precio kWh"
    )
    costo_material = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Costo de material"
    )
    costo_energia = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Costo de energía"
    )
    otros_costos = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Costos adicionales (envío, acabados, etc.)",
        verbose_name="Otros costos"
    )
    precio_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Precio total"
    )

    # Estado y fechas
    estado_pedido = models.CharField(
        max_length=20,
        choices=ESTADOS_PEDIDO,
        default="En_Espera",
        verbose_name="Estado"
    )
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de creación"
    )
    fecha_inicio_produccion = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha inicio producción"
    )
    fecha_entrega = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de entrega"
    )

    # Información adicional
    notas = models.TextField(
        blank=True,
        verbose_name="Notas"
    )

    @property
    def costo_total_produccion(self):
        """Costo total de producción (sin margen)"""
        return self.costo_material + self.costo_energia + self.otros_costos

    @property
    def ganancia(self):
        """Ganancia del pedido"""
        return self.precio_total - self.costo_total_produccion

    @property
    def margen_porcentaje(self):
        """Margen de ganancia en porcentaje"""
        costo = self.costo_total_produccion
        if costo > 0:
            return ((self.precio_total - costo) / costo * 100).quantize(Decimal("0.01"))
        return Decimal("0.00")

    @property
    def total_pagado(self):
        """Total de pagos recibidos"""
        return sum(pago.monto for pago in self.pagos.all())

    @property
    def saldo_pendiente(self):
        """Saldo pendiente de pago"""
        return self.precio_total - self.total_pagado

    @property
    def esta_pagado(self):
        """Verifica si el pedido está completamente pagado"""
        return self.total_pagado >= self.precio_total

    def __str__(self):
        return f"Pedido #{self.id} - {self.usuario.email} ({self.get_estado_pedido_display()})"

    class Meta:
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"
        ordering = ["-fecha_creacion"]


# =============================
# ITEMS DE PEDIDO
# =============================

class ItemPedido(models.Model):
    """
    Producto individual dentro de un pedido.
    Permite pedidos con múltiples productos.
    """
    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Pedido"
    )
    variante = models.ForeignKey(
        "productos.VarianteProducto",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name="Variante de producto"
    )
    descripcion = models.CharField(
        max_length=300,
        help_text="Descripción del ítem (para productos personalizados)",
        verbose_name="Descripción"
    )
    cantidad = models.PositiveIntegerField(
        default=1,
        verbose_name="Cantidad"
    )
    precio_unitario = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Precio unitario"
    )
    gramos_por_unidad = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Gramos por unidad"
    )

    @property
    def subtotal(self):
        """Subtotal del ítem"""
        return self.precio_unitario * self.cantidad

    @property
    def gramos_totales(self):
        """Total de gramos del ítem"""
        return self.gramos_por_unidad * self.cantidad

    def __str__(self):
        if self.variante:
            return f"{self.cantidad}x {self.variante}"
        return f"{self.cantidad}x {self.descripcion}"

    class Meta:
        verbose_name = "Ítem de Pedido"
        verbose_name_plural = "Ítems de Pedido"


# =============================
# PAGOS
# =============================

class Pago(models.Model):
    """Registro de pagos realizados por el cliente"""
    METODOS = (
        ("Efectivo", "Efectivo"),
        ("Transferencia", "Transferencia bancaria"),
        ("Tarjeta", "Tarjeta de crédito/débito"),
        ("PayPal", "PayPal"),
        ("Otro", "Otro"),
    )

    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name="pagos",
        verbose_name="Pedido"
    )
    monto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Monto"
    )
    metodo = models.CharField(
        max_length=20,
        choices=METODOS,
        verbose_name="Método de pago"
    )
    fecha_pago = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de pago"
    )
    referencia = models.CharField(
        max_length=200,
        blank=True,
        help_text="Número de referencia, transacción, etc.",
        verbose_name="Referencia"
    )
    comprobante = models.ImageField(
        upload_to="pagos/comprobantes/",
        blank=True,
        null=True,
        verbose_name="Comprobante"
    )
    notas = models.TextField(
        blank=True,
        verbose_name="Notas"
    )

    def __str__(self):
        return f"Pago #{self.id} - Pedido #{self.pedido.id} - ${self.monto} ({self.get_metodo_display()})"

    class Meta:
        verbose_name = "Pago"
        verbose_name_plural = "Pagos"
        ordering = ["-fecha_pago"]


# =============================
# COMENTARIOS/ACTUALIZACIONES
# =============================

class ActualizacionPedido(models.Model):
    """
    Actualizaciones sobre el progreso del pedido.
    Permite mantener al cliente informado.
    """
    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name="actualizaciones",
        verbose_name="Pedido"
    )
    mensaje = models.TextField(
        verbose_name="Mensaje"
    )
    imagen = models.ImageField(
        upload_to="pedidos/actualizaciones/",
        blank=True,
        null=True,
        help_text="Foto del progreso",
        verbose_name="Imagen"
    )
    visible_cliente = models.BooleanField(
        default=True,
        help_text="¿El cliente puede ver esta actualización?",
        verbose_name="Visible para cliente"
    )
    fecha = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha"
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Registrado por"
    )

    def __str__(self):
        return f"Actualización - Pedido #{self.pedido.id} ({self.fecha.date()})"

    class Meta:
        verbose_name = "Actualización de Pedido"
        verbose_name_plural = "Actualizaciones de Pedidos"
        ordering = ["-fecha"]
