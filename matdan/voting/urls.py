from django.urls import path
from . import views

urlpatterns =[
    path('', views.voting_home, name="voting_home")
]