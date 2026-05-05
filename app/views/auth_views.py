from django.views import View
from django.views.generic import FormView
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse_lazy
from app.forms import LoginForm, RegisterForm
from app.controllers import AuthController


class LoginView(FormView):
    template_name = 'auth/login.html'
    form_class = LoginForm
    success_url = reverse_lazy('app:index')

    def get_success_url(self):
        return self.request.GET.get('next', self.success_url)

    def get(self, request, *args, **kwargs):
        if request.session.get('access_token'):
            return redirect(self.get_success_url())
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        success, tokens, message = AuthController.login(
            form.cleaned_data['username'], form.cleaned_data['password']
        )
        if not success:
            messages.error(self.request, message)
            return self.form_invalid(form)

        self.request.session['access_token'] = tokens.get('access_token')
        self.request.session['refresh_token'] = tokens.get('refreshToken', '')

        user_data = AuthController.get_current_user(tokens.get('access_token'))
        if user_data:
            self.request.session['user_info'] = user_data
            self.request.session['user_role'] = user_data.get('role', 'guest')

        messages.success(self.request, f'Добро пожаловать, {form.cleaned_data["username"]}!')
        return redirect(self.get_success_url())


class RegisterView(FormView):
    template_name = 'auth/register.html'
    form_class = RegisterForm
    success_url = reverse_lazy('app:login')

    def form_valid(self, form):
        success, data, message = AuthController.register(
            form.cleaned_data['username'], form.cleaned_data['password']
        )
        if not success:
            detail = data.get('detail', message) if isinstance(data, dict) else message
            messages.error(self.request, detail)
            return self.form_invalid(form)

        messages.success(self.request, 'Регистрация успешна! Войдите в систему.')
        return redirect('app:login')


class LogoutView(View):
    def get(self, request):
        token = request.session.get('access_token')
        if token:
            AuthController.logout(token)
        request.session.flush()
        messages.success(request, 'Вы вышли из системы')
        return redirect('app:login')