# FX
Currency Conversion API
This project is a Django-based API service for currency conversion and management. It provides users with functionality to authenticate, fetch available currency codes, and perform currency conversions in real-time using external exchange rate APIs.

Features
User Authentication:

Obtain and refresh access tokens for secure API interactions.
Uses JWT (JSON Web Token) for authentication.
Available Currency Codes:

Retrieve a comprehensive list of supported currency codes and their descriptions.
Public API: No authentication required.
Currency Conversion:

Convert amounts between currencies using real-time exchange rates.
Requires user authentication via a token.
Secure API Requests:

HTTPS integration to ensure secure communication.
Support for external exchange rate APIs with configurable base URLs and API keys.
Endpoints
Authentication:

POST /api/token/: Obtain access and refresh tokens.
POST /api/token/refresh/: Renew expired access tokens.
Currencies:

GET /api/currencies/: Fetch all available currency codes (public endpoint).
Conversion:

POST /api/currency/convert/: Perform currency conversion (authentication required).
Tech Stack
Backend: Django REST Framework
Authentication: JWT (SimpleJWT package)
External API Integration: Real-time exchange rates using a configurable third-party API.
Database: SQLite (can be swapped for PostgreSQL, MySQL, etc.)
Others:
Requests library for external API communication.
Robust error handling for API failures and bad input.
How to Use
Clone the repository:

bash
Copy code
git clone <repo_url>
cd <repo_name>
Install dependencies:

bash
Copy code
pip install -r requirements.txt
Configure environment variables for API keys and URLs in settings.py or a .env file:

EXCHANGE_RATE_API_URL: Base URL of the exchange rate API.
EXCHANGE_RATE_API_KEY: API key for accessing the exchange rate service.
Run migrations:

bash
Copy code
python manage.py migrate
Start the server:

bash
Copy code
python manage.py runserver
Test endpoints using Postman or cURL.

Potential Use Cases
A financial application that provides currency conversion features.
Integration with e-commerce platforms for multi-currency transactions.
A learning resource for building APIs with Django REST Framework.
Future Enhancements
Add historical exchange rate data.
Improve error handling for unavailable currencies.
Support batch conversions for multiple currencies.
