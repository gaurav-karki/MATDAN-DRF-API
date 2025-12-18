from django.shortcuts import render
from django.http import HttpResponse

def elections_home(request):
    return HttpResponse("Welcome to election home page.")
