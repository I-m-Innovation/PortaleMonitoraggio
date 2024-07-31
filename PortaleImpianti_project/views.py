from django.shortcuts import render,redirect
from django.contrib.auth.decorators import login_required


def HomePage(request):
	return render(request,'HomePage.html')


# @login_required(login_url='login')
def loadingPageMonitoraggio(request):
	return render(request, 'loading_gif/loading_1.html')

@login_required(login_url='login')
def loadingPageAnalisi(request):
	return render(request, 'loading_gif/loading_2.html')

@login_required(login_url='login')
def loadingPageGSE(request):
	return render(request, 'loading_gif/loading_3.html')
