from celery import shared_task
from .models import Customer
from django.utils import timezone



@shared_task
def check_subscription_status():
    customers = Customer.objects.all()
    for customer in customers:
        days_since_last_payment = (timezone.now() - customer.last_payment).days
        if days_since_last_payment > 31:
            print("Deactivated")
            customer.subscription = False
            customer.save()
@shared_task
def activate_subscription():
    customers = Customer.objects.filter(subscription=False)
    for customer in customers:
        print(customer.last_payment)
        days_since_last_payment = (timezone.now() - customer.last_payment).days
        if days_since_last_payment < 31:
            print("Activated")
            customer.subscription = True
            customer.save()