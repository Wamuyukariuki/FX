FX
Currency Conversion and Management API
This project is a Django-based API service for currency conversion and management. It provides functionality for secure user authentication, fetching supported currency codes, performing currency conversions, and managing user preferences for enhanced usability.

Features
User Authentication
Obtain and refresh access tokens for secure API interactions.
Uses JWT (JSON Web Token) for authentication.
Available Currency Codes
Retrieve a comprehensive list of supported currency codes and their descriptions.
Public API: No authentication required.
Currency Conversion
Convert amounts between currencies using real-time exchange rates.
Requires user authentication via a token.
User Preferences
Allows users to configure:
Preferred currencies for conversions.
Decimal precision for converted amounts.
Automatically creates user preferences when a new user registers.
Secure API Requests
HTTPS integration to ensure secure communication.
Support for external exchange rate APIs with configurable base URLs and API keys.
Transaction Management
Record transactions with details such as:
Input and output currencies.
Converted amounts.
User who initiated the transaction.
Includes precise decimal handling based on user preferences.
Endpoints
Authentication
POST /api/token/: Obtain access and refresh tokens.
POST /api/token/refresh/: Renew expired access tokens.
Currencies
GET /api/currencies/: Fetch all available currency codes (public endpoint).
Conversion
POST /api/currency/convert/: Perform currency conversion (authentication required).
Transactions
POST /api/transactions/create/: Create a new transaction record.
GET /api/transactions/: Retrieve a list of user transactions (authentication required).
Tech Stack
Backend: Django REST Framework
Authentication: JWT (SimpleJWT package)
External API Integration: Real-time exchange rates using a configurable third-party API.
Database: SQLite (can be swapped for PostgreSQL, MySQL, etc.)
Additional Tools:
Requests library for external API communication.
Logging for monitoring user preference creation and updates.
