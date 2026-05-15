from django.urls import path,include
from rest_framework import routers

from railway.views import TripViewSet, OrderViewSet, RouteViewSet, TrainViewSet, TrainTypeViewSet, CrewViewSet, \
    StationViewSet

app_name = "railway"

router = routers.DefaultRouter()
router.register("trips", TripViewSet)
router.register("orders", OrderViewSet)
router.register("trains", TrainViewSet)
router.register("train_types", TrainTypeViewSet)
router.register("crews", CrewViewSet)
router.register("stations", StationViewSet)
router.register("routes", RouteViewSet)

urlpatterns = [path("", include(router.urls))]
