from django.views.generic import TemplateView
from app.controllers import FlightController, PassengerController
from app.utils import _get_role_perms, _get_token, _normalize_keys, _fetch_airlines_map, _fetch_airports_map, _enrich_flights_data

class IndexView(TemplateView):
    template_name = 'index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_get_role_perms(self.request))
        token = _get_token(self.request)

        try:
            flights_data = FlightController.get_all_flights(page=1, size=50, access_token=token)
            passengers_meta = PassengerController.get_all_passengers(page=1, size=1, access_token=token)

            all_items = flights_data.get('items', [])
            normalized_all = _normalize_keys(all_items)

            airlines_map = _fetch_airlines_map(self.request)
            airports_map = _fetch_airports_map(self.request)

            enriched_all = _enrich_flights_data(normalized_all, airlines_map, airports_map)
            active_count = sum(1 for f in normalized_all if f.get('free_seats', 0) > 0)

            context.update({
                'total_flights': flights_data.get('total', 0),
                'total_passengers': passengers_meta.get('total', 0),
                'active_flights': active_count,
                'total_bookings': 0,
                'recent_flights': enriched_all[:6],
                'flights_for_booking': enriched_all,
            })
        except Exception:
            context.update({
                'total_flights': 0, 'total_passengers': 0,
                'active_flights': 0, 'total_bookings': 0,
                'recent_flights': [], 'flights_for_booking': []
            })
        return context