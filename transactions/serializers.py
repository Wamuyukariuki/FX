from rest_framework import serializers
from decimal import Decimal, InvalidOperation
from .models import Transaction


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['id', 'identifier', 'customer_id', 'input_amount', 'input_currency', 'output_amount',
                  'output_currency', 'transaction_date']

    # Custom field-level validation for 'input_amount'
    def validate_input_amount(self, value):
        try:
            # Ensure it's a valid decimal value
            value = Decimal(value)
            if value <= 0:
                raise serializers.ValidationError("Amount must be greater than zero.")
            return value
        except InvalidOperation:
            raise serializers.ValidationError("Invalid input amount.")

    # Custom field-level validation for required fields (input_currency, output_currency)
    def validate(self, attrs):
        input_currency = attrs.get('input_currency')
        output_currency = attrs.get('output_currency')

        # Ensure both currencies are provided
        if not input_currency or not output_currency:
            raise serializers.ValidationError("Both input_currency and output_currency are required.")

        # Additional validation for input_currency and output_currency can be added here
        return attrs

    # Optional: Add logic for output_amount if you need it to be validated directly in the serializer
    def validate_output_amount(self, value):
        if len(str(value).replace('.', '')) > 15:
            raise serializers.ValidationError("Output amount exceeds precision limit.")
        return value
