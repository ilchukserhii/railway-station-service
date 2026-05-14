from django.core.exceptions import ValidationError
from django.db import models

from railway_station_service import settings


class Route(models.Model):
    source = models.ForeignKey(
        "Station",
        on_delete=models.CASCADE,
        related_name="source_routes"
    )
    destination = models.ForeignKey(
        "Station",
        on_delete=models.CASCADE,
        related_name="destination_routes"
    )
    distance = models.IntegerField()

    def clean(self):
        if self.destination == self.source:
            raise ValidationError(
                "Destination and source station"
                " must be different"
            )

    def save(
        self,
        *,
        force_insert = False,
        force_update = False,
        using = None,
        update_fields = None,
    ):
        self.full_clean()
        return super().save(
            force_insert = force_insert,
            force_update = force_update,
            using = using,
            update_fields = update_fields,
        )

    def __str__(self):
        return f"{self.source} -> {self.destination} (distance: {self.distance} km)"


class Station(models.Model):
    name = models.CharField(max_length=255, unique=True)
    latitude = models.FloatField()
    longitude = models.FloatField()

    def __str__(self):
        return f"Station: {self.name}, coordinates: {self.latitude}, {self.longitude}"


class Crew(models.Model):
    class RoleChoices(models.TextChoices):
        DRIVER = "driver", "Driver"
        ASSISTANT_DRIVER = "assistant_driver", "Assistant driver"
        CONDUCTOR = "conductor", "Conductor"
        SENIOR_CONDUCTOR = "senior_conductor", "Senior conductor"
        TRAIN_MANAGER = "train_manager", "Train manager"
        TECHNICIAN = "technician", "Technician"
    first_name = models.CharField(max_length=60)
    last_name = models.CharField(max_length=60)
    role = models.CharField(
        max_length=30,
        choices=RoleChoices.choices,
    )

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.role})"

class Trip(models.Model):
    route = models.ForeignKey("Route", on_delete=models.CASCADE, related_name="trips")
    train = models.ForeignKey(
        "Train",
        on_delete=models.SET_NULL,
        related_name="trips",
        null=True,
    )
    departure_time = models.DateTimeField()
    arrival_time = models.DateTimeField()
    crew = models.ManyToManyField("Crew", related_name="trips")

    def clean(self):
        if not self.arrival_time > self.departure_time:
            raise ValidationError(
                "Arrival time must be greater than departure time"
            )

    def save(
        self,
        *,
        force_insert = False,
        force_update = False,
        using = None,
        update_fields = None,
    ):
        self.full_clean()
        return super().save(
            force_insert = force_insert,
            force_update = force_update,
            using = using,
            update_fields = update_fields,
        )

    class Meta:
        ordering = ["-departure_time"]

    def __str__(self):
        return (
            f"Trip: {self.route}, "
            f"departure - {self.departure_time}, arrival -{self.arrival_time}, "
            f"Train: {self.train}"
        )

class Train(models.Model):
    name = models.CharField(max_length=255, unique=True)
    wagons_num = models.IntegerField()
    seats_in_wagon = models.IntegerField()
    train_type = models.ForeignKey(
        "TrainType",
        on_delete=models.SET_NULL,
        related_name="trains",
        null=True,
    )

    def __str__(self):
        return (
            f"Train {self.name} "
            f"(type: {self.train_type}, "
            f"wagons: {self.wagons_num})"
        )


class TrainType(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Ticket(models.Model):
    wagon_num = models.IntegerField()
    seat = models.IntegerField()
    trip = models.ForeignKey("Trip", on_delete=models.CASCADE, related_name="tickets")
    order = models.ForeignKey("Order", on_delete=models.CASCADE, related_name="tickets")

    @staticmethod
    def validate_ticket(wagon_num, seat, train, error_to_raise):
        for ticket_attr_value, ticket_attr_name, train_attr_name in [
            (wagon_num, "wagon_num", "wagons_num"),
            (seat, "seat", "seats_in_wagon"),
        ]:
            count_attrs = getattr(train, train_attr_name)
            if not (1 <= ticket_attr_value <= count_attrs):
                raise error_to_raise(
                    {
                        ticket_attr_name: f"{ticket_attr_name} "
                        f"number must be in available range: "
                        f"(1, {train_attr_name}): "
                        f"(1, {count_attrs})",
                    }
                )

    def clean(self):
        Ticket.validate_ticket(
            self.wagon_num,
            self.seat,
            self.trip.train,
            ValidationError,
        )

    def save(
        self,
        *,
        force_insert = False,
        force_update = False,
        using = None,
        update_fields = None,
    ):
        self.full_clean()
        return super().save(
            force_insert = force_insert,
            force_update = force_update,
            using = using,
            update_fields = update_fields,
        )
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["trip", "wagon_num", "seat"],
                name="unique_ticket_for_trip",
            )
        ]

    def __str__(self):
        return f"{str(self.trip)} (wagon number: {self.wagon_num}, seat: {self.seat})"


class Order(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="orders"
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{str(self.created_at)}"
