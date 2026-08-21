from django.urls import path

from .views import (
    capture_napari_result,
    create_acquisition_session,
    create_sensor_profile,
    demo_spectrum_view,
    napari_result_detail,
    napari_results_dashboard,
    store_raw_frame,
)

urlpatterns = [
    path("sensors/create/", create_sensor_profile, name="create_sensor_profile"),
    path("sessions/create/", create_acquisition_session, name="create_acquisition_session"),
    path("raw/store/", store_raw_frame, name="store_raw_frame"),
    path("results/submit/", capture_napari_result, name="capture_napari_result"),
    path("results/dashboard/", napari_results_dashboard, name="napari_results_dashboard"),
    path("results/demo/", demo_spectrum_view, name="demo_spectrum_view"),
    path("results/<int:result_id>/", napari_result_detail, name="napari_result_detail"),
]
