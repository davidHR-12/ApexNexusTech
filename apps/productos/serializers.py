from rest_framework import serializers

from .models import Categoria, Producto


class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = [
            "id",
            "nombre",
            "descripcion",
            "imagen",
            "slug",
        ]
        read_only_fields = fields


class ProductoCatalogoSerializer(serializers.ModelSerializer):
    categoria = CategoriaSerializer(read_only=True)

    class Meta:
        model = Producto
        fields = [
            "id",
            "nombre",
            "slug",
            "descripcion",
            "precio_venta",
            "imagen",
            "destacado",
            "activo",
            "categoria",
        ]
        read_only_fields = fields