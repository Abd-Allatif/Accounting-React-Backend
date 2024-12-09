import pandas as pd
import logging
from django.http import HttpResponse
from django.conf import settings
from .models import *
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate,Paragraph,PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import *
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework.decorators import api_view,permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status

logger = logging.getLogger(__name__)

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = TokenObtainSerializer

@api_view(['POST'])
def logout(request):
    try:
        refresh_token = request.data["refresh"]
        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response(status=status.HTTP_205_RESET_CONTENT)
    except Exception as e:
        return Response(status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    username = request.data.get('username')
    email = request.data.get('email')
    password = request.data.get('password')

    if User.objects.filter(user_name=username).exists():
        return Response({'error': 'Username already exists'}, status=status.HTTP_400_BAD_REQUEST)

    if User.objects.filter(email=email).exists():
        return Response({'error': 'Email already exists'}, status=status.HTTP_400_BAD_REQUEST)

    user = User(user_name=username,email=email,budget = 0)
    user.set_password(password)
    user.save()

    user_serializer = UserSerializer(user)
    return Response(user_serializer.data, status=status.HTTP_201_CREATED)

@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password(request):
    username = request.data.get('username')
    email = request.data.get('email')
    reset_code = request.data.get('reset_code')
    new_password = request.data.get('new_password')

    try:
        user = User.objects.get(user_name=username,email = email,password_reset_code = reset_code)
        user.set_password(new_password)
        user.save()
       # Generate new tokens
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        return Response({
            'message': 'Password reset successful',
            'access_token': access_token,
            'refresh_token': refresh_token
        }, status=status.HTTP_200_OK)
    except User.DoesNotExist:
        return Response({'error': 'Invalid username, email, or reset code'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def setupAccount(request,username):
    issatup = request.data.get('issatup')
    budget = int(request.data.get('budget'))
    types = request.data.get('types',[])
    customernames = request.data.get('customers',[])
    employees = request.data.get('employees',[])

    try:
        user = User.objects.get(user_name = username)
        user.budget = budget
        user.issatup = issatup
        user.save()

       
        if types:
            for type_name in types:
                Type.objects.get_or_create(user=user, type=type_name)
               

        # Save customer names
        if customernames:
            for customer in customernames:
                CustomerName.objects.create(user=user, customer_name=customer)

        # Save employees
        if employees:
            for employee in employees:
                Employee.objects.create(user=user, employee_name=employee)
        
        return Response({'message': 'Setup successful!'}, status=status.HTTP_200_OK)
    except User.DoesNotExist:
        logger.error("User not found for setup")
        return Response({'error': 'User not found'}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"SetupAccount error: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




@api_view(['GET', 'POST'])
def get_user_data(request, username):
    if request.method == 'GET':
        try:
            user = User.objects.get(user_name=username)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        # Fetch related data
        supplies = Supplies.objects.filter(user=user)
        customers = Customer.objects.filter(user=user)
        inventories = Inventory.objects.filter(user=user)
        types = Type.objects.filter(user=user)
        dispatched = DispatchSupply.objects.filter(user=user)
        customer_names = CustomerName.objects.filter(user=user)
        employees = Employee.objects.filter(user=user)
        money_funds = MoneyFund.objects.filter(user=user)
        sells = Sell.objects.filter(user=user)
        reciepts = Reciept.objects.filter(user=user)
        money_incomes = MoneyIncome.objects.filter(user=user)
        payments = Payment.objects.filter(user=user)

        # Serialize data
        user_serializer = UserSerializer(user)
        supplies_serializer = SuppliesSerializer(supplies, many=True)
        customers_serializer = CustomerSerializer(customers, many=True)
        inventories_serializer = InventorySerializer(inventories, many=True)
        type_serializer = TypeSerializer(types, many=True)
        dispatched_serializer = DispatchSupplySerializer(dispatched, many=True)
        customer_name_serializer = CustomerNameSerializer(customer_names, many=True)
        employee_serializer = EmployeeSerializer(employees, many=True)
        money_fund_serializer = MoneyFundSerializer(money_funds, many=True)
        sell_serializer = SellSerializer(sells, many=True)
        reciept_serializer = RecieptSerializer(reciepts, many=True)
        money_income_serializer = MoneyIncomeSerializer(money_incomes, many=True)
        payment_serializer = PaymentSerializer(payments, many=True)

        # Structure the response
        data = {
            'user': user_serializer.data,
            'employees': employee_serializer.data,
            'customer_names': customer_name_serializer.data,
            'types': type_serializer.data,
            'supplies': supplies_serializer.data,
            'Dispatched_Supplies': dispatched_serializer.data,
            'sells': sell_serializer.data,
            'reciepts': reciept_serializer.data,
            'customers': customers_serializer.data,
            'money_incomes': money_income_serializer.data,
            'payments': payment_serializer.data,
            'money_funds': money_fund_serializer.data,
            'inventories': inventories_serializer.data,
        }

        return Response(data)

    elif request.method == 'POST':
        try:
            user = User.objects.get(user_name=username)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        if 'employees' in request.data:
            employee_data_list = request.data['employees']
            for employee_data in employee_data_list:
                employee_data['user'] = user.user_name
                employee_serializer = EmployeeSerializer(data=employee_data)
                if employee_serializer.is_valid():
                    employee_serializer.save()
                else:
                    return Response(employee_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        if 'customer_names' in request.data:
            customer_name_data_list = request.data['customer_names']
            for customer_name_data in customer_name_data_list:
                customer_name_data['user'] = user.user_name
                customer_name_serializer = CustomerNameSerializer(data=customer_name_data)
                if customer_name_serializer.is_valid():
                    customer_name_serializer.save()
                else:
                    return Response(customer_name_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        if 'types' in request.data:
            type_data_list = request.data['types']
            for type_data in type_data_list:
                type_data['user'] = user.user_name
                type_serializer = TypeSerializer(data=type_data)
                if type_serializer.is_valid():
                    type_serializer.save()
                else:
                    return Response(type_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        if 'supplies' in request.data:
            supply_data_list = request.data['supplies']
            for supply_data in supply_data_list:
                supply_data['user'] = user.user_name
                supplies_serializer = SuppliesSerializer(data=supply_data)
                if supplies_serializer.is_valid():
                    supplies_serializer.save()
                else:
                    return Response(supplies_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        if 'Dispatched_Supplies' in request.data:
            dispatched_supply_data_list = request.data['Dispatched_Supplies']
            for dispatched_supply_data in dispatched_supply_data_list:
                dispatched_supply_data['user'] = user.user_name
                dispatched_serializer = DispatchSupplySerializer(data=dispatched_supply_data)
                if dispatched_serializer.is_valid():
                    dispatched_serializer.save()
                else:
                    return Response(dispatched_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        if 'sells' in request.data:
            sell_data_list = request.data['sells']
            for sell_data in sell_data_list:
                sell_data['user'] = user.user_name
                try:
                    supply_instance = Supplies.objects.get(supply_name=sell_data['supply'])
                    sell_data['supply'] = supply_instance.supply_name
                except Supplies.DoesNotExist:
                    return Response({'error': f'Supply {sell_data["supply"]} not found'}, status=status.HTTP_404_NOT_FOUND)

                sell_serializer = SellSerializer(data=sell_data)
                if sell_serializer.is_valid():
                    sell_serializer.save()
                else:
                    return Response(sell_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        if 'reciepts' in request.data:
            reciept_data_list = request.data['reciepts']
            for reciept_data in reciept_data_list:
                reciept_data['user'] = user.user_name
                reciept_serializer = RecieptSerializer(data=reciept_data)
                if reciept_serializer.is_valid():
                    reciept_serializer.save()
                else:
                    return Response(reciept_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        if 'customers' in request.data:
            customer_data_list = request.data['customers']
            for customer_data in customer_data_list:
                customer_data['user'] = user.user_name
                customer_serializer = CustomerSerializer(data=customer_data)
                if customer_serializer.is_valid():
                    customer_serializer.save()
                else:
                    return Response(customer_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        if 'money_incomes' in request.data:
            money_income_data_list = request.data['money_incomes']
            for money_income_data in money_income_data_list:
                money_income_data['user'] = user.user_name
                money_income_serializer = MoneyIncomeSerializer(data=money_income_data)
                if money_income_serializer.is_valid():
                    money_income_serializer.save()
                else:
                    return Response(money_income_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        if 'payments' in request.data:
            payment_data_list = request.data['payments']
            for payment_data in payment_data_list:
                payment_data['user'] = user.user_name
                payment_serializer = PaymentSerializer(data=payment_data)
                if payment_serializer.is_valid():
                    payment_serializer.save()
                else:
                    return Response(payment_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        if 'money_funds' in request.data:
            money_fund_data_list = request.data['money_funds']
            for money_fund_data in money_fund_data_list:
                money_fund_data['user'] = user.user_name
                money_fund_serializer = MoneyFundSerializer(data=money_fund_data)
                if money_fund_serializer.is_valid():
                    money_fund_serializer.save()
                else:
                    return Response(money_fund_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        if 'inventories' in request.data:
            inventory_data_list = request.data['inventories']
            for inventory_data in inventory_data_list:
                inventory_data['user'] = user.user_name
                inventory_serializer = InventorySerializer(data=inventory_data)
                if inventory_serializer.is_valid():
                    inventory_serializer.save()
                else:
                    return Response(inventory_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        return Response({'message': 'Data added successfully'}, status=status.HTTP_201_CREATED)



@api_view(['PUT', 'DELETE'])
def modify_user_data(request, username):
    try:
        user = User.objects.get(user_name=username)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'PUT':
    # Handle PUT requests (updating data)
        if 'employees' in request.data:
            employee_data_list = request.data['employees']
            for employee_data in employee_data_list:
                employee_data['user'] = user.user_name
                try:
                    employee_instance = Employee.objects.get(employee_name=employee_data['employee_name'])
                    employee_serializer = EmployeeSerializer(employee_instance, data=employee_data)
                    if employee_serializer.is_valid():
                        employee_serializer.save()
                    else:
                        return Response(employee_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                except Employee.DoesNotExist:
                    return Response({'error': 'Employee not found'}, status=status.HTTP_404_NOT_FOUND)

        if 'customer_names' in request.data:
            customer_name_data_list = request.data['customer_names']
            for customer_name_data in customer_name_data_list:
                customer_name_data['user'] = user.user_name
                try:
                    customer_name_instance = CustomerName.objects.get(customer_name=customer_name_data['customer_name'])
                    customer_name_serializer = CustomerNameSerializer(customer_name_instance, data=customer_name_data)
                    if customer_name_serializer.is_valid():
                        customer_name_serializer.save()
                    else:
                        return Response(customer_name_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                except CustomerName.DoesNotExist:
                    return Response({'error': 'Customer name not found'}, status=status.HTTP_404_NOT_FOUND)

        if 'types' in request.data:
            type_data_list = request.data['types']
            for type_data in type_data_list:
                type_data['user'] = user.user_name
                try:
                    type_instance = Type.objects.get(type=type_data['type'])
                    type_serializer = TypeSerializer(type_instance, data=type_data)
                    if type_serializer.is_valid():
                        type_serializer.save()
                    else:
                        return Response(type_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                except Type.DoesNotExist:
                    return Response({'error': 'Type not found'}, status=status.HTTP_404_NOT_FOUND)

        if 'supplies' in request.data:
            supply_data_list = request.data['supplies']
            for supply_data in supply_data_list:
                supply_data['user'] = user.user_name
                try:
                    supply_instance = Supplies.objects.get(supply_name=supply_data['supply_name'])
                    supplies_serializer = SuppliesSerializer(supply_instance, data=supply_data)
                    if supplies_serializer.is_valid():
                        supplies_serializer.save()
                    else:
                        return Response(supplies_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                except Supplies.DoesNotExist:
                    return Response({'error': 'Supply not found'}, status=status.HTTP_404_NOT_FOUND)

        if 'Dispatched_Supplies' in request.data:
            dispatched_supply_data_list = request.data['Dispatched_Supplies']
            for dispatched_supply_data in dispatched_supply_data_list:
                dispatched_supply_data['user'] = user.user_name
                try:
                    dispatched_instance = DispatchSupply.objects.get(id=dispatched_supply_data['id'])
                    dispatched_serializer = DispatchSupplySerializer(dispatched_instance, data=dispatched_supply_data)
                    if dispatched_serializer.is_valid():
                        dispatched_serializer.save()
                    else:
                        return Response(dispatched_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                except DispatchSupply.DoesNotExist:
                    return Response({'error': 'Dispatched supply not found'}, status=status.HTTP_404_NOT_FOUND)

        if 'sells' in request.data:
            sell_data_list = request.data['sells']
            for sell_data in sell_data_list:
                sell_data['user'] = user.user_name
                try:
                    supply_instance = Supplies.objects.get(supply=sell_data['supply'])
                    sell_data['supply'] = supply_instance.supply_name
                    sell_instance = Sell.objects.get(sell_id=sell_data['id'])
                    sell_serializer = SellSerializer(sell_instance, data=sell_data)
                    if sell_serializer.is_valid():
                        sell_serializer.save()
                    else:
                        return Response(sell_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                except (Supplies.DoesNotExist, Sell.DoesNotExist):
                    return Response({'error': 'Supply or Sell not found'}, status=status.HTTP_404_NOT_FOUND)

        if 'reciepts' in request.data:
            reciept_data_list = request.data['reciepts']
            for reciept_data in reciept_data_list:
                reciept_data['user'] = user.user_name
                try:
                    reciept_instance = Reciept.objects.get(id=reciept_data['id'])
                    reciept_serializer = RecieptSerializer(reciept_instance, data=reciept_data)
                    if reciept_serializer.is_valid():
                        reciept_serializer.save()
                    else:
                        return Response(reciept_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                except Reciept.DoesNotExist:
                    return Response({'error': 'Reciept not found'}, status=status.HTTP_404_NOT_FOUND)

        if 'customers' in request.data:
            customer_data_list = request.data['customers']
            for customer_data in customer_data_list:
                customer_data['user'] = user.user_name
                try:
                    customer_instance = Customer.objects.get(id=customer_data['id'])
                    customer_serializer = CustomerSerializer(customer_instance, data=customer_data)
                    if customer_serializer.is_valid():
                        customer_serializer.save()
                    else:
                        return Response(customer_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                except Customer.DoesNotExist:
                    return Response({'error': 'Customer not found'}, status=status.HTTP_404_NOT_FOUND)

        if 'money_incomes' in request.data:
            money_income_data_list = request.data['money_incomes']
            for money_income_data in money_income_data_list:
                money_income_data['user'] = user.user_name
                try:
                    money_income_instance = MoneyIncome.objects.get(id=money_income_data['id'])
                    money_income_serializer = MoneyIncomeSerializer(money_income_instance, data=money_income_data)
                    if money_income_serializer.is_valid():
                        money_income_serializer.save()
                    else:
                        return Response(money_income_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                except MoneyIncome.DoesNotExist:
                    return Response({'error': 'Money income not found'}, status=status.HTTP_404_NOT_FOUND)

        if 'payments' in request.data:
            payment_data_list = request.data['payments']
            for payment_data in payment_data_list:
                payment_data['user'] = user.user_name
                try:
                    payment_instance = Payment.objects.get(id=payment_data['id'])
                    payment_serializer = PaymentSerializer(payment_instance, data=payment_data)
                    if payment_serializer.is_valid():
                        payment_serializer.save()
                    else:
                        return Response(payment_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                except Payment.DoesNotExist:
                    return Response({'error': 'Payment not found'}, status=status.HTTP_404_NOT_FOUND)

        if 'money_funds' in request.data:
            money_fund_data_list = request.data['money_funds']
            for money_fund_data in money_fund_data_list:
                money_fund_data['user'] = user.user_name
                try:
                    money_fund_instance = MoneyFund.objects.get(id=money_fund_data['id'])
                    money_fund_serializer = MoneyFundSerializer(money_fund_instance, data=money_fund_data)
                    if money_fund_serializer.is_valid():
                        money_fund_serializer.save()
                    else:
                        return Response(money_fund_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                except MoneyFund.DoesNotExist:
                    return Response({'error': 'Money fund not found'}, status=status.HTTP_404_NOT_FOUND)

        if 'inventories' in request.data:
            inventory_data_list = request.data['inventories']
            for inventory_data in inventory_data_list:
                inventory_data['user'] = user.user_name
                try:
                    inventory_instance = Inventory.objects.get(id=inventory_data['id'])
                    inventory_serializer = InventorySerializer(inventory_instance, data=inventory_data)
                    if inventory_serializer.is_valid():
                        inventory_serializer.save()
                    else:
                        return Response(inventory_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                except Inventory.DoesNotExist:
                    return Response({'error': 'Inventory not found'}, status=status.HTTP_404_NOT_FOUND)

        return Response({'message': 'Data updated successfully'}, status=status.HTTP_200_OK)

        
    elif request.method == 'DELETE':
        # Handle DELETE requests (deleting data)
        if 'employees' in request.data:
            employee_data_list = request.data['employees']
            for employee_data in employee_data_list:
                try:
                    employee_instance = Employee.objects.get(employee_name=employee_data['employee_name'])
                    employee_instance.delete()
                except Employee.DoesNotExist:
                    return Response({'error': 'Employee not found'}, status=status.HTTP_404_NOT_FOUND)

        if 'customer_names' in request.data:
            customer_name_data_list = request.data['customer_names']
            for customer_name_data in customer_name_data_list:
                try:
                    customer_name_instance = CustomerName.objects.get(customer_name=customer_name_data['customer_name'])
                    customer_name_instance.delete()
                except CustomerName.DoesNotExist:
                    return Response({'error': 'Customer name not found'}, status=status.HTTP_404_NOT_FOUND)

        if 'types' in request.data:
            type_data_list = request.data['types']
            for type_data in type_data_list:
                try:
                    type_instance = Type.objects.get(type=type_data['type'])
                    type_instance.delete()
                except Type.DoesNotExist:
                    return Response({'error': 'Type not found'}, status=status.HTTP_404_NOT_FOUND)

        if 'supplies' in request.data:
            supply_data_list = request.data['supplies']
            for supply_data in supply_data_list:
                try:
                    supply_instance = Supplies.objects.get(id=supply_data['id'])
                    supply_instance.delete()
                except Supplies.DoesNotExist:
                    return Response({'error': 'Supply not found'}, status=status.HTTP_404_NOT_FOUND)

        if 'Dispatched_Supplies' in request.data:
            dispatched_supply_data_list = request.data['Dispatched_Supplies']
            for dispatched_supply_data in dispatched_supply_data_list:
                try:
                    dispatched_instance = DispatchSupply.objects.get(id=dispatched_supply_data['id'])
                    dispatched_instance.delete()
                except DispatchSupply.DoesNotExist:
                    return Response({'error': 'Dispatched supply not found'}, status=status.HTTP_404_NOT_FOUND)

        if 'sells' in request.data:
            sell_data_list = request.data['sells']
            for sell_data in sell_data_list:
                try:
                    sell_instance = Sell.objects.get(id=sell_data['id'])
                    sell_instance.delete()
                except Sell.DoesNotExist:
                    return Response({'error': 'Sell not found'}, status=status.HTTP_404_NOT_FOUND)

        if 'reciepts' in request.data:
            reciept_data_list = request.data['reciepts']
            for reciept_data in reciept_data_list:
                try:
                    reciept_instance = Reciept.objects.get(id=reciept_data['id'])
                    reciept_instance.delete()
                except Reciept.DoesNotExist:
                    return Response({'error': 'Reciept not found'}, status=status.HTTP_404_NOT_FOUND)

        if 'customers' in request.data:
            customer_data_list = request.data['customers']
            for customer_data in customer_data_list:
                try:
                    customer_instance = Customer.objects.get(id=customer_data['id'])
                    customer_instance.delete()
                except Customer.DoesNotExist:
                    return Response({'error': 'Customer not found'}, status=status.HTTP_404_NOT_FOUND)

        if 'money_incomes' in request.data:
            money_income_data_list = request.data['money_incomes']
            for money_income_data in money_income_data_list:
                try:
                    money_income_instance = MoneyIncome.objects.get(id=money_income_data['id'])
                    money_income_instance.delete()
                except MoneyIncome.DoesNotExist:
                    return Response({'error': 'Money income not found'}, status=status.HTTP_404_NOT_FOUND)

        if 'payments' in request.data:
            payment_data_list = request.data['payments']
            for payment_data in payment_data_list:
                try:
                    payment_instance = Payment.objects.get(id=payment_data['id'])
                    payment_instance.delete()
                except Payment.DoesNotExist:
                    return Response({'error': 'Payment not found'}, status=status.HTTP_404_NOT_FOUND)

        if 'money_funds' in request.data:
            money_fund_data_list = request.data['money_funds']
            for money_fund_data in money_fund_data_list:
                try:
                    money_fund_instance = MoneyFund.objects.get(id=money_fund_data['id'])
                    money_fund_instance.delete()
                except MoneyFund.DoesNotExist:
                    return Response({'error': 'Money fund not found'}, status=status.HTTP_404_NOT_FOUND)

        if 'inventories' in request.data:
            inventory_data_list = request.data['inventories']
            for inventory_data in inventory_data_list:
                try:
                    inventory_instance = Inventory.objects.get(id=inventory_data['id'])
                    inventory_instance.delete()
                except Inventory.DoesNotExist:
                    return Response({'error': 'Inventory not found'}, status=status.HTTP_404_NOT_FOUND)

        return Response({'message': 'Data deleted successfully'}, status=status.HTTP_200_OK)

#--------------------------------------------------------------------------
# Expoting Data

def export_all_data_excel(request, username):
    user = User.objects.get(user_name=username)

    # Get data from all models related to the user
    user_data = pd.DataFrame(list(User.objects.filter(user_name=user.user_name).values()))
    type_data = pd.DataFrame(list(Type.objects.filter(user=user).values()))
    supplies_data = pd.DataFrame(list(Supplies.objects.filter(user=user).values()))
    Dispatch_data = pd.DataFrame(list(DispatchSupply.objects.filter(user=user).values()))
    customer_name_data = pd.DataFrame(list(CustomerName.objects.filter(user=user).values()))
    customer_data = pd.DataFrame(list(Customer.objects.filter(user=user).values()))
    employee_data = pd.DataFrame(list(Employee.objects.filter(user=user).values()))
    money_fund_data = pd.DataFrame(list(MoneyFund.objects.filter(user=user).values()))
    sell_data = pd.DataFrame(list(Sell.objects.filter(user=user).values()))
    reciept_data = pd.DataFrame(list(Reciept.objects.filter(user=user).values()))
    money_income_data = pd.DataFrame(list(MoneyIncome.objects.filter(user=user).values()))
    payment_data = pd.DataFrame(list(Payment.objects.filter(user=user).values()))
    inventory_data = pd.DataFrame(list(Inventory.objects.filter(user=user).values()))

    # Create a Pandas Excel writer using openpyxl as the engine.
    with pd.ExcelWriter('all_data.xlsx', engine='openpyxl') as writer:
        # Write each DataFrame to a specific sheet
        user_data.to_excel(writer, sheet_name='User', index=False)
        type_data.to_excel(writer, sheet_name='Type', index=False)
        supplies_data.to_excel(writer, sheet_name='Supplies', index=False)
        Dispatch_data.to_excel(writer, sheet_name='DispatchSupply', index=False)
        customer_name_data.to_excel(writer, sheet_name='CustomerName', index=False)
        customer_data.to_excel(writer, sheet_name='Customer', index=False)
        employee_data.to_excel(writer, sheet_name='Employee', index=False)
        money_fund_data.to_excel(writer, sheet_name='MoneyFund', index=False)
        sell_data.to_excel(writer, sheet_name='Sell', index=False)
        reciept_data.to_excel(writer, sheet_name='Reciept', index=False)
        money_income_data.to_excel(writer, sheet_name='MoneyIncome', index=False)
        payment_data.to_excel(writer, sheet_name='Payment', index=False)
        inventory_data.to_excel(writer, sheet_name='Inventory', index=False)

        workbook = writer.book
        for sheet_name in writer.sheets:
            worksheet = workbook[sheet_name]
            for col in worksheet.columns:
                max_length = 0
                column = col[0].column_letter  # Get the column name
                for cell in col:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
                adjusted_width = (max_length + 2)
                worksheet.column_dimensions[column].width = adjusted_width

    # Open the file in binary mode to read
    with open('all_data.xlsx', 'rb') as excel_file:
        response = HttpResponse(excel_file.read(), content_type='application/vnd.ms-excel')
        response['Content-Disposition'] = f'attachment; filename="{username}_all_data.xlsx"'
        
    return response

def export_all_data_pdf(request, username):
    user = User.objects.get(user_name=username)

    # Create the HttpResponse object with the appropriate PDF headers.
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{username}_all_data.pdf"'

    # Create the PDF object, using the response object as its "file."
    doc = SimpleDocTemplate(response, pagesize=letter)
    elements = []

    # Title
    styles = getSampleStyleSheet()
    title_style = styles['Title']
    heading_style = ParagraphStyle(
        name='Heading2Center', 
        parent=styles['Heading2'], 
        alignment=1  # Center alignment
    )
    body_style = styles['BodyText']

    title = f"Data Export for {user.user_name}"
    elements.append(Paragraph(title, title_style))

    # Fetch data from each model
    models_data = [
        ("User", User.objects.filter(user_name=user.user_name).values()),
        ("Type", Type.objects.filter(user=user).values()),
        ("Supplies", Supplies.objects.filter(user=user).values()),
        ("DispactchSupply", DispatchSupply.objects.filter(user=user).values()),
        ("CustomerName", CustomerName.objects.filter(user=user).values()),
        ("Customer", Customer.objects.filter(user=user).values()),
        ("Employee", Employee.objects.filter(user=user).values()),
        ("MoneyFund", MoneyFund.objects.filter(user=user).values()),
        ("Sell", Sell.objects.filter(user=user).values()),
        ("Reciept", Reciept.objects.filter(user=user).values()),
        ("MoneyIncome", MoneyIncome.objects.filter(user=user).values()),
        ("Payment", Payment.objects.filter(user=user).values()),
        ("Inventory", Inventory.objects.filter(user=user).values())
    ]

    for model_name, data in models_data:
        elements.append(Paragraph(model_name, heading_style))
        if data.exists():
            for item in data:
                for key, value in item.items():
                    elements.append(Paragraph(f"{key}: {value}", body_style))
                elements.append(Paragraph("", body_style))  # Add a blank line between records
        else:
            elements.append(Paragraph("No data available.", body_style))
        elements.append(PageBreak())  # Add a page break after each model's data

    # Build the PDF
    doc.build(elements)

    return response




