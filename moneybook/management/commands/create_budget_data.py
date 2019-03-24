from django.core.management.base import BaseCommand
from moneybook.models import Budget, BudgetBundle


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('iteration', nargs='?', type=int, default=12)
        # Named (optional) arguments
        parser.add_argument(
            '--delete',
            action='store_true',
            dest='delete',
            help='Delete all budget',
        )

    def handle(self, *args, **options):
        if options['delete']:
            Budget.objects.all().delete()
            BudgetBundle.objects.all().delete()

        BudgetBundle.create_each_categories(iteration=options['iteration'])
