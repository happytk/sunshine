from django.core.management.base import BaseCommand
from moneybook.models import Transaction, Account
from django.utils.text import slugify
from category.models import Category
import datetime
import pytz
import csv


def _process(line):
    account, flag, checknumber, date, payee, category, mastercategory, subcategory, memo, outflow, inflow, cleared, runningbalance = line
    acc, _ = Account.objects.get_or_create(title=account)

    unaware_date = datetime.datetime.strptime(date, '%Y-%m-%d')
    aware_date = pytz.utc.localize(unaware_date)

    if category:
        category, _ = Category.objects.get_or_create(title=category, slug=slugify(category))
    else:
        category = None
    # amount = int(outflow[1:]) - int(inflow[1:])

    Transaction(
        inflow=int(inflow[1:]),
        outflow=int(outflow[1:]),
        category=category,
        expensed_at=aware_date,
        account=acc,
        memo=memo,
        payee=payee).save()


class Command(BaseCommand):
    help = 'Generate random datasets based on lorem-package text.'

    def handle(self, *args, **options):
        reader = csv.reader(open('resources/2019_FRESH_START.csv'))
        for line in reader:
            print(line)
            _process(line)
