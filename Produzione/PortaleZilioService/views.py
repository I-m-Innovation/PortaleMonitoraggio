from django.shortcuts import render

def home_view(request):
    return render(request, "PortaleZilioService/home.html")


def test_view(request):
    return render(request, "PortaleZilioService/test.html")
