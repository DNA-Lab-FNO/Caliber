from django.urls import path

from . import views

urlpatterns = [
    path("search/", views.search_variants, name="search_variants"),
    path("upload/", views.upload_variants_file, name="upload_variants_file"),
    path("classify/", views.classify_variants, name="classify_variants"),
]
