from django.shortcuts import render
from django.http import HttpResponse

def blockchain_home(request):
    return HttpResponse("wlcome to blockchain home page")

