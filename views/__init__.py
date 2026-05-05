from .index_views import IndexView
from .auth_views import LoginView, RegisterView, LogoutView
from .flight_views import FlightListView, FlightSearchView, FlightCreateView, FlightDetailView, FlightDeleteView, FlightDeleteAllView
from .passenger_views import PassengerListView, PassengerCreateView, PassengerDetailView, PassengerSearchView, PassengerDeleteView
from .booking_views import BookingCreateView, BookingConnectionView, BookingCancelView, BookingFlightSelectView, BookingDeleteView

__all__ = [
    'IndexView',
    'LoginView', 'RegisterView', 'LogoutView',
    'FlightListView', 'FlightSearchView', 'FlightCreateView', 'FlightDetailView', 'FlightDeleteView', 'FlightDeleteAllView',
    'PassengerListView', 'PassengerCreateView', 'PassengerDetailView', 'PassengerSearchView', 'PassengerDeleteView',
    'BookingCreateView', 'BookingConnectionView', 'BookingCancelView', 'BookingFlightSelectView', 'BookingDeleteView',
]