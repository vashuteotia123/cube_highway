from django.shortcuts import render
from django.http import HttpResponse,HttpResponseRedirect
from django.contrib.auth import login,logout,authenticate
from django.contrib.auth.models import User
from django.urls import reverse
from django.db.models import Q, Sum
from django.contrib import messages
from .models import *
from django.views.decorators.csrf import csrf_exempt
import requests, json
from numpy import loadtxt
from keras.models import Sequential
from keras.layers import Dense
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedShuffleSplit
import time

superuser = User.objects.filter(is_superuser=True)
if superuser.count() == 0:
    superuser=User.objects.create_user("admin","admin@admin.com")
    superuser.is_superuser = True
    superuser.is_staff = True
    superuser.save()

def index(request):
    if not request.user.is_authenticated:
        return render(request,"login.html")
    else:
        context={
            "user":request.user
        }
        return render(request,"index.html",context)

def Login(request):
    username=request.POST["username"]
    password=request.POST["password"]
    user=authenticate(request,username=username,password=password)
    if user is None:
        messages.add_message(request, messages.ERROR, "Invalid Credentials")
        return render(request,"login.html")
    else:
        login(request,user)
        return HttpResponseRedirect(reverse("index"))
    
def signup(request):
    if request.method=="POST":
        first_name=request.POST["first_name"]
        last_name=request.POST["last_name"]
        username=request.POST["username"]
        email=request.POST["email"]
        password=request.POST["password"]
        password2=request.POST["password_conf"]
        if not password==password2:
            messages.add_message(request, messages.ERROR, "Passwords do not match!")
            return render(request,"signup.html")
        user=User.objects.create_user(username,email,password)
        user.first_name=first_name
        user.last_name=last_name
        user.save()
        messages.add_message(request, messages.SUCCESS, "Registered. You can log in now.")
        return HttpResponseRedirect(reverse("index"))
    return render(request,"signup.html")

def Logout(request):
    logout(request)
    messages.add_message(request, messages.SUCCESS, "Logged Out")
    return HttpResponseRedirect(reverse("index"))

def pred(values):
    df = pd.read_csv("reserve/dataset_new.csv")
    df["Vehicle"].replace(["car", "bike", "truck", "bus"], [1, 2, 3, 4], inplace=True)
    df["Preorder"].replace([True, False], [1, 0], inplace=True)
    df = df[:100]
    df.head()
    x = df.drop("Status", axis=1)
    y = df["Status"]
    sss = StratifiedShuffleSplit(test_size=0.2, random_state=42)
    for train_index, test_index in sss.split(x, y):
        trainset = df.loc[train_index]
        testset = df.loc[test_index]
    trainset.head()
    train_x = trainset.drop("Status", axis=1)
    train_y = trainset["Status"]
    test_x = testset.drop("Status", axis=1)
    test_y = testset["Status"]


    # define the keras model
    model = Sequential()
    model.add(Dense(12, input_dim=4, activation='relu'))
    model.add(Dense(6, activation='relu'))
    model.add(Dense(1, activation='sigmoid'))
    # compile the keras model
    model.compile(loss='binary_crossentropy', optimizer='adam', metrics=['accuracy'])
    # fit the keras model on the dataset
    model.fit(train_x, train_y, epochs=150, batch_size=10)
    # evaluate the keras model
    accuracy = model.evaluate(test_x, test_y)
    # print((accuracy*100))
    # print((accuracy))
    temp1 = [values]
    return round(model.predict(temp1)[0][0]*100,2)


def reserve(request):
    if not request.user.is_authenticated:
        messages.add_message(request, messages.ERROR, "You must login first")
        return HttpResponseRedirect(reverse("index"))
    context={
        "slots":Slot.objects.all()
        }
    if request.method=="POST":
        slot=request.POST["slot"]
        pax=request.POST["pax"]
        sl=Slot.objects.get(id=int(slot))
        phase=sl.phase,
        vehicle=request.POST["vehicle"]
        preorder=request.POST["preorder"]
        try:
            pax=int(pax)
        except ValueError:
            messages.add_message(request, messages.ERROR, "No. of persons should be a number!")
            return HttpResponseRedirect(reverse("reserve"))
        dic={"car":1,"bike":2,"truck":3,"bus":4}
        pre={"yes":1,"no":0}
        pro=pred([phase[0],int(dic[vehicle]),pax,int(pre[preorder])])
        res=PendingRes(customer=request.user,slot=Slot.objects.get(id=int(slot)),PAX=pax,prob=pro)
        res.save()
        messages.add_message(request, messages.SUCCESS, "Reservation successfully requested. Go to My Reservations to see status")
        return HttpResponseRedirect(reverse("index"))
    return render(request,"reserve.html",context)

def reservation(request):
    if not request.user.is_authenticated:
        messages.add_message(request, messages.ERROR, "You must login first")
        return HttpResponseRedirect(reverse("index"))
    if(request.method=="POST"):
        if request.POST["action"]=="1":
            res=Reservation.objects.get(reservation__id=request.POST["resID"])
            res.status=2
            res.save()
    pending=PendingRes.objects.filter(customer=request.user)
    res=Reservation.objects.filter(reservation__customer=request.user)
    finalPending=PendingRes.objects.none()
    ids=[]
    for x in res:
        ids.append(x.reservation.id)
    for y in pending:
        if y.id not in ids:
            finalPending |= PendingRes.objects.filter(id=y.id)
    context={
        "reservations": res.filter(status__lte=6),
        "pending": finalPending
        }
    return render(request,"reservations.html",context)

def order(request, resID):
    if not request.user.is_authenticated:
        messages.add_message(request, messages.ERROR, "You must login first")
        HttpResponseRedirect(reverse("index"))
    res=Reservation.objects.get(reservation__id=int(resID))
    if res==None:
        messages.add_message(request, messages.ERROR, "Invalid Reservation ID")
        return HttpResponseRedirect(reverse("index"))
    if res.reservation.customer!=request.user:
        messages.add_message(request, messages.ERROR, "Not your reservation")
        return HttpResponseRedirect(reverse("index"))
    if res.status>4 or res.status<3:
        messages.add_message(request, messages.ERROR, "You cannot order anymore on this reservation!")
        return HttpResponseRedirect(reverse("index"))
    context={
        "reservation":res,
        "added_orders": Order.objects.filter(reservation=res,status=1),
        "cart_count": Order.objects.filter(reservation=res,status=1).count(),
        "process_orders": Order.objects.filter(~Q(status=1),reservation=res),
        "starters": MenuItem.objects.filter(category=1),
        "main_courses": MenuItem.objects.filter(category=2),
        "desserts": MenuItem.objects.filter(category=3),
        "added_total": ((list(Order.objects.filter(reservation=res,status=1).aggregate(Sum('item__cost')).values())[0]) if (list(Order.objects.filter(reservation=res,status=1).aggregate(Sum('item__cost')).values())[0]!=None) else 0),
        "process_count": Order.objects.filter(~Q(status=1),reservation=res).count()
    }
    return render(request,"order.html",context)

def add(request, resID, itemID):
    if not request.user.is_authenticated:
        messages.add_message(request, messages.ERROR, "You must login first")
        return HttpResponseRedirect(reverse("index"))
    res=Reservation.objects.get(reservation__id=int(resID))
    item=MenuItem.objects.get(id=int(itemID))
    if res==None:
        messages.add_message(request, messages.ERROR, "Invalid Reservation ID")
        return HttpResponseRedirect(reverse("index"))
    if res.reservation.customer!=request.user:
        messages.add_message(request, messages.ERROR, "Not your reservation")
        return HttpResponseRedirect(reverse("index"))
    if item==None:
        messages.add_message(request, messages.ERROR, "Invalid Item ID")
        return HttpResponseRedirect(reverse("index"))
    if res.status>4 or res.status<3:
        messages.add_message(request, messages.ERROR, "You cannot order anymore on this reservation!")
        return HttpResponseRedirect(reverse("index"))
    if res.status==3:
        res.status=4
        res.save()
    order=Order(reservation=res,item=item)
    order.save()
    return HttpResponseRedirect(reverse("order",args=[resID]))

def place(request, resID):
    if not request.user.is_authenticated:
        messages.add_message(request, messages.ERROR, "You must login first")
        return HttpResponseRedirect(reverse("index"))
    res=Reservation.objects.get(reservation__id=int(resID))
    if res==None:
        messages.add_message(request, messages.ERROR, "Invalid Reservation ID")
        return HttpResponseRedirect(reverse("index"))
    if res.reservation.customer!=request.user:
        messages.add_message(request, messages.ERROR, "Not your reservation")
        return HttpResponseRedirect(reverse("index"))
    if res.status>4 or res.status<3:
        messages.add_message(request, messages.ERROR, "You cannot order on this reservation!")
        return HttpResponseRedirect(reverse("index"))
    orders=Order.objects.filter(reservation=res,status=1)
    res.total += (list(Order.objects.filter(reservation=res,status=1).aggregate(Sum('item__cost')).values())[0] if list(Order.objects.filter(reservation=res,status=1).aggregate(Sum('item__cost')).values())[0]!=None else 0)
    res.save()
    for order in orders:
        order.status=2
        order.save()
    return HttpResponseRedirect(reverse("order",args=[resID]))

def clear(request, resID):
    if not request.user.is_authenticated:
        messages.add_message(request, messages.ERROR, "You must login first")
        return HttpResponseRedirect(reverse("index"))
    res=Reservation.objects.get(reservation__id=int(resID))
    if res==None:
        messages.add_message(request, messages.ERROR, "Invalid Reservation ID")
        return HttpResponseRedirect(reverse("index"))
    if res.reservation.customer!=request.user:
        messages.add_message(request, messages.ERROR, "Not your reservation")
        return HttpResponseRedirect(reverse("index"))
    if res.status>4 or res.status<3:
        messages.add_message(request, messages.ERROR, "You cannot order on this reservation!")
        return HttpResponseRedirect(reverse("index"))
    orders=Order.objects.filter(reservation=res,status=1)
    for order in orders:
        order.delete()
    return HttpResponseRedirect(reverse("order",args=[resID]))

def bill(request, resID):
    if not request.user.is_authenticated:
        messages.add_message(request, messages.ERROR, "You must login first")
        return HttpResponseRedirect(reverse("index"))
    res=Reservation.objects.get(reservation__id=int(resID))
    if res==None:
        messages.add_message(request, messages.ERROR, "Invalid Reservation ID")
        return HttpResponseRedirect(reverse("index"))
    if res.reservation.customer!=request.user:
        messages.add_message(request, messages.ERROR, "Not your reservation")
        return HttpResponseRedirect(reverse("index"))
    if res.status>4 or res.status<3:
        messages.add_message(request, messages.ERROR, "You cannot order on this reservation!")
        return HttpResponseRedirect(reverse("index"))
    res.status=5
    res.save()
    messages.add_message(request, messages.INFO, "Reservation Over. Please wait for payment confirmation from manager")
    return HttpResponseRedirect(reverse("reservation"))
    
def resmanage(request):
    if not request.user.is_authenticated:
        messages.add_message(request, messages.ERROR, "You must login first")
        return HttpResponseRedirect(reverse("index"))
    if not request.user.is_staff:
        messages.add_message(request, messages.ERROR, "Forbidden")
        return HttpResponseRedirect(reverse("index"))
    if request.method=="POST":
        if request.POST["action"]=="2":
            res=Reservation.objects.get(reservation__id=request.POST["resID"])
            res.status=3
            res.save()
        if request.POST["action"]=="5":
            res=Reservation.objects.get(reservation__id=request.POST["resID"])
            res.status=6
            res.save()
    pending=PendingRes.objects.all()
    res=Reservation.objects.all()
    finalPending=PendingRes.objects.none()
    ids=[]
    for x in res:
        ids.append(x.reservation.id)
    for y in pending:
        if y.id not in ids:
            finalPending |= PendingRes.objects.filter(id=y.id)
    finalPending=finalPending.filter(status=1)
    context={
        "pending": finalPending,
        "reservations" : Reservation.objects.filter(status__lte=5)
    }
    return render(request,"resmanage.html",context)

def decline(request, resID):
    if not request.user.is_authenticated:
        messages.add_message(request, messages.ERROR, "You must login first")
        return HttpResponseRedirect(reverse("index"))
    if not request.user.is_staff:
        messages.add_message(request, messages.ERROR, "Forbidden")
        return HttpResponseRedirect(reverse("index"))
    pending=PendingRes.objects.get(id=int(resID))
    pending.status=2
    pending.save()
    return HttpResponseRedirect(reverse("resmanage"))
    
def accept(request, resID):
    if not request.user.is_authenticated:
        messages.add_message(request, messages.ERROR, "You must login first")
        return HttpResponseRedirect(reverse("index"))
    if not request.user.is_staff:
        messages.add_message(request, messages.ERROR, "Forbidden")
        return HttpResponseRedirect(reverse("index"))
    pending=PendingRes.objects.get(id=int(resID))
    if(request.method=="POST"):
        table=Table.objects.get(id=request.POST["table"])
        res=Reservation(reservation=pending,table=table)
        res.save()
        return HttpResponseRedirect(reverse("resmanage"))
    res=Reservation.objects.filter(reservation__slot=pending.slot,status__lte=5)
    usedtables=Table.objects.none()
    for x in res:
        usedtables |= Table.objects.filter(id=x.table.id)
    tables=Table.objects.all().difference(usedtables)
    finalTables=Table.objects.none()
    for x in tables:
        if x.capacity>=pending.PAX:
            finalTables |= Table.objects.filter(id=x.id)
    if not finalTables:
        messages.add_message(request, messages.ERROR, "There are no more tables to accomodate this reservation at this slot")
        return HttpResponseRedirect(reverse("resmanage"))
    context={
        "tables": finalTables,
        "pending": pending
        }
    return render(request,"accept.html",context)

def ordermanage(request):
    if not request.user.is_authenticated:
        messages.add_message(request, messages.ERROR, "You must login first")
        return HttpResponseRedirect(reverse("index"))
    if not request.user.is_staff:
        messages.add_message(request, messages.ERROR, "Forbidden")
        return HttpResponseRedirect(reverse("index"))
    if request.method=="POST":
        if request.POST["action"]=="2":
            order=Order.objects.get(id=request.POST["orderID"])
            order.status=3
            order.save()
        if request.POST["action"]=="3":
            order=Order.objects.get(id=request.POST["orderID"])
            order.status=4
            order.save()
    orders=Order.objects.filter(~Q(status=1),~Q(status=4))
    return render(request,"ordermanage.html",{"orders": orders })


def feedback(request, resID):
    if not request.user.is_authenticated:
        messages.add_message(request, messages.ERROR, "You must login first")
        HttpResponseRedirect(reverse("index"))
    res=Reservation.objects.get(reservation__id=int(resID))
    if res==None:
        messages.add_message(request, messages.ERROR, "Invalid Reservation ID")
        return HttpResponseRedirect(reverse("index"))
    if res.reservation.customer!=request.user:
        messages.add_message(request, messages.ERROR, "Not your reservation")
        return HttpResponseRedirect(reverse("index"))
    if res.status<6:
        messages.add_message(request, messages.ERROR, "Feedback only after reservation over")
        return HttpResponseRedirect(reverse("reservation"))
    if res.status==7:
        messages.add_message(request, messages.ERROR, "Feedback already given")
        return HttpResponseRedirect(reverse("reservation"))
    if request.method=="POST":
        res.feedback=request.POST["feedback"]
        res.status=7
        res.save()
        messages.add_message(request, messages.SUCCESS, "Feedback successfully given")
        return HttpResponseRedirect(reverse("reservation"))
    return render(request,"feedback.html",{"res": res })

def feedbackmanage(request):
    if not request.user.is_authenticated:
        messages.add_message(request, messages.ERROR, "You must login first")
        return HttpResponseRedirect(reverse("index"))
    if not request.user.is_staff:
        messages.add_message(request, messages.ERROR, "Forbidden")
        return HttpResponseRedirect(reverse("index"))
    res=Reservation.objects.filter(status=7)
    return render(request,"feedbackmanager.html",{"reservations": res })

def drivein(request):
    drv=drive(customer=request.user)
    drv.save()
    context = {
        "starters": MenuItem.objects.filter(category=1),
        "main_courses": MenuItem.objects.filter(category=2),
        "desserts": MenuItem.objects.filter(category=3),
    }
    return render(request,"drivein.html",context)



