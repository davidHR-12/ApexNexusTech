# apps/core/admin.py
from django.contrib import admin
from .models import Impresora


@admin.register(Impresora)
class ImpresoraAdmin(admin.ModelAdmin):
    list_display = ("nombre", "modelo", "estado")
    list_filter = ("estado",)
    search_fields = ("nombre", "modelo")
    list_editable = ("estado",)
    ordering = ("nombre",)