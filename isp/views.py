# views.py
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from .tasks import check_subscription_status
from .forms import CustomerSignupForm, Signin_form, StaffSignupForm
from .models import Customer
from django.contrib import messages

def signup(request):
    if request.method == 'POST':
        form = CustomerSignupForm(request.POST)
        if form.is_valid():

            user = form.save()
            messages.success(request, f"{user.name} successfully registered")
            return redirect('home')
    else:
        form = CustomerSignupForm()

    return render(request, 'signup.html', {'form': form})


def signin(request):
    if request.method == 'POST':
        form = Signin_form(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                return redirect('home')
            else:
                messages.error(request, 'Username or password incorrect')
                return render(request,'login.html', {'form': form})
    return render(request, 'login.html', {'form': Signin_form()})


def home(request):
    customers = Customer.objects.all()
    return render(request, 'home.html', {'customers': customers})


def view_customer(request,id):
    customer = Customer.objects.get(pk=id)
    return render(request,'customer.html', {'customer': customer})



def update_customer(request,id):
    customer = Customer.objects.get(pk=id)
    form = CustomerSignupForm(instance=customer)
    if request.method == 'POST':
        form = CustomerSignupForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            messages.success(request, f"{customer.name} successfully updated!")
            return redirect('view_customer',customer.id)
        else:
            messages.error(request,"Unable to update customer account")
            return render(request,'signup.html', {'form': form})

    return render(request, 'signup.html', {'form': form})



def signout(request):
    logout(request)
    return redirect("signin")


def delete_customer(request,id):
    customer = Customer.objects.get(pk=id)
    customer.delete()
    messages.error(request, f"{customer.name} successfully deleted")
    return redirect('home')



def staff_signup(request):
    if request.method == 'POST':
        form = StaffSignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            permissions = form.cleaned_data['permissions']
            user.user_permissions.set(permissions)
            return redirect('home')  # Redirect to a success page
    else:
        form = StaffSignupForm()
    return render(request, 'signup.html', {'form': form})