from rest_framework import serializers
from .models import Transaction

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = '__all__'

    def validate(self, data):
        if data['input_amount'] <= 0:
            raise serializers.ValidationError("Input amount must be greater than zero.")
        return data