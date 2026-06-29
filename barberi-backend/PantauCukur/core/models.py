from django.db import models
from django.utils import timezone

class BarberSession(models.Model):
    chair_number = models.IntegerField()
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.IntegerField(default=0)
    # is_valid: True jika durasi > MIN_DURATION (misal 60 detik)
    is_valid = models.BooleanField(default=False) 

    def __str__(self):
        return f"Kursi {self.chair_number} - {self.start_time.strftime('%H:%M')}"

    class Meta:
        ordering = ['-start_time']