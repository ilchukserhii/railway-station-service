from django.contrib import admin
from railway.models import (
    Route,
    Station,
    Crew,
    Trip,
    Train,
    TrainType,
    Ticket,
    Order
)


class TicketInline(admin.TabularInline):
    model = Ticket
    extra = 1


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    inlines = [TicketInline,]


admin.site.register(Train)
admin.site.register(TrainType)
admin.site.register(Route)
admin.site.register(Station)
admin.site.register(Crew)
admin.site.register(Trip)
admin.site.register(Ticket)
