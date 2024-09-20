import json
import os
import logging
import uuid

import requests
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseServerError
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from requests.auth import HTTPBasicAuth
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from djangoProject27 import settings
from .serializers import CustomerSerializer, PaymentSerializer, SubscriptionSerializer, StaffSerializer
from .forms import CustomerSignupForm, Signin_form, StaffSignupForm, StaffUpdateForm
from .models import Customer, Payment, Subscription
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


#Connects to mikrotik router and the api variable is used globally for executing commands on the router
def get_routeros_api():
    connection = routeros_api.RouterOsApiPool(router_ip, router_username, router_password, plaintext_login=True)
    api = connection.get_api()
    return api, connection


@api_view(['POST'])
#@permission_classes([IsAuthenticated])
def create_customer(request):
    """
    API View to create a new customer and their subscription,
    and add them to the RouterOS queue.
    Requires the user to be authenticated.
    """
    form = CustomerSignupForm(request.data)
    if form.is_valid():
        customer = form.save()

        # Extract Subscription-related data from the request
        router_ip_address = request.data.get('router_ip_address', '192.168.88.1')
        bandwidth = request.data.get('bandwidth')
        subscription_amount = request.data.get('subscription_amount')
        start_date = request.data.get('start_date')
        thirty_days_later = timezone.now().date() + timezone.timedelta(days=30)
        last_payment_date = request.data.get('last_payment_date')

        bandwidth_format = f"{bandwidth}M/{bandwidth}M"

        # Log the extracted data
        logger.debug(
            f"Customer data: {customer.name}, Subscription data: router_ip_address={router_ip_address}, bandwidth={bandwidth}, subscription_amount={subscription_amount}")

        api, connection = get_routeros_api()
        try:
            # Interact with RouterOS API to add the customer to the queue
            list_queues = api.get_resource('/queue/simple')
            list_queues.add(name=customer.name, target=router_ip_address, max_limit=bandwidth_format)

            # Create the Subscription
            subscription = Subscription.objects.create(
                customer=customer,
                router_ip_address=router_ip_address,
                bandwidth=bandwidth,
                subscription_amount=subscription_amount,
                is_active=True,  # Assuming the subscription starts as active
                start_date=start_date,
                end_date=thirty_days_later,
                last_payment_date=last_payment_date
            )

            # Log success and return response
            logger.info(
                f"Customer {customer.name} and subscription {subscription.id} successfully created and added to "
                f"RouterOS queue")
            return Response({"detail": f"{customer.name} and subscription successfully registered"},
                            status=status.HTTP_201_CREATED)

        except Exception as e:
            # Log the error and return an error response
            logger.error(f"Error while adding customer to RouterOS queue: {e}")
            return Response({"error": "Error registering customer. Please try again."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        finally:
            # Ensure the connection is properly closed
            connection.disconnect()
            logger.debug("RouterOS API connection closed")

    else:
        # Log form errors and return a bad request response
        logger.warning(f"Form validation failed: {form.errors}")
        return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)


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

@api_view(['GET'])
#@permission_classes([IsAuthenticated])
def get_customers(request):
    """
    API View to get a list of customers from RouterOS queue.
    Requires the user to be authenticated.
    """
    # Establish connection with RouterOS API
    api, connection = get_routeros_api()
    try:
        # Fetch customers from RouterOS API
        list_queues = api.get_resource('/queue/simple')
        customers = list_queues.get()

        # Get all customer names from RouterOS
        customer_names = [customer.get('name') for customer in customers]

        # Fetch customers from the database that match the names from RouterOS
        db_customers = Customer.objects.filter(name__in=customer_names).prefetch_related('subscriptions')

        # Create a dictionary mapping names to customer objects
        name_to_customer = {customer.name: customer for customer in db_customers}

        # Convert RouterOS response to a suitable format and append database data
        customers_data = []
        for customer in customers:
            db_customer = name_to_customer.get(customer.get('name'))

            # Construct customer data dictionary
            customer_data = {
                'routeros_id': customer.get('id'),
                'name': customer.get('name'),
                'target': customer.get('target'),
                'max_limit': customer.get('max_limit'),
                'db_id': db_customer.id if db_customer else None,
                'phone': db_customer.phone if db_customer else None,
                'email': db_customer.email if db_customer else None,
                'balance': str(db_customer.balance) if db_customer else None,  # Convert Decimal to string
                'last_updated': db_customer.last_updated if db_customer else None,
                'subscriptions': []
            }

            # Append subscription details if customer exists in the database
            if db_customer:
                for subscription in db_customer.subscriptions.all():
                    customer_data['subscriptions'].append({
                        'router_ip_address': subscription.router_ip_address,
                        'bandwidth': subscription.bandwidth,
                        'subscription_amount': str(subscription.subscription_amount),  # Convert Decimal to string
                        'is_active': subscription.is_active,
                        'start_date': subscription.start_date,
                        'end_date': subscription.end_date,
                        'last_payment_date': subscription.last_payment_date,
                    })

            # Add the constructed data to the customers_data list
            customers_data.append(customer_data)

        logger.info("Successfully fetched customers from RouterOS and database")
        return Response(customers_data, status=status.HTTP_200_OK)

    except Exception as e:
        # Log the error and return a server error response
        logger.error(f"Error fetching customers from RouterOS or database: {e}")
        return Response({"error": "Error fetching customers"},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        # Ensure the connection is properly closed
        if 'connection' in locals():
            connection.disconnect()
            logger.debug("RouterOS API connection closed")

@api_view(['GET'])
#@permission_classes([IsAuthenticated])
def view_customer(request, id):
    """
    API endpoint that allows viewing a customer's details.

    :param request: The HTTP request object
    :param id: The ID of the customer to retrieve
    :return: Response object with customer data or error message
    """
    try:
        # Fetch the customer by ID
        logger.info(f"Attempting to fetch details for customer ID: {id}")
        customer = Customer.objects.get(id=id)

        # Fetch the subscriptions for the customer
        subscriptions = customer.subscriptions.all()

        # Construct the customer data dictionary
        customer_data = {
            'routeros_id': customer.name,  # Using 'name' as 'routeros_id'
            'name': customer.name,
            'target': '',  # Placeholder if you have no equivalent field
            'max_limit': '',  # Placeholder if you have no equivalent field
            'db_id': customer.id,
            'phone': customer.phone,
            'email': customer.email,
            'balance': str(customer.balance),  # Convert Decimal to string
            'last_updated': customer.last_updated,
            'subscriptions': []
        }

        # Append subscription details
        for subscription in subscriptions:
            customer_data['subscriptions'].append({
                'router_ip_address': subscription.router_ip_address,
                'bandwidth': subscription.bandwidth,
                'subscription_amount': str(subscription.subscription_amount),  # Convert Decimal to string
                'is_active': subscription.is_active,
                'start_date': subscription.start_date,
                'end_date': subscription.end_date,
                'last_payment_date': subscription.last_payment_date,
            })

        logger.info(f"Successfully retrieved details for customer ID: {id}")
        return Response(customer_data, status=status.HTTP_200_OK)

    except ObjectDoesNotExist:
        logger.warning(f"Customer with ID {id} not found")
        return Response({"error": "Customer not found"}, status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        logger.error(f"Error fetching customer details for ID {id}: {str(e)}", exc_info=True)
        return Response({"error": "An unexpected error occurred"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['PUT'])
#@permission_classes([IsAuthenticated])
def update_customer(request, id):
    """
    API endpoint to update a customer's details, associated RouterOS queue, and subscription.

    :param request: The HTTP request object
    :param id: The ID of the customer to update
    :return: Response object with updated customer data or error message
    """
    logger.info(f"Attempting to update customer with ID: {id}")
    api = None
    connection = None

    try:
        with transaction.atomic():
            # Fetch the customer from the database
            customer = Customer.objects.get(pk=id)
            logger.debug(f"Customer {customer.name} found in database")

            # Fetch the associated subscription
            subscription = Subscription.objects.filter(customer=customer, is_active=True).first()
            if not subscription:
                logger.warning(f"No active subscription found for customer {customer.name}")
                return Response({"error": "No active subscription found for this customer"},
                                status=status.HTTP_400_BAD_REQUEST)

            # Connect to RouterOS API
            api, connection = get_routeros_api()
            list_queues = api.get_resource('/queue/simple')

            # Find the corresponding RouterOS queue
            user = list_queues.get(name=customer.name)
            user_id = [i['id'] for i in user]
            logger.debug(f"Found RouterOS queue for customer: {customer.name}")

            # Validate and update the customer data
            customer_serializer = CustomerSerializer(customer, data=request.data, partial=True)
            subscription_serializer = SubscriptionSerializer(subscription, data=request.data, partial=True)

            if customer_serializer.is_valid() and subscription_serializer.is_valid():
                name = customer_serializer.validated_data.get('name', customer.name)
                target = subscription_serializer.validated_data.get('router_ip_address', subscription.router_ip_address)
                bandwidth = subscription_serializer.validated_data.get('bandwidth', subscription.bandwidth)

                # Update RouterOS queue if necessary
                if target or bandwidth:
                    bandwidth_format = f"{bandwidth}M/{bandwidth}M"
                    list_queues.set(id=user_id[0], name=name, target=target, max_limit=bandwidth_format)
                    logger.info(f"Updated RouterOS queue for customer: {name}")

                # Save the updated customer data
                updated_customer = customer_serializer.save()
                updated_subscription = subscription_serializer.save()

                logger.info(f"Successfully updated customer: {updated_customer.name} and subscription")

                # Combine the serialized data
                response_data = {
                    "customer": CustomerSerializer(updated_customer).data,
                    "subscription": SubscriptionSerializer(updated_subscription).data
                }

                return Response(response_data, status=status.HTTP_200_OK)
            else:
                errors = {}
                if not customer_serializer.is_valid():
                    errors['customer'] = customer_serializer.errors
                if not subscription_serializer.is_valid():
                    errors['subscription'] = subscription_serializer.errors
                logger.warning(f"Invalid data for customer/subscription update: {errors}")
                return Response(errors, status=status.HTTP_400_BAD_REQUEST)

    except ObjectDoesNotExist:
        logger.warning(f"Customer with ID {id} not found")
        return Response({"error": "Customer not found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error updating customer with ID {id}: {str(e)}", exc_info=True)
        return Response({"error": "An unexpected error occurred"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    finally:
        if connection:
            logger.debug("Closing RouterOS API connection")
            connection.disconnect()


@api_view(['POST'])
#@permission_classes([IsAuthenticated])
def signout(request):
    """
    API endpoint to sign out a user.

    :param request: The HTTP request object
    :return: Response object with success message
    """
    logger.info(f"User {request.user.username} attempting to sign out")
    logout(request)
    logger.info(f"User successfully signed out")
    return Response({"message": "Successfully signed out"}, status=status.HTTP_200_OK)


@api_view(['DELETE'])
#@permission_classes([IsAuthenticated])
def delete_customer(request, id):
    """
    API endpoint to delete a customer and their associated RouterOS queue.

    :param request: The HTTP request object
    :param id: The ID of the customer to delete
    :return: Response object with success message or error message
    """
    logger.info(f"Attempting to delete customer with ID: {id}")
    api = None
    connection = None

    try:
        # Fetch the customer from the database
        customer = Customer.objects.get(pk=id)
        logger.debug(f"Customer {customer.name} found in database")

        # Connect to RouterOS API
        api, connection = get_routeros_api()
        list_queues = api.get_resource('/queue/simple')

        # Find and remove the corresponding RouterOS queue
        user = list_queues.get(name=customer.name)
        user_id = [i['id'] for i in user]
        list_queues.remove(id=user_id[0])
        logger.info(f"Removed RouterOS queue for customer: {customer.name}")

        # Delete the customer from the database
        customer.delete()
        logger.info(f"Successfully deleted customer: {customer.name}")

        return Response({"message": "Customer successfully deleted"}, status=status.HTTP_200_OK)

    except ObjectDoesNotExist:
        logger.warning(f"Customer with ID {id} not found")
        return Response({"error": "Customer not found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error deleting customer with ID {id}: {str(e)}", exc_info=True)
        return Response({"error": "An unexpected error occurred"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    finally:
        if connection:
            logger.debug("Closing RouterOS API connection")
            connection.disconnect()


@api_view(['GET'])
#@permission_classes([IsAuthenticated])
def view_staff(request):
    """
    Retrieve a list of all staff members.
    """
    logger.info(f"User {request.user.username} accessed the staff list.")
    staff = User.objects.filter(is_staff=True)
    serializer = StaffSerializer(staff, many=True)
    return Response(serializer.data)

@api_view(['GET'])
#@permission_classes([IsAuthenticated])
def edit_staff_page(request, id):
    """
    Retrieve details of a specific staff member, including their permissions.
    """
    logger.info(f"User {request.user.username} accessed edit page for staff ID {id}.")
    staff = get_object_or_404(User, pk=id, is_staff=True)
    serializer = StaffSerializer(staff)
    return Response(serializer.data)

@api_view(['PUT'])
#@permission_classes([IsAuthenticated])
def update_staff(request, id):
    """
    Update details of a specific staff member.
    """
    logger.info(f"User {request.user.username} attempted to update staff ID {id}.")
    staff = get_object_or_404(User, pk=id, is_staff=True)
    serializer = StaffSerializer(staff, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        logger.info(f"Staff ID {id} updated successfully.")
        return Response(serializer.data)
    logger.warning(f"Failed to update staff ID {id}. Errors: {serializer.errors}")
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
# @permission_classes([IsAuthenticated])
def delete_staff(request, id):
    """
    Delete a specific staff member.
    """
    logger.info(f"User {request.user.username} attempted to delete staff ID {id}.")

    # Get the staff user
    staff = get_object_or_404(User, pk=id, is_staff=True)

    # Deleting the staff user
    staff.delete()
    logger.info(f"Staff ID {id} deleted successfully.")

    # Return a success response
    return Response({"detail": f"Staff ID {id} deleted successfully."}, status=status.HTTP_204_NO_CONTENT)

@api_view(['POST'])
#@permission_classes([IsAuthenticated])
def staff_signup(request):
    """
    Create a new staff member.
    """
    logger.info(f"User {request.user.username} attempted to create a new staff member.")
    serializer = StaffSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        logger.info(f"New staff member created with ID {user.id}.")
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    logger.warning(f"Failed to create new staff member. Errors: {serializer.errors}")
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def enable_customer_in_routeros(subscription):
    """
    Helper function to enable a customer in RouterOS.
    """
    api, connection = get_routeros_api()
    try:
        list_queues = api.get_resource('/queue/simple')
        bandwidth_value = subscription.bandwidth.rstrip('M')  # Remove 'M' if present
        bandwidth_format = f"{bandwidth_value}M/{bandwidth_value}M"
        list_queues.set(name=subscription.customer.name, max_limit=bandwidth_format)
        logger.info(f"Enabled customer in RouterOS: {subscription.customer.name}")
    except Exception as e:
        logger.error(f"Error enabling customer in RouterOS: {str(e)}")
        raise
    finally:
        connection.disconnect()


def disable_customer_in_routeros(subscription):
    """
    Helper function to disable a customer in RouterOS.
    """
    api, connection = get_routeros_api()
    try:
        list_queues = api.get_resource('/queue/simple')
        list_queues.set(name=subscription.customer.name, max_limit="1k/1k")
        logger.info(f"Disabled customer in RouterOS: {subscription.customer.name}")
    except Exception as e:
        logger.error(f"Error disabling customer in RouterOS: {str(e)}")
        raise
    finally:
        connection.disconnect()


@api_view(['GET'])
def process_subscriptions(request):
    """
    API view to process all active subscriptions that are due for payment.
    Checks if 30 days have passed since the last payment, then checks balance,
    deducts subscription amount if sufficient, and manages RouterOS accordingly.
    """
    try:
        with transaction.atomic():
            current_date = timezone.now().date()
            subscriptions = Subscription.objects.filter(
                is_active=True,
                end_date__lte=current_date
            ).select_related('customer')

            processed_count = 0
            disabled_count = 0

            for subscription in subscriptions:
                customer = subscription.customer

                if customer.balance >= subscription.subscription_amount:
                    # Sufficient balance, deduct subscription amount
                    customer.balance -= subscription.subscription_amount
                    customer.last_updated = timezone.now()
                    subscription.last_payment_date = timezone.now()

                    # Set end_date to 30 days from now
                    subscription.end_date = current_date + timezone.timedelta(days=30)

                    customer.save()
                    subscription.save()

                    # Enable customer in RouterOS
                    enable_customer_in_routeros(subscription)
                    processed_count += 1
                    logger.info(f"Processed subscription for customer: {customer.name}")
                else:
                    # Insufficient balance, disable subscription
                    subscription.is_active = False
                    subscription.end_date = current_date
                    subscription.save()

                    # Disable customer in RouterOS
                    disable_customer_in_routeros(subscription)
                    disabled_count += 1
                    logger.info(f"Disabled subscription for customer: {customer.name} due to insufficient balance")

        message = f"Processed {processed_count} subscriptions, disabled {disabled_count} subscriptions"
        logger.info(message)
        return Response({"message": message}, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error processing subscriptions: {str(e)}")
        return Response({"error": "An error occurred while processing subscriptions"},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


'''def get_access_token():
    """
    Fetch an access token from the M-Pesa API.

    Returns:
        str: The validated access token.

    Raises:
        requests.RequestException: If the API request fails.
        KeyError: If the response doesn't contain an access token.
    """
    try:
        consumer_key = settings.MPESA_CONSUMER_KEY
        consumer_secret = settings.MPESA_CONSUMER_SECRET
        api_url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"

        response = requests.get(api_url, auth=HTTPBasicAuth(consumer_key, consumer_secret))
        response.raise_for_status()  # Raise an exception for HTTP errors

        mpesa_access_token = response.json()
        validated_mpesa_access_token = mpesa_access_token["access_token"]

        logger.info("Successfully obtained M-Pesa access token")
        return validated_mpesa_access_token

    except requests.RequestException as e:
        logger.error(f"Failed to obtain M-Pesa access token: {str(e)}")
        raise
    except KeyError as e:
        logger.error(f"M-Pesa API response missing access token: {str(e)}")
        raise


@api_view(['POST'])
def register_c2b_url(request):
    """
    Register C2B URL with M-Pesa API.

    Returns:
        Response: Django Rest Framework Response object with the API response or error message.
    """
    try:
        access_token = get_access_token()
        api_url = "https://sandbox.safaricom.co.ke/mpesa/c2b/v1/registerurl"
        headers = {"Authorization": f"Bearer {access_token}"}
        payload = {
            "ShortCode": settings.MPESA_SHORTCODE,
            "ResponseType": "Cancelled",
            "ConfirmationURL": "https://0ca9-197-237-125-244.ngrok-free.app/api/confirmation/",
            "ValidationURL": "https://0ca9-197-237-125-244.ngrok-free.app/api/c2b/validation/"
        }

        logger.info("Sending C2B URL registration request to M-Pesa API")
        response = requests.post(api_url, json=payload, headers=headers)
        response.raise_for_status()

        logger.info("Successfully registered C2B URL with M-Pesa API")
        return Response(response.json(), status=status.HTTP_200_OK)
    except requests.RequestException as e:

        logger.error(f"Failed to register C2B URL with M-Pesa API: {str(e)}")

        logger.error(f"Response status code: {e.response.status_code if e.response else 'N/A'}")

        logger.error(f"Response content: {e.response.content if e.response else 'N/A'}")

        return Response({'error': 'Failed to communicate with M-Pesa API'}, status=status.HTTP_502_BAD_GATEWAY)
    except Exception as e:

        logger.exception(f"Unexpected error in register_c2b_url: {str(e)}")

        return Response({'error': 'An unexpected error occurred'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def c2b_confirmation(request):
    # Get the data from the request
    data = request.data
    print(data)
    # Process the confirmation data
    amount = data['TransAmount']
    transaction_id = data['TransID']
    phone_number = data['MSISDN']

    # Add  logic to handle the confirmation

    # Return a response to M-Pesa
    return Response({
        "ResultCode": 0,
        "ResultDesc": "Confirmation received successfully"
    })
'''