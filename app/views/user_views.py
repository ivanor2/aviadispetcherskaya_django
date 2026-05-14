from django.views import View
from django.views.generic import TemplateView, FormView
from django.shortcuts import redirect
from django.contrib import messages
from django import forms
from app.controllers import AuthController
from app.utils import _get_token, _get_role_perms


class UserManagementView(TemplateView):
    template_name = 'users/list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        perms = _get_role_perms(self.request)
        context.update(perms)

        if not perms.get('can_manage_users'):
            messages.error(self.request, 'Доступ запрещён')
            return redirect('app:index')

        token = _get_token(self.request)
        page_num = int(self.request.GET.get('page', 1))
        data = AuthController.get_all_users(page=page_num, size=50, access_token=token)

        context.update({
            'users': data.get('items', []),
            'page_obj': type('PageObj', (), {
                'number': page_num,
                'paginator': type('Paginator', (), {'num_pages': data.get('pages', 1)})()
            })()
        })
        return context


class UserEditForm(forms.Form):
    role = forms.ChoiceField(
        choices=[('guest', 'Гость'), ('dispatcher', 'Диспетчер'), ('admin', 'Администратор')],
        label='Роль пользователя'
    )


class UserEditView(FormView):
    template_name = 'users/edit.html'
    form_class = UserEditForm

    def dispatch(self, request, *args, **kwargs):
        if request.session.get('user_role') != 'admin':
            messages.error(request, 'Доступ запрещён. Требуются права администратора.')
            return redirect('app:index')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user_id'] = self.kwargs.get('pk')
        return context

    def form_valid(self, form):
        token = _get_token(self.request)
        user_id = self.kwargs.get('pk')
        success, data, msg = AuthController.update_user_role(user_id, form.cleaned_data['role'], token)
        if success:
            messages.success(self.request, msg)
        else:
            messages.error(self.request, msg)
        return redirect('app:user_list')