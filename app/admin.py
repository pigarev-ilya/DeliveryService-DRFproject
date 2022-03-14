from django.contrib import admin

# Register your models here.
from django.contrib.auth.admin import UserAdmin






from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from app.models import Account

class CustomUserCreationForm(UserCreationForm):

    class Meta(UserCreationForm):
        model = Account
        fields = ('email',)

class CustomUserChangeForm(UserChangeForm):

    class Meta:
        model = Account
        fields = ('email',)




class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = Account
    list_display = ('email', 'is_staff', 'is_active',)
    list_filter = ('email', 'is_staff', 'is_active',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Permissions', {'fields': ('is_staff', 'is_active')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'is_staff', 'is_active')}
        ),
    )
    search_fields = ('email',)
    ordering = ('email',)

admin.site.register(Account, CustomUserAdmin)