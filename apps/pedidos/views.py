from django.shortcuts import render

# Create your views here.
def pedidos_admin(request):
    return render(request, "pedidos/pedidos_admin.html")