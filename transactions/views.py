import requests
from decimal import Decimal, InvalidOperation
from django.conf import settings
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.core.cache import cache
from .models import Transaction
from .serializers import TransactionSerializer
import logging

logger = logging.getLogger(__name__)

# Utility to construct API URL
def get_exchange_rate_url(base_url, api_key, input_currency, output_currency):
    return f"{base_url}/{api_key}/pair/{input_currency.upper()}/{output_currency.upper()}"

# Utility to fetch data from external API
def fetch_data_from_api(url):
    try:
        response = requests.get(url, verify=False, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"API request error: {str(e)}")
        raise
    except ValueError:
        logger.error("Invalid JSON response from API")
        raise

# Transaction creation with Redis cache for exchange rates
class TransactionCreateView(generics.CreateAPIView):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        input_currency = request.data.get('input_currency')
        output_currency = request.data.get('output_currency')
        input_amount = request.data.get('input_amount')

        if not all([input_currency, output_currency, input_amount]):
            return Response({"error": "Missing required fields"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            input_amount = Decimal(input_amount)
        except InvalidOperation:
            return Response({"error": "Invalid input amount"}, status=status.HTTP_400_BAD_REQUEST)

        # Generate a unique cache key for the currency pair
        cache_key = f"exchange_rate_{input_currency.upper()}_{output_currency.upper()}"
        exchange_rate = cache.get(cache_key)

        if exchange_rate is None:
            try:
                url = get_exchange_rate_url(
                    settings.EXCHANGE_RATE_API_URL,
                    settings.EXCHANGE_RATE_API_KEY,
                    input_currency,
                    output_currency
                )
                exchange_rate = fetch_data_from_api(url).get('conversion_rate')
                if exchange_rate is None:
                    raise ValueError("Exchange rate missing in API response")
                # Cache the exchange rate for 1 hour
                cache.set(cache_key, exchange_rate, timeout=3600)
            except Exception as e:
                logger.error(f"Exchange rate API error: {str(e)}")
                return Response({"error": "Failed to fetch exchange rate"}, status=status.HTTP_502_BAD_GATEWAY)

        output_amount = (input_amount * Decimal(exchange_rate)).quantize(Decimal('0.01'))
        if len(str(output_amount).replace('.', '')) > 15:
            return Response({"error": "Output amount exceeds precision limit"}, status=status.HTTP_400_BAD_REQUEST)

        request.data['output_amount'] = str(output_amount)
        return super().create(request, *args, **kwargs)

# List transactions
class TransactionListView(generics.ListAPIView):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

# Retrieve a single transaction
class TransactionDetailView(generics.RetrieveAPIView):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    lookup_field = 'id'
    permission_classes = [IsAuthenticated]

# List available currencies with Redis cache
class AvailableCurrenciesListView(generics.ListAPIView):
    def get(self, request, *args, **kwargs):
        url = f"{settings.EXCHANGE_RATE_API_URL}/{settings.EXCHANGE_RATE_API_KEY}/latest/USD"

        # Try to fetch data from cache first
        cached_data = cache.get('available_currencies')
        if cached_data:
            return Response(cached_data, status=status.HTTP_200_OK)

        # Fetch data from API if cache is empty
        try:
            data = fetch_data_from_api(url)
            # Store the fetched data in Redis cache for 1 hour
            cache.set('available_currencies', data, timeout=3600)
        except Exception:
            return Response(
                {"error": "Failed to fetch currencies from external API"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(data, status=status.HTTP_200_OK)
