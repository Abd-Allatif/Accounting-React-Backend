from django.contrib import admin
from .models import *

#Displaying The Total By Summing
class UserAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(is_superuser=False)

    exclude = ('last_login',)
    # Customize the list display if needed
    list_display = ('user_name', 'email','issatup', 'budget', 'password_reset_code')
    search_fields = ('user_name', 'email')



admin.site.register(User, UserAdmin)
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









