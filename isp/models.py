from django.contrib.auth.models import AbstractUser, User
from django.db import models


class Customer(models.Model):
    name = models.CharField(max_length=100, unique=True)
    phone = models.CharField(max_length=25)
    email = models.EmailField(max_length=100)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Subscription(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='subscriptions')
    router_ip_address = models.GenericIPAddressField(default='192.168.88.1')
    bandwidth = models.CharField(max_length=7)
    subscription_amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    last_payment_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.customer.name} - {self.bandwidth} - {'Active' if self.is_active else 'Inactive'}"


class Payment(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='payments')
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    pesapal_transaction_tracking_id = models.CharField(max_length=100, unique=True)
    pesapal_merchant_reference = models.CharField(max_length=100, unique=True)
    payment_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('INVALID', 'Invalid')
    ], default='PENDING')

    def __str__(self):
        return f"{self.customer.name} - {self.subscription.bandwidth} - {self.amount} - {self.status}"
