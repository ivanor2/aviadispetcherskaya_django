# app/forms/auth_form.py
from django import forms
import re


class LoginForm(forms.Form):
    """Форма входа"""
    username = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Имя пользователя',
            'autocomplete': 'username'
        }),
        label='Имя пользователя'
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Пароль',
            'autocomplete': 'current-password'
        }),
        label='Пароль'
    )


class RegisterForm(forms.Form):
    """Форма регистрации"""
    username = forms.CharField(
        max_length=50,
        min_length=3,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Имя пользователя (мин. 3 символа)',
            'autocomplete': 'username'
        }),
        label='Имя пользователя'
    )
    password = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Пароль (мин. 8 символов)',
            'autocomplete': 'new-password'
        }),
        label='Пароль'
    )
    password_confirm = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Подтвердите пароль',
            'autocomplete': 'new-password'
        }),
        label='Подтверждение пароля'
    )

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')

        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError('Пароли не совпадают')

        # Проверка сложности пароля
        if password:
            if not re.search(r'[A-Za-z]', password):
                raise forms.ValidationError('Пароль должен содержать буквы')
            if not re.search(r'\d', password):
                raise forms.ValidationError('Пароль должен содержать цифры')
            if not re.search(r'[!@#$%^&*()_+=-]', password):
                raise forms.ValidationError('Пароль должен содержать спецсимволы')

        return cleaned_data