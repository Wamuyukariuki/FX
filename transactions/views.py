import logging
import time
from decimal import Decimal, InvalidOperation

import requests
from django.conf import settings
from django.core.cache import cache
from rest_framework import generics
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Transaction
from .models import UserPreference
from .serializers import TransactionSerializer, UserPreferenceSerializer

logger = logging.getLogger(__name__)

# Utility to construct API URL
def get_exchange_rate_url(base_url, api_key, input_currency, output_currency):
    return f"{base_url}/{api_key}/pair/{input_currency.upper()}/{output_currency.upper()}"

# Utility to fetch data from external API with time tracking
def fetch_data_from_api(url):
    try:
        start_time = time.time()  # Start timer
        response = requests.get(url, verify=False, timeout=10)
        response.raise_for_status()
        end_time = time.time()  # End timer
        logger.info(f"API response time: {end_time - start_time:.2f} seconds")
        return response.json()
    except requests.RequestException as e:
        logger.error(f"API request error: {str(e)}")
        raise
    except ValueError:
        logger.error("Invalid JSON response from API")
        raise


# TransactionCreateView with cache tracking and enhanced logging
class TransactionCreateView(generics.CreateAPIView):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        user = request.user

        # Fetch user preferences
        user_preferences = user.preferences
        decimal_precision = user_preferences.decimal_precision
        subscribed_currencies = user_preferences.preferred_currencies

        input_currency = request.data.get('input_currency')
        output_currency = request.data.get('output_currency')
        input_amount = request.data.get('input_amount')

        # Validate using the serializer
        serializer = self.get_serializer(data=request.data)

        # Check if output_currency is in subscribed currencies
        if output_currency not in subscribed_currencies:
            return Response({
                "data": {},
                "errors": {"message": "Currency not in subscription list"},
                "status": status.HTTP_400_BAD_REQUEST,
                "message": "You can only convert to subscribed currencies.",
                "success": False
            }, status=status.HTTP_400_BAD_REQUEST)

        # Validate required fields
        if not all([input_currency, output_currency, input_amount]):
            return Response({
                "data": {},
                "errors": {"message": "Missing required fields"},
                "status": status.HTTP_400_BAD_REQUEST,
                "message": "Please provide all required fields (input_currency, output_currency, input_amount).",
                "success": False
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            input_amount = Decimal(input_amount)
        except InvalidOperation:
            return Response({
                "data": {},
                "errors": {"message": "Invalid input amount"},
                "status": status.HTTP_400_BAD_REQUEST,
                "message": "The input amount is not a valid number.",
                "success": False
            }, status=status.HTTP_400_BAD_REQUEST)

        # Generate a unique cache key
        cache_key = f"exchange_rate_{input_currency.upper()}_{output_currency.upper()}"

        # Track cache retrieval
        cache_start_time = time.time()
        exchange_rate = cache.get(cache_key)
        cache_time_taken = time.time() - cache_start_time

        if exchange_rate:
            logger.info(f"Cache hit for {cache_key}. Time taken: {cache_time_taken:.4f} seconds.")
        else:
            logger.info(f"Cache miss for {cache_key}. Time taken: {cache_time_taken:.4f} seconds.")

            # Fetch exchange rate from API
            try:
                url = get_exchange_rate_url(
                    settings.EXCHANGE_RATE_API_URL,
                    settings.EXCHANGE_RATE_API_KEY,
                    input_currency,
                    output_currency
                )

                api_start_time = time.time()
                exchange_rate = fetch_data_from_api(url).get('conversion_rate')
                api_time_taken = time.time() - api_start_time
                logger.info(f"API request for {cache_key} took {api_time_taken:.4f} seconds.")

                if exchange_rate is None:
                    raise ValueError("Exchange rate missing in API response")

                # Cache the exchange rate
                cache.set(cache_key, exchange_rate, timeout=3600)
            except Exception as e:
                logger.error(f"Error fetching exchange rate: {str(e)}")
                return Response({
                    "data": {},
                    "errors": {"message": "Failed to fetch exchange rate"},
                    "status": status.HTTP_502_BAD_GATEWAY,
                    "message": "There was an issue fetching the exchange rate.",
                    "success": False
                }, status=status.HTTP_502_BAD_GATEWAY)

        # Calculate output amount
        output_amount = (input_amount * Decimal(exchange_rate)).quantize(Decimal('0.01'))
        if len(str(output_amount).replace('.', '')) > 15:
            return Response({
                "data": {},
                "errors": {"message": "Output amount exceeds precision limit"},
                "status": status.HTTP_400_BAD_REQUEST,
                "message": "The calculated output amount exceeds the allowed precision.",
                "success": False
            }, status=status.HTTP_400_BAD_REQUEST)

        request.data['output_amount'] = str(output_amount)
        request.data['customer_id'] = user.id

        return super().create(request, *args, **kwargs)

# List transactions
class TransactionListView(generics.ListAPIView):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Use the request object to filter the transactions by customer_id (user ID)
        return Transaction.objects.filter(customer_id=self.request.user.id)

    def list(self, request, *args, **kwargs):
        # Calling the base class's list method to get the transaction data
        response = super().list(request, *args, **kwargs)

        return Response({
            "data": response.data,
            "errors": {},
            "status": status.HTTP_200_OK,
            "message": "Transactions fetched successfully.",
            "success": True
        })


# Retrieve a single transaction
class TransactionDetailView(generics.RetrieveAPIView):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    lookup_field = 'id'
    permission_classes = [IsAuthenticated]

    def retrieve(self, request, *args, **kwargs):
        # Calling the base class's retrieve method to get the transaction data
        response = super().retrieve(request, *args, **kwargs)

        return Response({
            "data": response.data,
            "errors": {},
            "status": status.HTTP_200_OK,
            "message": "Transaction details fetched successfully.",
            "success": True
        })


class AvailableCurrenciesListView(generics.ListAPIView):
    def get(self, request, *args, **kwargs):
        cache_key = 'available_currencies'
        url = f"{settings.EXCHANGE_RATE_API_URL}/{settings.EXCHANGE_RATE_API_KEY}/latest/USD"

        # Check for cached currencies
        cache_start_time = time.time()
        cached_data = cache.get(cache_key)
        cache_end_time = time.time()

        if cached_data:
            logger.info(f"Cache hit for {cache_key}. Cache retrieval time: {cache_end_time - cache_start_time:.4f}s")
            return Response({
                "data": cached_data,
                "errors": {},
                "status": status.HTTP_200_OK,
                "message": "Available currencies fetched from cache.",
                "success": True
            }, status=status.HTTP_200_OK)

        # Cache miss: Fetch from API
        logger.info(f"Cache miss for {cache_key}. Fetching data from API.")
        try:
            api_start_time = time.time()
            data = fetch_data_from_api(url)
            api_end_time = time.time()

            # Cache the response for 1 hour
            cache.set(cache_key, data, timeout=3600)

            logger.info(f"API request took {api_end_time - api_start_time:.4f}s.")
            return Response({
                "data": data,
                "errors": {},
                "status": status.HTTP_200_OK,
                "message": "Available currencies fetched successfully.",
                "success": True
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Failed to fetch currencies from API: {str(e)}")
            return Response({
                "data": {},
                "errors": {"message": "Failed to fetch currencies from external API"},
                "status": status.HTTP_502_BAD_GATEWAY,
                "message": "There was an issue fetching the list of available currencies.",
                "success": False
            }, status=status.HTTP_502_BAD_GATEWAY)


class UserPreferenceUpdateView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated]

    def get_object(self):
        # Ensure that the user has a UserPreference instance
        try:
            return self.request.user.preferences
        except UserPreference.DoesNotExist:
            # If no preferences exist, create them
            preferences = UserPreference.objects.create(user=self.request.user)
            return preferences

    def update(self, request, *args, **kwargs):
        # Get available currencies from cache or API
        available_currencies = cache.get('available_currencies')
        if not available_currencies:
            try:
                url = f"{settings.EXCHANGE_RATE_API_URL}/{settings.EXCHANGE_RATE_API_KEY}/latest/USD"
                data = fetch_data_from_api(url)
                available_currencies = data.get('conversion_rates', {}).keys()
                cache.set('available_currencies', list(available_currencies), timeout=3600)
            except Exception as e:
                logger.error(f"Failed to fetch available currencies: {e}")
                return Response({
                    "data": {},
                    "errors": {"message": "Failed to fetch available currencies from external API"},
                    "status": status.HTTP_502_BAD_GATEWAY,
                    "message": "There was an issue fetching the available currencies.",
                    "success": False
                }, status=status.HTTP_502_BAD_GATEWAY)

        # Validate selected currencies
        selected_currencies = request.data.get('preferred_currencies', [])
        if len(selected_currencies) != 3:
            return Response({
                "data": {},
                "errors": {"message": "Please select exactly three currency pairs."},
                "status": status.HTTP_400_BAD_REQUEST,
                "message": "You must choose exactly three currency pairs.",
                "success": False
            }, status=status.HTTP_400_BAD_REQUEST)

        invalid_currencies = [pair for pair in selected_currencies if pair not in available_currencies]
        if invalid_currencies:
            return Response({
                "data": {},
                "errors": {"message": f"Invalid currency pairs: {', '.join(invalid_currencies)}"},
                "status": status.HTTP_400_BAD_REQUEST,
                "message": "Some selected currency pairs are invalid. Please check and try again.",
                "success": False
            }, status=status.HTTP_400_BAD_REQUEST)

        # Validate decimal precision
        decimal_precision = request.data.get('decimal_precision', 2)  # Default to 2 if not provided
        if not isinstance(decimal_precision, int) or decimal_precision < 0:
            return Response({
                "data": {},
                "errors": {"message": "Decimal precision must be a positive integer."},
                "status": status.HTTP_400_BAD_REQUEST,
                "message": "Invalid decimal precision.",
                "success": False
            }, status=status.HTTP_400_BAD_REQUEST)

        # Update user preferences
        preferences = self.get_object()
        preferences.preferred_currencies = selected_currencies
        preferences.decimal_precision = decimal_precision
        preferences.save()

        return Response({
            "data": {
                "preferred_currencies": preferences.preferred_currencies,
                "decimal_precision": preferences.decimal_precision
            },
            "errors": {},
            "status": status.HTTP_200_OK,
            "message": "User preferences updated successfully.",
            "success": True
        }, status=status.HTTP_200_OK)