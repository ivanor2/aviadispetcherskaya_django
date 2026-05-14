from .index_views import IndexView
from .auth_views import LoginView, RegisterView, LogoutView
from .flight_views import FlightListView, FlightSearchView, FlightCreateView, FlightDetailView, FlightDeleteView, FlightDeleteAllView
from .passenger_views import PassengerListView, PassengerCreateView, PassengerDetailView, PassengerSearchView, PassengerDeleteView
from .booking_views import BookingCreateView, BookingConnectionView, BookingCancelView, BookingFlightSelectView, BookingDeleteView
from .user_views import UserManagementView, UserEditView
from .airline_views import AirlineListView, AirlineCreateView, AirlineUpdateView, AirlineDeleteView
from .airport_views import AirportListView, AirportCreateView, AirportUpdateView, AirportDeleteView

__all__ = [
    'IndexView',
    'LoginView', 'RegisterView', 'LogoutView',
    'FlightListView', 'FlightSearchView', 'FlightCreateView', 'FlightDetailView', 'FlightDeleteView', 'FlightDeleteAllView',
    'PassengerListView', 'PassengerCreateView', 'PassengerDetailView', 'PassengerSearchView', 'PassengerDeleteView',
    'BookingCreateView', 'BookingConnectionView', 'BookingCancelView', 'BookingFlightSelectView', 'BookingDeleteView',
    'UserManagementView', 'UserEditView',
    'AirlineListView', 'AirlineCreateView', 'AirlineUpdateView', 'AirlineDeleteView',
    'AirportListView', 'AirportCreateView', 'AirportUpdateView', 'AirportDeleteView'
]