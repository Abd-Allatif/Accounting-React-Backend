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
#Creating the Permanant Customer Model /Done/
class CustomerName(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE)
    customer_name = models.CharField(max_length=50,primary_key=True)
    total_debt = models.IntegerField(null=True,blank=True,default=0)
    
    def __str__(self):
        return f'{self.customer_name}'
Creating the Permanant Customer Sells Model /Done/
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
class Employee(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE)
    employee_name = models.CharField(max_length=50,primary_key=True)
    date_of_employment = models.DateField()
    salary = models.IntegerField(default=0)
    next_salary = models.DateField()
#Creating the MoneyFund Model /Done/
class MoneyFund(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE)
    permanant_fund = models.IntegerField(default=0)
    sells_fund = models.IntegerField(default=0)
#Creating the Sell Model /Done/
class Sell(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE)
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
     