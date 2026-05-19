from datetime import datetime

from django.db.models import Q, F
from django.db.models.aggregates import Count
from django.utils import timezone
from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.viewsets import GenericViewSet

from railway.models import Train, Trip, Order, TrainType, Crew, Station, Route
from railway.serializers import TrainSerializer, TripListSerializer, \
    TripSerializer, OrderListSerializer, OrderSerializer, OrderRetrieveSerializer, TripRetrieveSerializer, \
    TrainTypeSerializer, CrewSerializer, StationSerializer, RouteSerializer


class TripViewSet(viewsets.ModelViewSet):
    queryset = Trip.objects.all()

    def get_queryset(self):
        departure = self.request.query_params.get("departure")
        arrival = self.request.query_params.get("arrival")
        route = self.request.query_params.get("route")
        train = self.request.query_params.get("train")
        queryset = Trip.objects.select_related(
                "route",
                "route__source",
                "route__destination",
                "train",
                "train__train_type",
            ).prefetch_related(
                "crew"
            ).annotate(tickets_available=F("train__seats_in_wagon") * F("train__wagons_num")
                       - Count("tickets", distinct=True))

        if departure:
            date = datetime.strptime(departure, "%Y-%m-%d").date()
            queryset = queryset.filter(departure_time__date=date)

        if arrival:
            date = datetime.strptime(arrival, "%Y-%m-%d").date()
            queryset = queryset.filter(arrival_time__date=date)

        if route:
            queryset = queryset.filter(
                Q(route__source__name__icontains=route) |
                Q(route__destination__name__icontains=route)
            )

        if train:
            queryset = queryset.filter(train__train_type__name__icontains=train)

        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return TripListSerializer
        if self.action == "retrieve":
            return TripRetrieveSerializer
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return TripSerializer
        return TripSerializer

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsAdminUser()]
        return [AllowAny()]


class OrderViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    GenericViewSet,
):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        is_active = self.request.query_params.get("is_active")
        route = self.request.query_params.get("route")

        queryset = (Order.objects.filter(user=self.request.user)
        .annotate(tickets_count=Count("tickets"))
        .prefetch_related(
            "tickets",
            "tickets__trip",
            "tickets__trip__route",
            "tickets__trip__route__source",
            "tickets__trip__route__destination",
            "tickets__trip__train",
            "tickets__trip__train__train_type",
            "tickets__trip__crew"
        ))

        if is_active:
            queryset = queryset.filter(tickets__trip__departure_time__gte=timezone.now())

        if route:
            queryset = queryset.filter(
                Q(tickets__trip__route__source__name__icontains=route) |
                Q(tickets__trip__route__destination__name__icontains=route)
            )

        return queryset.distinct()

    def get_serializer_class(self):
        if self.action == "list":
            return OrderListSerializer
        elif self.action == "retrieve":
            return OrderRetrieveSerializer
        return OrderSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class TrainViewSet(viewsets.ModelViewSet):
    queryset = Train.objects.all()
    serializer_class = TrainSerializer
    permission_classes = (IsAdminUser,)


class TrainTypeViewSet(viewsets.ModelViewSet):
    queryset = TrainType.objects.all()
    serializer_class = TrainTypeSerializer
    permission_classes = (IsAdminUser,)


class CrewViewSet(viewsets.ModelViewSet):
    queryset = Crew.objects.all()
    serializer_class = CrewSerializer
    permission_classes = (IsAdminUser,)


class StationViewSet(viewsets.ModelViewSet):
    queryset = Station.objects.all()
    serializer_class = StationSerializer
    permission_classes = (IsAdminUser,)


class RouteViewSet(viewsets.ModelViewSet):
    queryset = Route.objects.all()
    serializer_class = RouteSerializer
    permission_classes = (IsAdminUser,)
