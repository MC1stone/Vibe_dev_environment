# NIR Intelligence Platform - ILIAS learning path API URLs (roadmap S8)

from django.urls import include, path

from .ilias_views import ilias_status, learning_path_sync

urlpatterns = [
    path("learning-paths/sync/", learning_path_sync, name="ilias_learning_path_sync"),
    path("status/", ilias_status, name="ilias_status"),
]

ilias_api_urls = [path("api/ilias/", include(urlpatterns))]
ilias_urls = urlpatterns
