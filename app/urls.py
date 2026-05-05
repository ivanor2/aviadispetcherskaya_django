# app/urls.py
from django.urls import path
from app.views import (
    IndexView,
    LoginView, RegisterView, LogoutView,
    FlightListView, FlightSearchView, FlightCreateView, FlightDetailView, FlightDeleteView, FlightDeleteAllView,
    PassengerListView, PassengerCreateView, PassengerDetailView, PassengerSearchView, PassengerDeleteView,
    BookingCreateView, BookingConnectionView, BookingCancelView, BookingFlightSelectView, BookingDeleteView
)
from django.contrib.auth import views as auth_views

app_name = 'app'

urlpatterns = [
    # Главная страница
    path('login/', LoginView.as_view(), name='login'),
    path('register/', RegisterView.as_view(), name='register'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('', IndexView.as_view(), name='index'),

    # Рейсы
    path('flights/', FlightListView.as_view(), name='flight_list'),
    path('flights/<int:pk>/', FlightDetailView.as_view(), name='flight_detail'),
    path('flights/create/', FlightCreateView.as_view(), name='flight_create'),
    path('flights/search/', FlightSearchView.as_view(), name='flight_search'),
    path('flights/<int:pk>/delete/', FlightDeleteView.as_view(), name='flight_delete'),
    path('flights/delete-all/', FlightDeleteAllView.as_view(), name='flight_delete_all'),

    # Пассажиры
    path('passengers/', PassengerListView.as_view(), name='passenger_list'),
    path('passengers/create/', PassengerCreateView.as_view(), name='passenger_create'),
    path('passengers/<int:pk>/delete/', PassengerDeleteView.as_view(), name='passenger_delete'),
    path('passengers/<int:pk>/', PassengerDetailView.as_view(), name='passenger_detail'),
    path('passengers/search/', PassengerSearchView.as_view(), name='passenger_search'),

    # Бронирования
    path('bookings/create/<int:flight_id>/', BookingCreateView.as_view(), name='booking_create'),
    path('bookings/cancel/<int:booking_id>/', BookingCancelView.as_view(), name='booking_cancel'),
    path('bookings/<int:booking_id>/delete/', BookingDeleteView.as_view(), name='booking_delete'),
    path('bookings/select/', BookingFlightSelectView.as_view(), name='booking_select'),
    path('bookings/add-connection/', BookingConnectionView.as_view(), name='booking_add_connection'),
]