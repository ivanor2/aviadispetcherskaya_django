# app/urls.py
from django.urls import path
from app import views
from django.contrib.auth import views as auth_views

app_name = 'app'  # ✅ Пространство имён

urlpatterns = [
    # Главная страница
    path('login/', views.LoginView.as_view(), name='login'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('logout/', views.LogoutView.as_view(), name='logout'),

    path('logout/', auth_views.LogoutView.as_view(next_page='app:index'), name='logout'),
    path('', views.IndexView.as_view(), name='index'),

    # Рейсы
    path('flights/', views.FlightListView.as_view(), name='flight_list'),
    path('flights/<int:pk>/', views.FlightDetailView.as_view(), name='flight_detail'),
    path('flights/create/', views.FlightCreateView.as_view(), name='flight_create'),
    path('flights/search/', views.FlightSearchView.as_view(), name='flight_search'),
    path('flights/<int:pk>/delete/', views.FlightDeleteView.as_view(), name='flight_delete'),
    path('flights/delete-all/', views.FlightDeleteAllView.as_view(), name='flight_delete_all'),

    # Пассажиры
    path('passengers/', views.PassengerListView.as_view(), name='passenger_list'),
    path('passengers/search/', views.PassengerSearchView.as_view(), name='passenger_search'),

    # Бронирования
    path('bookings/create/<int:flight_id>/', views.BookingCreateView.as_view(), name='booking_create'),
    path('bookings/cancel/<int:booking_id>/', views.BookingCancelView.as_view(), name='booking_cancel'),
]