from django.db import models
from django.db.models import Sum
from django.db.models.signals import pre_save,post_delete,post_save,pre_delete
from django.dispatch import receiver
import bcrypt
from django.utils.crypto import get_random_string
from django.contrib.auth.models import BaseUserManager,AbstractBaseUser,PermissionsMixin

class UserManager(BaseUserManager):
    def create_user(self, user_name, email, password=None, **extra_fields):
        if not email:
            raise ValueError('You Did Not Enter a Valid Email')

        email = self.normalize_email(email)
        user = self.model(user_name=user_name, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, user_name, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(user_name, email, password, **extra_fields)


class User (AbstractBaseUser,PermissionsMixin):
    # User Name
    user_name = models.CharField(max_length=100,primary_key=True)
    # Email
    email = models.CharField(max_length=250,unique=True)
    # # Passowrd Taken from UserManager
    # password = models.CharField(max_length=128)
    # Budegt
    budget = models.IntegerField(default=0)
    # Password Reset Code
    password_reset_code = models.CharField(max_length=20, blank=True, null=True)

    is_active = models.BooleanField(default=True,editable=False) 
    is_staff = models.BooleanField(default=False,editable=False) 
    is_superuser = models.BooleanField(default=False,editable=False) 
    date_joined = models.DateTimeField(auto_now_add=True)

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='accounting_user_set',  # Ensure this is unique
        blank=True,
        help_text=('The groups this user belongs to. A user will get all permissions granted to each of their groups.'),
        verbose_name=('groups'),
        editable=False
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='accounting_user_permissions',  # Ensure this is unique
        blank=True,
        help_text=('Specific permissions for this user.'),
        verbose_name=('user permissions'),
        editable=False
    )

    objects = UserManager()

    USERNAME_FIELD = 'user_name'
    REQUIRED_FIELDS = ['email']

    def set_password(self,raw_password):
        hashed_password = bcrypt.hashpw(raw_password.encode('utf-8'), bcrypt.gensalt())  # type: ignore
        self.password = hashed_password.decode('utf-8')

    def check_password(self,raw_password):
        return bcrypt.checkpw(raw_password.encode('utf-8'), self.password.encode('utf-8'))
    # Hashing the Passwords before saving
    def save(self, *args, **kwargs):
       if not self.password_reset_code:
           self.password_reset_code = get_random_string(10) 
       super(User, self).save(*args, **kwargs)
    def __str__(self):
        return f'{self.user_name}'

@receiver(post_save,sender = User)
def update_permanant_fund(sender,instance,**kwargs):
    money_fund, created = MoneyFund.objects.get_or_create(
    permanant_fund=instance.budget,  # Use a specific field to look up the object
    defaults={'user':instance,'permanant_fund': instance.budget, 'sells_fund': 0}
)
    if not created:
        money_fund.permanant_fund = instance.budget
        money_fund.save()

@receiver(post_delete,sender = User)
def update_permanant_fund_on_delete(sender,instance,**kwargs):
    money_fund = MoneyFund.objects.first()

    if money_fund:
        money_fund.permanant_fund -= instance.budget
        money_fund.save()

@receiver(pre_save, sender=User)
def update_permanant_fund_on_edit(sender, instance, **kwargs):
    try:
        if instance.pk:
            old_instance = User.objects.get(pk=instance.pk)
            old_budget = old_instance.budget
            new_budget = instance.budget
            money_fund = MoneyFund.objects.first()
            
            if money_fund:
                # Adjust the permanent fund based on the budget change
                money_fund.permanant_fund -= old_budget
                money_fund.permanant_fund += new_budget
                money_fund.save()
    except User.DoesNotExist:
        # This block will be executed during user creation, ignore it
        pass


#Creating the Type Model /Done/Checked
class Type(models.Model):
    type = models.CharField(max_length=50,primary_key=True)
    user = models.ForeignKey(User,on_delete=models.CASCADE)
    def __str__(self):
        return f'{self.type}'

#Creating the Supplies Model /Done/Checked
class Supplies(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE)
    # Type Fk
    type = models.ForeignKey(Type,on_delete=models.CASCADE,default="")
    # Supply Name
    supply_name = models.CharField(max_length=50,primary_key=True)
    # Countity
    countity = models.IntegerField(default=0)
    # Buy Price
    buy_price = models.IntegerField(default=0)
    # Sell Price
    sell_price = models.IntegerField(default=0)
    # BarCode
    # Later
    def __str__(self):
        return f'{self.supply_name}'

class DispatchSupply(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE)
    supply = models.ForeignKey(Supplies,on_delete=models.CASCADE,default="")
    countity = models.IntegerField(default=0)
    buy_price = models.IntegerField(default=0)
    dispatch_date = models.DateField(auto_now=True)
    reason = models.CharField(max_length=400,null=True,blank=True)

    def __str__(self):
        return f'{self.supply} Countity: {self.countity}'

@receiver(post_save, sender=DispatchSupply)
def update_supply_and_fund(sender, instance, created, **kwargs):
    if created:
        supply = instance.supply
        countity = instance.countity
        buy_price = instance.buy_price

        # Update supply countity
        if supply.countity >= countity:
            supply.countity -= countity
            supply.save()

            # Update money fund
            money_fund = MoneyFund.objects.first()
            if money_fund.permanant_fund >= (countity * buy_price):
                money_fund.permanant_fund -= (countity * buy_price)
                money_fund.save()
            else:
                raise ValueError("Not enough funds")
        else:
            raise ValueError("Not enough supplies to dispatch")


@receiver(post_delete, sender=DispatchSupply)
def handle_dispatch_deletion(sender, instance, **kwargs):
    supply = instance.supply
    countity = instance.countity
    buy_price = instance.buy_price

    # Revert supply countity
    supply.countity += countity
    supply.save()

    # Revert money fund
    money_fund = MoneyFund.objects.first()
    money_fund.permanant_fund += (countity * buy_price)
    money_fund.save()


@receiver(pre_save, sender=DispatchSupply)
def handle_dispatch_update(sender, instance, **kwargs):
    try:
        # Get the original state before saving
        original = DispatchSupply.objects.get(pk=instance.pk)
    except DispatchSupply.DoesNotExist:
        original = None

    if original:
        supply = instance.supply
        countity_difference = instance.countity - original.countity

        # Update supply countity
        if supply.countity + original.countity >= instance.countity:
            supply.countity -= countity_difference
            supply.save()

            # Update money fund
            money_fund = MoneyFund.objects.first()
            if money_fund.permanant_fund + (original.countity * original.buy_price) >= (instance.countity * instance.buy_price):
                money_fund.permanant_fund -= (countity_difference * instance.buy_price)
                money_fund.save()

            else:
                raise ValueError("Not enough funds")
        else:
            raise ValueError("Not enough supplies to dispatch")


#Creating the Permanant Customer Model /Done/
class CustomerName(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE)
    customer_name = models.CharField(max_length=50,primary_key=True)
    total_debt = models.IntegerField(null=True,blank=True,default=0)
    
    def __str__(self):
        return f'{self.customer_name}'

#Creating the Permanant Customer Sells Model /Done/
class Customer(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE)
    # Customer Name
    customer_name = models.ForeignKey(CustomerName,on_delete=models.CASCADE)
    # Customer Date Of Buying
    date_of_buying = models.DateField(auto_now=True)
    # Customer Supply Fk
    supply = models.ForeignKey(Supplies,on_delete=models.CASCADE,default="")
    # Supply Price
    price = models.IntegerField(default=0)
    # Supllys Countity
    countity = models.IntegerField(default=0)
    # Total Value: Countity x Price
    total = models.IntegerField(editable=False,default=0)
    # The Debt
    debt = models.IntegerField(default=0,null=True,blank=True)
    # paid
    paid = models.IntegerField(default=0,null=True,blank=True)
    # Notes
    notes = models.CharField(max_length=400,null=True,blank=True)

    # Defining a Function to Calculate the Total Value: Countity x Price
    def save(self,*args,**kwrgs):
        # if self.debt > 0 and self.paid > 0:
        #     self.debt = abs(self.total - self.paid)

        self.total = self.countity * self.price
        # Saving Changes
        super(Customer,self).save(*args,**kwrgs)

    def __str__(self):
        return f'{self.customer_name}'

#---------------------------------------------------------------
# Defining The functions to Update Related Tables
# On Customer

# /Done Update MoneyFund by Customer If debt or If not debt/

@receiver(pre_save, sender=Customer)
def capture_old_customer_instance(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._old_instance = Customer.objects.get(pk=instance.pk)
        except Customer.DoesNotExist:
            instance._old_instance = None

@receiver(pre_delete, sender=Customer)
def capture_old_customer_value(sender, instance, **kwargs):
    instance._old_paid = instance.paid
    instance._old_debt = instance.debt
    instance._old_countity = instance.countity

@receiver(post_save, sender=Customer)
def handle_customer_save(sender, instance, created, **kwargs):
    money_fund = MoneyFund.objects.first()
    customer_name, _ = CustomerName.objects.get_or_create(customer_name=instance.customer_name.customer_name)
    supply = instance.supply

    # Handle creation and updates
    if created:
        if instance.debt == 0:
            if not money_fund:
                money_fund = MoneyFund.objects.create(permanant_fund=0, sells_fund=0)
            money_fund.sells_fund += instance.total
        elif instance.debt > 0:
            if instance.paid > 0:
                money_fund.sells_fund += instance.paid
            customer_name.total_debt += instance.debt
        if supply:
            supply.countity -= instance.countity
            supply.save()
    else:
        old_instance = getattr(instance, '_old_instance', None)
        if old_instance:
            if old_instance.debt == 0 and money_fund:
                money_fund.sells_fund -= old_instance.total
            elif old_instance.debt > 0:
                if old_instance.paid > 0 and old_instance.debt > 0 and money_fund:
                    money_fund.sells_fund -= old_instance.paid
                customer_name.total_debt -= old_instance.debt

            if old_instance.countity != instance.countity:
                supply.countity += old_instance.countity - instance.countity
                supply.save()

            # Update new values
            if instance.debt == 0 and money_fund:
                money_fund.sells_fund += instance.total
            elif instance.debt > 0:
                if instance.paid > 0 and instance.debt > 0:
                    money_fund.sells_fund += instance.paid
                customer_name.total_debt += instance.debt

    money_fund.save()
    customer_name.save()

# Handle customer deletion
@receiver(post_delete, sender=Customer)
def handle_customer_deletion(sender, instance, **kwargs):
    customer_name = instance.customer_name
    old_paid = getattr(instance, '_old_paid', 0)
    old_debt = getattr(instance, '_old_debt', 0)
    old_countity = getattr(instance, '_old_countity', 0)
    money_fund = MoneyFund.objects.first()

    if old_paid > 0 and money_fund:
        money_fund.sells_fund -= old_paid
        money_fund.save()

    if customer_name:
        customer_name.total_debt -= old_debt
        customer_name.save()

    supply = instance.supply
    if supply:
        supply.countity += old_countity
        supply.save()


#---------------------------------------------------------------

#Creating the Employee Model
class Employee(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE)
    employee_name = models.CharField(max_length=50,primary_key=True)

    date_of_employment = models.DateField(blank=True,null=True)

    salary = models.IntegerField(default=0)

    next_salary = models.DateField(blank=True,null=True)

    def __str__(self):
        return f'{self.employee_name}'

#Creating the MoneyFund Model /Done/
class MoneyFund(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE)
    permanant_fund = models.IntegerField(default=0)

    sells_fund = models.IntegerField(default=0)

    def __str__(self):
        return f'{self.permanant_fund} {self.sells_fund}'

#Creating the Sell Model /Done/
class Sell(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE)
    # Supply Fk
    supply = models.ForeignKey(Supplies,on_delete=models.CASCADE)
    # Countity
    countity = models.IntegerField()
    # Price
    price = models.IntegerField()
    # Total
    total = models.IntegerField(editable=False,default=0)
    # Date
    date = models.DateField(auto_now=True)
    # Notes
    notes = models.CharField(max_length=400,null=True,blank=True)

    # Defining a Function to Calculate the Total Value: Countity x Price
    def save(self,*args,**kwrgs):
        self.total = self.countity * self.price
        # Saving Changes
        super(Sell,self).save(*args,**kwrgs)

    def __str__(self):
        return f'Date: {self.date} Supply: {self.supply} Total: {self.total}'

# Defining The functions to Update Related Tables
# On Sells Table

# /Done Update MoneyFund by Sell/
@receiver(post_save,sender=Sell)
def update_money_on_sell (sender,instance,**kwargs):
    money_fund = MoneyFund.objects.first()
    
    if not money_fund:
        money_fund = MoneyFund.objects.create(permanant_fund = 0,sells_fund = 0)
    
    money_fund.sells_fund += instance.total
    money_fund.save()

@receiver(post_delete,sender=Sell)
def update_money_delete_on_sell (sender,instance,**kwargs):
    money_fund = MoneyFund.objects.first()
    
    if money_fund:
        money_fund.sells_fund -= instance.total
        money_fund.save()


@receiver(pre_save,sender=Sell)
def update_money_on_edit(sender,instance,**kwargs):
    if instance.pk:
        old_instance = Sell.objects.get(pk=instance.pk)
        old_total = old_instance.total
        money_fund = MoneyFund.objects.first()
        if money_fund:
            money_fund.sells_fund -= old_total
            money_fund.save()

#---------------------------------------------------------------
# /Done Update Supply by Sell/
@receiver(post_save,sender=Sell)
def update_supply_on_sells(sender,instance,**kwargs):
     if instance.supply.pk:
         supply = Supplies.objects.get(pk = instance.supply)
         if supply:   
             supply.countity -= instance.countity
             supply.save()

@receiver(post_delete,sender=Sell)
def update_supply_delete_on_sells(sender,instance,**kwargs):
    supply = Supplies.objects.get(pk = instance.supply)

    if supply.pk:
        supply.countity += instance.countity
        supply.save()

@receiver(pre_save,sender=Sell)
def update_supply_edit_on_sells(sender,instance,**kwargs):
    if instance.pk:
        old_intance = Sell.objects.get(pk= instance.pk)
        old_countity = old_intance.countity
        supply = Supplies.objects.get(pk= instance.supply)
        if supply:
            supply.countity += old_countity
            supply.save()

#Creating the Reciept (Supply Buying) Model /Done/
class Reciept(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE)
    # Type Fk
    type = models.ForeignKey(Type,on_delete=models.CASCADE)
    # Supply Fk
    supply = models.ForeignKey(Supplies,on_delete=models.CASCADE)
    # Countity
    countity = models.IntegerField()
    # Buy Price
    buy_price = models.IntegerField()
    # Sell Price
    sell_price = models.IntegerField()
    # Total Value: Buy Price x Countity
    total = models.IntegerField(editable=False,default=0)
    # Date
    date = models.DateField(auto_now=True)
    # Notes
    notes = models.CharField(max_length=400,null=True,blank=True)

    # Defining a Function to Calculate the Total Value: Countity x Price
    def save(self,*args,**kwargs):
        self.total = self.countity * self.buy_price
         # Saving Changes``
        super(Reciept,self).save(*args,**kwargs)


    def __str__(self):
        return f'Type: {self.type} Supply:{self.supply}'

#---------------------------------------------------------------
# Defining The functions to Update Related Tables
# On Reciept

# /Done Update MoneyFund by Reciept/
@receiver(post_save,sender=Reciept)
def update_money_on_reciepts(sender,instance,**kwargs):
    money_fund = MoneyFund.objects.first()

    if not money_fund:
        money_fund = MoneyFund.objects.create(permanant_fund = 0,sells_fund = 0)
    
    money_fund.permanant_fund -= instance.total
    money_fund.save()

@receiver(post_delete,sender=Reciept)
def update_money_delete_on_reciepts(sender,instance,**kwargs):
    money_fund = MoneyFund.objects.first()

    if money_fund:
        money_fund.permanant_fund += instance.total
        money_fund.save()

@receiver(pre_save,sender=Reciept)
def update_money_ediut_on_reciepts(sender,instance,**kwargs):
    if instance.pk:
        old_instance = Reciept.objects.get(pk=instance.pk)
        old_total = old_instance.total
        money_fund = MoneyFund.objects.first()
        if money_fund:
            money_fund.permanant_fund += old_total
            money_fund.save()

#---------------------------------------------------------------

# /Done Update Supply by Reciept/
@receiver(post_save, sender=Reciept)
def update_supply_on_receipts(sender, instance, **kwargs):
    supply, created = Supplies.objects.get_or_create(
        supply_name= instance.supply.supply_name,
        defaults={
            'countity': instance.countity,
            'buy_price': instance.buy_price,
            'sell_price': instance.sell_price,
            'type': instance.type,
        }
    )
    if not created:  # If the supply already exists, update the countity
        supply.countity += instance.countity
        supply.buy_price = instance.buy_price
        supply.sell_price = instance.sell_price
        supply.save()


@receiver(post_delete,sender=Reciept)
def update_supply_delete_on_receipts(sender,instance,**kwargs):
    supply = Supplies.objects.get(pk = instance.supply)

    if supply.pk:
        supply.countity -= instance.countity 
        supply.save()

@receiver(pre_save,sender=Reciept)
def update_supply_edit_on_receipt(sender,instance,**kwargs):
    if instance.pk:
        old_intance = Reciept.objects.get(pk= instance.pk)
        old_countity = old_intance.countity
        supply = Supplies.objects.get(pk= instance.supply)
        if supply:
            supply.countity -= old_countity
            supply.save()

#Creating the MoneyIncome Model  /Done/
class MoneyIncome(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE)
    # Money Comming from
    money_from = models.ForeignKey(CustomerName,on_delete=models.CASCADE,null=True,blank=True)
    # Total Value Incoming
    total = models.IntegerField()
    # Date
    date = models.DateField(auto_now=True)
    # notes
    notes = models.CharField(max_length=400,null=True,blank=True)

    def __str__(self):
        return f'Date: {self.date} Total: {self.total}'

#---------------------------------------------------------------

@receiver(post_delete, sender=MoneyIncome)
def reverse_debt_on_payment_deletion(sender, instance, **kwargs):
    customer_name = instance.money_from

    # Update individual customer records
    customers = Customer.objects.filter(customer_name=customer_name).order_by('date_of_buying')
    
    remaining_payment = instance.total

    for customer in customers:
        if remaining_payment <= 0:
            break
        if customer.paid > 0:
            if remaining_payment >= customer.paid:
                remaining_payment -= customer.paid
                customer.debt += customer.paid  # Reverse the payment by adding it back to debt
                customer.paid = 0
                customer.notes = 'Reversed payment.'
            else:
                customer.debt += remaining_payment
                customer.paid -= remaining_payment  # Ensure correct decrement
                customer.notes = 'Partial payment reversal.'
                remaining_payment = 0
            customer.save()

# Handle MoneyIncome creation
@receiver(post_save, sender=MoneyIncome)
def update_debt_on_payment(sender, instance, created, **kwargs):
    customer_name = instance.money_from

    # Update individual customer records
    customers = Customer.objects.filter(customer_name=customer_name).order_by('date_of_buying')
    
    remaining_payment = instance.total

    for customer in customers:
        if remaining_payment <= 0:
            break
        if customer.debt > 0:
            if remaining_payment >= customer.debt:
                remaining_payment -= customer.debt
                customer.paid += customer.debt  # Ensure correct increment
                customer.debt = 0
                customer.notes = 'Debt has been paid.'
            else:
                customer.debt -= remaining_payment
                customer.paid += remaining_payment  # Ensure correct increment
                customer.notes = 'Partial payment made.'
                remaining_payment = 0
            customer.save()


#---------------------------------------------------------------

#Creating the MoneyIncome Model  /Done/
class Payment(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE)
    # Money Comming from
    money_for = models.CharField(max_length=250)
    # Total Value Incoming
    total = models.IntegerField()
    # Date
    date = models.DateField(auto_now=True)
    # notes
    notes = models.CharField(max_length=400,null=True,blank=True)

    def __str__(self):
        return f'Paid for: {self.money_for} Date: {self.date} Total: {self.total}'
    
#---------------------------------------------------------------
# Defining The functions to Update Related Tables
# On Payment

# /Done Update MoneyFund by Payment/
@receiver(post_save,sender=Payment)
def update_money_on_payment (sender,instance,**kwargs):
    money_fund = MoneyFund.objects.first()
    
    if not money_fund:
        money_fund = MoneyFund.objects.create(permanant_fund = 0,sells_fund = 0)
    
    money_fund.permanant_fund -= instance.total
    money_fund.save()

@receiver(post_delete,sender=Payment)
def update_money_delete_on_payment (sender,instance,**kwargs):
    money_fund = MoneyFund.objects.first()
    
    if money_fund:
        money_fund.permanant_fund += instance.total
        money_fund.save()


@receiver(pre_save,sender=Payment)
def update_money_on_edit(sender,instance,**kwargs):
    if instance.pk:
        old_instance = Payment.objects.get(pk=instance.pk)
        old_total = old_instance.total
        money_fund = MoneyFund.objects.first()
        if money_fund:
            money_fund.permanant_fund += old_total
            money_fund.save()


#-------------------------------------------------------------------

class Inventory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    supply = models.ForeignKey('Supplies', on_delete=models.CASCADE)
    initial_countity = models.IntegerField(blank=True)
    final_countity = models.IntegerField(blank=True)
    initial_fund = models.IntegerField(blank=True)
    final_fund = models.IntegerField(blank=True)
    sales_countity = models.IntegerField(default=0, blank=True)
    purchase_countity = models.IntegerField(default=0, blank=True)
    debt_countity = models.IntegerField(default=0, blank=True)
    unpaid_customers = models.TextField(blank=True)
    discrepancy = models.IntegerField(default=0, blank=True)
    dispatched_supply = models.IntegerField(default=0, blank=True)
    dispatched_value = models.IntegerField(default=0, blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    inventory_date = models.DateField(auto_now=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f'Inventory for {self.supply} from {self.start_date} to {self.end_date}'

    def calculate_inventory(self):
        # Retrieve initial values
        self.initial_countity = self.supply.countity
        money_fund = MoneyFund.objects.first()
        self.initial_fund = money_fund.sells_fund if money_fund else 0

        # Retrieve data from the models
        sales = Sell.objects.filter(date__range=[self.start_date, self.end_date], supply=self.supply).aggregate(Sum('countity'))['countity__sum'] or 0
        purchases = Reciept.objects.filter(date__range=[self.start_date, self.end_date], supply=self.supply).aggregate(Sum('countity'))['countity__sum'] or 0
        unpaid_customers_query = Customer.objects.filter(date_of_buying__range=[self.start_date, self.end_date], debt__gt=0, supply=self.supply)
        unpaid_customers_list = unpaid_customers_query.values_list('customer_name__customer_name', flat=True)
        unpaid_customers_str = ', '.join(unpaid_customers_list)
        unpaid_debts = unpaid_customers_query.aggregate(Sum('debt'))['debt__sum'] or 0
        unpaid_countity = unpaid_customers_query.aggregate(Sum('countity'))['countity__sum'] or 0
        income_total = MoneyIncome.objects.filter(date__range=[self.start_date, self.end_date]).aggregate(Sum('total'))['total__sum'] or 0
        expense_total = Payment.objects.filter(date__range=[self.start_date, self.end_date]).aggregate(Sum('total'))['total__sum'] or 0

        # Retrieve dispatched data
        dispatches = DispatchSupply.objects.filter(dispatch_date__range=[self.start_date, self.end_date], supply=self.supply)
        dispatched_countity = dispatches.aggregate(Sum('countity'))['countity__sum'] or 0
        dispatched_value = sum(dispatch.buy_price * dispatch.countity for dispatch in dispatches)

        # Calculate updated quantities and funds
        self.sales_countity = sales
        self.purchase_countity = purchases
        self.debt_countity = unpaid_countity
        self.dispatched_supply = dispatched_countity
        self.dispatched_value = dispatched_value
        self.final_countity = self.initial_countity + purchases - sales - unpaid_countity - dispatched_countity
        self.unpaid_customers = unpaid_customers_str

        expected_countity = self.initial_countity + purchases - sales - dispatched_countity
        self.discrepancy = self.final_countity - expected_countity

        # Check if final countity is accurate
        if self.final_countity != self.initial_countity + purchases - sales - unpaid_countity - dispatched_countity:
            self.notes = 'Losses detected due to inventory miscalculation.'
        else:
            self.notes = 'No losses detected.'

        # Calculate final fund and handle discrepancies
        if money_fund:
            self.final_fund = self.initial_fund + income_total - expense_total - dispatched_value
            if self.discrepancy != 0:
                money_fund.sells_fund += self.discrepancy
                money_fund.save()
            if self.final_fund < 0:
                self.notes += ' Warning: Final fund is negative.'

    def save(self, *args, **kwargs):
        self.calculate_inventory()
        super(Inventory, self).save(*args, **kwargs)


# @receiver(pre_save, sender=Inventory)
# def inventory_pre_save(sender, instance, **kwargs):
#     if instance.pk:
#         # Capture the old instance before saving
#         instance._old_instance = Inventory.objects.get(pk=instance.pk)

@receiver(post_save, sender=Inventory)
def inventory_post_save(sender, instance, created, **kwargs):
    if created:
        instance.calculate_inventory()

# @receiver(post_delete, sender=Inventory)
# def inventory_post_delete(sender, instance, **kwargs):
#     # Reverse the calculations if the record is deleted
#     old_instance = getattr(instance, '_old_instance', None)
#     if old_instance:
#         # Adjust counts back to the initial state
#         sales = Sell.objects.filter(date__range=[old_instance.start_date, old_instance.end_date], supply=instance.supply).aggregate(Sum('countity'))['countity__sum'] or 0
#         purchases = Reciept.objects.filter(date__range=[old_instance.start_date, old_instance.end_date], supply=instance.supply).aggregate(Sum('countity'))['countity__sum'] or 0
#         unpaid_customers_query = Customer.objects.filter(date_of_buying__range=[old_instance.start_date, old_instance.end_date], debt__gt=0, supply=instance.supply)
#         unpaid_debts = unpaid_customers_query.aggregate(Sum('debt'))['debt__sum'] or 0

#         # Handle dispatches
#         dispatches = DispatchSupply.objects.filter(dispatch_date__range=[old_instance.start_date, old_instance.end_date], supply=instance.supply)
#         dispatched_countity = dispatches.aggregate(Sum('countity'))['countity__sum'] or 0
#         dispatched_value = sum(dispatch.buy_price * dispatch.countity for dispatch in dispatches)

#         instance.supply.countity += sales - purchases + unpaid_debts + dispatched_countity
#         instance.supply.save()

#         money_fund = MoneyFund.objects.first()
#         if money_fund:
#             money_fund.sells_fund -= old_instance.final_fund - old_instance.initial_fund - dispatched_value
#             money_fund.save()



