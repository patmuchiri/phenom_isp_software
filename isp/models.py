from django.db import models

# Create your models here.
class Customer(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=25)
    password = models.CharField(max_length=100)
    email = models.CharField(max_length=100)
    subscription = models.BooleanField()
    last_updated = models.DateTimeField(auto_now_add=True)
    last_payment = models.DateTimeField()

    def __str__(self):
        return self.name