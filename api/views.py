from django.shortcuts import render
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.decorators import api_view
from apps.productos.models import Producto
from apps.productos.serializers import ProductoCatalogoSerializer


# Create your views here.

@api_view(["GET"])
def inicio_api(request):
    return Response({
        "mensaje": "API de ApexNexusTech funcionando",
        "version": "1.0",
    })


class ProductoCatalogoListView(generics.ListAPIView):
    queryset = (
        Producto.objects
        .filter(mostrar_en_web=True, activo=True)
        .select_related("categoria")
    )
    serializer_class = ProductoCatalogoSerializer