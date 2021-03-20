from django.db import models
from django.contrib.auth.models import User
#Create your models here.

class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role=models.CharField(max_length=64)
    salary=models.IntegerField(default=0)
    def __str__(self):
        return f"{self.user.username} ({self.role})"

class Table(models.Model):
    capacity=models.IntegerField()
    def __str__(self):
        return f"Table {self.id} for {self.capacity} person(s)"

class Slot(models.Model):
    time=models.CharField(max_length=64)
    phase=models.IntegerField(max_length="2")
    def __str__(self):
        return f"{self.time}"

class PendingRes(models.Model):
    CHOICES=((1,"Awaiting confirmation from restaurant"),
             (2,"Your reservation request was cancelled by the restaurant"))
    customer=models.ForeignKey(User,on_delete=models.CASCADE)
    slot=models.ForeignKey(Slot,on_delete=models.CASCADE)
    PAX=models.IntegerField()
    prob = models.CharField(max_length=2, null=True)
    status=models.IntegerField(default=1,choices=CHOICES)
    def __str__(self):
        return f"{self.customer.username} requested table for {self.PAX} at slot {self.slot}"



class Reservation(models.Model):
    CHOICES=((1,"Confirmed! Please inform manager on arrival"),
            (2,"Manager will ensure that you are in the restaurant. Please wait"),
            (3,"Manager has confirmed. Start Ordering now!"),
            (4,"Food ordering and preparation in progress"),
            (5,"Awaiting Bill Payment Confirmation"),
            (6,"Bill Paid and Reservation Over"),
            (7,"Feedback given"))
    reservation=models.ForeignKey(PendingRes,on_delete=models.CASCADE,related_name="pending")
    table=models.ForeignKey(Table,on_delete=models.CASCADE)
    status=models.IntegerField(default=1,choices=CHOICES)

    total=models.IntegerField(default=0)
    feedback=models.CharField(max_length=128,blank=True)
    def __str__(self):
        return f"{self.reservation.customer.username} has {self.table} at {self.reservation.slot}"

class MenuItem(models.Model):
    CATEGORIES=((1,"Starters"),
                (2,"Main Course"),
                (3,"Desserts"))
    category=models.IntegerField(default=1,choices=CATEGORIES)
    description=models.CharField(max_length=128)
    name=models.CharField(max_length=64)
    cost=models.IntegerField()
    veg=models.BooleanField(default=True)
    def __str__(self):
        return f"{self.name} (Rs{self.cost})"

class Order(models.Model):
    CHOICES=((1,"Added to cart"),
             (2,"Order Recieved"),
             (3,"Preparing"),
             (4,"Delivered"))
    reservation=models.ForeignKey(Reservation,on_delete=models.CASCADE)
    item=models.ForeignKey(MenuItem,on_delete=models.CASCADE)
    status=models.IntegerField(default=1,choices=CHOICES)
    def __str__(self):
        return f"{self.reservation.reservation.customer.username} ordered {self.item.name}"


class drive(models.Model):
    customer=models.ForeignKey(User,on_delete=models.CASCADE)
    time=models.TimeField(auto_now=True)

class dorder(models.Model):
    reservation=models.ForeignKey(drive,on_delete=models.CASCADE)
    item=models.ForeignKey(MenuItem,on_delete=models.CASCADE)