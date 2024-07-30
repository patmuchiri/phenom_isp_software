# urls.py
from django.conf.urls import handler404
from django.urls import path
from .views import signup, signin, home, view_customer, update_customer, signout, delete_customer, staff_signup, \
    view_staff, edit_staff_page, update_staff, disable_customer, enable_customer, \
    all_customers, get_customer_payments, initiate_pesapal_payments,pesapal_callback
from django.contrib.auth import views as auth_views
urlpatterns = [
    path('signup', signup, name='signup'),
    path('signin',signin,name='signin'),
    path('',home,name='home'),
    path('view_customer/<str:id>',view_customer,name='view_customer'),
    path('update/<int:id>',update_customer,name='update_customer'),
    path('logout',signout,name='logout'),
    path('delete/<int:id>,delete_customer',delete_customer,name='delete_customer'),
    path('staff_signup',staff_signup,name='staff_signup'),
    path('staff',view_staff,name='view_staff'),
    path('edit_staff_page/<int:id>',edit_staff_page,name='edit_staff_page'),
    path('update_staff/<int:id>',update_staff,name='update_staff'),
    path('disable_customer',disable_customer,name='disable_customer'),
    path('enable_customer',enable_customer,name='enable_customer'),
    path('password_reset/', auth_views.PasswordResetView.as_view(template_name='password_reset_form.html'), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='password_reset_confirm.html'), name='password_reset_confirm'),
    path('api/customers',all_customers,name='all_customers'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='password_reset_complete.html'), name='password_reset_complete'),
    path('api/payments/<int:customer_id>',get_customer_payments,name='get_customer_payments'),
    path('api/initiaite-payment',initiate_pesapal_payments,name='initiate_pesapal_payment'),
    path('api/callback',pesapal_callback,name='callback'),
]