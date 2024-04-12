# urls.py
from django.urls import path
from .views import signup,check_subscription_view

urlpatterns = [
    path('', signup, name='signup'),
    path('check/',check_subscription_view,name='check_subscription_status'),
    # Add other URL patterns as needed
]
