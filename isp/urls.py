# urls.py
from django.urls import path
from .views import signup,signin,home,view_customer,update_customer,signout,delete_customer,staff_signup,view_staff,edit_staff_page,update_staff,initiate_payment,callback,disable_customer,enable_customer
from django.contrib.auth import views as auth_views
urlpatterns = [
    path('signup', signup, name='signup'),
    path('',signin,name='signin'),
    path('home',home,name='home'),
    path('view_customer/<str:id>',view_customer,name='view_customer'),
    path('update/<int:id>',update_customer,name='update_customer'),
    path('logout',signout,name='logout'),
    path('delete/<int:id>,delete_customer',delete_customer,name='delete_customer'),
    path('staff_signup',staff_signup,name='staff_signup'),
    path('staff',view_staff,name='view_staff'),
    path('edit_staff_page/<int:id>',edit_staff_page,name='edit_staff_page'),
    path('update_staff/<int:id>',update_staff,name='update_staff'),
    path('initiate_payment/<int:id>',initiate_payment,name='initiate_payment'),
    path('callback/<int:id>',callback,name='callback'),
    path('disable_customer',disable_customer,name='disable_customer'),
    path('enable_customer',enable_customer,name='enable_customer'),
    path('password_reset/', auth_views.PasswordResetView.as_view(template_name='password_reset_form.html'), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),

    # Add other URL patterns as needed
]
