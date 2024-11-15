import uuid

from django.db import models

# Create your models here.
class Transaction(models.Model):
    id = models.AutoField(primary_key=True)
    identifier = models.UUIDField(max_length=15, unique=True, default=uuid.uuid4, editable=False)
    customer_id = models.IntegerField()
    input_amount = models.DecimalField(max_digits=15, decimal_places=2)
    input_currency = models.CharField(max_length=3)
    output_amount = models.DecimalField(max_digits=15, decimal_places=2)
    output_currency = models.CharField(max_length=3)
    transaction_date = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f"{self.customer_id} {self.input_amount} {self.input_currency}"
