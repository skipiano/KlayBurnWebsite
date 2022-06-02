from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('blocks/', views.BlockView.as_view(), name='block'),
    path('blocks/download', views.block_download, name='block-download'),
    path('blocks/<str:pk>', views.block_member, name='block-member'),
    path('transactions/', views.transaction, name='transaction'),
    path('transactions/download', views.transaction_download,
         name='transaction-download'),
    path('gas_fee/', views.gas_fee, name='gas'),
    path('gas_fee/download', views.gas_fee_download, name='gas-download'),
    path('update', views.update, name='update'),
    path('test', views.test, name='test'),
]
