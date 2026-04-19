# app/forms/__init__.py
from .flight_form import FlightForm, FlightSearchForm
from .passenger_form import PassengerForm, PassengerSearchForm
from .booking_form import BookingForm, BookingCancelForm
from .airport_form import AirportForm
from .auth_form import LoginForm, RegisterForm

__all__ = [
    'FlightForm', 'FlightSearchForm',
    'PassengerForm', 'PassengerSearchForm',
    'BookingForm', 'BookingCancelForm',
    'AirportForm',
    'LoginForm', 'RegisterForm'
]