# views.py


from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from .tasks import check_subscription_status
from .forms import CustomerSignupForm
from .models import Customer


def signup(request):
    if request.method == 'POST':
        form = CustomerSignupForm(request.POST)
        if form.is_valid():

            password = form.cleaned_data['password']
            hashed_password = make_password(password)
            form.instance.password = hashed_password
            form.save()
            # Redirect to a success page or login page
            return HttpResponse('created')
    else:
        form = CustomerSignupForm()
    return render(request, 'signup.html', {'form': form})




def check_subscription_view(request):

    return HttpResponse("Subscription status check task has been scheduled to run after 5 minutes.")
