from django.contrib.auth.models import Permission, User
from rest_framework import serializers

from isp.models import Customer, Payment, Subscription


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = '__all__'


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = '__all__'


class StaffSerializer(serializers.ModelSerializer):
    permissions = serializers.PrimaryKeyRelatedField(
        queryset=Permission.objects.all(),
        many=True,
        required=False
    )
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = (
        'id', 'username', 'first_name', 'last_name', 'email', 'is_superuser', 'is_staff', 'permissions', 'password')

    def create(self, validated_data):
        permissions = validated_data.pop('permissions', [])
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.is_staff = True  # Ensure the user is marked as staff
        user.save()
        user.user_permissions.set(permissions)
        return user

    def update(self, instance, validated_data):
        permissions = validated_data.pop('permissions', None)
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        if permissions is not None:
            instance.user_permissions.set(permissions)
        return instance
