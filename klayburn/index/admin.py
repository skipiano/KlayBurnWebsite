from django.contrib import admin
from .models import Member, BlockData, TransactionData, GasFeeData

# Register your models here.
admin.site.register(Member)
admin.site.register(BlockData)
admin.site.register(TransactionData)
admin.site.register(GasFeeData)
