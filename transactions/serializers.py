from decimal import Decimal, InvalidOperation

from django.contrib.auth.models import User  # Import User model
from rest_framework import serializers

from .models import Transaction, UserPreference


class TransactionSerializer(serializers.ModelSerializer):
    customer = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())  # Reference User model

    class Meta:
        model = Transaction
        fields = ['id', 'identifier', 'customer', 'input_amount', 'input_currency', 'output_amount',
                  'output_currency', 'transaction_date']

    # Custom validation for 'input_amount'
    def validate_input_amount(self, value):
        try:
            value = Decimal(value)
            if value <= 0:
                raise serializers.ValidationError("Amount must be greater than zero.")
            return value
        except InvalidOperation:
            raise serializers.ValidationError("Invalid input amount.")

    # Custom validation for 'output_amount'
    def validate_output_amount(self, value):
        try:
            value = Decimal(value)
            user = self.context['request'].user
            decimal_precision = user.preferences.decimal_precision  # Use user's decimal precision preference
            value = value.quantize(Decimal(10) ** -decimal_precision)
            return value
        except InvalidOperation:
            raise serializers.ValidationError("Invalid output amount.")

    # Custom validation for required fields (input_currency, output_currency)
    def validate(self, attrs):
        input_currency = attrs.get('input_currency')
        output_currency = attrs.get('output_currency')

        if not input_currency or not output_currency:
            raise serializers.ValidationError("Both input_currency and output_currency are required.")

        # You can add more checks for valid currency codes here
        return attrs


class UserPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPreference
        fields = ['preferred_currencies', 'decimal_precision']


class UserSerializer(serializers.ModelSerializer):
    preferences = UserPreferenceSerializer()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'preferences']
