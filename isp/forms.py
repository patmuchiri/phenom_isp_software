from django import forms
from .models import Customer

class CustomerSignupForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['name', 'email', 'phone', 'password','subscription','last_payment']
        widgets = {
            'last_payment':forms.DateInput(format=('%m/%d/%Y'), attrs={'type':'date'}),
        }