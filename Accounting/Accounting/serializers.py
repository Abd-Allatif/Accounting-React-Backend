from rest_framework import serializers
from django.contrib.auth import get_user_model,authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from .models import *

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('user_name','email','password','budget','password_reset_code')


class TokenObtainSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        identifier = attrs.get('identifier')
        password = attrs.get('password')

        # Check if identifier is email or user_name
        if '@' in identifier:
            user = authenticate(email=identifier, password=password)
        else:
            try:
                user = User.objects.get(user_name=identifier)
                if not user.check_password(password):
                    user = None
            except User.DoesNotExist:
                user = None

        if user is not None:
            refresh = RefreshToken.for_user(user)
            return {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': UserSerializer(user).data
            }
        else:
            raise serializers.ValidationError('Invalid credentials')



class TypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Type
        fields = '__all__'

class SuppliesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplies
        fields = '__all__'

class DispatchSupplySerializer(serializers.ModelSerializer):
    class Meta:
        model = DispatchSupply
        fields = '__all__'

class CustomerNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerName
        fields = '__all__'

class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = '__all__'

class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = '__all__'

class MoneyFundSerializer(serializers.ModelSerializer):
    class Meta:
        model = MoneyFund
        fields = '__all__'

class SellSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sell
        fields = '__all__'

class RecieptSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reciept
        fields = '__all__'

class MoneyIncomeSerializer(serializers.ModelSerializer):
    class Meta:
        model = MoneyIncome
        fields = '__all__'

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'

class InventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Inventory
        fields = '__all__'
