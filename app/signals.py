from django.dispatch import receiver, Signal
from django.urls import reverse
from django_rest_passwordreset.signals import reset_password_token_created
from django.core.mail import send_mail
from DeliveryService import settings
from app.models import Account
from django.contrib.auth.tokens import default_token_generator

new_order = Signal()
confirm_email = Signal()

@receiver(reset_password_token_created)
def password_reset_token_created(sender, instance, reset_password_token, *args, **kwargs):

    email_plaintext_message = f'{reverse("reset-password-request")}?token={reset_password_token.key}'

    send_mail(
        # title:
        'Website title. Password Reset.',
        # message:
        email_plaintext_message,
        # from:
        settings.EMAIL_HOST_USER,
        # to:
        [reset_password_token.user.email]
    )

@receiver(new_order)
def new_order_signal(user_id, **kwargs):
    # send an e-mail to the user
    user = Account.objects.get(id=user_id)

    send_mail(
        # title:
        f'Обновление статуса заказа',
        # message:
        'Заказ сформирован',
        # from:
        settings.EMAIL_HOST_USER,
        # to:
        [user.email]
    )


@receiver(confirm_email)
def confirm_email_signal(user_id, **kwargs):
    user = Account.objects.get(id=user_id)
    confirmation_token = default_token_generator.make_token(user)

    send_mail(
        # title:
        f'Подтверждение регистрации',
        # message:
        confirmation_token,
        # from:
        settings.EMAIL_HOST_USER,
        # to:
        [user.email]
    )