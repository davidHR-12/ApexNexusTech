from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Sum
from decimal import Decimal

# Importaciones de tus nuevas apps modulares
from apps.pedidos.models import Pago
from apps.finanzas.models import Gasto  # Ajusta si Gasto está en otra app
from apps.materiales.models import Material
from apps.pedidos.models import Pedido
# El modelo que ya tenías en reportes
from .models import ConfiguracionDashboard


