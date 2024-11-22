import uuid
from django.contrib.auth.models import User
from django.db import models
from decimal import Decimal, InvalidOperation


class UserPreference(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="preferences")
    preferred_currencies = models.JSONField(default=list)  # Store subscribed currencies as a list
    decimal_precision = models.PositiveSmallIntegerField(default=2)  # Store the precision (e.g., 2 dp or 3 dp)

    def save(self, *args, **kwargs):
        # Validate decimal_precision range
        if not (0 <= self.decimal_precision <= 10):
            raise ValueError("Decimal precision must be between 0 and 10.")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username}'s Preferences"


class Transaction(models.Model):
    identifier = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="transactions", db_index=True)
    input_amount = models.DecimalField(max_digits=15, decimal_places=3)
    input_currency = models.CharField(max_length=3)
    output_amount = models.DecimalField(max_digits=15, decimal_places=5)
    output_currency = models.CharField(max_length=3)
    transaction_date = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        try:
            # Ensure input_amount and output_amount respect the user's decimal precision
            user_preferences = getattr(self.customer, "preferences", None)
            decimal_precision = getattr(user_preferences, "decimal_precision", 2) if user_preferences else 2
            decimal_precision = max(0, min(decimal_precision, 10))  # Clamp to valid range

            # Apply rounding
            quantize_value = Decimal(10) ** -decimal_precision
            self.input_amount = self.input_amount.quantize(quantize_value)
            self.output_amount = self.output_amount.quantize(quantize_value)
        except (AttributeError, InvalidOperation) as e:
            raise ValueError(f"Error in processing transaction: {e}")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Transaction {self.identifier} by {self.customer.username}"
