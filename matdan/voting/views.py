from django.shortcuts import render
from django.http import HttpResponse

def voting_home(request):
    return HttpResponse("Welcome to voting page")

