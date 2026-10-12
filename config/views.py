from django.shortcuts import render


def landing_page(request):
    """
    Página de vendas do CardápioPro.
    """
    return render(request, "landing.html")