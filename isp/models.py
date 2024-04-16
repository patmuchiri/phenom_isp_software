from django.contrib.auth.models import AbstractUser, User
from django.db import models

# Create your models here.
class Customer(models.Model):
    name = models.CharField(max_length=100)
    router_ip_address = models.GenericIPAddressField()
    bandwith = models.DecimalField(max_length=5,decimal_places=2,max_digits=5)
    phone = models.CharField(max_length=25)
    email = models.EmailField(max_length=100)
    subscription = models.BooleanField(default=False)
    last_updated = models.DateTimeField(auto_now_add=True)
    last_payment = models.DateTimeField()

    def __str__(self):
        return self.name