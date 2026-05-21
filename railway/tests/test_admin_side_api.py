import os
import tempfile

from PIL import Image
from django.contrib.auth import get_user_model
from django.db.migrations import serializer
from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from rest_framework.test import APIClient

from railway.models import TrainType, Train
from railway.serializers import TrainSerializer, TrainListSerializer

TRAINS_URL = reverse("railway:train-list")


def detail_url(train_id):
    return reverse("railway:train-detail", args=[train_id])

def image_upload_url(train_id):
    return reverse("railway:train-upload-image", args=[train_id])

def sample_train_type(**params):
    defaults = {
        "name": "train-type",
    }
    defaults.update(params)
    return TrainType.objects.create(**defaults)

def sample_train(**params):
    train_type = sample_train_type()
    defaults = {
        "name": "Train 1",
        "wagons_num": 10,
        "seats_in_wagon": 10,
        "train_type": train_type,
    }
    defaults.update(params)
    return Train.objects.create(**defaults)


class UnauthenticatedTrainApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(TRAINS_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_admin_required(self):
        self.user = get_user_model().objects.create_user(
            email="user@user.com",
            password="12345"
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(TRAINS_URL)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminTrainApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@admin.com",
            password="adminpassword",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.user)

    def test_create_train(self):
        train_type = sample_train_type()
        payload = {
            "name": "Train 1",
            "wagons_num": 10,
            "seats_in_wagon": 10,
            "train_type": train_type.id,
        }

        response = self.client.post(TRAINS_URL, payload)
        train = Train.objects.get(id=response.data["id"])

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(train.name, payload["name"])
        self.assertEqual(train.wagons_num, payload["wagons_num"])
        self.assertEqual(train.seats_in_wagon, payload["seats_in_wagon"])
        self.assertEqual(train.train_type.id, payload["train_type"])

    def test_update_train(self):
        train_type = sample_train_type()
        payload = {
            "name": "Train 1",
            "wagons_num": 11,
            "seats_in_wagon": 10,
            "train_type": train_type.id,
        }
        train = sample_train(train_type=train_type)

        url = detail_url(train.id)
        response = self.client.put(url, payload)
        train_id = Train.objects.get(id=response.data["id"])

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(train_id.wagons_num, payload["wagons_num"])

    def test_delete_train(self):
        train_type = sample_train_type()
        train = sample_train(train_type=train_type)

        url = detail_url(train.id)
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_list_trains(self):
        train_type = sample_train_type()
        sample_train(train_type=train_type)

        response = self.client.get(TRAINS_URL)
        trains = Train.objects.all()
        serializer = TrainSerializer(trains, many=True)

        self.assertEqual(response.data["results"], serializer.data)

    def test_retrieve_train(self):
        train_type = sample_train_type()
        train = sample_train(train_type=train_type)

        url = detail_url(train.id)
        response = self.client.get(url)

        serializer = TrainSerializer(train)

        self.assertEqual(response.data, serializer.data)


class TrainImageUploadApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@admin.com",
            password="adminpassword",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)
        train_type = sample_train_type()
        self.train = sample_train(train_type=train_type)

    def tearDown(self):
        self.train.image.delete()

    def test_upload_image_to_train(self):
        url = image_upload_url(self.train.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as tmp:
            image = Image.new("RGB", (10, 10))
            image.save(tmp, format="JPEG")
            tmp.seek(0)
            res = self.client.post(url, {"image": tmp}, format="multipart")

        self.train.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data)
        self.assertTrue(os.path.exists(self.train.image.path))

    def test_upload_image_bad_request(self):
        url = image_upload_url(self.train.id)
        res = self.client.post(url, {"image": "not image"}, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

