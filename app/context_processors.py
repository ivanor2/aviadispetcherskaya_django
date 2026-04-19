# app/context_processors.py
def user_role(request):
    """Добавляет информацию о пользователе и роли в контекст всех шаблонов"""
    return {
        'user_info': request.session.get('user_info'),
        'user_role': request.session.get('user_role', 'guest'),
        'is_authenticated': request.session.get('access_token') is not None,
        'is_admin': request.session.get('user_role') == 'admin',
        'is_dispatcher': request.session.get('user_role') == 'dispatcher',
        'is_guest': request.session.get('user_role') == 'guest',
    }