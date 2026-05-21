import uuid
from datetime import timedelta, datetime
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import Count
from django.test import TestCase

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from railway.models import Station, Route, TrainType, Train, Crew, Trip, Order, Ticket
from railway.serializers import OrderSerializer, OrderListSerializer, OrderRetrieveSerializer

ORDERS_URL = reverse("railway:order-list")


def detail_url(order_id):
    return reverse("railway:order-detail", args=[order_id])


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


def sample_user(**params):
    defaults = {
        "email": f"{uuid.uuid4()}@email.com",
        "password": "password",
    }
    defaults.update(params)
    return get_user_model().objects.create_user(**defaults)


def sample_order(**params):
    defaults = {
        "user": sample_user(),
    }
    defaults.update(params)
    return Order.objects.create(**defaults)


def sample_ticket(**params):
    trip = sample_trip()
    order = sample_order()
    defaults = {
        "wagon_num": 5,
        "seat": 5,
        "trip": trip,
        "order": order,
    }
    defaults.update(params)
    return Ticket.objects.create(**defaults)


class UnauthorizedOrderTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(ORDERS_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TicketModelTest(TestCase):
    def test_validate_ticket(self):
        with self.assertRaises(ValidationError):
            sample_ticket(
                wagon_num=11,
                seat=11,
            )


class OrderSerializerTest(TestCase):
    def test_validate_order(self):
        trip_1 = sample_trip()
        trip_2 = sample_trip()

        payload = {
            "tickets": [
                {
                    "wagon_num": 1,
                    "seat": 1,
                    "trip": trip_1.id,
                },
                {
                    "wagon_num": 1,
                    "seat": 2,
                    "trip": trip_2.id,
                }
            ]
        }

        serializer = OrderSerializer(data=payload)

        self.assertFalse(serializer.is_valid())
        self.assertEqual(
            serializer.errors["non_field_errors"][0],
            "All tickets in one order must be for the same trip"
        )


class OrderAuthorizedApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="user1@email.com",
            password="password",
        )
        self.client.force_authenticate(self.user)

    def test_list_orders(self):
        order = sample_order(user=self.user)
        ticket_1 = sample_ticket(order=order)
        ticket_2 = sample_ticket(order=order)

        res = self.client.get(ORDERS_URL)
        orders = Order.objects.filter(
            user=self.user
        ).annotate(
            tickets_count=Count("tickets")
        )

        serializer = OrderListSerializer(orders, many=True)

        self.assertEqual(res.data["results"], serializer.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(
            Decimal(res.data["results"][0]["total_price"]),
            ticket_1.trip.price + ticket_2.trip.price
        )

    def test_filter_by_is_active(self):
        trip = sample_trip(
            departure_time=timezone.make_aware(
                datetime(2026, 6, 1, 15, 0)
            ),
            arrival_time=timezone.make_aware(
                datetime(2026, 6, 1, 17, 0)
            )
        )
        order = sample_order(user=self.user)
        ticket = sample_ticket(order=order, trip=trip)

        res = self.client.get(ORDERS_URL, {"is_active": 1})

        self.assertEqual(len(res.data["results"]), 1)
        self.assertEqual(res.data["results"][0]["id"], order.id)

    def test_filter_order_by_route(self):
        station_1 = sample_station(name="Station 1")
        station_2 = sample_station(name="Station 2")
        route_1 = sample_route(source=station_1, destination=station_2)
        trip = sample_trip(route=route_1)
        order = sample_order(user=self.user)
        ticket_1 = sample_ticket(order=order, trip=trip)
        other_order = sample_order(user=self.user)
        other_trip = sample_trip()
        sample_ticket(order=other_order, trip=other_trip)

        res = self.client.get(ORDERS_URL, {"route": "Station 1"})

        returned_ids = [item["id"] for item in res.data["results"]]

        self.assertIn(order.id, returned_ids)
        self.assertNotIn(other_order.id, returned_ids)

    def test_detail_order(self):
        order = sample_order(user=self.user)
        ticket = sample_ticket(order=order)

        url = detail_url(order.id)
        res = self.client.get(url)

        serializer = OrderRetrieveSerializer(order)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)
