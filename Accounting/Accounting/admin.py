from django.contrib import admin
from .models import *

#Displaying The Total By Summing
class SellAdmin(admin.ModelAdmin):
    readonly_fields = ('total')
    list_display = ('supply','countity','price','total','date','notes')
    fields = ('supply','countity','price','date','notes')

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


admin.site.register(User)
admin.site.register(Type)
admin.site.register(DispatchSupply)
admin.site.register(Supplies)
admin.site.register(Customer)
admin.site.register(Employee)
admin.site.register(MoneyFund)
admin.site.register(Sell)
admin.site.register(Reciept)
admin.site.register(MoneyIncome)
admin.site.register(Payment)
admin.site.register(CustomerName)
admin.site.register(Inventory)
#admin.site.register(CashInventory)









