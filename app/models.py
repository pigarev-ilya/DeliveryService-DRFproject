from django.contrib.auth.base_user import AbstractBaseUser

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.contrib.auth.models import PermissionsMixin
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from app.managers import CustomUserManager


class Account(AbstractBaseUser, PermissionsMixin):
    USER_TYPE_CHOICES = (
        ('seller', 'Продавец'),
        ('buyer', 'Покупатель'),

    )
    email = models.EmailField(_('email address'), unique=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    first_name = models.CharField(verbose_name='Имя', max_length=100, null=False, blank=False)
    last_name = models.CharField(verbose_name='Фамилия', max_length=100, null=False, blank=False)
    surname = models.CharField(verbose_name='Отчество', max_length=100, null=False, blank=False)
    position = models.CharField(verbose_name='Должность', max_length=100, null=False, blank=False)
    type_account = models.CharField(verbose_name='Тип пользователя', choices=USER_TYPE_CHOICES,
                                    max_length=6, default='buyer')
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    objects = CustomUserManager()

    class Meta:
        verbose_name = _('Пользователь')
        verbose_name_plural = _('Пользователи')
        ordering = ('email',)

    def __str__(self):
        return self.email


class Shop(models.Model):
    name = models.CharField(verbose_name='Название', max_length=128, null=False, blank=False)
    url = models.URLField(verbose_name='Ссылка на прайс', null=False, blank=False)
    filename = models.CharField(verbose_name='Название файла', max_length=128, null=False, blank=False),
    user = models.ForeignKey(Account, verbose_name='Продавец', related_name='user_shops',
                             null=True, blank=True, on_delete=models.CASCADE)
    status = models.BooleanField(verbose_name='статус получения заказов', default=True)


    class Meta:
        verbose_name = "Магазин"
        verbose_name_plural = "Магазины"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Category(models.Model):
    shops = models.ManyToManyField(Shop, verbose_name='Магазин', blank=False, related_name='category')
    name = models.CharField(verbose_name='Название категории', max_length=128, null=False, blank=False)

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(Category, verbose_name='Категория', on_delete=models.CASCADE, related_name='products')
    name = models.CharField(verbose_name='Название продукта', max_length=128, null=False, blank=False)

    class Meta:
        verbose_name = "Продукт"
        verbose_name_plural = "Продукты"
        ordering = ["name"]

    def __str__(self):
        return self.name


class ProductInfo(models.Model):
    product = models.ForeignKey(Product, verbose_name='Продукт', on_delete=models.CASCADE, null=False, blank=False,
                                related_name='product_infos')
    shop = models.ForeignKey(Shop, verbose_name='Магазин', on_delete=models.CASCADE, null=False, blank=False,
                             related_name='product_infos')
    quantity = models.PositiveIntegerField(default=1, verbose_name='Количество', null=False, blank=False)
    price = models.DecimalField(verbose_name='Цена', null=False, blank=False, decimal_places=2, max_digits=20,
                                validators=[MinValueValidator(0)])
    price_rrc = models.DecimalField(verbose_name='Рекомендуемая розничная цена', null=False, blank=False,
                                    decimal_places=2, max_digits=20, validators=[MinValueValidator(0)])

    class Meta:
        verbose_name = "Информация о продукте"
        verbose_name_plural = "Информация о продуктах"
        ordering = ["product"]

    constraints = [
        models.UniqueConstraint(fields=['product', 'shop'], name='unique_product_info'),
    ]


class Parameter(models.Model):
    name = models.CharField(verbose_name='Название параметра', max_length=128, null=False, blank=False)

    class Meta:
        verbose_name = "Название параметра"
        verbose_name_plural = "Название параметров"
        ordering = ["name"]

    def __str__(self):
        return self.name


class ProductParameter(models.Model):
    product_info = models.ForeignKey(ProductInfo, verbose_name='Информация о продукте',
                                     on_delete=models.CASCADE, null=False, blank=False,
                                     related_name='product_parameters')
    parameter = models.ForeignKey(Parameter, verbose_name='Параметр', on_delete=models.CASCADE, null=False, blank=False,
                                  related_name='product_parameters')
    value = models.CharField(verbose_name='Значение', max_length=128, null=False, blank=False)

    class Meta:
        verbose_name = "Параметр продукта"
        verbose_name_plural = "Параметры продукта"
        ordering = ["value"]

    constraints = [
        models.UniqueConstraint(fields=['product_info', 'parameter'], name='unique_parameter_product_info'),
    ]


class Order(models.Model):
    CHOICES_STATUS = (
        ('basket', 'Статус корзины'),
        ('new', 'Новый'),
        ('confirmed', 'Подтвержден'),
        ('assembled', 'Собран'),
        ('sent', 'Отправлен'),
        ('delivered', 'Доставлен'),
        ('canceled', 'Отменен'),
    )

    user = models.ForeignKey(Account, verbose_name='Пользователь', on_delete=models.CASCADE,
                             null=False, blank=False, related_name='orders')
    dt = models.DateTimeField(verbose_name='Дата создания', auto_now_add=True)
    status = models.CharField(verbose_name='Статус заказа', max_length=100, choices=CHOICES_STATUS, default='new')


    class Meta:
        verbose_name = "Контакт"
        verbose_name_plural = "Контакты"
        ordering = ["dt"]

    def __str__(self):
        return f"{self.dt}, {self.status}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, verbose_name='Заказ', on_delete=models.CASCADE, null=False, blank=False,
                              related_name='ordered_items')
    product_info = models.ForeignKey(ProductInfo, verbose_name='Продукт', on_delete=models.CASCADE,
                                     null=False, blank=False, related_name='ordered_items')
    quantity = models.PositiveIntegerField(verbose_name='Количество', null=False, blank=False, )

    class Meta:
        verbose_name = "Позиция в заказе"
        verbose_name_plural = "Позиции в заказе"
        ordering = ["order"]




class Contact(models.Model):
    CHOICES_CONTACT = (
        ('address', 'Адрес'),
        ('phone', 'Телефон'),
    )


    type = models.CharField(verbose_name='Тип', max_length=100, choices=CHOICES_CONTACT, default='phone')
    user = models.ForeignKey(Account, verbose_name='Пользователь', on_delete=models.CASCADE, null=False, blank=False,
                             related_name='contacts')
    value = models.CharField(verbose_name='Данные', max_length=50, null=False, blank=False)


    class Meta:
        verbose_name = "Контакт"
        verbose_name_plural = "Контакты"
        ordering = ["user"]

    def __str__(self):
        return f"{self.type}, {self.value}"

