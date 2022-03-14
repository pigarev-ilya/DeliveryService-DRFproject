from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationErrror
from django.core.validators import URLValidator
from django.db.models import Sum, F
from django.http import JsonResponse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.mixins import ListModelMixin
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from app.filters import ProductFilterSet
from app.models import Account, Category, Shop, ProductInfo, Product, \
    ProductParameter, Parameter, Order, OrderItem, Contact
from rest_framework.viewsets import GenericViewSet
from rest_framework.serializers import ValidationError

from app.permissions import IsNotAuthenticated, IsBuyerOnly, IsShopOnly
from app.serilizers import CategorySerializer, RegistrationSerializer, CustomAuthTokenSerializer, \
    ShopSerializer, ProductInfoSerializer, OrderItemSerializer, ContactSerializer, OrderUserSerializer, \
    OrderPartnerSerializer, UpdateBusketSerializer, UpdateContactSerializer, UserSerializer
from django.db import IntegrityError
from yaml import load as load_yaml, Loader
from requests import get
from app.signals import new_order, confirm_email


class RegisterView(APIView):
    # User registration
    permission_classes = [IsNotAuthenticated]

    def post(self, request):
        try:
            data = {}
            serializer = RegistrationSerializer(data=request.data)
            if serializer.is_valid():
                account = serializer.save()
                token = Token.objects.get_or_create(user=account)[0].key
                data["message"] = 'User registered successfully'
                data["email"] = account.email
                data["token"] = token
                confirm_email.send(sender=self.__class__, user_id=account.id)
                return JsonResponse({'Status': True, 'Data': data})
            else:
                return JsonResponse({'Status': False, 'Errors': serializer.errors})
        except IntegrityError as error:
            return JsonResponse({'Status': False, 'Errors': f'{str(error)}'})
        except KeyError as error:
            return JsonResponse({'Status': False, 'Errors': f'Field {str(error)} missing.'})


class ConfirmAccount(APIView):
    # User email confirmation
    permission_classes = [AllowAny]

    def patch(self, request):
        if not {'email', 'token'}.issubset(request.data):
            return JsonResponse({'Status': False, 'Errors': 'Wrong request format.'})
        user = Account.objects.get(email=request.data['email'])
        token = request.data['token']
        if not default_token_generator.check_token(user, token):
            return JsonResponse({'Status': False, 'Errors': 'Token or email error.'})
        user.is_active = True
        user.save()
        return JsonResponse({'Status': True})


class AccountView(APIView):
    # Working with a user account
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request, *args, **kwargs):
        if {'password', 'old_password'}.issubset(request.data):
            password = request.data['password']
            check_pw = request.user.check_password(request.data['old_password'])
            if not check_pw:
                return JsonResponse({'Status': False, 'Errors': 'Old password is not correct.'})
            try:
                validate_password(password)
                request.user.set_password(password)
            except DjangoValidationErrror as error:
                return JsonResponse({'Status': False, 'Errors': f'{error}'})
        serializer = UserSerializer(request.user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return JsonResponse({'Status': True})
        else:
            return JsonResponse({'Status': False, 'Errors': serializer.errors})


class LoginView(ObtainAuthToken):
    # Login user
    permission_classes = [IsNotAuthenticated]
    serializer_class = CustomAuthTokenSerializer


class ShopView(ListModelMixin, GenericViewSet):
    # Displaying a list of shops
    permission_classes = [AllowAny]
    queryset = Shop.objects.all()
    serializer_class = ShopSerializer
    pagination_class = LimitOffsetPagination


class CategoryView(ListModelMixin, GenericViewSet):
    # Displaying a list of categories
    permission_classes = [AllowAny]
    queryset = Category.objects.prefetch_related('shops').all()
    serializer_class = CategorySerializer
    pagination_class = LimitOffsetPagination


class ProductView(ListModelMixin, GenericViewSet):
    # Displaying a list of products
    permission_classes = [AllowAny]
    serializer_class = ProductInfoSerializer
    queryset = ProductInfo.objects.filter(shop__status=True).select_related(
        'shop', 'product__category').prefetch_related(
        'product_parameters__parameter').distinct()
    filter_backends = [DjangoFilterBackend]
    filter_class = ProductFilterSet


class PartnerUpdateView(APIView):
    # Loading shop data in yaml format
    permission_classes = [IsAuthenticated, IsShopOnly]

    def post(self, request, *args, **kwargs):
        url = request.data.get('url')
        if not url:
            return JsonResponse({'Status': False, 'Errors': 'Wrong request format.'})
        try:
            URLValidator(url)
        except ValidationError as e:
            return JsonResponse({'Status': False, 'Error': str(e)})
        stream = get(url).content

        data = load_yaml(stream, Loader=Loader)
        try:
            shop, _ = Shop.objects.get_or_create(name=data['shop'], user_id=request.user.id)

            for category in data['categories']:
                category_object, _ = Category.objects.get_or_create(id=category['id'], name=category['name'])
                category_object.shops.add(shop.id)
                category_object.save()
            ProductInfo.objects.filter(shop_id=shop.id).delete()
            for item in data['goods']:
                product, _ = Product.objects.get_or_create(name=item['name'], category_id=item['category'])
                product_info = ProductInfo.objects.create(product_id=product.id,
                                                          price=item['price'],
                                                          price_rrc=item['price_rrc'],
                                                          quantity=item['quantity'],
                                                          shop_id=shop.id)
                for name, value in item['parameters'].items():
                    parameter_object, _ = Parameter.objects.get_or_create(name=name)
                    ProductParameter.objects.create(product_info_id=product_info.id,
                                                    parameter_id=parameter_object.id,
                                                    value=value)
        except KeyError as error:
            return JsonResponse({'Status': False,
                                 'Error': f'Field {str(error)} missing. Check the file for errors.'})
        return JsonResponse({'Status': True})


class BasketView(APIView):
    # User basket
    permission_classes = [IsAuthenticated, IsBuyerOnly]

    def get(self, request, *args, **kwargs):
        queryset = Order.objects.filter(
            user_id=request.user.id, status='basket').prefetch_related(
            'ordered_items__product_info__product__category',
            'ordered_items__product_info__product_parameters__parameter').annotate(
            total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price'))).distinct()
        serializer = OrderUserSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        input_data = request.data.get('items')
        data_type = list
        if not input_data or not isinstance(input_data, data_type):
            return JsonResponse({'Status': False, 'Errors': 'Wrong request format.'})
        objects_created = 0
        for index, items in enumerate(input_data):
            serializer = OrderItemSerializer(data=items)
            basket, _ = Order.objects.get_or_create(user_id=request.user.id, status='basket')
            items.update({'order': basket.id})
            if serializer.is_valid():
                try:
                    serializer.save()
                    objects_created = index + 1
                except IntegrityError as error:
                    return JsonResponse({'Status': False, 'Errors': f'{str(error)}',
                                         'Objects created': f'{objects_created}'})
            else:
                return JsonResponse({'Status': False, 'Errors': serializer.errors,
                                     'Objects created': f'{objects_created}'})
        return JsonResponse({'Status': True, 'Objects created': f'{len(input_data)}'})

    def patch(self, request, *args, **kwargs):
        input_data = request.data.get('items')
        data_type = list
        if not input_data or not isinstance(input_data, data_type):
            return JsonResponse({'Status': False, 'Errors': 'Wrong request format'})
        basket, _ = Order.objects.get_or_create(user_id=request.user.id, status='basket')
        for counter_update, items in enumerate(input_data):
            serializer = UpdateBusketSerializer(data=items)
            if not serializer.is_valid():
                return JsonResponse({'Status': False, 'Errors': serializer.errors,
                                     'Updated objects': f'{counter_update}'})
            order_item = OrderItem.objects.filter(order_id=basket.id, id=items['id'])
            if order_item:
                order_item.update(quantity=items['quantity'])
            else:
                return JsonResponse({'Status': False,
                                     'Errors': 'There are no matches in the database. Data error.'})
        return JsonResponse({'Status': True, 'Updated objects': f'{len(input_data)}'})

    def delete(self, request, *args, **kwargs):
        input_data = request.data.get('items')
        data_type = {'list': list, 'integer': int}
        if not input_data or not isinstance(input_data, data_type.get('list')):
            return JsonResponse({'Status': False, 'Errors': 'Wrong request format'})
        basket, _ = Order.objects.get_or_create(user_id=request.user.id, status='basket')
        for counter_delete, object_id in enumerate(input_data):
            if not isinstance(object_id, data_type.get('integer')):
                return JsonResponse({'Status': False,
                                     'Errors': f'The {counter_delete + 1}th element in list is not an integer.',
                                     'Delete objects': f'{counter_delete}'})
            order_item = OrderItem.objects.filter(order_id=basket.id, id=object_id)
            if order_item:
                order_item.delete()
            else:
                return JsonResponse({'Status': False,
                                     'Errors': f'The {counter_delete + 1}th element in is not '
                                               f'in the database. Data error.',
                                     'Delete objects': f'{counter_delete}'})
        return JsonResponse({'Status': True, 'Delete objects': f'{len(input_data)}'})


class PartnerView(APIView):
    # User basket
    permission_classes = [IsAuthenticated, IsShopOnly]

    def get(self, request, *args, **kwargs):
        shop = Shop.objects.get(user_id=request.user.id)
        serializer = ShopSerializer(shop)
        return Response(serializer.data)

    def patch(self, request, *args, **kwargs):
        input_data = request.data.get('status')
        data_type = bool
        if not input_data or not isinstance(input_data, data_type):
            return JsonResponse({'Status': False, 'Errors': 'Wrong request format'})
        Shop.objects.filter(user_id=request.user.id).update(status=input_data)
        return JsonResponse({'Status': True})


class PartnerOrdersView(APIView):
    # Displaying the shop data and changing the work status
    permission_classes = [IsAuthenticated, IsShopOnly]

    def get(self, request, *args, **kwargs):
        order = Order.objects.filter(
            ordered_items__product_info__shop__user_id=request.user.id).exclude(status='basket').prefetch_related(
            'ordered_items__product_info__product__category',
            'ordered_items__product_info__product_parameters__parameter').annotate(
            total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price'))).distinct()
        serializer = OrderPartnerSerializer(order, many=True)
        return Response(serializer.data)


class ContactView(APIView):
    # Displaying the shop data and changing the work status
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        contact = Contact.objects.filter(
            user_id=request.user.id)
        serializer = ContactSerializer(contact, many=True)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        request.data.update({'user': request.user.id})
        serializer = ContactSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return JsonResponse({'Status': False, 'Errors': serializer.errors})
        serializer.save()
        return JsonResponse({'Status': True})

    def patch(self, request, *args, **kwargs):
        serializer = UpdateContactSerializer(data=request.data)
        if not serializer.is_valid():
            return JsonResponse({'Status': False, 'Errors': serializer.errors})
        contact = Contact.objects.filter(id=request.data['id'], user_id=request.user.id)
        if contact:
            contact.update(value=request.data['value'])
            return JsonResponse({'Status': True})
        else:
            return JsonResponse({'Status': False,
                                 'Errors': 'There are no matches in the database. Data error.'})

    def delete(self, request, *args, **kwargs):
        # Working with user contacts
        contact_id = request.data.get('id')
        data_type = int
        if not contact_id or not isinstance(contact_id, data_type):
            return JsonResponse({'Status': False, 'Errors': 'Wrong request format'})
        contact = Contact.objects.filter(user_id=request.user.id, id=contact_id)
        if contact:
            contact.delete()
            return JsonResponse({'Status': True})
        else:
            return JsonResponse({'Status': False,
                                 'Errors': 'There are no matches in the database. Data error.'})


class UserOrderView(APIView):
    # Displaying user orders and changing status
    permission_classes = [IsAuthenticated, IsBuyerOnly]

    def get(self, request, *args, **kwargs):
        queryset = Order.objects.filter(
            user_id=request.user.id).exclude(status='basket').prefetch_related(
            'ordered_items__product_info__product__category',
            'ordered_items__product_info__product_parameters__parameter').annotate(
            total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price'))).distinct()
        serializer = OrderUserSerializer(queryset, many=True)
        return Response(serializer.data)

    def patch(self, request, *args, **kwargs):
        order_id = request.data.get('id')
        data_type = int
        if not order_id or not isinstance(order_id, data_type):
            return JsonResponse({'Status': False, 'Errors': 'Wrong request format'})
        order = Order.objects.filter(user_id=request.user.id, id=order_id)
        if order:
            order.update(status='new')
            new_order.send(sender=self.__class__, user_id=request.user.id)
            return JsonResponse({'Status': True})
        else:
            return JsonResponse({'Status': False,
                                 'Errors': 'There are no matches in the database. Data error.'})
