from django.db import models


class BarberSession(models.Model):
    # EXISTING FIELDS
    chair_number = models.IntegerField()
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.IntegerField(default=0)
    is_valid = models.BooleanField(default=False)

    # NEW FIELDS FOR SCORING
    confidence_score = models.IntegerField(
        default=0, help_text="Session confidence score (0-100)"
    )
    tracking_data = models.JSONField(
        default=dict, help_text="Per-frame tracking metrics and session data"
    )
    session_status = models.CharField(
        max_length=20,
        choices=[("PENDING", "Pending"), ("ACTIVE", "Active"), ("ENDED", "Ended")],
        default="PENDING",
        help_text="State machine status",
    )

    class Meta:
        ordering = ["-start_time"]

    def __str__(self):
        return f"Chair {self.chair_number} - {self.start_time}"
