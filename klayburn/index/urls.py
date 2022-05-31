from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('blocks/', views.BlockView.as_view(), name='block'),
    path('blocks/<str:pk>', views.block_member, name='block-member'),
]
