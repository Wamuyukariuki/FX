import logging
import time
from decimal import Decimal, InvalidOperation
import requests
from django.conf import settings
from django.core.cache import cache
from django.http import Http404
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Transaction, UserPreference
from .serializers import TransactionSerializer, UserPreferenceSerializer

logger = logging.getLogger(__name__)

# Utility function to generate API URLs
def get_exchange_rate_url(base_url, api_key, input_currency, output_currency):
    return f"{base_url}/{api_key}/pair/{input_currency.upper()}/{output_currency.upper()}"

# Utility function to fetch data from an external API
def fetch_data_from_api(url):
    try:
        start_time = time.time()
        response = requests.get(url, verify=False, timeout=10)
        response.raise_for_status()
        logger.info(f"API response time: {time.time() - start_time:.2f} seconds")
        return response.json()
    except requests.RequestException as e:
        logger.error(f"API request error: {e}")
        raise
    except ValueError:
        logger.error("Invalid JSON response from API")
        raise

# Transaction creation with user-defined decimal precision
class TransactionCreateView(generics.CreateAPIView):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        user = request.user

        # Fetch user preferences with a fallback
        user_preferences = getattr(user, 'preferences', None)
        decimal_precision = getattr(user_preferences, 'decimal_precision', 2)

        # Safeguard: Ensure precision is within a logical range
        decimal_precision = max(0, min(decimal_precision, 10))
        subscribed_currencies = getattr(user_preferences, 'preferred_currencies', [])

        input_currency = request.data.get('input_currency')
        output_currency = request.data.get('output_currency')
        input_amount = request.data.get('input_amount')

        # Validate required fields
        if not all([input_currency, output_currency, input_amount]):
            return Response(
                {
                    "data": {},
                    "errors": {"message": "Missing required fields"},
                    "status": status.HTTP_400_BAD_REQUEST,
                    "message": "Provide input_currency, output_currency, and input_amount.",
                    "success": False,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Ensure output_currency is within subscribed currencies
        if output_currency not in subscribed_currencies:
            return Response(
                {
                    "data": {},
                    "errors": {"message": "Currency not in subscription list"},
                    "status": status.HTTP_400_BAD_REQUEST,
                    "message": "You can only convert to subscribed currencies.",
                    "success": False,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate input_amount as Decimal
        try:
            input_amount = Decimal(input_amount)
        except InvalidOperation:
            return Response(
                {
                    "data": {},
                    "errors": {"message": "Invalid input amount"},
                    "status": status.HTTP_400_BAD_REQUEST,
                    "message": "Input amount must be a valid number.",
                    "success": False,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Fetch or cache exchange rate
        cache_key = f"exchange_rate_{input_currency.upper()}_{output_currency.upper()}"
        exchange_rate = cache.get(cache_key)
        if not exchange_rate:
            try:
                url = get_exchange_rate_url(
                    settings.EXCHANGE_RATE_API_URL,
                    settings.EXCHANGE_RATE_API_KEY,
                    input_currency,
                    output_currency,
                )
                exchange_rate = fetch_data_from_api(url).get('conversion_rate')
                if exchange_rate is None:
                    raise ValueError("Exchange rate missing in API response")
                cache.set(cache_key, exchange_rate, timeout=3600)
            except Exception as e:
                logger.error(f"Error fetching exchange rate: {e}")
                return Response(
                    {
                        "data": {},
                        "errors": {"message": "Failed to fetch exchange rate"},
                        "status": status.HTTP_502_BAD_GATEWAY,
                        "message": "Error fetching exchange rate.",
                        "success": False,
                    },
                    status=status.HTTP_502_BAD_GATEWAY,
                )

        # Calculate output amount
        try:
            quantize_value = Decimal(f'1.{"0" * decimal_precision}')
            output_amount = (input_amount * Decimal(exchange_rate)).quantize(quantize_value)
        except Exception as e:
            logger.error(f"Calculation error: {e}")
            return Response(
                {
                    "data": {},
                    "errors": {"message": "Calculation error"},
                    "status": status.HTTP_400_BAD_REQUEST,
                    "message": "Error calculating output amount.",
                    "success": False,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Update request data
        request.data.update({
            'output_amount': str(output_amount),
            'customer_id': user.id,
        })

        return super().create(request, *args, **kwargs)

# List all transactions for the authenticated user
class TransactionListView(generics.ListAPIView):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Transaction.objects.filter(customer_id=self.request.user.id)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        if not queryset.exists():
            return Response(
                {
                    "data": [],
                    "errors": {"message": "No transactions found for this user."},
                    "status": status.HTTP_404_NOT_FOUND,
                    "message": "No transactions available.",
                    "success": False,
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {
                "data": self.get_serializer(queryset, many=True).data,
                "errors": {},
                "status": status.HTTP_200_OK,
                "message": "Transactions fetched successfully.",
                "success": True,
            }
        )

# Retrieve transaction details
class TransactionDetailView(generics.RetrieveAPIView):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    lookup_field = 'id'
    permission_classes = [IsAuthenticated]

    def handle_exception(self, exc):
        if isinstance(exc, Http404):
            return Response(
                {
                    "data": {},
                    "errors": {"message": "Transaction not found."},
                    "status": status.HTTP_404_NOT_FOUND,
                    "message": "Transaction does not exist.",
                    "success": False,
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        return super().handle_exception(exc)

# List available currencies
class AvailableCurrenciesListView(generics.ListAPIView):
    def get(self, request, *args, **kwargs):
        cache_key = 'available_currencies'
        url = f"{settings.EXCHANGE_RATE_API_URL}/{settings.EXCHANGE_RATE_API_KEY}/latest/USD"

        # Check cache
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info("Cache hit for available currencies.")
            return Response(
                {
                    "data": cached_data,
                    "errors": {},
                    "status": status.HTTP_200_OK,
                    "message": "Currencies fetched from cache.",
                    "success": True,
                }
            )

        # Fetch from API
        try:
            data = fetch_data_from_api(url)
            cache.set(cache_key, data, timeout=3600)
            return Response(
                {
                    "data": data,
                    "errors": {},
                    "status": status.HTTP_200_OK,
                    "message": "Currencies fetched successfully.",
                    "success": True,
                }
            )
        except Exception as e:
            logger.error(f"Failed to fetch currencies: {e}")
            return Response(
                {
                    "data": {},
                    "errors": {"message": "Failed to fetch currencies."},
                    "status": status.HTTP_502_BAD_GATEWAY,
                    "message": "Error fetching currencies.",
                    "success": False,
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

# Update user preferences
class UserPreferenceUpdateView(generics.UpdateAPIView):
    serializer_class = UserPreferenceSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        user_preferences, _ = UserPreference.objects.get_or_create(user=self.request.user)
        return user_preferences

    def update(self, request, *args, **kwargs):
        decimal_precision = request.data.get('decimal_precision', 2)
        if not (0 <= decimal_precision <= 10):
            return Response(
                {
                    "data": {},
                    "errors": {"message": "Invalid decimal precision."},
                    "status": status.HTTP_400_BAD_REQUEST,
                    "message": "Decimal precision must be between 0 and 10.",
                    "success": False,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user_preferences = self.get_object()
        user_preferences.decimal_precision = decimal_precision
        user_preferences.save()

        return super().update(request, *args, **kwargs)
