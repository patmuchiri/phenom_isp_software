from django.contrib.auth.models import AbstractUser, User
from django.db import models

# Create your models here.
class Customer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=25)
    email = models.EmailField(max_length=100)
    subscription = models.BooleanField(default=False)
    last_updated = models.DateTimeField(auto_now_add=True)
    last_payment = models.DateTimeField()

    def __str__(self):
        return self.name