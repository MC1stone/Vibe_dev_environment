from django.db import models


class SensorProfile(models.Model):
    INTERFACE_CHOICES = [
        ("usb_camera", "USB Camera"),
        ("serial", "Serial Device"),
        ("mock", "Mock / Test Interface"),
    ]

    name = models.CharField(max_length=255)
    interface_type = models.CharField(max_length=32, choices=INTERFACE_CHOICES)
    device_path = models.CharField(max_length=255, blank=True, default="")
    serial_number = models.CharField(max_length=255, blank=True, default="")
    connection_settings = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class AcquisitionSession(models.Model):
    STATUS_CHOICES = [
        ("idle", "Idle"),
        ("recording", "Recording"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    sensor = models.ForeignKey(SensorProfile, on_delete=models.CASCADE, related_name="sessions")
    name = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="idle")
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True, default="")

    def __str__(self):
        return self.name


class RawFrame(models.Model):
    session = models.ForeignKey(AcquisitionSession, on_delete=models.CASCADE, related_name="frames")
    sample_id = models.CharField(max_length=255, blank=True, default="")
    exposure_ms = models.FloatField(default=0.0)
    timestamp = models.DateTimeField(auto_now_add=True)
    file_path = models.CharField(max_length=500, blank=True, default="")
    raw_payload = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"Raw frame for {self.session.name}"


class NapariResult(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("ready", "Ready"),
        ("failed", "Failed"),
    ]

    session = models.ForeignKey(AcquisitionSession, on_delete=models.CASCADE, related_name="napari_results")
    title = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    summary = models.TextField(blank=True, default="")
    image_url = models.CharField(max_length=500, blank=True, default="")
    metrics = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.title
