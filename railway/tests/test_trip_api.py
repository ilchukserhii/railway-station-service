import uuid
from datetime import timedelta, datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.core.exceptions import ValidationError

from rest_framework.test import APIClient
from rest_framework import status

from railway.models import Station, Route, Train, TrainType, Crew, Trip
from railway.serializers import TripListSerializer, TripRetrieveSerializer, TripSerializer

TRIP_URL = reverse("railway:trip-list")

def detail_url(trip_id):
    return reverse("railway:trip-detail", args=[trip_id])


def sample_station(**params):
    defaults = {
        "name": str(uuid.uuid4()),
        "latitude": 10.00,
        "longitude": 10.00,
    }
    defaults.update(params)
    return Station.objects.create(**defaults)

def sample_route(**params):
    source = sample_station()
    destination = sample_station()
    defaults = {
        "source": source,
        "destination": destination,
        "distance": 100,
    }
    defaults.update(params)
    return Route.objects.create(**defaults)

def sample_train_type(**params):
    defaults = {
        "name": str(uuid.uuid4()),
    }
    defaults.update(params)
    return TrainType.objects.create(**defaults)

def sample_train(**params):
    train_type = sample_train_type()
    defaults = {
        "name": str(uuid.uuid4()),
        "wagons_num": 10,
        "seats_in_wagon": 10,
        "train_type": train_type,
    }
    defaults.update(params)
    return Train.objects.create(**defaults)

def sample_crew(**params):
    defaults = {
        "first_name": "John",
        "last_name": "Doe",
        "role": "driver",
    }
    defaults.update(params)
    return Crew.objects.create(**defaults)

def sample_trip(**params):
    route = sample_route()
    train = sample_train()
    defaults = {
        "route": route,
        "train": train,
        "departure_time": timezone.now(),
        "arrival_time": timezone.now() + timedelta(hours=2),
        "price": 1000,
    }
    defaults.update(params)
    crew = defaults.pop("crew", [])
    trip = Trip.objects.create(**defaults)
    if crew:
        trip.crew.set(crew)
    return trip


class TripModelApiTest(TestCase):
    def test_arrival_time_gte_departure_time(self):
        with self.assertRaisesMessage(
            ValidationError,
            "Arrival time must be greater than departure time"
        ):
            sample_trip(
                departure_time=timezone.now() + timedelta(hours=2),
                arrival_time=timezone.now()
            )


class UnauthenticatedTripApiTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_unauthenticated_trip_list(self):
        sample_trip()
        sample_trip()

        res = self.client.get(TRIP_URL)
        returned_ids = [item["id"] for item in res.data["results"]]

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(returned_ids), 2)

    def test_unauthenticated_trip_detail(self):
        trip = sample_trip()
        url = detail_url(trip.id)

        res = self.client.get(url)
        serializer = TripRetrieveSerializer(trip)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(serializer.data, res.data)

    def test_filter_trip_by_departure_or_arrival_time(self):
        trip = sample_trip(
            departure_time=timezone.make_aware(
                datetime(2026, 5, 28, 15, 0)
            ),
            arrival_time=timezone.make_aware(
                datetime(2026, 5, 28, 17, 0)
            )
        )
        trip_2 = sample_trip(
            departure_time=timezone.make_aware(
                datetime(2026, 6, 1, 15, 0)
            ),
            arrival_time=timezone.make_aware(
                datetime(2026, 6, 1, 17, 0)
            )
        )

        res_departure = self.client.get(TRIP_URL, data={"departure": "2026-06-01"})
        res_arrival = self.client.get(TRIP_URL, data={"arrival": "2026-05-28"})

        returned_ids_departure = [item["id"] for item in res_departure.data["results"]]
        returned_ids_arrival = [item["id"] for item in res_arrival.data["results"]]

        self.assertIn(trip_2.id, returned_ids_departure)
        self.assertNotIn(trip.id, returned_ids_departure)
        self.assertIn(trip.id, returned_ids_arrival)
        self.assertNotIn(trip_2.id, returned_ids_arrival)

    def test_filter_trip_by_route(self):
        station_1 = sample_station(name="Station 1")
        station_2 = sample_station(name="Station 2")
        station_3 = sample_station(name="Station 3")
        station_4 = sample_station(name="Station 4")
        route_1 = sample_route(source=station_1, destination=station_2)
        route_2 = sample_route(source=station_3, destination=station_4)
        trip = sample_trip(route=route_1)
        trip_2 = sample_trip(route=route_2)

        res = self.client.get(TRIP_URL, data={"route": "Station 1"})

        returned_ids = [item["id"] for item in res.data["results"]]

        self.assertIn(trip.id, returned_ids)
        self.assertNotIn(trip_2.id, returned_ids)

    def test_filter_trip_by_train(self):
        train_type_1 = sample_train_type(name="Train 1")
        train_type_2 = sample_train_type(name="Train 2")
        train_1 = sample_train(train_type=train_type_1)
        train_2 = sample_train(train_type=train_type_2)
        trip_1 = sample_trip(train=train_1)
        trip_2 = sample_trip(train=train_2)

        res = self.client.get(TRIP_URL, data={"train": "Train 1"})

        returned_ids = [item["id"] for item in res.data["results"]]

        self.assertIn(trip_1.id, returned_ids)
        self.assertNotIn(trip_2.id, returned_ids)

class AdminTripApiTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@admin.com", "admin123", is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_trip(self):
        route = sample_route()
        train = sample_train()
        crew = sample_crew()

        payload = {
            "route": route.id,
            "train": train.id,
            "departure_time": timezone.now(),
            "arrival_time": timezone.now() + timedelta(hours=2),
            "crew": [crew.id],
            "price": 1000,
        }

        res = self.client.post(TRIP_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        trip = Trip.objects.get(id=res.data["id"])
        serializer = TripSerializer(trip)

        self.assertEqual(serializer.data, res.data)

    def test_update_trip(self):
        route = sample_route()
        train = sample_train()
        crew = sample_crew()
        trip = sample_trip(
            route=route,
            train=train,
            departure_time=timezone.now(),
            arrival_time=timezone.now() + timedelta(hours=2),
            crew=[crew.id],
            price=1000,
        )

        payload = {
            "route": route.id,
            "train": train.id,
            "departure_time": timezone.now(),
            "arrival_time": timezone.now() + timedelta(hours=2),
            "crew": [crew.id],
            "price": 800,
        }

        url = detail_url(trip.id)

        res = self.client.put(url, payload)
        trip.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(trip.price, 800)

    def test_delete_trip(self):
        route = sample_route()
        train = sample_train()
        crew = sample_crew()
        trip = sample_trip(
            route=route,
            train=train,
            departure_time=timezone.now(),
            arrival_time=timezone.now() + timedelta(hours=2),
            crew=[crew.id],
            price=1000,
        )
        url = detail_url(trip.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
