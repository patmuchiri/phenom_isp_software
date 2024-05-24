import json
import os
import logging

import requests
from django.contrib.auth import authenticate, login, logout
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
from .tasks import check_subscription_status
from .forms import CustomerSignupForm, Signin_form, StaffSignupForm, StaffUpdateForm
from .models import Customer
from django.contrib import messages
import routeros_api
import clicksend_client
from clicksend_client import SmsMessage
from clicksend_client.rest import ApiException

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


def home(request):
    try:
        api, connection = get_routeros_api()
        list_queues = api.get_resource('/queue/simple')
        customers = list_queues.get()
    except Exception as e:
        logger.error(f"Error fetching customers from RouterOS: {e}")
        return HttpResponseServerError(e)
    return render(request, 'home.html', {'customers': customers})


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


def signout(request):
    logout(request)
    return redirect("signin")


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


def view_staff(request):
    staff = User.objects.all()
    return render(request, 'staff.html', {'staff': staff})


def edit_staff_page(request, id):
    staff = User.objects.get(pk=id)
    staff_permissions = staff.get_all_permissions()
    return render(request, 'view_staff.html', {'staff': staff, 'permissions': staff_permissions})


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


@csrf_exempt
def initiate_payment(request, id):
    customer = Customer.objects.get(pk=id)
    if request.method == "POST":
        phone = request.POST["phone"].split('0', 1)[1]
        amount = request.POST["amount"]
        data = {
            "BusinessShortCode": mpesa.get_business_shortcode(),
            "Password": mpesa.generate_password(),
            "Timestamp": mpesa.get_current_timestamp(),
            "TransactionType": "CustomerPayBillOnline",
            "Amount": customer.subscription_amount,
            "PartyA": f"254{phone}",
            "PartyB": mpesa.get_business_shortcode(),
            "PhoneNumber": f"254{phone}",
            "CallBackURL": mpesa.get_callback_url(),
            "AccountReference": f"{customer.id}",
            "TransactionDesc": "Payment for merchandise"
        }
        headers = mpesa.generate_request_headers()

        try:
            resp = requests.post(mpesa.get_payment_url(), json=data, headers=headers)
            json_resp = resp.json()
            if "ResponseCode" in json_resp and json_resp["ResponseCode"] == "0":
                messages.success(request, "M-Pesa prompt sent successfully")
                return render(request, 'await_payment.html', {'customer': customer})
            else:
                messages.error(request, "Failed to send M-Pesa prompt")
        except Exception as e:
            logger.error(f"Error initiating M-Pesa payment: {e}")
            messages.error(request, "Error initiating payment. Please try again.")

    return render(request, "payment.html", {"customer": customer})


@csrf_exempt
def callback(request, id):
    customer = Customer.objects.get(pk=id)
    try:
        result = json.loads(request.body)
        code = result["Body"]["stkCallback"]["ResultCode"]
        if code == "0":
            return render(request, 'success.html')
    except Exception as e:
        logger.error(f"Error handling M-Pesa callback: {e}")

    return render(request, 'await_payment.html', {"customer": customer})


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

