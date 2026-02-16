from django.shortcuts import render
from apps.usuarios.decorators import admin_required
from django.utils import timezone
from django.db.models import Sum
from decimal import Decimal

from apps.pedidos.models import Pago
from apps.finanzas.models import Gasto
from apps.materiales.models import Material
from apps.pedidos.models import Pedido
from .models import ConfiguracionDashboard


