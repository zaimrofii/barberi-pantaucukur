from django.db import models
from django.utils import timezone

class BarberSession(models.Model):
    chair_number = models.IntegerField()
    chair_name = models.CharField(max_length=50, blank=True, default='')
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.IntegerField(default=0)
    # is_valid: True jika durasi > MIN_DURATION (misal 60 detik)
    is_valid = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        # Hitung durasi jika end_time diisi
        if self.end_time and self.start_time:
            delta = self.end_time - self.start_time
            self.duration_seconds = int(delta.total_seconds())
        else:
            self.duration_seconds = 0
        # Tentukan validitas berdasarkan durasi
        MIN_DURATION = 60  # detik
        self.is_valid = self.duration_seconds > MIN_DURATION
        # Jika chair_name kosong, isi dengan default
        if not self.chair_name:
            self.chair_name = f"Kursi {self.chair_number:02d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.chair_name} - {self.start_time.strftime('%H:%M')}"

    class Meta:
        ordering = ['-start_time']
