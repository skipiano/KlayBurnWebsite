from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('blocks/', views.BlockView.as_view(), name='block'),
    path('blocks/<str:pk>', views.block_member, name='block-member'),
    path('transactions/', views.transaction, name='transaction'),
    path('gas_fee/', views.gas_fee, name='gas'),
]
