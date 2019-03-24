from django.db.models import Q
from django.db import models
# from django.db.models import CharField, Model
# from autoslug import AutoSlugField
# from category.models import Category as BaseCategory
# import uuid
# from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from datetime import timedelta
from django.urls import reverse


# class CategoryManager(models.Manager):
#     def get_queryset(self):
#         return super().get_queryset().exclude(title='Income:Available this month')

class MasterCategory(models.Model):

    title = models.CharField(
        max_length=200,
        help_text="Short descriptive name for this category.",
    )

    def __str__(self):
        return self.title


class Category(models.Model):
    """
    Category model to be used for categorization of content. Categories are
    high level constructs to be used for grouping and organizing content,
    thus creating a site"s table of contents.
    """
    full_title = models.CharField(
        max_length=400)
    title = models.CharField(
        max_length=200,
        help_text="Short descriptive name for this category.",
    )
    is_builtin = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
    # subtitle = models.CharField(
    #     max_length=200,
    #     blank=True,
    #     null=True,
    #     default="",
    #     help_text="Some titles may be the same and cause confusion in admin "
    #               "UI. A subtitle makes a distinction.",
    # )
    # slug = models.SlugField(
    #     max_length=255,
    #     db_index=True,
    #     unique=True,
    #     help_text="Short descriptive unique name for use in urls.",
    # )
    parent = models.ForeignKey(
        MasterCategory, on_delete=models.CASCADE
    )
    # sites = models.ManyToManyField(
    #     "sites.Site",
    #     blank=True,
    #     help_text="Limits category scope to selected sites.",
    # )

    def __str__(self):
        return f'{self.parent.title}:{self.title}'

    class Meta:
        ordering = ("full_title",)
        verbose_name = "category"
        verbose_name_plural = "categories"

    # def save(self, *args, **kwargs):
    #     # Raise on circular reference
    #     parent = self.parent
    #     while parent is not None:
    #         if parent == self:
    #             raise RuntimeError("Circular references not allowed")
    #         parent = parent.parent

    #     super(Category, self).save(*args, **kwargs)

    # @property
    # def children(self):
    #     return self.category_set.all().order_by("title")

    # @property
    # def tags(self):
    #     return Tag.objects.filter(categories__in=[self]).order_by("title")

    # def get_absolute_url(self):
    #     return reverse("category_object_list", kwargs={"pk": self.pk})

    @property
    def short_title(self):
        return self.title.split(':')[-1]

    # @property
    # def is_builtin(self):
    #     return self.title.startswith('Income:')

    # @property
    # def is_master(self):
    #     return ':' not in self.title

    # class Meta:
    #     # proxy = True
    #     db_table = 'moneybook_category'

    # trable_objects = CategoryManager()

    class Meta:
        ordering = ['order', 'title']


def after_1month():
    return timezone.now() + relativedelta(months=1) - timedelta(days=1)


class BudgetBundle(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    modified_at = models.DateTimeField(auto_now_add=True, editable=False)

    date_from = models.DateField(default=timezone.now)
    date_to = models.DateField(default=after_1month)

    name = models.TextField()

    def __str__(self):
        return f'{self.date_from}-{self.date_to}'

    def get_transaction_queryset(self):
        return Transaction.objects.filter(
            expensed_at__range=(self.date_from, self.date_to)
        )

    # @property
    # def budgets(self):
    #     return [
    #         (c, Budget.objects.get_or_create(budget_bundle=self, category=c)[0])
    #         for c in Category.objects.all()
    #     ]

    # @property
    # def previous(self):
    #     return BudgetBundle.objects.filter(date_to=self.date_from).first()

    # Not budgeted in previous month:<br/>
    # overspent in previous month:<br/>
    # Income for this month:<br/>
    # budgeted in this month:<br/>
    # available to budget:
    @property
    def overspending(self):
        return sum(
            b.balance
            for b in self.budgets.filter(overspending_in_budget=False).all())

    @property
    def previous_bundle(self):
        return BudgetBundle.objects.filter(
            date_to=self.date_from - timedelta(days=1)
        ).first()

    @property
    def next_bundle(self):
        return BudgetBundle.objects.filter(date_from=self.date_to).first()

    @property
    def available_to_budget(self):
        # return sum([
        #     t.inflow - t.outflow
        #     for t in self.get_transaction_queryset().all()
        # ])
        # return sum([
        #     t.inflow - t.outflow
        #     for t in self.get_transaction_queryset().filter(
        #         category=Category.objects.filter(is_builtin=True).get()
        #     ).all()
        # ])
        pb = self.previous_bundle
        if pb and pb.overspending:
            before = pb.overspending
        else:
            before = 0
        return (
            before + self.income - self.budgeted
        )

    @property
    def budgeted(self):
        return sum([
            b.budgeted
            for b in self.budgets.all()
            if b.category.is_builtin is False
        ])

    @property
    def balance(self):
        return self.budgeted - self.spent

    @property
    def income(self):
        return sum([
            t.inflow
            for t in self.get_transaction_queryset().all()
            if t.category and t.category.is_builtin is True
        ])

    @property
    def spent(self):
        return sum([
            t.outflow
            for t in self.get_transaction_queryset().all()
        ])

    @classmethod
    def create_each_categories(cls, date_from=None, date_to=None, iteration=1):
        if date_from is None and date_to is None:
            date_from = timezone.now()
            date_to = timezone.now() + relativedelta(months=1)
        elif date_from is None:
            date_from = date_to - relativedelta(months=1)
        elif date_to is None:
            date_to = date_from + relativedelta(months=1)

        bb, _ = BudgetBundle.objects.get_or_create(name='%s-%s' % (
            date_from.strftime('%Y-%m-%d'),
            date_to.strftime('%Y-%m-%d')), date_to=date_to, date_from=date_from)
        for category in Category.objects.all():
            Budget(
                category=category,
                budget_bundle=bb
            ).save()

        if iteration > 1:
            cls.create_each_categories(date_to=date_from, iteration=iteration-1)


class Budget(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    modified_at = models.DateTimeField(auto_now_add=True, editable=False)

    overspending_in_budget = models.BooleanField(default=False)
    budget_bundle = models.ForeignKey(BudgetBundle, related_name='budgets', on_delete=models.CASCADE)
    budgeted = models.IntegerField(default=0)
    category = models.ForeignKey(
        Category,
        related_name='budgets',
        on_delete=models.CASCADE)

    def get_transaction_queryset(self):
        return self.category.transactions.filter(
                expensed_at__range=(self.budget_bundle.date_from, self.budget_bundle.date_to))

    @property
    def parent_budgeted(self):
        categories = Category.objects.filter(parent=self.category.parent).all()
        return sum(
            Budget.objects.filter(budget_bundle=self.budget_bundle, category=c).get().budgeted
            for c in categories
        )

    @property
    def parent_outflows(self):
        return sum(
            t.inflow - t.outflow
            for t in Transaction.objects.filter(
                category__parent=self.category.parent,
                expensed_at__range=(self.budget_bundle.date_from, self.budget_bundle.date_to)).all()
        )

    @property
    def parent_balance(self):
        categories = Category.objects.filter(parent=self.category.parent).all()
        return sum(
            Budget.objects.filter(budget_bundle=self.budget_bundle, category=c).get().balance
            for c in categories
        )

    @property
    def outflows(self):
        return sum(
            t.inflow - t.outflow
            for t in self.get_transaction_queryset().all()
        )

    @property
    def balance(self):
        result = 0
        # print(self.budget_bundle, 'next', self.budget_bundle.previous_bundle)
        p_budget = Budget.objects.filter(
            budget_bundle=self.budget_bundle.previous_bundle,
            category=self.category,
        ).first()
        if p_budget:
            p_balance = p_budget.balance
            if p_balance < 0 and not p_budget.overspending_in_budget:
                result = 0
            else:
                result = p_balance

        # if result < 0 and not self.overspending_in_budget:
        #     result = 0

        return result + self.budgeted + self.outflows


class Account(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    modified_at = models.DateTimeField(auto_now_add=True, editable=False)

    first_balance = models.IntegerField(default=0)
    title = models.CharField(max_length=1000)
    description = models.TextField()

    def __str__(self):
        return self.title

    @property
    def balance(self):
        return (
            self.first_balance -
            sum(t.outflow for t in self.transactions.all()) +
            sum(t.inflow for t in self.transactions.all())
        )


# class HookTest(models.Model):
#     dummy = models.TextField()
#     def save(self, *args, **kwargs):
#         print('called'*1000)
#         return super().save(*args, **kwargs)


class Transfer(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    modified_at = models.DateTimeField(auto_now_add=True, editable=False)

    account_from = models.ForeignKey(
        Account,
        related_name='transfer_from',
        on_delete=models.CASCADE)
    account_to = models.ForeignKey(
        Account,
        related_name='transfer_to',
        on_delete=models.CASCADE)

    transfered_at = models.DateField()
    amount = models.IntegerField(default=0)

    def save(self, *args, **kwargs):
        ret = super().save(*args, **kwargs)

        Transaction.objects.filter(transfer=self).delete()
        t_from = Transaction.objects.filter(
            transfer=self,
            account=self.account_from,
        ).first()
        if t_from is None:
            t_from = Transaction(transfer=self, account=self.account_from)
        t_from.payee = f'Transfer: {self.account_to.title}'
        t_from.category = None
        t_from.outflow = self.amount
        t_from.expensed_at = self.transfered_at
        t_from.save()

        t_to = Transaction.objects.filter(
            transfer=self,
            account=self.account_to,
        ).first()
        if t_to is None:
            t_to = Transaction(transfer=self, account=self.account_to)
        t_to.payee = f'Transfer: {self.account_from.title}'
        t_to.category = None
        t_to.inflow = self.amount
        t_to.expensed_at = self.transfered_at
        t_to.save()

        return ret


# Create your models here.
class Transaction(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    modified_at = models.DateTimeField(auto_now_add=True, editable=False)

    inflow = models.IntegerField(default=0)
    outflow = models.IntegerField(default=0)
    account = models.ForeignKey(
        Account,
        related_name='transactions',
        on_delete=models.CASCADE)
    transfer = models.ForeignKey(
        Transfer,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )

    cleared = models.BooleanField(default=False)

    category = models.ForeignKey(
        Category,
        related_name='transactions',
        on_delete=models.CASCADE,
        null=True,
        blank=True)
    # tags = models.ManyToManyField('category.Tag', blank=True)

    expensed_at = models.DateField()
    payee = models.CharField(max_length=1000)
    memo = models.CharField(max_length=1000, null=True, blank=True)

    def __str__(self):
        return f'Transaction({self.pk})-{self.payee}-{self.inflow}-{self.outflow}'

    def clone(self):
        self.id = None
        self.created_at = timezone.now()
        self.modified_at = timezone.now()
        self.expensed_at = timezone.now()
        return self.save()

    @property
    def balance(self):
        # for t in Transaction.objects.filter(account=self.account, expensed_at__lte=self.expensed_at):
        #     print(t)
        return sum([
            t.inflow - t.outflow
            for t in Transaction.objects.filter(
                Q(account=self.account) &
                (
                    Q(expensed_at__lt=self.expensed_at) | (Q(expensed_at=self.expensed_at) & Q(created_at__lte=self.created_at))
                ),
            )
        ])
