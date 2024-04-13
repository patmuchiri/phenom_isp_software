from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Customer

class CustomerSignupForm(UserCreationForm):
    subscription = forms.BooleanField(required=False)
    last_payment = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    name = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Name'}))
    phone = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Phone Number'}))
    class Meta:
        model = User
        fields = ['username','name', 'email', 'phone','subscription','last_payment','password','password2',]


class Signin_form(forms.Form):
    username = forms.CharField(label='Username',max_length=30)
    password = forms.CharField(label='Password',max_length=30,widget=forms.PasswordInput(attrs={"type":"password"}))