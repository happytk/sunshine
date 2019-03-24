from django.core.management.base import BaseCommand
from moneybook.models import Transaction, Account
from django.utils.text import slugify
from category.models import Category
import datetime
import pytz
import csv


def _process(line):
    # 2018.04.05 12:53:31,정상,일시불,10,500,03 월 버스 10건,129-86-38970
    date, _, _, outflow, payee, _, _ = line
    # account, flag, checknumber, date, payee, category, mastercategory, subcategory, memo, outflow, inflow, cleared, runningbalance = line
    acc, _ = Account.objects.get_or_create(title='KAKAOBANK')

    unaware_date = datetime.datetime.strptime(date, '%Y.%m.%d %H:%M:%S')
    aware_date = pytz.utc.localize(unaware_date)
    category = None
    outflow = int(outflow.replace(',', ''))

    Transaction(
        inflow=0,
        outflow=outflow,
        category=category,
        expensed_at=aware_date,
        account=acc,
        payee=payee).save()


class Command(BaseCommand):
    help = 'Generate random datasets based on lorem-package text.'

    def handle(self, *args, **options):
        reader = csv.reader(open('resources/kakao_to_190313.csv'), delimiter='\t')
        for line in reader:
            print(line)
            _process(line)
