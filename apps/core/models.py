from django.db import models


# Modelos de Impresoras
class Impresora(models.Model):
    ESTADOS = (
        ("Disponible", "Disponible"),
        ("Imprimiendo", "Imprimiendo"),
        ("Mantenimiento", "En Mantenimiento"),
        ("Offline", "Fuera de Servicio"),  # Añadí este para el botón de "apagar"
    )

    nombre = models.CharField(
        max_length=100, verbose_name="Nombre de la Impresora", unique=True
    )
    modelo = models.CharField(max_length=100, help_text="Ej: Ender 3, Artillery X2")
    estado = models.CharField(max_length=20, choices=ESTADOS, default="Disponible")

    def actualizar_estado_automatico(self):
        """
        Solo interviene si la impresora dice estar 'Imprimiendo'.
        Si está en Mantenimiento u Offline, respeta la decisión del administrador.
        """
        if self.estado == "Imprimiendo":
            # Verificamos si existe algún ítem de pedido que REALMENTE
            # esté en producción ahora mismo con esta máquina.
            hay_trabajo_real = self.items_asignados.filter(
                pedido__estado_pedido="En_Produccion"
            ).exists()

            if not hay_trabajo_real:
                self.estado = "Disponible"
                self.save()
                return True

        return False

    def __str__(self):
        return f"{self.nombre} ({self.modelo})"

    class Meta:
        verbose_name = "Impresora"
        verbose_name_plural = "Impresoras"
