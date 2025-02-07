from django.shortcuts import render
import requests
from django.contrib.auth.models import User
from django.db import connections



def home(request):
    return render(request, 'home.html')

