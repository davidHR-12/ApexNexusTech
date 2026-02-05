"""
Modelos para la gestión financiera y contabilidad
"""
from django.db import models
from decimal import Decimal


# =============================
# GASTOS
# =============================

class Gasto(models.Model):
    """
    Registro de todos los gastos del negocio.
    Incluye compras de material, mantenimiento, energía, etc.
    """
    TIPOS = (
        ("Mantenimiento", "Mantenimiento de equipo"),
        ("Energia", "Energía eléctrica"),
        ("Compra_Material", "Compra de material"),
        ("Herramientas", "Herramientas y accesorios"),
        ("Servicios", "Servicios (internet, teléfono, etc.)"),
        ("Otro", "Otro"),
    )

    descripcion = models.CharField(
        max_length=200,
        verbose_name="Descripción"
    )
    monto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Monto"
    )
    fecha = models.DateField(
        verbose_name="Fecha"
    )
    tipo = models.CharField(
        max_length=20,
        choices=TIPOS,
        verbose_name="Tipo de gasto"
    )

    # Relación opcional con entrada de inventario
    entrada_inventario = models.ForeignKey(
        "materiales.EntradaInventario",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Entrada de inventario"
    )

    # Información adicional
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
    comprobante = models.ImageField(
        upload_to="finanzas/comprobantes/",
        blank=True,
        null=True,
        verbose_name="Comprobante"
    )
    notas = models.TextField(
        blank=True,
        verbose_name="Notas"
    )

    # Categorización
    es_recurrente = models.BooleanField(
        default=False,
        help_text="¿Es un gasto mensual recurrente?",
        verbose_name="Gasto recurrente"
    )

    def __str__(self):
        return f"{self.get_tipo_display()}: {self.descripcion} - ${self.monto} ({self.fecha})"

    class Meta:
        verbose_name = "Gasto"
        verbose_name_plural = "Gastos"
        ordering = ["-fecha"]


# =============================
# INGRESOS
# =============================

class Ingreso(models.Model):
    """
    Registro de ingresos del negocio.
    Se genera automáticamente al registrar pagos de pedidos.
    """
    FUENTES = (
        ("Pedido", "Pago de pedido"),
        ("Venta_Directa", "Venta directa"),
        ("Servicio", "Servicio adicional"),
        ("Otro", "Otro"),
    )

    descripcion = models.CharField(
        max_length=200,
        verbose_name="Descripción"
    )
    monto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Monto"
    )
    fecha = models.DateField(
        verbose_name="Fecha"
    )
    fuente = models.CharField(
        max_length=20,
        choices=FUENTES,
        default="Pedido",
        verbose_name="Fuente de ingreso"
    )

    # Relación opcional con pago de pedido
    pago = models.OneToOneField(
        "pedidos.Pago",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Pago relacionado"
    )

    # Información adicional
    cliente = models.ForeignKey(
        "usuarios.Usuario",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Cliente"
    )
    notas = models.TextField(
        blank=True,
        verbose_name="Notas"
    )

    def __str__(self):
        return f"{self.get_fuente_display()}: {self.descripcion} - ${self.monto} ({self.fecha})"

    class Meta:
        verbose_name = "Ingreso"
        verbose_name_plural = "Ingresos"
        ordering = ["-fecha"]


# =============================
# PRESUPUESTOS MENSUALES
# =============================

class PresupuestoMensual(models.Model):
    """
    Presupuesto planificado por mes y categoría.
    Permite comparar gastos reales vs. planificados.
    """
    mes = models.DateField(
        help_text="Primer día del mes",
        verbose_name="Mes"
    )
    tipo_gasto = models.CharField(
        max_length=20,
        choices=Gasto.TIPOS,
        verbose_name="Tipo de gasto"
    )
    monto_presupuestado = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Monto presupuestado"
    )
    notas = models.TextField(
        blank=True,
        verbose_name="Notas"
    )

    def gasto_real(self):
        """Calcula el gasto real del mes en esta categoría"""
        mes_inicio = self.mes
        # Último día del mes
        if mes_inicio.month == 12:
            mes_fin = mes_inicio.replace(
                year=mes_inicio.year + 1, month=1, day=1)
        else:
            mes_fin = mes_inicio.replace(month=mes_inicio.month + 1, day=1)

        gastos = Gasto.objects.filter(
            tipo=self.tipo_gasto,
            fecha__gte=mes_inicio,
            fecha__lt=mes_fin
        )
        return sum(g.monto for g in gastos)

    def diferencia(self):
        """Diferencia entre presupuestado y real (positivo = ahorro)"""
        return self.monto_presupuestado - self.gasto_real()

    def porcentaje_usado(self):
        """Porcentaje del presupuesto utilizado"""
        if self.monto_presupuestado > 0:
            return (self.gasto_real() / self.monto_presupuestado * 100).quantize(Decimal("0.01"))
        return Decimal("0.00")

    def __str__(self):
        return f"{self.mes.strftime('%B %Y')} - {self.get_tipo_gasto_display()}: ${self.monto_presupuestado}"

    class Meta:
        verbose_name = "Presupuesto Mensual"
        verbose_name_plural = "Presupuestos Mensuales"
        unique_together = ("mes", "tipo_gasto")
        ordering = ["-mes", "tipo_gasto"]


# =============================
# CUENTAS POR COBRAR
# =============================

class CuentaPorCobrar(models.Model):
    """
    Registro de deudas pendientes de clientes.
    Para pedidos que aún no han sido pagados completamente.
    """
    ESTADOS = (
        ("Pendiente", "Pendiente"),
        ("Parcial", "Pago parcial"),
        ("Cobrado", "Cobrado"),
        ("Vencido", "Vencido"),
        ("Incobrable", "Incobrable"),
    )

    pedido = models.OneToOneField(
        "pedidos.Pedido",
        on_delete=models.CASCADE,
        verbose_name="Pedido"
    )
    monto_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Monto total"
    )
    monto_pagado = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Monto pagado"
    )
    estado = models.CharField(
        max_length=15,
        choices=ESTADOS,
        default="Pendiente",
        verbose_name="Estado"
    )
    fecha_emision = models.DateField(
        verbose_name="Fecha de emisión"
    )
    fecha_vencimiento = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de vencimiento"
    )
    notas = models.TextField(
        blank=True,
        verbose_name="Notas"
    )

    @property
    def monto_pendiente(self):
        """Monto que falta por pagar"""
        return self.monto_total - self.monto_pagado

    @property
    def esta_vencida(self):
        """Verifica si la cuenta está vencida"""
        from datetime import date
        return self.fecha_vencimiento and date.today() > self.fecha_vencimiento

    def __str__(self):
        return f"CxC - Pedido #{self.pedido.id} - ${self.monto_pendiente} pendiente"

    class Meta:
        verbose_name = "Cuenta por Cobrar"
        verbose_name_plural = "Cuentas por Cobrar"
        ordering = ["fecha_vencimiento"]
