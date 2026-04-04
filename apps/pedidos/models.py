"""
Modelos para la gestión de pedidos y cotizaciones
"""

from django.db import models
from django.conf import settings
from decimal import Decimal
from django.db.models.signals import post_delete
from django.dispatch import receiver
from apps.core.models import Impresora
from django.contrib.auth.models import User
from django.conf import settings
from django.core.validators import FileExtensionValidator

# =============================
# SOLICITUDES DE COTIZACIÓN
# =============================


class SolicitudCotizacion(models.Model):
    """
    Solicitud de cotización iniciada por un cliente.
    Puede convertirse en un pedido una vez cotizada y aceptada.
    """

    ESTADOS = (
        ("Pendiente",   "Pendiente de revisión"),
        ("Completada",  "Convertida a pedido"),
        ("Rechazada",   "Rechazada"),
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="solicitudes_cotizacion",
        verbose_name="Cliente",
    )
    descripcion = models.TextField(
        help_text="Descripción del producto a cotizar", verbose_name="Descripción"
    )
    imagen_referencia = models.FileField(
        upload_to="pedidos/referencias/",
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp', 'svg'])],
        blank=True,
        max_length=255,
        null=True,
        verbose_name="Imagen de referencia",
    )
    enlace_referencia = models.URLField(
        blank=True,
        null=True,
        help_text="Link a un modelo 3D o referencia",
        verbose_name="Enlace de referencia",
    )
    dimensiones_aprox = models.CharField(
        max_length=100,
        help_text="Ej: 10x10x5 cm",
        blank=True,
        verbose_name="Dimensiones aproximadas",
    )
    estado = models.CharField(
        max_length=15, choices=ESTADOS, default="Pendiente", verbose_name="Estado"
    )
    fecha_solicitud = models.DateTimeField(
        auto_now_add=True, verbose_name="Fecha de solicitud"
    )

    def __str__(self):
        return (
            f"Solicitud #{self.id} - {self.usuario.email} ({self.get_estado_display()})"
        )

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
        verbose_name="Cliente",
        null=True,
        blank=True,
    )

    # Relación opcional con solicitud de cotización
    solicitud = models.OneToOneField(
        SolicitudCotizacion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Solicitud de cotización",
    )

    # Detalles del pedido
    descripcion = models.TextField(
        help_text="Descripción del pedido", verbose_name="Descripción"
    )
    stock_descontado = models.BooleanField(
        default=False, verbose_name="Stock descontado"
    )
    # Datos técnicos
    peso_estimado_g = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Peso estimado (gramos)",
    )

    costo_material = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, verbose_name="Costo de material"
    )
    otros_costos = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Costos adicionales (envío, acabados, etc.)",
        verbose_name="Otros costos",
    )
    precio_total = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, verbose_name="Precio total"
    )

    # Estado y fechas
    estado_pedido = models.CharField(
        max_length=20,
        choices=ESTADOS_PEDIDO,
        default="En_Espera",
        verbose_name="Estado",
    )
    fecha_creacion = models.DateTimeField(
        auto_now_add=True, verbose_name="Fecha de creación"
    )
    fecha_inicio_produccion = models.DateTimeField(
        null=True, blank=True, verbose_name="Fecha inicio producción"
    )
    fecha_entrega = models.DateTimeField(
        null=True, blank=True, verbose_name="Fecha de entrega"
    )

    # Información adicional
    notas = models.TextField(blank=True, verbose_name="Notas")

    metodo_pago_preferido = models.CharField(
        max_length=20,
        blank=True,
        choices=[
            ("Efectivo", "Efectivo"),
            ("Transferencia", "Transferencia bancaria"),
            ("Contraentrega", "Pago contraentrega"),
        ],
        verbose_name="Método de pago preferido",
    )

    comprobante_cliente = models.ImageField(
        upload_to="pagos/comprobantes_cliente/",
        blank=True,
        null=True,
        verbose_name="Comprobante del cliente",
    )
    comprobante_estado = models.CharField(
        max_length=20,
        blank=True,
        choices=[
            ("Pendiente", "Pendiente de revisión"),
            ("Aprobado", "Aprobado"),
            ("Rechazado", "Rechazado"),
        ],
        verbose_name="Estado del comprobante",
    )

    guest_nombre = models.CharField(
        max_length=200, blank=True, verbose_name="Nombre (Invitado)"
    )
    guest_email = models.EmailField(blank=True, verbose_name="Email (Invitado)")
    guest_telefono = models.CharField(
        max_length=20, blank=True, verbose_name="Teléfono (Invitado)"
    )
    guest_direccion = models.TextField(blank=True, verbose_name="Dirección (Invitado)")
    guest_ciudad = models.CharField(
        max_length=100, blank=True, verbose_name="Ciudad (Invitado)"
    )

    @property
    def costo_total_produccion(self):
        """Costo total de producción (sin margen)"""
        return self.costo_material +  self.otros_costos

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

    @property
    def porcentaje_progreso(self):
        progresos = {
            "En_Espera": 10,
            "Confirmado": 25,
            "En_Produccion": 60,
            "Listo": 90,
            "Entregado": 100,
        }
        return progresos.get(self.estado_pedido, 0)

    @property
    def nombre_cliente(self):
        if self.usuario:
            return self.usuario.get_full_name_or_user()
        return self.guest_nombre or "Invitado"

    @property
    def email_cliente(self):
        if self.usuario:
            return self.usuario.email
        return self.guest_email or "—"

    @property
    def telefono_cliente(self):
        if self.usuario:
            return self.usuario.telefono or "—"
        return self.guest_telefono or "—"
    
    @property
    def direccion_cliente(self):
        if self.usuario and hasattr(self.usuario, "perfil_cliente"):
            return self.usuario.perfil_cliente.get_direccion_completa()
        return self.guest_direccion or "—"
    

    def actualizar_totales(self):
        """
        Recalcula precio_total, costo_material y peso_estimado_g del pedido.

        Usa item.subtotal y item.gramos_totales (propiedades del modelo ItemPedido)
        que ya manejan la agregación de componentes para ítems contenedor.
        Prefetchear 'componentes' evita queries N+1.
        """
        items = self.items.filter(item_padre__isnull=True).prefetch_related(
            "componentes",
            "componentes__material_personalizado",
        )
        total_costo_prod = Decimal("0.00")
        total_venta      = Decimal("0.00")
        total_peso       = Decimal("0.00")

        for item in items:
            # ── Venta: usar la propiedad subtotal que ya sabe agregar componentes ──
            total_venta += item.subtotal          # Decimal
            total_peso  += item.gramos_totales    # Decimal

            # ── Costo de producción ───────────────────────────────────────────────
            if item.variante:
                total_costo_prod += item.variante.costo_produccion_total * item.cantidad

            elif item.es_contenedor:
                # Suma el costo de cada componente (gramos × costo_por_gramo)
                for comp in item.componentes.all():
                    total_costo_prod += (
                        Decimal(comp.gramos_por_unidad or 0)
                        * Decimal(comp.costo_material_unitario or 0)
                        * Decimal(comp.cantidad or 1)
                    )

            else:
                # Ítem legacy manual (sin variante, sin componentes)
                total_costo_prod += (
                    Decimal(item.gramos_por_unidad or 0)
                    * Decimal(item.costo_material_unitario or 0)
                    * Decimal(item.cantidad or 0)
                )

        self.costo_material  = total_costo_prod
        self.precio_total    = total_venta
        self.peso_estimado_g = total_peso
        super(Pedido, self).save(
            update_fields=["costo_material", "precio_total", "peso_estimado_g"]
        )

    def __str__(self):
        # Usamos el ID y la propiedad nombre_cliente para evitar errores de None
        return f"Pedido #{self.id} - {self.nombre_cliente} ({self.get_estado_pedido_display()})"

    class Meta:
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"
        ordering = ["-fecha_creacion"]




class ConfiguracionPago(models.Model):
    """
    Datos bancarios y de pago del negocio.
    Singleton: solo debe existir un registro activo.
    El admin los gestiona desde el panel de Django Admin.
    """
    banco = models.CharField(max_length=100, verbose_name="Nombre del banco")
    titular = models.CharField(max_length=200, verbose_name="Titular de la cuenta")
    numero_cuenta = models.CharField(max_length=50, verbose_name="Número de cuenta")
    tipo_cuenta = models.CharField(
        max_length=50, blank=True,
        verbose_name="Tipo de cuenta",
        help_text="Ej: Ahorro, Corriente"
    )
    cedula = models.CharField(
        max_length=20, blank=True,
        verbose_name="Cédula del titular"
    )
    telefono_pago = models.CharField(
        max_length=20, blank=True,
        verbose_name="Teléfono para pagos móviles"
    )
    instrucciones_adicionales = models.TextField(
        blank=True,
        verbose_name="Instrucciones adicionales",
        help_text="Texto extra que verá el cliente al seleccionar transferencia"
    )
    porcentaje_anticipo = models.DecimalField(
        max_digits=5, decimal_places=2, default=50.00,
        verbose_name="% de anticipo para pedidos personalizados",
        help_text="Porcentaje del total que se pide como pago inicial (ej: 50)"
    )
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Configuración de Pago"
        verbose_name_plural = "Configuración de Pagos"

    def __str__(self):
        return f"{self.banco} — {self.titular}"

    @classmethod
    def obtener(cls):
        """Retorna la configuración activa o None."""
        return cls.objects.filter(activo=True).first()

# =============================
# NOTAS DE PEDIDO
# =============================


class NotaPedido(models.Model):
    TIPOS = (
        ('manual',       'Manual'),           # Admin escribió manualmente
        ('otros_costos', 'Otros Costos'),      # Generada por agregar_otros_costos
        ('fallo',        'Fallo de Impresión'), # Generada por registrar_fallo
        ('sistema',      'Sistema'),           # Cualquier otra acción automática
    )
    pedido = models.ForeignKey(
        Pedido, on_delete=models.CASCADE, related_name="anotaciones"
    )
    # Cambiamos User por settings.AUTH_USER_MODEL
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    contenido = models.TextField()
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    # Campo nuevo para controlar la visibilidad
    visible_para_cliente = models.BooleanField(default=False)

    tipo = models.CharField(
        max_length=20,
        choices=TIPOS,
        default='manual',
        verbose_name='Tipo de nota',
    )

    class Meta:
        ordering = ["-fecha_creacion"]
        verbose_name = "Nota de pedido"
        verbose_name_plural = "Notas de pedido"

    def __str__(self):
        return f"Nota #{self.id} - Pedido {self.pedido.id} ({self.get_tipo_display()})"


# =============================
# ITEMS DE PEDIDO
# =============================


class ItemPedido(models.Model):
    """
    Producto individual dentro de un pedido.
    Permite pedidos con múltiples productos.
    """

    pedido = models.ForeignKey(
        Pedido, on_delete=models.CASCADE, related_name="items", verbose_name="Pedido"
    )
    variante = models.ForeignKey(
        "productos.VarianteProducto",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name="Variante de producto",
    )

    # Relación directa con material para piezas personalizadas
    material_personalizado = models.ForeignKey(
        "materiales.Material",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Material utilizado",
    )

    item_padre = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='componentes',
        verbose_name='Ítem contenedor',
        help_text='Si está asignado, este ítem es un componente de producción del ítem padre.',
    )

    fallo_registrado = models.BooleanField(
    default=False,
    verbose_name='Fallo registrado',
    help_text=(
        'True si este ítem/componente tuvo un fallo de impresión confirmado. '
        'El stock de su material NO se devuelve al revertir el pedido.'
        ),
    )

    descripcion = models.CharField(
        max_length=300,
        null=True,
        blank=True,
        help_text="Descripción del ítem (para productos personalizados)",
        verbose_name="Descripción/Nombre de pieza",
    )
    cantidad = models.PositiveIntegerField(default=1, verbose_name="Cantidad")
    precio_unitario = models.DecimalField(
        max_digits=12, decimal_places=2, default=0.00, verbose_name="Precio unitario"
    )
    gramos_por_unidad = models.DecimalField(
        default=0.00, max_digits=10, decimal_places=2, verbose_name="Gramos por unidad"
    )
    costo_material_unitario = models.DecimalField(
        max_digits=12, decimal_places=4, default=0.00
    )
    impresora_asignada = models.ForeignKey(
        "core.Impresora",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="items_asignados",
        verbose_name="Impresora",
    )

    @property
    def es_contenedor(self):
        """True si es un ítem personalizado padre (sin material propio, con componentes)."""
        return self.item_padre_id is None and self.variante_id is None

    @property
    def es_componente(self):
        return self.item_padre_id is not None

    @property
    def subtotal(self):
        """
        Si el ítem tiene componentes, el subtotal es la suma de ellos.
        Si no, es precio_unitario × cantidad (comportamiento original).
        """
        # Usamos _prefetched_objects_cache si ya está prefetcheado para evitar N+1
        if hasattr(self, '_componentes_cache'):
            comps = self._componentes_cache
        else:
            comps = list(self.componentes.all())

        if comps:
            return sum(c.precio_unitario * c.cantidad for c in comps)
        return self.precio_unitario * self.cantidad

    @property
    def precio_unitario_efectivo(self):
        """
        Precio por unidad real para mostrar al cliente.

        - Catálogo / componente → precio_unitario (guardado en DB).
        - Contenedor             → subtotal ÷ cantidad (precio_unitario está en 0
                                   porque el precio surge de los componentes).
        """
        if self.es_contenedor:
            cantidad = self.cantidad or 1
            return (self.subtotal / cantidad).quantize(Decimal("0.01")) if self.subtotal else Decimal("0.00")
        return self.precio_unitario

    @property
    def gramos_totales(self):
        if hasattr(self, '_componentes_cache'):
            comps = self._componentes_cache
        else:
            comps = list(self.componentes.all())

        if comps:
            return sum(c.gramos_por_unidad * c.cantidad for c in comps)
        return self.gramos_por_unidad * self.cantidad

    def __str__(self):
        if self.variante:
            return f"{self.cantidad}x {self.variante}"
        return f"{self.cantidad}x {self.descripcion}"

    def save(self, *args, **kwargs):
        if self.variante and (
            self.precio_unitario is None or self.precio_unitario == 0
        ):
            self.precio_unitario = self.variante.precio_final

        if self.variante and (
            self.gramos_por_unidad is None or self.gramos_por_unidad == 0
        ):
            # Si el producto base tiene el peso, lo traemos
            self.gramos_por_unidad = self.variante.peso_total

        # Guardamos el ítem
        super(ItemPedido, self).save(*args, **kwargs)

        # Después de guardar el ítem, disparamos el recálculo del pedido padre
        self.pedido.actualizar_totales()

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
        ("Contra_entrega", "Contra entrega"),
        ("Transferencia", "Transferencia bancaria"),
        ("Tarjeta", "Tarjeta de crédito/débito"),
        ("PayPal", "PayPal"),
        ("Otro", "Otro"),
    )

    pedido = models.ForeignKey(
        Pedido, on_delete=models.CASCADE, related_name="pagos", verbose_name="Pedido"
    )
    monto = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Monto")
    metodo = models.CharField(
        max_length=20, choices=METODOS, verbose_name="Método de pago"
    )
    fecha_pago = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de pago")
    referencia = models.CharField(
        max_length=200,
        blank=True,
        help_text="Número de referencia, transacción, etc.",
        verbose_name="Referencia",
    )
    comprobante = models.ImageField(
        upload_to="pagos/comprobantes/",
        blank=True,
        null=True,
        verbose_name="Comprobante",
    )
    notas = models.TextField(blank=True, verbose_name="Notas")

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
        verbose_name="Pedido",
    )
    mensaje = models.TextField(verbose_name="Mensaje")
    imagen = models.ImageField(
        upload_to="pedidos/actualizaciones/",
        blank=True,
        null=True,
        help_text="Foto del progreso",
        verbose_name="Imagen",
    )
    visible_cliente = models.BooleanField(
        default=True,
        help_text="¿El cliente puede ver esta actualización?",
        verbose_name="Visible para cliente",
    )
    fecha = models.DateTimeField(auto_now_add=True, verbose_name="Fecha")
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Registrado por",
    )

    def __str__(self):
        return f"Actualización - Pedido #{self.pedido.id} ({self.fecha.date()})"

    class Meta:
        verbose_name = "Actualización de Pedido"
        verbose_name_plural = "Actualizaciones de Pedidos"
        ordering = ["-fecha"]


class PerdidaMaterial(models.Model):
    """
    Registro interno de material perdido por fallos de impresión.
    
    - NO es un estado del pedido.
    - NO es visible para el cliente.
    - El pedido regresa a 'Confirmado' para poder reintentar la impresión.
    - El administrador puede ver el historial de pérdidas por pedido.
    """

    pedido = models.ForeignKey(
        'Pedido',
        on_delete=models.CASCADE,
        related_name='perdidas_material',
        verbose_name='Pedido',
    )
    material = models.ForeignKey(
        'materiales.Material',
        on_delete=models.PROTECT,
        verbose_name='Material perdido',
    )
    gramos_perdidos = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Gramos perdidos',
    )
    motivo = models.TextField(
        blank=True,
        verbose_name='Motivo / descripción del fallo',
        help_text='Ej: Adhesión fallida a la mitad de la impresión, fallo de filamento, etc.',
    )
    fecha = models.DateTimeField(auto_now_add=True, verbose_name='Fecha')
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Registrado por',
    )

    class Meta:
        verbose_name = 'Pérdida de Material'
        verbose_name_plural = 'Pérdidas de Material'
        ordering = ['-fecha']

    def __str__(self):
        return (
            f"Pérdida {self.gramos_perdidos}g de {self.material} "
            f"— Pedido #{self.pedido.id} ({self.fecha.date()})"
        )


# =============================
# SIGNALS
# =============================


@receiver(post_delete, sender=ItemPedido)
def recalcular_pedido_al_borrar_item(sender, instance, **kwargs):
    """
    Cuando se elimina un ítem, forzamos el recálculo de los totales del pedido.
    """
    if instance.pedido:
        instance.pedido.actualizar_totales()
