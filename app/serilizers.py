from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from app.models import Account, Shop, Category, Product, ProductInfo, \
    ProductParameter, Order, OrderItem, Contact
from rest_framework.serializers import ModelSerializer
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError as PasswordValidationErrror


class RegistrationSerializer(ModelSerializer):
    class Meta:
        model = Account
        fields = ['email', 'password', 'first_name', 'last_name', 'surname', 'position']

    extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        try:
            validate_password(validated_data['password'])
        except PasswordValidationErrror as error:
            raise serializers.ValidationError({'Status': False, 'Errors': f'{error}'})
        user = Account.objects.create(
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            surname=validated_data['surname'],
            position=validated_data['position'],
        )
        user.set_password(validated_data['password'])
        user.save()

        return user


class CustomAuthTokenSerializer(serializers.Serializer):
    email = serializers.CharField()
    password = serializers.CharField()

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')
        if email and password:
            user = authenticate(request=self.context.get('request'),
                                email=email, password=password)
            if not user:
                raise serializers.ValidationError({'Status': False,
                                                   'Errors': 'Unable to log in with provided credentials.'})
        else:
            raise serializers.ValidationError({'Status': False,
                                               'Errors': 'Must include "username" and "password.'})

        data['user'] = user
        return data


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ['id', 'type', 'value', 'user']
        read_only_fields = ['id']
        extra_kwargs = {
            'user': {'write_only': True}
        }

    def create(self, validated_data):
        contact_phone_query = Contact.objects.filter(type='phone', user_id=self.context.get(
                "request").user.id).count()
        contact_address_query = Contact.objects.filter(type='address', user_id=self.context.get(
                "request").user.id).count()
        if validated_data['type'] == 'phone' and contact_phone_query >= 1:
            raise serializers.ValidationError({'Status': False,
                                               'Errors': 'User can only have 1 phone.'})
        if validated_data['type'] == 'address' and contact_address_query >= 1:
            raise serializers.ValidationError({'Status': False,
                                               'Errors': 'User can only have 1 address'})
        return Contact.objects.create(**validated_data)


class UserSerializer(serializers.ModelSerializer):
    contacts = ContactSerializer(read_only=True, many=True)

    class Meta:
        model = Account
        fields = ['id', 'email', 'first_name', 'last_name', 'surname', 'position', 'type_account',
                  'contacts']
        extra_kwargs = {"email": {"required": False, "allow_null": True},
                        "first_name": {"required": False, "allow_null": True},
                        "last_name": {"required": False, "allow_null": True},
                        "surname": {"required": False, "allow_null": True},
                        "position": {"required": False, "allow_null": True}}
        read_only_fields = ['id', 'type_account']


class ShopSerializer(ModelSerializer):
    class Meta:
        model = Shop
        fields = ['id', 'name', 'status']
        read_only_fields = ['id']
        extra_kwargs = {"user": {"write_only": True}}

class CategorySerializer(ModelSerializer):
    shops = ShopSerializer(many=True)
    class Meta:
        model = Category
        fields = ['id', 'shops', 'name']
        read_only_fields = ['id']

class ProductSerializer(serializers.ModelSerializer):
    category = serializers.StringRelatedField()

    class Meta:
        model = Product
        fields = ['name', 'category']


class ProductParameterSerializer(serializers.ModelSerializer):
    parameter = serializers.StringRelatedField()

    class Meta:
        model = ProductParameter
        fields = ['parameter', 'value']


class ProductInfoSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_parameters = ProductParameterSerializer(read_only=True, many=True)

    class Meta:
        model = ProductInfo
        fields = ['id', 'shop', 'quantity', 'price', 'price_rrc', 'product', 'product_parameters']
        read_only_fields = ['id']


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['id', 'product_info', 'quantity', 'order']
        read_only_fields = ['id']
        extra_kwargs = {
            'order': {'write_only': True}
        }


class OrderItemCreateSerializer(OrderItemSerializer):
    product_info = ProductInfoSerializer(read_only=True)


class UserContactOrderSerializer(serializers.ModelSerializer):
    contacts = ContactSerializer(read_only=True, many=True)

    class Meta:
        model = Account
        fields = ['id', 'contacts']
        read_only_fields = ['id']


class OrderPartnerSerializer(serializers.ModelSerializer):
    ordered_items = OrderItemCreateSerializer(read_only=True, many=True)
    total_sum = serializers.IntegerField()
    user = UserContactOrderSerializer(read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'ordered_items', 'status', 'dt', 'total_sum', 'user', ]
        read_only_fields = ['id']


class OrderUserSerializer(serializers.ModelSerializer):
    ordered_items = OrderItemCreateSerializer(read_only=True, many=True)
    total_sum = serializers.IntegerField()

    class Meta:
        model = Order
        fields = ['id', 'ordered_items', 'status', 'dt', 'total_sum']
        read_only_fields = ['id']


class UpdateBusketSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    quantity = serializers.IntegerField()


class UpdateContactSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    value = serializers.CharField()
