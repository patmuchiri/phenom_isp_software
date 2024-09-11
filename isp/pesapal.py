
def get_pesapal_token():
    url = "https://pay.pesapal.com/v3/api/Auth/RequestToken"
    consumer_key = os.getenv('CONSUMER_KEY')
    consumer_secret = os.getenv('CONSUMER_SECRET')
    if not consumer_key or not consumer_secret:
        print("Environment variables not set properly")
        raise ValueError("Missing CONSUMER_KEY or CONSUMER_SECRET")
    #print("Consumer Key:", consumer_key)
    #print("Consumer Secret:", consumer_secret)
    body = {
        "consumer_key": f"{consumer_key}",
        "consumer_secret": f"{consumer_secret}",
    }
    response = requests.post(url, json=body,headers={'Content-Type': 'application/json', 'Accept': 'application/json'}).json()
    print(response)
    token = response['token']
    return token


@api_view(['POST'])
def initiate_pesapal_payments(request):
    customer_id = request.data.get('customer_id')
    customer = get_object_or_404(Customer, id=customer_id)
    amount = customer.subscription_amount
    # Generate a unique merchant reference
    merchant_reference = str(uuid.uuid4())
    # Prepare the payload for Pesapal API
    payload = {
        "id": merchant_reference,
        "currency": "KES",
        "amount": float(customer.subscription_amount),
        "description": f"Wi-Fi Subscription payment for {customer.name}",
        "callback_url": "https://payment-coral-one.vercel.app/callback",
        "notification_id": "670b6eeb-289d-4a90-9372-dcefa6f71d44",
        "billing_address": {
            "phone_number": customer.phone,
            "first_name": customer.name.split()[0],
        }
    }
    token = get_pesapal_token()

    # Make a request to Pesapal API
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    response = requests.post(
        f"https://pay.pesapal.com/v3/api/Transactions/SubmitOrderRequest",
        json=payload,
        headers=headers
    )

    if response.status_code == 200:
        pesapal_response = response.json()

        # Create a new Payment object
        payment = Payment.objects.create(
            customer=customer,
            amount=amount,
            pesapal_transaction_tracking_id=pesapal_response['order_tracking_id'],
            pesapal_merchant_reference=merchant_reference,
            status='PENDING'
        )

        serializer = PaymentSerializer(payment)
        return Response({
            'payment': serializer.data,
            'redirect_url': pesapal_response['redirect_url']
        }, status=status.HTTP_201_CREATED)
    else:
        return Response({'error': 'Failed to initiate payment'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def pesapal_callback(request):
    order_tracking_id = request.data.get('OrderTrackingId')
    merchant_reference = request.data.get('MerchantReference')
    print(order_tracking_id)
    payment = get_object_or_404(Payment, pesapal_transaction_tracking_id=order_tracking_id,
                                pesapal_merchant_reference=merchant_reference)
    token = get_pesapal_token()

    # Make a request to Pesapal API to get the transaction status
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }
    response = requests.get(
        f"https://pay.pesapal.com/v3/api/Transactions/GetTransactionStatus?orderTrackingId={order_tracking_id}",
        headers=headers
    )

    if response.status_code == 200:
        pesapal_response = response.json()
        print(pesapal_response)
        payment.status = pesapal_response['payment_status_description']

        if payment.status == 'Completed':
            if payment.customer.subscription:
                payment.customer.balance += int(pesapal_response['amount'])
                payment.status = 'COMPLETED'
                payment.customer.save()
            else:
                payment.customer.last_payment = timezone.now()
                payment.customer.subscription = True
                payment.customer.balance = int(payment.customer.subscription_amount) - int(pesapal_response['amount'])
                payment.status = 'COMPLETED'

                payment.customer.save()

        payment.save()
        print(payment.customer.balance)

        serializer = PaymentSerializer(payment)
        return Response(serializer.data)
    else:
        return Response({'error': 'Failed to get transaction status'}, status=status.HTTP_400_BAD_REQUEST)
