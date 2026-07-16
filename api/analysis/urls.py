from django.urls import path
from analysis.views import AnalyzeChangeView

urlpatterns = [
    path("analyze/", AnalyzeChangeView.as_view(), name="analyze-change"),
]
