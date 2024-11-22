from django.contrib.auth.models import User  # Import User model
from rest_framework import serializers

from .models import Transaction
from .models import UserPreference


class TransactionSerializer(serializers.ModelSerializer):
    customer = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())  # Reference User model

    class Meta:
        model = Transaction
        fields = ['id', 'identifier', 'customer', 'input_amount', 'input_currency', 'output_amount',
                  'output_currency', 'transaction_date']


class UserPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPreference
        fields = ['preferred_currencies', 'decimal_precision']


class UserSerializer(serializers.ModelSerializer):
    preferences = UserPreferenceSerializer()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'preferences']
