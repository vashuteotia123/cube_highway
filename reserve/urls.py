from django.urls import path

from . import views

urlpatterns = [
    path("login", views.Login, name="login"),
    path("logout", views.Logout, name="logout"),
    path("signup", views.signup, name="signup"),
    path("reserve", views.reserve, name="reserve"),
    path("reservation", views.reservation, name="reservation"),
    path("order/<str:resID>",views.order,name="order"),
    path("place/<str:resID>",views.place,name="place"),
    path("clear/<str:resID>",views.clear,name="clear"),
    path("bill/<str:resID>",views.bill,name="bill"),
    path("add/<str:resID>/<str:itemID>",views.add,name="add"),
    path("feedback/<str:resID>",views.feedback,name="feedback"),
    path("resmanage",views.resmanage,name="resmanage"),
    path("decline/<str:resID>",views.decline,name="decline"),
    path("accept/<str:resID>",views.accept,name="accept"),
    path("ordermanage",views.ordermanage,name="ordermanage"),
    path("feedbackmanage",views.feedbackmanage,name="feedbackmanage"),
    path("", views.index, name="index"),
    path("drivein",views.drivein,name="drivein")
    
]
