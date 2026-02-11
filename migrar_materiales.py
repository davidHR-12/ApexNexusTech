import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.productos.models import VarianteProducto, VarianteMaterialDetalle

def migrar():
    variantes = VarianteProducto.objects.all()
    for v in variantes:
        if v.material: # Si tiene el material viejo
            # Crear el detalle usando el peso_gramos del producto base
            VarianteMaterialDetalle.objects.get_or_create(
                variante=v,
                material=v.material,
                defaults={'gramos_usados': v.producto.peso_gramos}
            )
            print(f"Migrada variante: {v}")

if __name__ == "__main__":
    migrar()