# coding=utf-8

from django.db                  import models
from django.contrib.auth.models import User


LEAGUE = (
    ("FI", "младшая лига"),
    ("SE", "старшая лига"),
)

class Task(models.Model):
    date_created = models.DateTimeField(auto_now_add = True)
    title        = models.CharField(max_length = 100)
    content      = models.CharField(max_length = 10000)
    right_answer = models.CharField(max_length = 100)
    league       = models.CharField(max_length = 2, choices = LEAGUE)
    image        = models.ImageField(upload_to = 'images', blank = True)

    def __unicode__(self):
        return self.title

class Profile(models.Model):
    user         = models.OneToOneField(User)
    date_created = models.DateTimeField(auto_now_add = True)
    first_name   = models.CharField(max_length = 100)
    last_name    = models.CharField(max_length = 100)
    league       = models.CharField(max_length = 2, choices = LEAGUE)
    money        = models.IntegerField(default = 0)
    solved_tasks = models.ManyToManyField(Task, blank = True)

    def __unicode__(self):
        return self.first_name + " " + self.last_name

class AdminProfile(models.Model):
    user         = models.OneToOneField(User)
    date_created = models.DateTimeField(auto_now_add = True)
    first_name   = models.CharField(max_length = 100)
    last_name    = models.CharField(max_length = 100)

    def __unicode__(self):
        return self.first_name + " " + self.last_name

class Answer(models.Model):
    profile    = models.ForeignKey(Profile)
    task       = models.ForeignKey(Task)
    answer     = models.CharField(max_length = 100)
    is_correct = models.BooleanField(default = False)
    attempts   = models.IntegerField(default = 0)

    def __unicode__(self):
        user_full_name     = self.profile.first_name + " " + self.profile.last_name
        answer_description = self.task.title + " | " + user_full_name + ": " + self.answer

        return answer_description
