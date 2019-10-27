from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.sites.shortcuts import get_current_site
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_text
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.views.defaults import server_error

from yourvocab import forms, models
from yourvocab.tokens import account_activation_token


def signup(request):
    if request.method == 'POST':
        form = forms.SignUpForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()
            current_site = get_current_site(request)
            subject = 'Activate Your MySite Account'
            message = render_to_string('account_activation_email.html', {
                'user': user,
                'domain': current_site.domain,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': account_activation_token.make_token(user),
            })
            user.email_user(subject, message)
            return redirect('/account_activation_sent')
    else:
        form = forms.SignUpForm()
    return render(request, 'signup.html', {'form': form})


def account_activation_sent(request):
    return render(request, 'account_activation_sent.html')


def activate(request, uidb64, token):
    try:
        uid = force_text(urlsafe_base64_decode(uidb64))
        user = models.User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, models.User.DoesNotExist):
        user = None

    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.profile.email_confirmed = True
        user.save()
        login(request, user)
        return redirect('/')
    else:
        return render(request, 'account_activation_invalid.html')


def courses(request):
    if request.user.is_authenticated:
        user = request.user

        mycourses = models.CourseStudent.objects.filter(user=user).all()
        course_list = list([x.course for x in mycourses])
        return render(request, 'yourvocab/courses_list.html', {'courses': course_list})
    else:
        return render(request, 'yourvocab/index.html', {'user': request.user})


@login_required
def course(request, course_id = None):
    if request.method == 'POST':
        form = forms.CourseForm(request.POST)

        if form.is_valid():
            course = form.save(commit=False)
            course.author = request.user
            course.save()

            sign = models.CourseStudent(user=request.user,
                                        course=course,
                                        answer_bonus=form.cleaned_data['right_answer_bonus'],
                                        mistake_penalty=form.cleaned_data['wrong_answer_penalty'],
                                        show_answer_penalty=form.cleaned_data['show_answer_penalty'])
            sign.save()
            return redirect(F'/course/{course.id}')

    if course_id:
        cur_course = models.Course.objects.get(pk=course_id)
        cur_setup = models.CourseStudent.objects.get(course=cur_course, user=request.user)
        lessons = models.Lesson.objects.filter(course=cur_course).all()
        return render(request, 'yourvocab/course.html', {'course': cur_course,
                                                         'setup': cur_setup,
                                                         'lessons': lessons})
    else:
        return render(request, 'yourvocab/new_course.html', {'form': forms.CourseForm()})


@login_required
def lesson(request, course_id, lesson_id = None):
    course = models.Course.objects.get(pk=course_id)

    if request.method == 'POST':
        form = forms.LessonForm(request.POST)

        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.course = course
            lesson.save()

            questions = form.cleaned_data['questions'].split('\r\n')
            answers = form.cleaned_data['answers'].split('\r\n')

            if len(questions) != len(answers):
                return server_error()

            for (q, a) in zip(questions, answers):
                qa = models.Question(question_text=q, answer_text=a, lesson=lesson)
                qa.save()

            return redirect(F'/course/{course.id}')

        return server_error()

    if lesson_id:
        lesson = models.Lesson.objects.get(pk=lesson_id)
        qa = models.Question.objects.filter(lesson=lesson).all()
        return render(request, 'yourvocab/lesson.html', {'lesson': lesson, 'qa': qa})
    return render(request, 'yourvocab/new_lesson.html', {'form': forms.LessonForm()})
