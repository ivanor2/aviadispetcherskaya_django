# app/controllers/__init__.py
from .booking_controller import BookingController
from .flight_controller import FlightController
from .passenger_controller import PassengerController
from .auth_controller import AuthController
from .airline_controller import AirlineController
from .airport_controller import AirportController

__all__ = [
    'BookingController',
    'FlightController',
    'PassengerController',
    'AuthController',
    'AirlineController', 'AirportController'
]