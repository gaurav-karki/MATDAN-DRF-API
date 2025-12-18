from django.urls import path
from . import views

urlpatterns =[
    path('',views.blockchain_home, name='blockchain'),
]