from django.urls import path
from videos.views import home, upload_video, get_videos,videos_page
from django.conf.urls.static import static
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', home),
    path('upload/', upload_video),
    path('videos/', get_videos),
    path('videos-page/', videos_page)
]


# urlpatterns += static('/media/', document_root='storage/processed')
urlpatterns += static(settings.STATIC_URL, document_root='static')
urlpatterns += static(
    settings.MEDIA_URL,
    document_root=settings.MEDIA_ROOT
)