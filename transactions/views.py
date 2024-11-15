import requests
from decimal import Decimal, InvalidOperation
from django.conf import settings
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Transaction
from .serializers import TransactionSerializer


def get_exchange_rate_url(base_url, api_key, input_currency, output_currency):
    return f"{base_url}/{api_key}/pair/{input_currency}/{output_currency}"


class TransactionCreateView(generics.CreateAPIView):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        input_currency = request.data.get('input_currency')
        output_currency = request.data.get('output_currency')
        input_amount = request.data.get('input_amount')

        # Validate required fields
        if not input_currency or not output_currency or not input_amount:
            return Response({"error": "Missing required fields: input_currency, output_currency, input_amount"},
                            status=status.HTTP_400_BAD_REQUEST)

        # Convert input amount to Decimal for precision
        try:
            input_amount = Decimal(input_amount)
        except InvalidOperation:
            return Response({"error": "Invalid input amount. Please provide a valid number."},
                             status=status.HTTP_400_BAD_REQUEST)

        # Fetch exchange rate
        url = get_exchange_rate_url(settings.EXCHANGE_RATE_API_URL, settings.EXCHANGE_RATE_API_KEY, input_currency, output_currency)
        response = requests.get(url, verify=False)

        if response.status_code != 200:
            return Response(
                {"error": f"Failed to fetch exchange rate: {response.text}"},
                status=status.HTTP_502_BAD_GATEWAY
            )

        # Parse exchange rate data
        try:
            exchange_rate_data = response.json()
            exchange_rate = exchange_rate_data.get('conversion_rate')
        except ValueError:
            return Response({"error": "Invalid response from exchange rate API"},
                            status=status.HTTP_502_BAD_GATEWAY)

        # Check if exchange rate is available
        if exchange_rate is None:
            return Response({"error": "Exchange rate not available"}, status=status.HTTP_400_BAD_REQUEST)

        # Calculate the output amount
        output_amount = input_amount * Decimal(exchange_rate)

        # Round output_amount to 2 decimal places
        output_amount = output_amount.quantize(Decimal('0.01'))

        # Check for total digit length (max 15 digits in total)
        if len(str(output_amount).replace('.', '')) > 15:
            return Response({"error": "Output amount exceeds the allowed precision limit of 15 digits."},
                             status=status.HTTP_400_BAD_REQUEST)

        request.data['output_amount'] = str(output_amount)  # Ensure it's a string for API processing

        return super().create(request, *args, **kwargs)


class TransactionListView(generics.ListAPIView):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]


class TransactionDetailView(generics.RetrieveAPIView):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    lookup_field = 'id'
    permission_classes = [IsAuthenticated]


class AvailableCurrenciesListView(generics.ListAPIView):
    def get(self, request, *args, **kwargs):
        url = f"{settings.EXCHANGE_RATE_API_URL}/{settings.EXCHANGE_RATE_API_KEY}/latest/USD"
        response = requests.get(url, verify=False)
 
        if response.status_code != 200:
            return Response(
                {"error": f"Failed to fetch currencies: {response.text}"},
                status=status.HTTP_502_BAD_GATEWAY
            )

        try:
            currencies_data = response.json()
        except ValueError:
            return Response(
                {"error": "Invalid response from exchange rate API"},
                status=status.HTTP_502_BAD_GATEWAY
            )

        return Response(currencies_data, status=status.HTTP_200_OK)