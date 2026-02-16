from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.text import slugify
import threading
import logging
from apps.materiales.models import Marca, TipoMaterial, Color, Material
from apps.productos.models import Categoria, Producto
from decimal import Decimal
import time
import os
from django.db.models.signals import post_delete, pre_save
from apps.finanzas.models import Gasto 

# Lista de modelos para no repetir código
MODELOS_CON_IMAGEN = [Categoria, Producto, Gasto]

@receiver(post_delete)
def borrar_archivo_al_eliminar_registro(sender, instance, **kwargs):
    if sender in MODELOS_CON_IMAGEN:
        # Buscamos campos de tipo imagen/archivo en la instancia
        for field in instance._meta.fields:
            if field.get_internal_type() in ['FileField', 'ImageField']:
                archivo = getattr(instance, field.name)
                if archivo and os.path.isfile(archivo.path):
                    os.remove(archivo.path)

@receiver(pre_save)
def borrar_archivo_viejo_al_actualizar(sender, instance, **kwargs):
    if sender in MODELOS_CON_IMAGEN:
        if not instance.pk:
            return False

        try:
            old_instance = sender.objects.get(pk=instance.pk)
        except sender.DoesNotExist:
            return False

        for field in instance._meta.fields:
            if field.get_internal_type() in ['FileField', 'ImageField']:
                old_file = getattr(old_instance, field.name)
                new_file = getattr(instance, field.name)
                
                # Si el archivo cambió, borramos el viejo
                if old_file and old_file != new_file:
                    if os.path.isfile(old_file.path):
                        os.remove(old_file.path)


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
                # IMPORTANTE: Generar slug antes de bulk_create
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
            logger.info(f"{len(categorias_a_crear)} categorías creadas")

        # --- 2. Inicializar Atributos de Impresión ---
        marcas_config = {
            "Creality": "https://store.creality.com/eu/collections/materials",
            "Bambu Lab": "https://us.store.bambulab.com/",
            "eSun": "https://www.esun3d.com/filaments/",
            "Polyterra": "https://keitron.com/collections/filamento",
            "Elegoo": "https://gabytronicx.com/product-category/filamentos/"
        }
        tipos = ["PLA", "PETG", "ABS", "TPU"]
        colores = {
            "Negro": "#000000",
            "Blanco": "#FFFFFF",
            "Gris": "#808080",
            "Rojo": "#FF0000",
            "Azul": "#0000FF",
            "Verde": "#00FF00",
            "Amarillo": "#FFFF00",
        }

        # Creamos las Marcas y guardamos referencia en un dict para acceso rápido
        m_objs = {nombre: Marca.objects.get_or_create(nombre=nombre)[0] for nombre in marcas_config.keys()}
        # Creamos los Tipos
        t_objs = [TipoMaterial.objects.get_or_create(nombre=t)[0] for t in tipos]
        
        # Creamos los Colores
        c_objs = []
        for nombre, hex_code in colores.items():
            color, created = Color.objects.get_or_create(
                nombre=nombre,
                defaults={'codigo_hex': hex_code}
            )
            if not created and (not color.codigo_hex or color.codigo_hex == ''):
                color.codigo_hex = hex_code
                color.save()
            c_objs.append(color)

        logger.info("Marcas, tipos y colores base configurados")

        # --- 3. Crear Combinaciones de Materiales (CON ENLACE DE COMPRA) ---
        materiales_a_crear = []
        
        for nombre_marca, m_obj in m_objs.items():
            enlace = marcas_config[nombre_marca]  # Obtenemos el link del dict
            
            for t_obj in t_objs:
                for c_obj in c_objs:
                    # Verificar si ya existe
                    if not Material.objects.filter(tipo=t_obj, marca=m_obj, color=c_obj).exists():
                        materiales_a_crear.append(
                            Material(
                                tipo=t_obj,
                                marca=m_obj,
                                color=c_obj,
                                costo_por_gramo=Decimal("1.25"),
                                stock_actual=Decimal("0.00"),
                                stock_minimo=Decimal("250.00"),
                                enlace_compra=enlace,  # ← Se asigna el link según la marca
                                activo=True
                            )
                        )

        if materiales_a_crear:
            Material.objects.bulk_create(materiales_a_crear, batch_size=500)
            logger.info(f"{len(materiales_a_crear)} materiales creados con sus respectivos enlaces")

        end = time.time()
        logger.info(f"Catálogo inicializado en {end - start:.2f} segundos")

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
            "Primer usuario detectado. Programando inicialización de catálogo..."
        )

        # Ejecutar en background DESPUÉS de que la transacción se guarde
        transaction.on_commit(
            lambda: threading.Thread(
                target=_inicializar_catalogo_background,
                daemon=True,
                name="InitCatalogThread",
            ).start()
        )