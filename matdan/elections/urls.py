from django.urls import path
from . import views

urlpatterns = [
    path('',views.elections_home, name='elections_home')
]