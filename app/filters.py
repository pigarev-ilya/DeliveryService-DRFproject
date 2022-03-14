import django_filters
from django_filters.rest_framework import FilterSet

from app.models import ProductInfo


class ProductFilterSet(FilterSet):
    category = django_filters.NumberFilter(field_name='product__category_id')
    product = django_filters.NumberFilter(field_name='product_id')
    shop = django_filters.NumberFilter(field_name='shop_id')

    class Meta:
        model = ProductInfo
        fields = ['category', 'product', 'shop']