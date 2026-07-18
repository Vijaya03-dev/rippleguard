from django.urls import path
from analysis.views import AnalyzeChangeView, AnalyzeFunctionChangeView

urlpatterns = [
    path("analyze/", AnalyzeChangeView.as_view(), name="analyze-change"),
    path("analyze-function/", AnalyzeFunctionChangeView.as_view(), name="analyze-function-change"),
]

