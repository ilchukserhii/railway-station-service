from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from railway.models import Train, TrainType, Station, Route, Trip, Crew, Ticket, Order


class StationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Station
        fields = ("id", "name", "latitude", "longitude")

class StationListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Station
        fields = ("id", "name")


class RouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Route
        fields = ("id", "source", "destination", "distance")


class RouteListSerializer(serializers.ModelSerializer):
    source = serializers.SlugRelatedField(slug_field="name", read_only=True)
    destination = serializers.SlugRelatedField(slug_field="name", read_only=True)

    class Meta:
        model = Route
        fields = ("id", "source", "destination", "distance")


class RouteRetrieveSerializer(serializers.ModelSerializer):
    source = StationListSerializer(read_only=True)
    destination = StationListSerializer(read_only=True)

    class Meta:
        model = Route
        fields = ("id", "source", "destination", "distance")


class CrewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Crew
        fields = ("id", "first_name", "last_name", "role")


class TrainSerializer(serializers.ModelSerializer):
    class Meta:
        model = Train
        fields = ("id", "name", "wagons_num", "seats_in_wagon", "train_type")


class TrainListSerializer(TrainSerializer):
    train_type = serializers.SlugRelatedField(
        read_only=True,
        slug_field="name",
    )


class TrainTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainType
        fields = ("id", "name")


class TripSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trip
        fields = ("id", "route", "price", "train", "departure_time", "arrival_time", "crew")


class TripListSerializer(serializers.ModelSerializer):
    route = serializers.StringRelatedField(
        read_only=True
    )
    train = serializers.SlugRelatedField(
        read_only=True,
        slug_field="train_type.name",
    )
    crew = serializers.SerializerMethodField()
    tickets_available = serializers.IntegerField(read_only=True)

    class Meta:
        model = Trip
        fields = ("id", "route", "price", "train", "departure_time", "arrival_time", "crew", "tickets_available")

    def get_crew(self, obj):
        roles = [member.role for member in obj.crew.all()]

        return {
            "members_count": len(roles),
            "roles": roles,
        }


class TripForTrainSerializer(serializers.ModelSerializer):
    route = RouteListSerializer(read_only=True)

    class Meta:
        model = Trip
        fields = ("id", "route", "departure_time", "arrival_time")


class TripForTicketSerializer(serializers.ModelSerializer):
    route = RouteListSerializer(read_only=True)
    train = TrainListSerializer(read_only=True)

    class Meta:
        model = Trip
        fields = ("id", "route", "train", "departure_time", "arrival_time")


class TrainRetrieveSerializer(TrainSerializer):
    train_type = TrainTypeSerializer(read_only=True)
    trips = TripForTrainSerializer(many=True, read_only=True)

    class Meta:
        model = Train
        fields = ("id", "name", "wagons_num", "seats_in_wagon", "train_type", "trips")


class TicketSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        data = super(TicketSerializer, self).validate(attrs=attrs)
        Ticket.validate_ticket(
            attrs["wagon_num"],
            attrs["seat"],
            attrs["trip"].train,
            ValidationError
        )
        return data

    class Meta:
        model = Ticket
        fields = ("id", "wagon_num", "seat", "trip", "order")


class OrderSerializer(serializers.ModelSerializer):
    tickets = TicketSerializer(many=True, read_only=False, allow_empty=False)

    def validate(self, attrs):
        tickets = attrs.get("tickets")

        trips_ids = {
            ticket["trip"].id
            for ticket in tickets
        }

        if len(trips_ids) > 1:
            raise ValidationError(
                "All tickets in one order must be for the same trip"
            )

        return attrs

    class Meta:
        model = Order
        fields = ("id", "created_at", "tickets")

    def create(self, validated_data):
        with transaction.atomic():
            tickets_data = validated_data.pop("tickets")
            order = Order.objects.create(**validated_data)

            for ticket in tickets_data:
                Ticket.objects.create(order=order, **ticket)

            return order

class TicketListSerializer(serializers.ModelSerializer):
    trip = TripForTicketSerializer(read_only=True)

    class Meta:
        model = Ticket
        fields = ("id", "wagon_num", "seat", "trip")


class TicketForOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = ("id", "wagon_num", "seat")


class TicketForTripSerializer(TicketSerializer):
    class Meta:
        model = Ticket
        fields = ("wagon_num", "seat")


class TripRetrieveSerializer(TripSerializer):
    route = RouteListSerializer(read_only=True)
    train = TrainListSerializer(read_only=True)
    crew = CrewSerializer(many=True, read_only=True)
    taken_places = TicketForTripSerializer(
        source="tickets", many=True, read_only=True
    )
    class Meta:
        model = Trip
        fields = ("id", "route", "price", "train", "taken_places", "crew")


class OrderListSerializer(serializers.ModelSerializer):
    tickets_count = serializers.IntegerField(read_only=True)
    departure_time = serializers.SerializerMethodField()
    route = serializers.SerializerMethodField()
    total_price = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True)

    class Meta:
        model = Order
        fields = ("id", "created_at", "tickets_count", "departure_time", "route", "total_price")

    def get_departure_time(self, obj):
        ticket = obj.tickets.all()

        if ticket:
            return ticket[0].trip.departure_time
        return None

    def get_route(self, obj):
        ticket = obj.tickets.all()

        if ticket:
            return str(ticket[0].trip.route)

        return None


class OrderRetrieveSerializer(OrderSerializer):
    trip = serializers.SerializerMethodField()
    tickets = TicketForOrderSerializer(many=True, read_only=True)
    total_price = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True)

    class Meta:
        model = Order
        fields = ("id", "created_at", "trip", "tickets", "total_price")

    def get_trip(self, obj):
        ticket = obj.tickets.all()

        if ticket:
            return TripForTicketSerializer(ticket[0].trip).data

        return None
