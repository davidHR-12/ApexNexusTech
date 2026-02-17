from django.db import models

# Modelos de Impresoras
class Impresora(models.Model):
    ESTADOS = (
        ("Disponible", "Disponible"),
        ("Imprimiendo", "Imprimiendo"),
        ("Mantenimiento", "En Mantenimiento"),
        ("Offline", "Fuera de Servicio"), # Añadí este para el botón de "apagar"
    )

    nombre = models.CharField(max_length=100, verbose_name="Nombre de la Impresora", unique=True)
    modelo = models.CharField(max_length=100, help_text="Ej: Ender 3, Artillery X2")
    estado = models.CharField(max_length=20, choices=ESTADOS, default="Disponible")
    
    # Podrías agregar campos técnicos aquí más adelante
    # costo_hora = models.DecimalField(...) 

    def __str__(self):
        return f"{self.nombre} ({self.modelo})"

    class Meta:
        verbose_name = "Impresora"
        verbose_name_plural = "Impresoras"