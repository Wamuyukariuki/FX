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
import time

logger = logging.getLogger(__name__)

# Utility to construct API URL
def get_exchange_rate_url(base_url, api_key, input_currency, output_currency):
    return f"{base_url}/{api_key}/pair/{input_currency.upper()}/{output_currency.upper()}"

# Utility to fetch data from external API
import time


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


# TransactionCreateView,track cache hits/misses and log the time taken
class TransactionCreateView(generics.CreateAPIView):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        input_currency = request.data.get('input_currency')
        output_currency = request.data.get('output_currency')
        input_amount = request.data.get('input_amount')

        # Validate using the serializer
        serializer = self.get_serializer(data=request.data)

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

        # Automatically add the customer_id from the logged-in user
        if not request.user.is_authenticated:
            return Response({
                "data": {},
                "errors": {"message": "Authentication required"},
                "status": status.HTTP_401_UNAUTHORIZED,
                "message": "User is not authenticated.",
                "success": False
            }, status=status.HTTP_401_UNAUTHORIZED)

        request.data['customer_id'] = request.user.id

        # Generate a unique cache key for the currency pair
        cache_key = f"exchange_rate_{input_currency.upper()}_{output_currency.upper()}"

        # Start timer to track cache retrieval time
        cache_start_time = time.time()

        # Check cache for exchange rate first
        exchange_rate = cache.get(cache_key)

        # Log cache hit/miss and time taken
        cache_end_time = time.time()
        cache_time_taken = cache_end_time - cache_start_time
        if exchange_rate:
            logger.info(f"Cache hit for {cache_key}. Time taken: {cache_time_taken:.4f} seconds.")
        else:
            logger.info(f"Cache miss for {cache_key}. Time taken: {cache_time_taken:.4f} seconds.")

        # If exchange rate is not found in cache, make the API call
        if exchange_rate is None:
            try:
                url = get_exchange_rate_url(
                    settings.EXCHANGE_RATE_API_URL,
                    settings.EXCHANGE_RATE_API_KEY,
                    input_currency,
                    output_currency
                )

                # Log the start and end time for fetching the API response
                api_start_time = time.time()
                exchange_rate = fetch_data_from_api(url).get('conversion_rate')
                api_end_time = time.time()
                api_time_taken = api_end_time - api_start_time
                logger.info(f"API request for {cache_key} took {api_time_taken:.4f} seconds.")

                if exchange_rate is None:
                    raise ValueError("Exchange rate missing in API response")

                # Cache the exchange rate for 1 hour
                cache.set(cache_key, exchange_rate, timeout=3600)
            except Exception as e:
                logger.error(f"Exchange rate API error: {str(e)}")
                return Response({
                    "data": {},
                    "errors": {"message": "Failed to fetch exchange rate"},
                    "status": status.HTTP_502_BAD_GATEWAY,
                    "message": "There was an issue fetching the exchange rate.",
                    "success": False
                }, status=status.HTTP_502_BAD_GATEWAY)

        # Calculate the output amount
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

        # Ensure customer_id is in request data
        if 'customer_id' not in request.data:
            return Response({
                "data": {},
                "errors": {"message": "customer_id is required"},
                "status": status.HTTP_400_BAD_REQUEST,
                "message": "Please provide the customer_id.",
                "success": False
            }, status=status.HTTP_400_BAD_REQUEST)

        return super().create(request, *args, **kwargs)

# List transactions
class TransactionListView(generics.ListAPIView):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

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


# List available currencies with Redis cache
class AvailableCurrenciesListView(generics.ListAPIView):
    def get(self, request, *args, **kwargs):
        # Define the cache key and URL for the API request
        cache_key = 'available_currencies'
        url = f"{settings.EXCHANGE_RATE_API_URL}/{settings.EXCHANGE_RATE_API_KEY}/latest/USD"

        # Check if the available currencies are in the cache
        cache_start_time = time.time()  # Track cache retrieval time
        cached_data = cache.get(cache_key)

        # Log the cache hit or miss
        cache_end_time = time.time()
        cache_time_taken = cache_end_time - cache_start_time
        if cached_data:
            logger.info(f"Cache hit for {cache_key}. Time taken: {cache_time_taken:.4f} seconds.")
            return Response({
                "data": cached_data,
                "errors": {},
                "status": status.HTTP_200_OK,
                "message": "Available currencies fetched from cache.",
                "success": True
            }, status=status.HTTP_200_OK)
        else:
            logger.info(f"Cache miss for {cache_key}. Time taken: {cache_time_taken:.4f} seconds.")

        # Fetch data from the API if cache is empty
        try:
            # Fetch the data from the external API
            api_start_time = time.time()  # Track API call time
            data = fetch_data_from_api(url)
            api_end_time = time.time()
            api_time_taken = api_end_time - api_start_time
            logger.info(f"API request for {cache_key} took {api_time_taken:.4f} seconds.")

            # Store the fetched data in the cache for 1 hour
            cache.set(cache_key, data, timeout=3600)
        except Exception as e:
            logger.error(f"Failed to fetch available currencies from API: {str(e)}")
            return Response({
                "data": {},
                "errors": {"message": "Failed to fetch currencies from external API"},
                "status": status.HTTP_502_BAD_GATEWAY,
                "message": "There was an issue fetching the list of available currencies.",
                "success": False
            }, status=status.HTTP_502_BAD_GATEWAY)

        # Return the data fetched from the API
        return Response({
            "data": data,
            "errors": {},
            "status": status.HTTP_200_OK,
            "message": "Available currencies fetched successfully.",
            "success": True
        }, status=status.HTTP_200_OK)
