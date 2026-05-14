from django.views import View
from django.views.generic import TemplateView, FormView
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse_lazy
from app.forms import AirlineForm
from app.controllers import AirlineController
from app.utils import _get_token, _get_role_perms, _normalize_keys

class AirlineListView(TemplateView):
    template_name = 'airlines/list.html'
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(_get_role_perms(self.request))
        token = _get_token(self.request)
        page = int(self.request.GET.get('page', 1))
        data = AirlineController.get_all(page=page, size=20, access_token=token)
        ctx['items'] = [_normalize_keys(i) for i in data.get('items', [])]
        ctx['page_obj'] = {
            'number': page, 'has_previous': page > 1,
            'has_next': page < data.get('pages', 1),
            'pages': data.get('pages', 1)
        }
        return ctx

class AirlineCreateView(FormView):
    template_name = 'airlines/form.html'
    form_class = AirlineForm
    success_url = reverse_lazy('app:airline_list')
    def dispatch(self, request, *args, **kwargs):
        if request.session.get('user_role') != 'admin':
            messages.error(request, 'Доступ запрещён'); return redirect('app:index')
        return super().dispatch(request, *args, **kwargs)
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs); ctx.update(_get_role_perms(self.request)); ctx['title'] = 'Добавить авиакомпанию'
        return ctx
    def form_valid(self, form):
        token = _get_token(self.request)
        success, _, msg = AirlineController.create({'code': form.cleaned_data['code'], 'name': form.cleaned_data['name']}, token)
        if success: messages.success(self.request, msg); return super().form_valid(form)
        messages.error(self.request, msg); return self.form_invalid(form)

class AirlineUpdateView(FormView):
    template_name = 'airlines/form.html'
    form_class = AirlineForm
    success_url = reverse_lazy('app:airline_list')
    def dispatch(self, request, *args, **kwargs):
        if request.session.get('user_role') != 'admin':
            messages.error(request, 'Доступ запрещён'); return redirect('app:index')
        return super().dispatch(request, *args, **kwargs)
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs); ctx.update(_get_role_perms(self.request)); ctx['title'] = 'Редактировать авиакомпанию'
        token = _get_token(self.request)
        data = AirlineController.get_by_code(kwargs['code'], token)
        if not data: messages.error(self.request, 'Авиакомпания не найдена'); return redirect('app:airline_list')
        ctx['form'] = self.get_form(initial={'code': data.get('code'), 'name': data.get('name')})
        return ctx
    def form_valid(self, form):
        token = _get_token(self.request)
        success, _, msg = AirlineController.update(self.kwargs['code'], {'code': form.cleaned_data['code'], 'name': form.cleaned_data['name']}, token)
        if success: messages.success(self.request, msg); return super().form_valid(form)
        messages.error(self.request, msg); return self.form_invalid(form)

class AirlineDeleteView(View):
    def post(self, request, code):
        if request.session.get('user_role') != 'admin': messages.error(request, 'Доступ запрещён'); return redirect('app:airline_list')
        token = _get_token(request)
        if AirlineController.delete(code, token): messages.success(request, 'Авиакомпания удалена')
        else: messages.error(request, 'Ошибка удаления')
        return redirect('app:airline_list')