# app/urls.py
from django.urls import path
from app import views
from django.contrib.auth import views as auth_views

app_name = 'app'

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
    path('passengers/create/', views.PassengerCreateView.as_view(), name='passenger_create'),
    path('passengers/<int:pk>/delete/', views.PassengerDeleteView.as_view(), name='passenger_delete'),
    path('passengers/<int:pk>/', views.PassengerDetailView.as_view(), name='passenger_detail'),
    path('passengers/search/', views.PassengerSearchView.as_view(), name='passenger_search'),

    # Бронирования
    path('bookings/create/<int:flight_id>/', views.BookingCreateView.as_view(), name='booking_create'),
    path('bookings/cancel/<int:booking_id>/', views.BookingCancelView.as_view(), name='booking_cancel'),
    path('bookings/<int:booking_id>/delete/', views.BookingDeleteView.as_view(), name='booking_delete'),
    path('bookings/select/', views.BookingFlightSelectView.as_view(), name='booking_select'),
    path('bookings/add-connection/', views.BookingConnectionView.as_view(), name='booking_add_connection'),

]