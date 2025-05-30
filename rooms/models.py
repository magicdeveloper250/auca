from django.db import models

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)   
    updated_at = models.DateTimeField(auto_now=True)       

    class Meta:
        abstract = True 
 
class Room(TimeStampedModel):
    name = models.CharField(max_length=50, unique=True)
    capacity = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.name} ({self.capacity} seats)"


class RoomAllocationSwitch(models.Model):
    is_enabled = models.BooleanField(default=True)

    def __str__(self):
        return "Enabled" if self.is_enabled else "Disabled"