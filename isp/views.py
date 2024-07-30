import json
import os
import logging
import uuid

import requests
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseServerError
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from . import mpesa
from .serializers import CustomerSerializer, PaymentSerializer
from .tasks import check_subscription_status
from .forms import CustomerSignupForm, Signin_form, StaffSignupForm, StaffUpdateForm
from .models import Customer, Payment
from django.contrib import messages
import routeros_api
import clicksend_client
from clicksend_client import SmsMessage
from clicksend_client.rest import ApiException
from dotenv import load_dotenv
import os

load_dotenv()
# Configure logging
logger = logging.getLogger(__name__)

# Configure HTTP basic authorization: BasicAuth Clicksend
configuration = clicksend_client.Configuration()
configuration.username = os.getenv('CLICKSEND_USERNAME')
configuration.password = os.getenv('CLICKSEND_PASSWORD')
api_instance = clicksend_client.SMSApi(clicksend_client.ApiClient(configuration))

# RouterOS config
router_ip = os.getenv('ROUTER_IP')
router_username = os.getenv('ROUTER_USERNAME')
router_password = os.getenv('ROUTER_PASSWORD')


def get_routeros_api():
    connection = routeros_api.RouterOsApiPool(router_ip, router_username, router_password, plaintext_login=True)
    api = connection.get_api()
    return api, connection

@login_required
def signup(request):
    if request.method == 'POST':
        form = CustomerSignupForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            name = user.name
            target = user.router_ip_address
            bandwith = user.bandwith
            bandwith_format = f"{bandwith}M/{bandwith}M"
            api, connection = get_routeros_api()
            try:
                list_queues = api.get_resource('/queue/simple')
                list_queues.add(name=name, target=target, max_limit=bandwith_format)
                user.save()
                messages.success(request, f"{user.name} successfully registered")
            except Exception as e:
                logger.error(f"Error while adding user to RouterOS queue: {e}")
                messages.error(request, "Error registering user. Please try again.")
            finally:
                connection.disconnect()
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
    return render(request, 'login.html', {'form': Signin_form()})

@login_required
def home(request):
    try:
        api, connection = get_routeros_api()
        list_queues = api.get_resource('/queue/simple')
        customers = list_queues.get()
    except Exception as e:
        logger.error(f"Error fetching customers from RouterOS: {e}")
        return HttpResponseServerError(e)
    return render(request, 'home.html', {'customers': customers})

@login_required
def view_customer(request, id):
    try:
        api, connection = get_routeros_api()
        list_queues = api.get_resource('/queue/simple')
        customer = list_queues.get(id=id)
        user_names = [i['name'] for i in customer]
        users = Customer.objects.filter(name__in=user_names)
        details = [
            {'id': user.id, 'name': user.name, 'email': user.email, 'phone': user.phone, 'status': user.subscription,
             'last_payment': user.last_payment} for user in users]
    except Exception as e:
        logger.error(f"Error fetching customer details: {e}")
        return HttpResponseServerError(e)
    return render(request, 'customer.html', {'customer': customer, 'details': details})

@login_required
def update_customer(request, id):
    try:
        customer = Customer.objects.get(pk=id)
        api, connection = get_routeros_api()
        list_queues = api.get_resource('/queue/simple')
        user = list_queues.get(name=customer.name)
        user_id = [i['id'] for i in user]
        if request.method == 'POST':
            form = CustomerSignupForm(request.POST, instance=customer)
            if form.is_valid():
                name = form.cleaned_data['name']
                target = form.cleaned_data['router_ip_address']
                bandwith = form.cleaned_data['bandwith']
                bandwith_format = f"{bandwith}M/{bandwith}M"
                list_queues.set(id=user_id[0], name=name, target=target, max_limit=bandwith_format)
                form.save()
                messages.success(request, f"{name} successfully updated")
                return HttpResponseRedirect(reverse('view_customer', args=[user_id[0]]))
        else:
            form = CustomerSignupForm(instance=customer)
    except Exception as e:
        logger.error(f"Error updating customer: {e}")
        return HttpResponseServerError(e)

    return render(request, 'signup.html', {'form': form})

@login_required
def signout(request):
    logout(request)
    return redirect("signin")

@login_required
def delete_customer(request, id):
    try:
        customer = Customer.objects.get(pk=id)
        api, connection = get_routeros_api()
        list_queues = api.get_resource('/queue/simple')
        user = list_queues.get(name=customer.name)
        user_id = [i['id'] for i in user]
        list_queues.remove(id=user_id[0])
        customer.delete()
        messages.success(request, "Successfully deleted")
    except Exception as e:
        logger.error(f"Error deleting customer: {e}")
        return HttpResponseServerError(e)

    return redirect('home')

@login_required
def staff_signup(request):
    if request.method == 'POST':
        form = StaffSignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            permissions = form.cleaned_data['permissions']
            user.user_permissions.set(permissions)
            return redirect('view_staff')
    else:
        form = StaffSignupForm()
    return render(request, 'signup.html', {'form': form})

@login_required
def view_staff(request):
    staff = User.objects.all()
    return render(request, 'staff.html', {'staff': staff})

@login_required
def edit_staff_page(request, id):
    staff = User.objects.get(pk=id)
    staff_permissions = staff.get_all_permissions()
    return render(request, 'view_staff.html', {'staff': staff, 'permissions': staff_permissions})

@login_required
def update_staff(request, id):
    staff = get_object_or_404(User, pk=id)
    if request.method == 'POST':
        form = StaffUpdateForm(request.POST, instance=staff)
        if form.is_valid():
            form.save()
            return redirect('view_staff')
    else:
        form = StaffUpdateForm(instance=staff)
    return render(request, 'signup.html', {'form': form})

@login_required
def send_sms_view(request):
    sms_message = SmsMessage(
        source="php",
        body="This is a test message.",
        to="+254712240197",
        schedule=1436874701
    )
    sms_messages = clicksend_client.SmsMessageCollection(messages=[sms_message])
    try:
        api_response = api_instance.sms_send_post(sms_messages)
        logger.info(f"SMS sent successfully: {api_response}")
    except ApiException as e:
        logger.error(f"Exception when calling SMSApi->sms_send_post: {e}")
    return HttpResponse("Message sent")


@api_view(['GET'])
def disable_customer(request):
    try:
        customers = Customer.objects.all()
        disabled_customers = []
        for customer in customers:
            days_since_last_payment = (timezone.now() - customer.last_payment).days
            if days_since_last_payment > 31:
                customer.subscription = False
                api, connection = get_routeros_api()
                list_queues = api.get_resource('/queue/simple')
                list_queues.set(name=customer.name, max_limit="1k/1k")
                customer.save()
                disabled_customers.append(customer.name)
                connection.disconnect()
        if disabled_customers:
            return Response({"message": f"The following customers have been disabled: {', '.join(disabled_customers)}"},
                            status=status.HTTP_200_OK)
        else:
            return Response({"message": "No customers have been disabled"}, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error disabling customers: {e}")
        return Response({"message": "An error occurred while processing the request"},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def enable_customer(request):
    try:
        customers = Customer.objects.filter(subscription=False)
        disabled_customers = []
        for customer in customers:
            days_since_last_payment = (timezone.now() - customer.last_payment).days
            if days_since_last_payment < 31:
                customer.subscription = True
                api, connection = get_routeros_api()
                list_queues = api.get_resource('/queue/simple')
                bandwith = customer.bandwith
                bandwith_format = f"{bandwith}M/{bandwith}M"
                list_queues.set(name=customer.name, max_limit=bandwith_format)
                customer.save()
                disabled_customers.append(customer.name)
                connection.disconnect()
        if disabled_customers:
            return Response({"message": f"The following customers have been enabled: {', '.join(disabled_customers)}"},
                            status=status.HTTP_200_OK)
        else:
            return Response({"message": "No customers have been enabled"}, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error enabling customers: {e}")
        return Response({"message": e},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@api_view(['GET'])
def all_customers(request):
    customers = Customer.objects.all()
    serializer = CustomerSerializer(customers, many=True)
    return Response({"customers": serializer.data})



@api_view(['GET'])
def get_customer_payments(request, customer_id):
    customer = get_object_or_404(Customer, id=customer_id)
    payments = Payment.objects.filter(customer=customer)
    if payments:
        serializer = PaymentSerializer(payments, many=True)
        return Response({"Payments":serializer.data})
    return Response("No payments found", status=status.HTTP_404_NOT_FOUND)


def get_pesapal_token():
    url = "https://pay.pesapal.com/v3/api/Auth/RequestToken"
    consumer_key = os.getenv('CONSUMER_KEY')
    consumer_secret = os.getenv('CONSUMER_SECRET')
    if not consumer_key or not consumer_secret:
        print("Environment variables not set properly")
        raise ValueError("Missing CONSUMER_KEY or CONSUMER_SECRET")
    print("Consumer Key:", consumer_key)
    print("Consumer Secret:", consumer_secret)
    body = {
        "consumer_key": f"{consumer_key}",
        "consumer_secret": f"{consumer_secret}",
    }
    response = requests.post(url, json=body,headers={'Content-Type': 'application/json', 'Accept': 'application/json'}).json()
    print(response)
    token = response['token']
    return token


@api_view(['POST'])
def initiate_pesapal_payments(request):
    customer_id = request.data.get('customer_id')
    customer = get_object_or_404(Customer, id=customer_id)
    amount = customer.subscription_amount
    # Generate a unique merchant reference
    merchant_reference = str(uuid.uuid4())
    # Prepare the payload for Pesapal API
    payload = {
        "id": merchant_reference,
        "currency": "KES",
        "amount": float(customer.subscription_amount),
        "description": f"Wi-Fi Subscription payment for {customer.name}",
        "callback_url": "http://localhost:3000/callback",
        "notification_id": "2296d92a-ea6a-4a3b-990a-dcefbdff86c5",
        "billing_address": {
            "phone_number": customer.phone,
            "first_name": customer.name.split()[0],
        }
    }
    token = get_pesapal_token()

    # Make a request to Pesapal API
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    response = requests.post(
        f"https://pay.pesapal.com/v3/api/Transactions/SubmitOrderRequest",
        json=payload,
        headers=headers
    )

    if response.status_code == 200:
        pesapal_response = response.json()

        # Create a new Payment object
        payment = Payment.objects.create(
            customer=customer,
            amount=amount,
            pesapal_transaction_tracking_id=pesapal_response['order_tracking_id'],
            pesapal_merchant_reference=merchant_reference,
            status='PENDING'
        )

        serializer = PaymentSerializer(payment)
        return Response({
            'payment': serializer.data,
            'redirect_url': pesapal_response['redirect_url']
        }, status=status.HTTP_201_CREATED)
    else:
        return Response({'error': 'Failed to initiate payment'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def pesapal_callback(request):
    order_tracking_id = request.data.get('OrderTrackingId')
    merchant_reference = request.data.get('MerchantReference')

    payment = get_object_or_404(Payment, pesapal_transaction_tracking_id=order_tracking_id,
                                pesapal_merchant_reference=merchant_reference)
    token = get_pesapal_token()

    # Make a request to Pesapal API to get the transaction status
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    response = requests.get(
        f"https://pay.pesapal.com/api/Transactions/GetTransactionStatus?orderTrackingId={order_tracking_id}",
        headers=headers
    )

    if response.status_code == 200:
        pesapal_response = response.json()
        payment.status = pesapal_response['payment_status_description']

        if payment.status == 'COMPLETED':
            payment.customer.last_payment = timezone.now()
            payment.customer.subscription = True
            payment.customer.save()

        payment.save()

        serializer = PaymentSerializer(payment)
        return Response(serializer.data)
    else:
        return Response({'error': 'Failed to get transaction status'}, status=status.HTTP_400_BAD_REQUEST)
