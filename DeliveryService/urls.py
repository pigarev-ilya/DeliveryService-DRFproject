"""DeliveryService URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django_rest_passwordreset.views import reset_password_request_token, reset_password_confirm
from rest_framework.routers import DefaultRouter
from app.views import RegisterView, LoginView, CategoryView, ShopView, ProductView, BasketView, \
    PartnerView, ContactView, UserOrderView, PartnerOrdersView, AccountView, ConfirmAccount, PartnerUpdateView

app_name = 'password_reset'

router = DefaultRouter()
router.register(r'category', CategoryView, basename='category')
router.register(r'shops', ShopView, basename='shops')
router.register(r'products', ProductView, basename='products')

urlpatterns = [
    path('api/v1/', include(router.urls)),
    path('api/v1/account/register', RegisterView.as_view()),
    path('api/v1/account/confirm', ConfirmAccount.as_view()),
    path('api/v1/account/login', LoginView.as_view()),
    path('api/v1/account/bayer', AccountView.as_view()),
    path('api/v1/basket', BasketView.as_view()),
    path('api/v1/basket/update', UserOrderView.as_view()),
    path('api/v1/partner/orders', PartnerOrdersView.as_view()),
    # reset pasword send "POST" api/v1/account/password-reset
    path('api/v1/account/password-reset', reset_password_request_token, name='reset-password-request'),
    # new pasword and token send "POST"- api/v1/account/password_reset/confirm
    path('api/v1/account/password_reset/confirm', reset_password_confirm, name='password-reset-confirm'),
    path('api/v1/partner/shop', PartnerView.as_view()),
    path('api/v1/partner/contacts', ContactView.as_view()),
    path('api/v1/partner/update', PartnerUpdateView.as_view()),
    path('admin/', admin.site.urls)
]
