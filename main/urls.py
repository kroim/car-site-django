from django.conf.urls import url, include
from main import views
from django.conf import settings
from django.conf.urls.static import static
urlpatterns = [
    url(r'^$', views.home_page, name='home_page'),
    url(r'^browse$', views.car_browse, name='car_browse'),
    url(r'^buying_process', views.buying_process, name='buying_process'),
    url(r'^finance', views.finance, name='finance'),
    # url(r'^about_us', views.about_us, name='about_us'),
    url(r'^faq', views.faq, name='faq'),
    url(r'^car/(?P<car_id>[0-9]+)$', views.car_profile, name='car_profile'),
    url(r'^car/customer/(?P<unique_customer_link>[a-zA-Z0-9]+)$', views.customer_car_view, name='customer_car_view'),
    url(r'^ajax_load_cars$', views.ajax_load_cars, name='ajax_load_cars'),
    url(r'^ajax_load_models$', views.ajax_load_models, name='ajax_load_models'),
    url(r'^showroom/(?P<car_id>[0-9]+)$', views.showroom, name='showroom'),
    url(r'^signup/$', views.signup, name='signup'),
    url(r'^login/$', views.selfLogin, name='login'),
    url(r'^logout/$', views.selfLogout, name='logout'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)