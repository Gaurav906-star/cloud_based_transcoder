from django.urls import path, include
from videos.views import home,upload_video, get_videos,videos_page,generate_pdf_api,login_api,logout_api
from django.conf.urls.static import static
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin

from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.contrib.auth import views as auth_views

schema_view = get_schema_view(
    openapi.Info(
        title="TranscodeCloud API",
        default_version='v1',
        description="API for Video Transcoding + PDF Generation",
        contact=openapi.Contact(email="you@example.com"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    
    path('', home),
    path('upload/', upload_video),
    path('videos/', get_videos),
    path('videos-page/', videos_page),
    path('generate_pdf_api/',generate_pdf_api),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0)),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0)),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('admin/', admin.site.urls),
     path('', upload_video),
]


# urlpatterns += static('/media/', document_root='storage/processed')
urlpatterns += static(settings.STATIC_URL, document_root='static')
urlpatterns += static(
    settings.MEDIA_URL,
    document_root=settings.MEDIA_ROOT
)