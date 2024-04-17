from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User, Permission

from .models import Customer

class CustomerSignupForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = "__all__"
        widgets = {
            'last_payment':forms.DateInput(attrs={'type': 'date',"min":"2022-01-01"}),
            "router_ip_address":forms.TextInput(attrs={'type':'ipv4'})
        }





class Signin_form(forms.Form):
    username = forms.CharField(label='Username',max_length=30)
    password = forms.CharField(label='Password',max_length=30,widget=forms.PasswordInput(attrs={"type":"password"}))



class StaffSignupForm(UserCreationForm):
    permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='Permissions'
    )

    class Meta:
        model = User
        fields = ('username','first_name', 'email', 'password1', 'password2','is_superuser','is_staff','permissions')


    def __init__(self, *args, **kwargs):
        super(StaffSignupForm, self).__init__(*args, **kwargs)
        self.fields['permissions'].queryset = Permission.objects.all()



class StaffUpdateForm(forms.ModelForm):
    permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='Permissions'
    )

    class Meta:
        model = User
        fields = (
            'username', 'first_name', 'last_name', 'email', 'is_superuser', 'is_staff', 'permissions'
        )

    def __init__(self, *args, **kwargs):
        super(StaffUpdateForm, self).__init__(*args, **kwargs)
        # Get the instance (user being updated)
        instance = kwargs.get('instance')
        if instance:
            # If instance exists, set initial permissions
            self.fields['permissions'].initial = instance.user_permissions.all()