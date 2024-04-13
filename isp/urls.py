# urls.py
from django.urls import path
from .views import signup,signin,home,view_customer

urlpatterns = [
    path('signup', signup, name='signup'),
    path('',signin,name='signin'),
    path('home',home,name='home'),
    path('view_customer/<int:id>',view_customer,name='view_customer'),
    # Add other URL patterns as needed
]
