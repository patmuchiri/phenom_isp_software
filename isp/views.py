# views.py
from django.contrib.auth import authenticate, login
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from .tasks import check_subscription_status
from .forms import CustomerSignupForm, Signin_form
from .models import Customer


def signup(request):
    if request.method == 'POST':
        form = CustomerSignupForm(request.POST)
        if form.is_valid():
            # Save the user object from the form data
            user = form.save()

            # Extract additional data from the form
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            phone = form.cleaned_data['phone']
            subscription = form.cleaned_data.get('subscription')
            last_payment = form.cleaned_data.get('last_payment')

            # Create a Customer object associated with the newly created user
            new_customer = Customer.objects.create(
                user=user,
                name=name,
                email=email,
                phone=phone,
                subscription=subscription,
                last_payment=last_payment
            )

            # Redirect to a success page or login page
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
                print("Username or Password is incorrect")
                return render(request,'login.html', {'form': form})
    return render(request, 'login.html', {'form': Signin_form()})


def home(request):
    customers = Customer.objects.all()
    return render(request, 'home.html', {'customers': customers})


def view_customer(request,id):
    customer = Customer.objects.get(pk=id)
    return render(request,'customer.html', {'customer': customer})