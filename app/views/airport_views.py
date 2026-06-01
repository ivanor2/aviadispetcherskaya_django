from django.views import View
from django.views.generic import TemplateView, FormView
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse_lazy
from app.forms import AirportForm
from app.controllers import AirportController
from app.utils import _get_token, _get_role_perms, _normalize_keys

class AirportListView(TemplateView):
    template_name = 'airports/list.html'
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(_get_role_perms(self.request))
        token = _get_token(self.request)
        page = int(self.request.GET.get('page', 1))
        data = AirportController.get_all(page=page, size=20, access_token=token)
        ctx['items'] = [_normalize_keys(i) for i in data.get('items', [])]
        ctx['page_obj'] = {
            'number': page, 'has_previous': page > 1,
            'has_next': page < data.get('pages', 1),
            'pages': data.get('pages', 1)
        }
        return ctx

class AirportCreateView(FormView):
    template_name = 'airports/form.html'
    form_class = AirportForm
    success_url = reverse_lazy('app:airport_list')
    def dispatch(self, request, *args, **kwargs):
        if request.session.get('user_role') != 'admin':
            messages.error(request, 'Доступ запрещён'); return redirect('app:index')
        return super().dispatch(request, *args, **kwargs)
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs); ctx.update(_get_role_perms(self.request)); ctx['title'] = 'Добавить аэропорт'
        return ctx
    def form_valid(self, form):
        token = _get_token(self.request)
        success, _, msg = AirportController.create({'icaoCode': form.cleaned_data['icao_code'], 'name': form.cleaned_data['name']}, token)
        if success: messages.success(self.request, msg); return super().form_valid(form)
        messages.error(self.request, msg); return self.form_invalid(form)

class AirportUpdateView(FormView):
    template_name = 'airports/edit.html'
    form_class = AirportForm
    success_url = reverse_lazy('app:airport_list')
    def dispatch(self, request, *args, **kwargs):
        if request.session.get('user_role') != 'admin':
            messages.error(request, 'Доступ запрещён'); return redirect('app:index')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        token = _get_token(request)
        data = AirportController.get_by_id(self.kwargs['pk'], token)
        if not data:
            messages.error(request, 'Аэропорт не найден')
            return redirect('app:airport_list')
        self.airport_data = data
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(_get_role_perms(self.request))
        ctx['title'] = 'Редактировать аэропорт'

        data = getattr(self, 'airport_data', None)
        if data:
            form_class = self.get_form_class()
            ctx['form'] = form_class(initial={'icao_code': data.get('icao_code'), 'name': data.get('name')})

        return ctx

    def form_valid(self, form):
        token = _get_token(self.request)
        success, _, msg = AirportController.update(self.kwargs['pk'], {'icaoCode': form.cleaned_data['icao_code'], 'name': form.cleaned_data['name']}, token)
        if success: messages.success(self.request, msg); return super().form_valid(form)
        messages.error(self.request, msg); return self.form_invalid(form)

class AirportDeleteView(View):
    def post(self, request, pk):
        if request.session.get('user_role') != 'admin': messages.error(request, 'Доступ запрещён'); return redirect('app:airport_list')
        token = _get_token(request)
        if AirportController.delete(pk, token): messages.success(request, 'Аэропорт удалён')
        else: messages.error(request, 'Ошибка удаления')
        return redirect('app:airport_list')