from datetime import datetime

from django.db.models import Q, F
from django.db.models.aggregates import Count
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import mixins, viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from railway.models import (
    Train,
    Trip,
    Order,
    TrainType,
    Crew,
    Station,
    Route
)
from railway.serializers import (
    TrainSerializer,
    TripListSerializer,
    TripSerializer,
    OrderListSerializer,
    OrderSerializer,
    OrderRetrieveSerializer,
    TripRetrieveSerializer,
    TrainTypeSerializer,
    CrewSerializer,
    StationSerializer,
    RouteSerializer,
    TrainImageSerializer,
    CrewImageSerializer
)


class UploadImageMixin:
    @action(
        methods=["POST"],
        detail=True,
        url_path="upload-image",
    )
    def upload_image(self, request, pk=None):
        obj = self.get_object()
        serializer = self.get_serializer(obj, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


class TripViewSet(viewsets.ModelViewSet):
    queryset = Trip.objects.all()

    def get_queryset(self):
        departure = self.request.query_params.get("departure")
        arrival = self.request.query_params.get("arrival")
        route = self.request.query_params.get("route")
        train = self.request.query_params.get("train")
        queryset = (
            Trip.objects.select_related(
                "route",
                "route__source",
                "route__destination",
                "train",
                "train__train_type",
            )
            .prefetch_related(
                "crew",
            )
            .annotate(
                tickets_available=(
                        F("train__seats_in_wagon")
                        * F("train__wagons_num")
                        - Count("tickets", distinct=True)
                )
            )
        )

        if departure:
            try:
                date = datetime.strptime(departure, "%Y-%m-%d").date()
            except ValueError:
                raise ValidationError(
                    {"departure": "Departure must be in YYYY-MM-DD format"}
                )
            queryset = queryset.filter(departure_time__date=date)

        if arrival:
            try:
                date = datetime.strptime(arrival, "%Y-%m-%d").date()
            except ValueError:
                raise ValidationError(
                    {"arrival": "Arrival must be in YYYY-MM-DD format"}
                )
            queryset = queryset.filter(arrival_time__date=date)

        if route:
            queryset = queryset.filter(
                Q(route__source__name__icontains=route) |
                Q(route__destination__name__icontains=route)
            )

        if train:
            queryset = (
                queryset.filter(train__train_type__name__icontains=train)
            )

        return queryset.order_by("id")

    def get_serializer_class(self):
        if self.action == "list":
            return TripListSerializer
        if self.action == "retrieve":
            return TripRetrieveSerializer
        return TripSerializer

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsAdminUser()]
        return [AllowAny()]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="departure",
                type=OpenApiTypes.DATE,
                description=(
                        "Filter by departure time (ex. ?departure=2026-07-01)"
                ),
            ),
            OpenApiParameter(
                name="arrival",
                type=OpenApiTypes.DATE,
                description=(
                        "Filter by arrival time (ex. ?arrival=2026-07-01)"
                ),
            ),
            OpenApiParameter(
                name="route",
                type=OpenApiTypes.STR,
                description=(
                        "Filter by route source & destination "
                        "(ex. ?route=Kyiv)"
                ),
            ),
            OpenApiParameter(
                name="train",
                type=OpenApiTypes.STR,
                description="Filter by train type (ex. ?train=Intercity)",
            )
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class OrderViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    GenericViewSet,
):
    queryset = Order.objects.all()
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        is_active = self.request.query_params.get("is_active")
        route = self.request.query_params.get("route")

        queryset = (
            Order.objects.filter(user=self.request.user)
            .annotate(
                tickets_count=Count("tickets")
            )
            .prefetch_related(
                "tickets",
                "tickets__trip",
                "tickets__trip__route",
                "tickets__trip__route__source",
                "tickets__trip__route__destination",
                "tickets__trip__train",
                "tickets__trip__train__train_type",
                "tickets__trip__crew",
            )
        )

        if is_active in ["true", "1"]:
            queryset = queryset.filter(
                tickets__trip__departure_time__gte=timezone.now()
            )

        if route:
            queryset = queryset.filter(
                Q(tickets__trip__route__source__name__icontains=route) |
                Q(tickets__trip__route__destination__name__icontains=route)
            )

        return queryset.distinct().order_by("id")

    def get_serializer_class(self):
        if self.action == "list":
            return OrderListSerializer
        elif self.action == "retrieve":
            return OrderRetrieveSerializer
        return OrderSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="is_active",
                type=OpenApiTypes.BOOL,
                description="Filter by is_active order (ex. ?is_active=true)",
            ),
            OpenApiParameter(
                name="route",
                type=OpenApiTypes.STR,
                description=(
                        "Filter by route source & destination "
                        "(ex. ?route=Kyiv)"
                ),
            )
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class TrainViewSet(
    UploadImageMixin,
    viewsets.ModelViewSet
):
    queryset = Train.objects.all().order_by("id")
    serializer_class = TrainSerializer
    permission_classes = (IsAdminUser,)

    def get_serializer_class(self):
        if self.action == "upload_image":
            return TrainImageSerializer
        return TrainSerializer


class TrainTypeViewSet(viewsets.ModelViewSet):
    queryset = TrainType.objects.all().order_by("id")
    serializer_class = TrainTypeSerializer
    permission_classes = (IsAdminUser,)


class CrewViewSet(
    UploadImageMixin,
    viewsets.ModelViewSet
):
    queryset = Crew.objects.all().order_by("id")
    serializer_class = CrewSerializer
    permission_classes = (IsAdminUser,)

    def get_serializer_class(self):
        if self.action == "upload_image":
            return CrewImageSerializer
        return CrewSerializer


class StationViewSet(viewsets.ModelViewSet):
    queryset = Station.objects.all().order_by("id")
    serializer_class = StationSerializer
    permission_classes = (IsAdminUser,)


class RouteViewSet(viewsets.ModelViewSet):
    queryset = Route.objects.all().order_by("id")
    serializer_class = RouteSerializer
    permission_classes = (IsAdminUser,)
