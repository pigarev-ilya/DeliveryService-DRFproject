from rest_framework import permissions

from rest_framework.views import exception_handler
from rest_framework.exceptions import NotAuthenticated
from rest_framework.response import Response


def custom_exception_handler(exc, context):
    if isinstance(exc, NotAuthenticated):
        return Response({'Status': False, 'Errors': 'Error or missing authorization data.'})

    return exception_handler(exc, context)


class IsShopOnly(permissions.BasePermission):
    message = {'Status': False, 'Errors': 'Your account type is not "seller".'}
    def has_permission(self, request, view):
        return request.user.type_account == 'seller'


class IsBuyerOnly(permissions.BasePermission):
    message = {'Status': False, 'Errors': 'Your account type is not "buyer".'}
    def has_permission(self, request, view):
        return request.user.type_account == 'buyer'


class IsNotAuthenticated(permissions.BasePermission):
    message = {'Status': False, 'Errors': 'You are already logged in.'}
    def has_permission(self, request, view):
        return bool(not request.user.is_authenticated)
