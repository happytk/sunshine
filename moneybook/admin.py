from django.template.response import TemplateResponse
# from rangefilter.filter import DateRangeFilter
from django.urls import reverse
from django.contrib import admin
from django.conf.urls import url
from django.urls import reverse
from django.contrib.admin.views.main import ChangeList
from django.db.models import Count, Sum
from django.contrib.humanize.templatetags.humanize import intcomma, naturalday
from django.utils.html import format_html
# from django_admin_multiple_choice_list_filter.list_filters import MultipleChoiceListFilter
# from admin_auto_filters.filters import AutocompleteFilter

from .models import Transaction, Account, Budget, Transfer, BudgetBundle, Category, BudgetBundle, MasterCategory


admin.site.register(MasterCategory)


# class CategoryFilter(AutocompleteFilter):
#     title = 'Category'  # display title
#     field_name = 'category'  # name of the foreign key field


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    search_fields = ['title', ]
    list_display = ('full_title', 'parent', 'title', )
    ordering = ('full_title', )

# Register your models here.
@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('title', 'description', 'humanize_balance', 'last_transaction', 'transaction_count', 'created_at')
    ordering = ('title',)

    def transaction_count(self, obj):
        transactions_url = reverse('admin:moneybook_transaction_changelist')
        transactions_url += '?account__id__exact=' + str(obj.id)
        return format_html(f'<a href="{transactions_url}">{obj.transactions.count()}</a>')
    transaction_count.short_description = 'transactions'

    def last_transaction(self, obj):
        last = obj.transactions.order_by('-expensed_at').first()
        if last:
            return last.expensed_at

    def humanize_balance(self, obj):
        ret = intcomma(obj.balance)
        if obj.balance < 0:
            return format_html(f"<span style='color:red;'>{ret}")
        return ret

    humanize_balance.short_description = 'balance'


class TransactionList(ChangeList):

    def get_results(self, *args, **kwargs):
        super().get_results(*args, **kwargs)
        # q = self.result_list.aggregate(total_amount=Sum('amount'))
        d = self.result_list.aggregate(total_outflow=Sum('outflow'), total_inflow=Sum('inflow'))
        self.total_outflow = d.get('total_outflow', 0) or 0
        self.total_inflow = d.get('total_inflow', 0) or 0
        self.total_balance = self.total_inflow - self.total_outflow


# class AccountListFilter(MultipleChoiceListFilter):
#     title = 'Account'
#     parameter_name = 'account__in'

#     def lookups(self, request, model_admin):
#         return [
#             (acc.id, acc.title)
#             for acc in Account.objects.all()
#         ]


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    date_hierarchy = 'expensed_at'
    ordering = ('-expensed_at', '-created_at')
    # list_filter = (('expensed_at', DateRangeFilter), AccountListFilter, 'category', 'payee')
    # list_filter = ('expensed_at', AccountListFilter, 'category', 'payee')
    list_filter = ('expensed_at', 'account', 'category', 'payee')
    list_display = ('account_link', 'expensed_at', 'category', 'payee', 'memo', 'humanize_outflow', 'humanize_inflow', 'humanize_balance', 'cleared')
    list_display_links = ('expensed_at', )
    list_editable = (
        # 'payee',
        # 'memo',
        # 'outflow',
        # 'inflow',
        # 'category',
    )
    actions = ['clone_as_new', 'change_the_category', 'move_to_other_account', 'mark_as_cleared', 'mark_as_uncleared']
    search_fields = ('payee', 'memo', 'inflow', 'outflow', )
    readonly_fields = ('balance', )
    fields = (
        'account',
        'expensed_at',
        'payee',
        'category',
        'memo',
        ('inflow', 'outflow',),
    )

    def clone_as_new(self, request, queryset):
        # queryset.update(status='p')
        count = 0
        for obj in queryset:
            obj.clone()
            count += 1
        self.message_user(request, "%d items are successfully cloned as new." % count)

    clone_as_new.short_description = "Clone selected transactions as now"

    def mark_as_cleared(self, request, queryset):
        queryset.update(cleared=True)
        self.message_user(request, "%d items are successfully cleared." % queryset.count())

    def mark_as_uncleared(self, request, queryset):
        queryset.update(cleared=False)
        self.message_user(request, "%d items are successfully uncleared." % queryset.count())

    def change_the_category(self, request, queryset):
        if request.POST.get('_confirmation'):
            category = Category.objects.get(pk=request.POST.get('category'))
            count = 0
            for pk in request.POST.getlist('_selected_action'):
                t = Transaction.objects.get(pk=pk)
                t.category = category
                t.save()
                count += 1
            self.message_user(request, "%d items are successfully changed the category as %s." % (count, category.title))
            return None
        else:
            # request.current_app = modeladmin.admin_site.name
            categories = Category.objects.all()
            return TemplateResponse(
                request,
                "admin/moneybook/change_category_action_confirmation.html",
                {
                    'queryset': queryset,
                    'categories': categories,
                }
            )

    def move_to_other_account(self, request, queryset):
        if request.POST.get('_confirmation'):
            account = Account.objects.get(pk=request.POST.get('account'))
            count = 0
            for pk in request.POST.getlist('_selected_action'):
                t = Transaction.objects.get(pk=pk)
                t.account = account
                t.save()
                count += 1
            self.message_user(request, "%d items are moved to '%s' successfully." % (count, account.title))
            return None
        else:
            # request.current_app = modeladmin.admin_site.name
            accounts = Account.objects.all()
            return TemplateResponse(
                request,
                "admin/moneybook/change_account_action_confirmation.html",
                {
                    'queryset': queryset,
                    'accounts': accounts,
                }
            )

    def account_link(self, obj):
        link_url = reverse('admin:moneybook_account_changelist')
        return format_html(f'<a href="{link_url}">{obj.account.title}</a>')
    account_link.short_description = 'Account'

    # def humanize_expensed_at(self, obj):
    #     d = naturalday(obj.expensed_at).capitalize()
    #     if d == 'Today':
    #         return format_html(f'<b style="color:red;">{d}</b>')
    #     return d
    # humanize_expensed_at.short_description = 'Date'

    def humanize_outflow(self, obj):
        return intcomma(obj.outflow or '')
    humanize_outflow.short_description = "Outflow"

    def humanize_inflow(self, obj):
        return intcomma(obj.inflow or '')
    humanize_inflow.short_description = "Inflow"

    def humanize_balance(self, obj):
        return intcomma(obj.balance or '')
    humanize_balance.short_description = "Balance"

    def get_changelist(self, request):
        return TransactionList

    class Meta:
        model = Transaction

    class Media:
        pass

    # def get_urls(self):
    #     urls = super().get_urls()
    #     custom_urls = [
    #         url(
    #             r'^(?P<transaction_id>.+)/process_category/$',
    #             self.admin_site.admin_view(self.process_category),
    #             name='account-category',
    #         ),
    #         url(
    #             r'^(?P<transaction_id>.+)/process_account/$',
    #             self.admin_site.admin_view(self.process_account),
    #             name='account-account',
    #         ),
    #     ]
    #     return custom_urls + urls

    # def transaction_actions(self, obj):
    #     return format_html(
    #         '<a class="button" href="{}">category</a>&nbsp;'
    #         '<a class="button" href="{}">account</a>',
    #         reverse('admin:account-category', args=[obj.pk]),
    #         reverse('admin:account-account', args=[obj.pk]),
    #     )
    # transaction_actions.short_description = 'Transaction Actions'
    # transaction_actions.allow_tags = True

    # def process_category(self, request, transaction_id, *args, **kwargs):
    #     return self.process_action(
    #         request=request,
    #         transaction_id=transaction_id,
    #         action_form=DepositForm,
    #         action_title='Deposit',
    #     )

    # def process_account(self, request, transaction_id, *args, **kwargs):
    #     return self.process_action(
    #         request=request,
    #         transaction_id=transaction_id,
    #         action_form=WithdrawForm,
    #         action_title='Withdraw',
    #     )

    # def process_action(
    #     self,
    #     request,
    #     transaction_id,
    #     action_form,
    #     action_title
    # ):
    #     transaction = self.get_object(request, transaction_id)

    #     if request.method != 'POST':
    #         form = action_form()

    #     else:
    #         form = action_form(request.POST)
    #         if form.is_valid():
    #             try:
    #                 form.save(transaction, request.user)
    #             except errors.Error as e:
    #                 # If save() raised, the form will a have a non
    #                 # field error containing an informative message.
    #                 pass
    #             else:
    #                 self.message_user(request, 'Success')
    #                 url = reverse(
    #                     'admin:moneybook_transaction_change',
    #                    args=[transaction.pk],
    #                     current_app=self.admin_site.name,
    #                 )
    #                 return HttpResponseRedirect(url)

    #     context = self.admin_site.each_context(request)
    #     context['opts'] = self.model._meta
    #     context['form'] = form
    #     context['transaction'] = transaction
    #     context['title'] = action_title

    #     return TemplateResponse(
    #         request,
    #         'admin/transaction/transaction_action.html',
    #         context,
    #     )


@admin.register(BudgetBundle)
class BudgetBundleAdmin(admin.ModelAdmin):
    pass


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ('budget_bundle', 'category', 'transaction_count', 'budgeted', 'humanize_outflows', 'humanize_balance',)
    # list_filter = (('date_from', DateRangeFilter), 'category', 'date_to', )
    list_filter = ('category', 'budget_bundle', )
    search_fields = ('category__title',)
    actions = ('set_budget_as_spent', )
    ordering = ('budget_bundle', 'category', )
    # readonly_fields = ('budget_bundle', 'category', )
    list_editable = ('budgeted', )

    def transaction_count(self, obj):
        return obj.get_transaction_queryset().count()
    transaction_count.short_description = 'transactions'

    def humanize_outflows(self, obj):
        return intcomma(obj.outflows or '0')
    humanize_outflows.short_description = 'outflows'

    def humanize_balance(self, obj):
        return intcomma(obj.balance or '0')
    humanize_balance.short_description = 'balance'

    def changelist_view(self, request, extra_context=None):
        categories = Category.objects.filter(is_builtin=False).order_by('full_title').all()
        bundles = BudgetBundle.objects.order_by('date_from').all()[:4]
        table = [
            Budget.objects.get_or_create(
                budget_bundle=bundle,
                category=category)[0]
            for category in categories
            for bundle in bundles
        ]
        if len(bundles):
            table = [table[i:i+len(bundles)] for i in range(0, len(table), len(bundles))]
        else:
            table = []

        for (c, r) in zip(categories, table):
            r.insert(0, c)

        d = {
            'categories': categories,
            'bundles': bundles,
            'table': table,
        }
        if extra_context:
            extra_context.update(d)
        else:
            extra_context = d
        return super().changelist_view(request, extra_context)

    def set_budget_as_spent(self, request, queryset):
        # queryset.update(status='p')
        count = 0
        for obj in queryset:
            obj.budgeted = -obj.outflows
            obj.save()
            count += 1
        self.message_user(request, "%d items are successfully cloned as new." % count)

    class Media:
        pass


@admin.register(Transfer)
class TransferAdmin(admin.ModelAdmin):
    list_display = ('transfered_at', 'account_from', 'account_to', 'amount',)
