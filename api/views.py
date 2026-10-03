from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.decorators import api_view

# Create your views here.

@api_view(["GET"])
def inicio_api(request):
    return Response({
        "mensaje": "API de ApexNexusTech funcionando",
        "version": "1.0",
    })