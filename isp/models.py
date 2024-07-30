from django.contrib.auth.models import AbstractUser, User
from django.db import models

# Create your models here.
class Customer(models.Model):
    name = models.CharField(max_length=100,unique=True)
    router_ip_address = models.GenericIPAddressField(default='192.168.88')
    bandwith = models.CharField(max_length=7)
    phone = models.CharField(max_length=25)
    subscription_amount = models.IntegerField(default=1)
    email = models.EmailField(max_length=100)
    subscription = models.BooleanField(default=False)
    last_updated = models.DateTimeField(auto_now_add=True)
    last_payment = models.DateTimeField()
    balance = models.DecimalField(max_digits=7, decimal_places=2, default=0)

    def __str__(self):
        return self.name


class Payment(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='payments')
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
        return f"{self.customer.name} - {self.amount} - {self.status}"