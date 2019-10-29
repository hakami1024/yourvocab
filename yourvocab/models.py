from django.conf import settings

# Create your models here.
from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    email_confirmed = models.BooleanField(default=False)


@receiver(post_save, sender=User)
def update_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    instance.profile.save()


class Course(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    public = models.BooleanField(default=False)
    helper_symbols = models.CharField(max_length=200)


class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, editable=False)
    name = models.CharField(max_length=200)
    attendance_count = models.IntegerField(default=0)


class Question(models.Model):
    question_text = models.TextField()
    answer_text = models.TextField()
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, editable=False)


class CourseStudent(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, editable=False)
    answer_bonus = models.SmallIntegerField(default=5)
    mistake_penalty = models.SmallIntegerField(default=1)
    show_answer_penalty = models.SmallIntegerField(default=2)


class LessonStudent(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, editable=False)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, editable=False)
    date_time = models.DateTimeField()
    elapsed_time = models.BigIntegerField()
    points = models.IntegerField()
    mistakes_count = models.IntegerField()


class QuestionStudent(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    mistakes_count = models.IntegerField(default=0)
