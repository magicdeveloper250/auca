from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import (
    
    CourseScheduleViewSet,
)

router = DefaultRouter()
 
router.register(r'', CourseScheduleViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
