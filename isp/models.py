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

    def __str__(self):
        return self.name
