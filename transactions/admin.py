from django.contrib import admin
from .models import Transaction, UserPreference

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('identifier', 'customer', 'input_currency', 'output_currency', 'transaction_date')
    search_fields = ('customer__username', 'identifier')

@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'decimal_precision')
