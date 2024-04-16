# urls.py
from django.urls import path
from .views import signup,signin,home,view_customer,update_customer,signout,delete_customer,staff_signup

urlpatterns = [
    path('signup', signup, name='signup'),
    path('',signin,name='signin'),
    path('home',home,name='home'),
    path('view_customer/<int:id>',view_customer,name='view_customer'),
    path('update/<int:id>',update_customer,name='update_customer'),
    path('logout',signout,name='logout'),
    path('delete/<int:id>,delete_customer',delete_customer,name='delete_customer'),
    path('staff_signup',staff_signup,name='staff_signup'),
    # Add other URL patterns as needed
]
