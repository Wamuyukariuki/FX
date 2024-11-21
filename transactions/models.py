import uuid
from django.contrib.auth.models import User
from django.db import models
from decimal import Decimal

class Transaction(models.Model):
    identifier = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="transactions", db_index=True)
    input_amount = models.DecimalField(max_digits=15, decimal_places=2)
    input_currency = models.CharField(max_length=3)
    output_amount = models.DecimalField(max_digits=15, decimal_places=2)
    output_currency = models.CharField(max_length=3)
    transaction_date = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Ensure input_amount and output_amount respect the user's decimal precision
        if self.input_amount and self.output_amount:
            decimal_precision = self.customer.preferences.decimal_precision
            self.input_amount = self.input_amount.quantize(Decimal(10) ** -decimal_precision)
            self.output_amount = self.output_amount.quantize(Decimal(10) ** -decimal_precision)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Transaction {self.identifier} by {self.customer.username}"


class UserPreference(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="preferences")
    preferred_currencies = models.JSONField(default=list)  # Store subscribed currencies as a list
    decimal_precision = models.PositiveSmallIntegerField(default=2)  # Store the precision (e.g., 2 dp or 3 dp)

    def __str__(self):
        return f"{self.user.username}'s Preferences"
