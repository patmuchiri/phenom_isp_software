import routeros_api
from celery import shared_task
import os
from .models import Customer
from django.utils import timezone
connection = routeros_api.RouterOsApiPool(os.getenv('ROUTER_IP'), os.getenv('ROUTER_USERNAME'), os.getenv('ROUTER_PASSWORD'), plaintext_login=True)
api = connection.get_api()
list_queues = api.get_resource('/queue/simple')
import clicksend_client
from clicksend_client import SmsMessage
from clicksend_client.rest import ApiException
# Configure HTTP basic authorization: BasicAuth Clicksend
configuration = clicksend_client.Configuration()
configuration.username = os.getenv('CLICKSEND_USERNAME')
configuration.password = os.getenv('CLICKSEND_PASSWORD')
api_instance = clicksend_client.SMSApi(clicksend_client.ApiClient(configuration))



@shared_task
def check_subscription_status():
    customers = Customer.objects.all()
    for customer in customers:
        days_since_last_payment = (timezone.now() - customer.last_payment).days
        if days_since_last_payment > 31:
            customer.subscription = False
            list_queues.set(name=customer.name,max_limit="1k/1k")
            customer.save()
@shared_task
def activate_subscription():
    customers = Customer.objects.filter(subscription=False)
    for customer in customers:
        days_since_last_payment = (timezone.now() - customer.last_payment).days
        if days_since_last_payment < 31:

            customer.subscription = True
            list_queues.set(name=customer.name,max_limit=customer.bandwith.upper())
            customer.save()


@shared_task
def remind_subscription():
    customers = Customer.objects.filter(subscription=True)
    for customer in customers:
        days_since_last_payment = (timezone.now() - customer.last_payment).days
        if days_since_last_payment == 28:
            sms_message = SmsMessage(source="php",
                                     body="Your subscription has 3 more days left",
                                     to="+254712240197",
                                     schedule=1436874701)

            sms_messages = clicksend_client.SmsMessageCollection(messages=[sms_message])

            try:
                # Send sms message(s)
                api_response = api_instance.sms_send_post(sms_messages)
                print(api_response)
            except ApiException as e:
                print("Exception when calling SMSApi->sms_send_post: %s\n" % e)


