from django.urls import path
from . import views

app_name = "pedidos"

urlpatterns = [
    path("pedidos/", views.pedidos_admin, name="pedidos"),
]