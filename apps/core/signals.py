from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.text import slugify
import threading
import logging
from apps.materiales.models import Marca, TipoMaterial, Color, Material
from apps.productos.models import Categoria
from decimal import Decimal
import time

Usuario = get_user_model()
logger = logging.getLogger(__name__)


def _inicializar_catalogo_background():
    """
    Inicializa el catálogo en un thread separado.
    Se ejecuta DESPUÉS de que la transacción de registro se guarde,
    sin bloquear la respuesta HTTP del usuario.
    """
    start = time.time()
    try:
        logger.info("Iniciando inicialización de catálogo en background...")

        # --- 1. Inicializar Categorías Detalladas ---
        categorias_iniciales = [
            {
                "nombre": "Sin Categorizar",
                "descripcion": "Categoría temporal para productos que han perdido su clasificación original o sin categorizar.",
            },
            {
                "nombre": "Bustos y FanArt",
                "descripcion": "Modelos detallados de personajes, figuras de acción y esculturas artísticas de alta complejidad.",
            },
            {
                "nombre": "Llaveros y Souvenirs",
                "descripcion": "Piezas pequeñas de alta rotación, ideales para regalos masivos, logos personalizados y recuerdos.",
            },
            {
                "nombre": "Hogar y Gadgets",
                "descripcion": "Soluciones útiles: desde macetas autorregables y lámparas hasta soportes para audífonos y cocina.",
            },
            {
                "nombre": "Prototipos Técnicos",
                "descripcion": "Piezas mecánicas, engranajes y componentes funcionales que requieren precisión y resistencia industrial.",
            },
            {
                "nombre": "Litofanías y Arte Personalizado",
                "descripcion": "Impresiones que revelan imágenes detalladas al pasar la luz, cuadros 3D y decoraciones de pared.",
            },
            {
                "nombre": "Accesorios y Joyería",
                "descripcion": "Aretes, brazaletes y complementos de moda impresos con filamentos especiales (seda, mármol, madera).",
            },
            {
                "nombre": "Organizadores y Taller",
                "descripcion": "Soportes para herramientas, racks de filamento y sistemas modulares para mantener el orden.",
            },
        ]

        # Crear categorías con slug generado
        categorias_a_crear = []
        for cat_data in categorias_iniciales:
            if not Categoria.objects.filter(nombre=cat_data["nombre"]).exists():
                # 🔑 IMPORTANTE: Generar slug antes de bulk_create
                slug = slugify(cat_data["nombre"])
                categorias_a_crear.append(
                    Categoria(
                        nombre=cat_data["nombre"],
                        slug=slug,  # ← Slug generado automáticamente
                        descripcion=cat_data["descripcion"],
                    )
                )

        if categorias_a_crear:
            Categoria.objects.bulk_create(categorias_a_crear)
            logger.info(f"✓ {len(categorias_a_crear)} categorías creadas")

        # --- 2. Inicializar Atributos de Impresión ---
        marcas = ["Creality", "Bambu Lab", "eSun", "Hatchbox", "Polyterra", "Overture"]
        tipos = ["PLA", "PETG", "ABS", "ASA", "TPU"]
        colores = [
            "Negro",
            "Blanco",
            "Gris",
            "Rojo",
            "Azul",
            "Verde",
            "Dorado",
            "Plateado",
            "Amarillo",
        ]

        # Creamos los objetos base con get_or_create (más lento pero seguro)
        m_objs = [Marca.objects.get_or_create(nombre=m)[0] for m in marcas]
        t_objs = [TipoMaterial.objects.get_or_create(nombre=t)[0] for t in tipos]
        c_objs = [Color.objects.get_or_create(nombre=c)[0] for c in colores]

        logger.info("Marcas, tipos y colores base configurados")

        # --- 3. Crear Combinaciones de Materiales (OPTIMIZADO) ---
        marcas_principales = ["Creality", "Bambu Lab", "eSun", "Polyterra"]

        materiales_a_crear = []
        for m in m_objs:
            if m.nombre in marcas_principales:
                for t in t_objs:
                    for c in c_objs:
                        # Verificar si ya existe para evitar duplicados
                        if not Material.objects.filter(
                            tipo=t, marca=m, color=c
                        ).exists():
                            materiales_a_crear.append(
                                Material(
                                    tipo=t,
                                    marca=m,
                                    color=c,
                                    costo_por_gramo=Decimal("1.25"),
                                    stock_actual=Decimal("0.00"),
                                    stock_minimo=Decimal("250.00"),
                                )
                            )

        # Usar bulk_create para crear todos los materiales de una vez
        if materiales_a_crear:
            Material.objects.bulk_create(materiales_a_crear, batch_size=500)
            logger.info(f"✓ {len(materiales_a_crear)} materiales creados")

        end = time.time()
        logger.info(f"⏱ Catálogo inicializado en {end - start:.2f} segundos")

    except Exception as e:
        logger.error(f"Error inicializando catálogo: {str(e)}", exc_info=True)


@receiver(post_save, sender=Usuario)
def inicializar_sistema_primer_usuario(sender, instance, created, **kwargs):
    """
    Signal que se dispara cuando se crea un nuevo usuario.
    Si es el primer usuario, programa la inicialización del catálogo
    en un thread background para no bloquear la respuesta HTTP.
    """
    if created and Usuario.objects.count() == 1:
        logger.info(
            "👤 Primer usuario detectado. Programando inicialización de catálogo..."
        )

        # Ejecutar en background DESPUÉS de que la transacción se guarde
        transaction.on_commit(
            lambda: threading.Thread(
                target=_inicializar_catalogo_background,
                daemon=True,
                name="InitCatalogThread",
            ).start()
        )
