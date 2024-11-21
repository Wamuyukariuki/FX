from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import TransactionCreateView, TransactionListView, TransactionDetailView, AvailableCurrenciesListView, \
    UserPreferenceUpdateView

urlpatterns = [
    path('transactions/', TransactionListView.as_view(), name='transaction-list'),
    path('transactions/<int:id>/', TransactionDetailView.as_view(), name='transaction-detail'),
    path('transactions/create/', TransactionCreateView.as_view(), name='transaction-create'),
    path('currencies/', AvailableCurrenciesListView.as_view(), name='available-currencies'),
    path('update-preferences/', UserPreferenceUpdateView.as_view(), name='update-preferences'),

]
