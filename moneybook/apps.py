from django.apps import AppConfig
# from moneybook.models import MasterCategory, Category


class MoneybookConfig(AppConfig):
    name = 'moneybook'

    def ready(self):
        # master = MasterCategory.objects.get_or_create(title='Income')
        # Category.objects.get_or_create(parent=master, title='Available this month')
        pass
