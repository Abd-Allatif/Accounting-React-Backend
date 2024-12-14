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

# Login
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


@api_view(['POST','GET'])
@permission_classes([IsAuthenticated])
def manage_types(request,username):
    try:
        user = User.objects.get(user_name = username)

        if request.method == 'POST':
            types = request.data.get('types')
            user_data = request.data.get('user')

            if types and user_data:
                user_instance = User.objects.get(user_name = user_data)
                Type.objects.create(type=types,user = user_instance)

            return Response({'message': 'Setup successful!'}, status=status.HTTP_200_OK)

        if request.method == 'GET':
            types = Type.objects.filter(user=user)
            serializer = TypeSerializer(types, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)



    except User.DoesNotExist:
        return Response({'error': 'User not found'})
    except Exception as e:
        logger.error(f"SetupAccount error: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




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




