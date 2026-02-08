from django.apps import AppConfig


class ClientesConfig(AppConfig):
    name = 'apps.clientes'

    def ready(self):
        import apps.clientes.signals
