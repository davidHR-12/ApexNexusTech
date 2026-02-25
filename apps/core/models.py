from django.db import models


# Modelos de Impresoras
class Impresora(models.Model):
    ESTADOS = (
        ("Disponible", "Disponible"),
        ("Imprimiendo", "Imprimiendo"),
        ("Mantenimiento", "En Mantenimiento"),
        ("Offline", "Fuera de Servicio"),
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


class ConfiguracionSitio(models.Model):
    """
    Singleton — solo existe 1 registro (pk=1).
    Configuración SIMPLIFICADA del sitio público.
    """

    # ══════════════════════════════════════════════
    # ESTADÍSTICAS (franja de métricas) - ESTÁTICAS
    # ══════════════════════════════════════════════
    stat_piezas_numero = models.PositiveIntegerField(
        default=50, verbose_name="Número: piezas producidas"
    )
    stat_piezas_etiqueta = models.CharField(
        max_length=40, default="Piezas Producidas",
        verbose_name="Etiqueta: piezas producidas"
    )
    stat_respuesta_numero = models.CharField(
        max_length=20, default="24h",
        verbose_name="Número: tiempo de respuesta"
    )
    stat_respuesta_etiqueta = models.CharField(
        max_length=40, default="Respuesta Rápida",
        verbose_name="Etiqueta: tiempo de respuesta"
    )
    stat_materiales_numero = models.CharField(
        max_length=20, default="8+",
        verbose_name="Número: tipos de material"
    )
    stat_materiales_etiqueta = models.CharField(
        max_length=40, default="Tipos de Material",
        verbose_name="Etiqueta: tipos de material"
    )
    stat_garantia_numero = models.CharField(
        max_length=20, default="100%",
        verbose_name="Número: garantía"
    )
    stat_garantia_etiqueta = models.CharField(
        max_length=40, default="Garantía de Calidad",
        verbose_name="Etiqueta: garantía"
    )

    # ══════════════════════════════════════════════
    # SECCIÓN MATERIALES - DÓNDE MOSTRAR
    # ══════════════════════════════════════════════
    mostrar_materiales_en_index = models.BooleanField(
        default=True, 
        verbose_name="Mostrar materiales en Inicio"
    )
    mostrar_materiales_en_pagina = models.BooleanField(
        default=True, 
        verbose_name="Mostrar materiales en página Materiales"
    )

    # ══════════════════════════════════════════════
    # SECCIÓN PRODUCTOS DESTACADOS - OPCIONAL
    # ══════════════════════════════════════════════
    mostrar_seccion_productos_destacados = models.BooleanField(
        default=True, verbose_name="Mostrar sección 'Lo más pedido'"
    )
    max_productos_destacados = models.PositiveSmallIntegerField(
        default=4, verbose_name="Máx. productos a mostrar (1–8)"
    )

    # ══════════════════════════════════════════════
    # PÁGINA DE PROCESO - ESTÁTICA
    # ══════════════════════════════════════════════
    proceso_titulo = models.CharField(
        max_length=80, default="Proceso de Realización",
        verbose_name="Título de la página Proceso"
    )
    proceso_subtitulo = models.CharField(
        max_length=200, default="Desde una simple idea o un archivo profesional hasta la pieza en tus manos.",
        verbose_name="Subtítulo de la página Proceso"
    )

    # ══════════════════════════════════════════════
    # CONTACTO / WHATSAPP
    # ══════════════════════════════════════════════
    whatsapp_numero = models.CharField(
        max_length=20, blank=True, default="",
        verbose_name="Número WhatsApp (formato: 18095551234)"
    )
    mostrar_boton_whatsapp = models.BooleanField(
        default=False, verbose_name="Mostrar botón flotante de WhatsApp"
    )
    email_contacto = models.EmailField(
        blank=True, default="info@3dprint.do",
        verbose_name="Email de contacto (footer)"
    )
    ciudad_contacto = models.CharField(
        max_length=80, blank=True, default="Santo Domingo, RD",
        verbose_name="Ciudad (footer)"
    )

    class Meta:
        verbose_name = "Configuración del Sitio"
        verbose_name_plural = "Configuración del Sitio"

    def __str__(self):
        return "Configuración del Sitio Público"

    @classmethod
    def obtener(cls):
        """Devuelve la única instancia, creándola con defaults si no existe."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class CardPublica(models.Model):
    """
    Cards editables del sitio público.
    Se usan en:
    - index.html: Carrusel de materiales (si está activado)
    - materiales.html: Las tarjetas de materiales (si está activado)
    - proceso.html: Los pasos del proceso de producción
    """
    SECCION_CHOICES = (
        ('materiales', 'Materiales'),
        ('proceso',    'Pasos del Proceso'),
    )
    BADGE_COLOR_CHOICES = (
        ('gray',   'Gris (default)'),
        ('green',  'Verde'),
        ('purple', 'Morado'),
        ('blue',   'Azul'),
        ('red',    'Rojo'),
        ('yellow', 'Amarillo'),
    )

    seccion     = models.CharField(max_length=20, choices=SECCION_CHOICES, verbose_name="Sección")
    orden       = models.PositiveSmallIntegerField(default=0, verbose_name="Orden")
    activo      = models.BooleanField(default=True, verbose_name="Visible")

    # Compartido
    titulo      = models.CharField(max_length=100, verbose_name="Título")
    descripcion = models.TextField(verbose_name="Descripción / Contenido")
    
    # IMAGEN
    imagen      = models.ImageField(
        upload_to='cards/', 
        blank=True, 
        null=True, 
        max_length=255,
        verbose_name="Imagen del card",
        help_text="Recomendado: 400x300px"
    )

    # Solo materiales
    badge_texto = models.CharField(
        max_length=40, blank=True, default="", 
        verbose_name="Texto del badge (ej: Estético)"
    )
    badge_color = models.CharField(
        max_length=10, choices=BADGE_COLOR_CHOICES, default='gray', 
        verbose_name="Color del badge"
    )
    tags        = models.CharField(
        max_length=200, blank=True, default="",
        verbose_name="Tags separados por coma",
        help_text="Ej: Fácil de Pintar, Eco-Friendly"
    )

    # Solo proceso
    paso_numero = models.PositiveSmallIntegerField(
        null=True, blank=True, 
        verbose_name="Número del paso"
    )
    es_paso_destacado = models.BooleanField(
        default=False, 
        verbose_name="Paso destacado (verde)"
    )

    class Meta:
        ordering = ['seccion', 'orden']
        verbose_name = "Card Pública"
        verbose_name_plural = "Cards Públicas"

    def get_tags_list(self):
        """Retorna los tags como lista para iterar en templates."""
        if not self.tags:
            return []
        return [t.strip() for t in self.tags.split(',') if t.strip()]

    def get_badge_classes(self):
        """Retorna las clases Tailwind según el color del badge."""
        mapa = {
            'gray':   'bg-black/50 text-white',
            'green':  'bg-[#10b981]/20 text-[#10b981] border border-[#10b981]/30',
            'purple': 'bg-purple-500/20 text-purple-400 border border-purple-500/30',
            'blue':   'bg-blue-500/20 text-blue-400 border border-blue-500/30',
            'red':    'bg-red-500/20 text-red-400 border border-red-500/30',
            'yellow': 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30',
        }
        return mapa.get(self.badge_color, mapa['gray'])

    def __str__(self):
        return f"[{self.get_seccion_display()}] {self.titulo}"