from django.conf.urls import url, include
from administrator import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
                  url(r'^$', views.dashboard, name='dashboard'),
                  url(r'^login$', views.login, name='login'),
                  url(r'^signout$', views.signout, name='signout'),
                  url(r'^actions$', views.actions, name='actions'),
                  url(r'^damages$', views.fill_damages, name='fill_damages'),
                  url(r'^search_car$', views.search_car, name='search_car'),
                  url(r'^car/list$', views.car_list, name='car_list'),
                  url(r'^contacts$', views.contacts, name='contacts'),
                  url(r'^stock_images$', views.stock_images, name='stock_images'),

              ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
