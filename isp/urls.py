# urls.py
from django.urls import path
from .views import create_customer, signin, get_customers, view_customer, update_customer, signout, delete_customer, staff_signup, \
    view_staff, edit_staff_page, update_staff, process_subscriptions,delete_staff
from django.contrib.auth import views as auth_views
from rest_framework_simplejwt import views as jwt_views

urlpatterns = [
    path('api/create', create_customer, name='create'),
    path('',signin,name='signin'),
    path('api/token/', jwt_views.TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/get_customers',get_customers,name='get_customers'),
    path('api/view_customer/<str:id>',view_customer,name='view_customer'),
    path('api/update/<int:id>',update_customer,name='update_customer'),
    path('api/logout',signout,name='logout'),
    path('api/delete/<int:id>',delete_customer,name='delete_customer'),
    path('staff_signup',staff_signup,name='staff_signup'),
    path('staff',view_staff,name='view_staff'),
    path('edit_staff_page/<int:id>',edit_staff_page,name='edit_staff_page'),
    path('update_staff/<int:id>',update_staff,name='update_staff'),
    path('api/process_subscriptions',process_subscriptions,name='process_subscriptions'),
    path('api/delete_staff/<int:id>',delete_staff,name='delete_staff'),
]