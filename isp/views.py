# views.py
import json
import os

import requests
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from . import mpesa
from .tasks import check_subscription_status
from .forms import CustomerSignupForm, Signin_form, StaffSignupForm, StaffUpdateForm
from .models import Customer
from django.contrib import messages
import routeros_api
import clicksend_client
from clicksend_client import SmsMessage
from clicksend_client.rest import ApiException


# Configure HTTP basic authorization: BasicAuth Clicksend
configuration = clicksend_client.Configuration()
configuration.username = os.getenv('CLICKSEND_USERNAME')
configuration.password = os.getenv('CLICKSEND_PASSWORD')
api_instance = clicksend_client.SMSApi(clicksend_client.ApiClient(configuration))

#Routeros config
connection = routeros_api.RouterOsApiPool(os.getenv('ROUTER_IP'), os.getenv('ROUTER_USERNAME'), os.getenv('ROUTER_PASSWORD'), plaintext_login=True)
api = connection.get_api()
list_queues = api.get_resource('/queue/simple')


def signup(request):
    if request.method == 'POST':
        form = CustomerSignupForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            name = user.name
            target = user.router_ip_address
            bandwith = user.bandwith.upper()
            list_queues.add(name=name, target=target, max_limit=bandwith)
            user.save()
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
    customers = list_queues.get()
    return render(request, 'home.html', {'customers': customers})


def view_customer(request, id):
    customer = list_queues.get(id=id)
    user_names = [i['name'] for i in customer]
    users = Customer.objects.filter(name__in=user_names)
    details = [{'id':user.id,'name': user.name, 'email': user.email, 'phone': user.phone, 'status': user.subscription, 'last_payment': user.last_payment} for user in users]
    return render(request, 'customer.html', {'customer': customer, 'details': details})




def update_customer(request, id):
    customer = Customer.objects.get(pk=id)
    user = list_queues.get(name=customer.name)
    user_id = [i['id'] for i in user]
    if request.method == 'POST':
        form = CustomerSignupForm(request.POST, instance=customer)
        if form.is_valid():
            name = form.cleaned_data['name']
            target = form.cleaned_data['router_ip_address']
            bandwith = form.cleaned_data['bandwith'].upper()
            list_queues.set(id=user_id[0],name=name,target=target,max_limit=bandwith)
            form.save()
            messages.success(request, f"{name} successfully updated")
            return HttpResponseRedirect(reverse('view_customer', args=[user_id[0]]))
    else:
        form = CustomerSignupForm(instance=customer)
    return render(request, 'signup.html', {'form': form})



def signout(request):
    logout(request)
    return redirect("signin")


def delete_customer(request,id):
    customer = Customer.objects.get(pk=id)
    user = list_queues.get(name=customer.name)
    user_id = [i['id'] for i in user]
    list_queues.remove(id=user_id[0])
    customer.delete()
    messages.error(request, f"Successfully deleted")
    return redirect('home')



def staff_signup(request):
    if request.method == 'POST':
        form = StaffSignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            permissions = form.cleaned_data['permissions']
            user.user_permissions.set(permissions)
            return redirect('view_staff')  # Redirect to a success page
    else:
        form = StaffSignupForm()
    return render(request, 'signup.html', {'form': form})

def view_staff(request):
    staff = User.objects.all()
    return render(request,'staff.html', {'staff': staff})


def edit_staff_page(request, id):
    staff = User.objects.get(pk=id)
    staff_permissions = staff.get_all_permissions()
    return render(request, 'view_staff.html', {'staff': staff, 'permissions': staff_permissions})


def update_staff(request, id):
    staff = get_object_or_404(User, pk=id)
    form = StaffUpdateForm(instance=staff)
    if request.method == 'POST':
        form = StaffUpdateForm(request.POST, instance=staff)
        if form.is_valid():
            form.save()
            return redirect('view_staff')
    return render(request, 'signup.html', {'form': form})


# views.py

def send_sms_view(request):
    sms_message = SmsMessage(source="php",
                            body="This is a test message.",
                            to="+254712240197",
                            schedule=1436874701)

    sms_messages = clicksend_client.SmsMessageCollection(messages=[sms_message])

    try:
        # Send sms message(s)
        api_response = api_instance.sms_send_post(sms_messages)
        print(api_response)
    except ApiException as e:
        print("Exception when calling SMSApi->sms_send_post: %s\n" % e)
    return HttpResponse("message sent")


@csrf_exempt
def initiate_payment(request,id):

    customer = Customer.objects.get(pk=id)
    if request.method == "POST":
        phone = request.POST["phone"]
        phone = phone.split('0',1)
        phone = phone[1]
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

        resp = requests.post(mpesa.get_payment_url(), json=data, headers=headers)
        print(resp.json())
        json_resp = resp.json()
        if "ResponseCode" in json_resp:
            code = json_resp["ResponseCode"]
            messages.success(request,"M-Pesa prompt sent successfully")
            if code == "0":
                mid = json_resp["MerchantRequestID"]
                cid = json_resp["CheckoutRequestID"]
                print(json_resp)
                return render(request,'await_payment.html')
            else:
                print("failed")
        elif "errorCode" in json_resp:
            errorCode = json_resp["errorCode"]

    return render(request, "payment.html",{"customer": customer})


@csrf_exempt
def callback(request):
    result = json.loads(request.body)
    mid = result["Body"]["stkCallback"]["MerchantRequestID"]
    cid = result["Body"]["stkCallback"]["CheckoutRequestID"]
    code = result["Body"]["stkCallback"]["ResultCode"]
    return render(request,'await_payment.html')
