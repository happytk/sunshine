from django.core.management.base import BaseCommand
from moneybook.models import Transaction, Account, Transfer, Category, MasterCategory
# from django.utils.text import slugify
import datetime
import pytz
import csv


def _process(line):
    account, flag, checknumber, date, payee, category, mastercategory, subcategory, memo, outflow, inflow, cleared, runningbalance = line
    acc, _ = Account.objects.get_or_create(title=account)

    unaware_date = datetime.datetime.strptime(date, '%Y-%m-%d')
    aware_date = pytz.utc.localize(unaware_date)

    if category:
        # master_category, _ = Category.objects.get_or_create(title=category.split(':')[0], slug=slugify(category.split(':')[0]))
        master_category, _ = MasterCategory.objects.get_or_create(
            title=mastercategory)

        category, _ = Category.objects.get_or_create(
            # parent=master_category,
            full_title=category,
            title=subcategory,
            parent=master_category,
            # slug=slugify(category)
        )
    else:
        category = None
    # amount = int(outflow[1:]) - int(inflow[1:])
    inflow = int(inflow[1:])
    outflow = int(outflow[1:])
    cleared = (cleared == 'R')

    if payee.startswith('Transfer :'):  # Transfer : KEB-HANA
        if outflow:
            acc_to, _ = Account.objects.get_or_create(title=payee[len('Transfer : '):])
            # print('hello', memo, acc_to)
            Transfer(
                account_from=acc,
                account_to=acc_to,
                transfered_at=aware_date,
                amount=outflow
            ).save()
        elif inflow:
            pass  # inflow transfer is skipped because it is duplicated item with outflow.
    else:
        Transaction(
            inflow=inflow,
            outflow=outflow,
            category=category,
            expensed_at=aware_date,
            account=acc,
            memo=memo,
            cleared=cleared,
            payee=payee).save()


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            'csvfile',
        )
        parser.add_argument(
            '--delete',
            action='store_true',
            dest='delete',
            help='Delete all budget',
        )

    def handle(self, *args, **options):
        reader = csv.reader(open(options['csvfile']))
        if options['delete']:
            Transaction.objects.all().delete()
            Transfer.objects.all().delete()
            Category.objects.all().delete()
            Account.objects.all().delete()
        for index, line in enumerate(reader):
            if index == 0:
                self.stdout.write(self.style.SUCCESS(line))
                continue
            self.stdout.write(self.style.SUCCESS(line))
            _process(line)
