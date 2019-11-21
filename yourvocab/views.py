import datetime
import random

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.sites.shortcuts import get_current_site
from django.http import JsonResponse
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
            subject = 'Activate YourVocab Account'
            message = render_to_string('account_activation_email.html', {
                'user': user,
                'domain': current_site.domain,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': account_activation_token.make_token(user),
            })
            user.email_user(subject, message, 'noreply@yourvocab.heroku.com')
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

        mycourses = models.CourseStudent.objects.filter(student=user).all()
        course_list = list([x.course for x in mycourses])
        return render(request, 'yourvocab/courses_list.html', {'courses': course_list})
    else:
        return render(request, 'yourvocab/index.html', {'user': request.user})


@login_required
def course(request, course_id=None):
    if request.method == 'POST':
        form = forms.CourseForm(request.POST)

        if form.is_valid():
            course = form.save(commit=False)
            course.author = request.user
            course.save()

            sign = models.CourseStudent(student=request.user,
                                        course=course,
                                        answer_bonus=form.cleaned_data['right_answer_bonus'],
                                        mistake_penalty=form.cleaned_data['wrong_answer_penalty'],
                                        show_answer_penalty=form.cleaned_data['show_answer_penalty'])
            sign.save()
            return redirect(F'/course/{course.id}')

    if course_id:
        cur_course = models.Course.objects.get(pk=course_id)
        cur_setup = models.CourseStudent.objects.get(course=cur_course, student=request.user)
        lessons = models.Lesson.objects.filter(course=cur_course).all()
        return render(request, 'yourvocab/course.html', {'course': cur_course,
                                                         'setup': cur_setup,
                                                         'lessons': lessons})
    else:
        return render(request, 'yourvocab/new_course.html', {'form': forms.CourseForm()})


def assess_answer(target, answer, request, show_answer, no_score_upd):
    session = request.session
    if no_score_upd:
        return True, session['score']

    q = models.Question.objects.get(pk=target['id'])

    if show_answer:
        session['qa'].append(target)
        session['mistakes_count'] += 1
        qs = models.QuestionStudent.objects.filter(question=q, student=request.user).first()
        qs.mistakes_count += 1
        qs.save()
        return False, session['score'] - session['show_a_penalty']

    if target['answer_text'].strip() == answer.strip():
        return True, session['score'] + session['bonus']

    session['mistakes_count'] += 1
    qs = models.QuestionStudent.objects.filter(question=q, student=request.user).first()
    qs.mistakes_count += 1
    qs.save()
    return False, session['score'] - session['wrong_a_penalty']


@login_required
def check(request, course_id, lesson_id):
    course = models.Course.objects.get(pk=course_id)
    lesson = models.Lesson.objects.get(pk=lesson_id)

    qa = list(models.Question.objects.filter(lesson=lesson).all())
    if len(qa) == 0:
        return server_error(request)

    if request.method == 'POST':
        show_answer = request.POST['show_answer'] == 'true'
        no_score_upd = request.POST['no_score_upd'] == 'true'

        answer = request.POST['answer']
        question_index = request.session['question_index']
        qa = request.session['qa']

        target = qa[question_index]

        to_next, score = assess_answer(target, answer, request, show_answer, no_score_upd)
        request.session['score'] = score
        qa = request.session['qa']  # could have been changed in assess_answer #TODO: smells, refactor

        if not to_next:

            if show_answer:
                return JsonResponse({'result': 'show_answer',
                                     'question': target['question_text'],
                                     'score': F'Your score: {score}.',
                                     'last': False,
                                     'answer': 'The right answer was: ' + target['answer_text']})
            else:
                return JsonResponse({'result': 'mistake',
                                     'question': target['question_text'],
                                     'score': F'Your score: {score}.',
                                     'last': False,
                                     'answer': 'The right answer was: ' + target['answer_text']
                                     })

        if question_index < len(qa) - 1:
            question_index += 1
            request.session['question_index'] = question_index

            title = F'Question {question_index + 1} out of {len(qa)}. {qa[question_index]["question_text"]}'
            return JsonResponse({'result': 'ok',
                                 'question': title,
                                 'last': False,
                                 'score': F'Your score: {score}. {"Learning is a process and progress!" if score <= 0 else "Well done!"}'})
        else:
            title = F'Well done! You have finished the lesson with score {request.session["score"]}.'
            lesson.attendance_count += 1
            lesson.save()

            elapsed_time = datetime.datetime.now().timestamp() - request.session['start_time']
            score_data = models.LessonStudent(student=request.user,
                                              lesson=lesson,
                                              date_time=datetime.datetime.now(),
                                              elapsed_time=elapsed_time,
                                              points=score,
                                              mistakes_count=request.session['mistakes_count'])
            score_data.save()

            return JsonResponse({'result': 'ok',
                                 'question': title,
                                 'last': True,
                                 'score': "Keep learning! No pain no gain!" if score <= 0 else "You are awesome."})

    if len(qa) == 0:
        return server_error(request)

    random.shuffle(qa)

    request.session['qa'] = [{'question_text': i.question_text,
                              'answer_text': i.answer_text,
                              'id': i.id} for i in qa]
    request.session['question_index'] = 0
    request.session['score'] = 0
    request.session['start_time'] = datetime.datetime.now().timestamp()

    setup = models.CourseStudent.objects.filter(course=course, student=request.user).first()

    request.session['bonus'] = setup.answer_bonus
    request.session['wrong_a_penalty'] = setup.mistake_penalty
    request.session['show_a_penalty'] = setup.show_answer_penalty
    request.session['mistakes_count'] = 0

    qa_pair = qa[0]
    questions_count = len(qa)

    return render(request, 'yourvocab/check.html', {'course': course,
                                                    'lesson': lesson,
                                                    'question_index': 1,
                                                    'questions_count': questions_count,
                                                    'qa': qa_pair})


@login_required
def lesson(request, course_id, lesson_id=None):
    course = models.Course.objects.get(pk=course_id)
    lesson = models.Lesson.objects.get(pk=lesson_id) if lesson_id else None

    if request.method == 'POST':
        form = forms.LessonForm(request.POST, instance=lesson)

        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.course = course

            questions = form.cleaned_data['questions'].split('\r\n')
            answers = form.cleaned_data['answers'].split('\r\n')

            if len(questions) != len(answers):
                return server_error(request)

            lesson.save()

            # Regenerating all questions for particular lesson:

            last_qa = models.Question.objects.filter(lesson=lesson)
            q_stats = {}
            for last_q in last_qa:
                qs = models.QuestionStudent.objects.get(question=last_q, student=request.user)
                q_stats[(last_q.question_text, last_q.answer_text)] = qs.mistakes_count

            last_qa.delete()

            for (q, a) in zip(questions, answers):
                qa = models.Question(question_text=q.strip(), answer_text=a.strip(), lesson=lesson)
                qa.save()

                q_key = (q.strip(), a.strip())
                mistakes_count = q_stats[q_key] if q_key in q_stats else 0

                qs = models.QuestionStudent(question=qa, student=request.user, mistakes_count=mistakes_count)
                qs.save()

            return redirect(F'/course/{course.id}')
    elif lesson:
        qa = models.Question.objects.filter(lesson=lesson).all()
        questions = '\n'.join([q.question_text for q in qa])
        answers = '\n'.join([q.answer_text for q in qa])
        form = forms.LessonForm({'name': lesson.name, 'questions': questions, 'answers': answers}, instance=lesson)
        return render(request, 'yourvocab/new_lesson.html', {'form': form, 'helper_symbols': course.helper_symbols})
    else:
        form = forms.LessonForm()

    return render(request, 'yourvocab/new_lesson.html', {'form': form, 'helper_symbols': course.helper_symbols})


def lesson_stats(request, course_id, lesson_id):
    course = models.Course.objects.get(pk=course_id)
    lesson = models.Lesson.objects.get(pk=lesson_id)

    qa = models.Question.objects.filter(lesson=lesson)
    qs = [models.QuestionStudent.objects.get(question=q, student=request.user) for q in qa]

    scores = models.LessonStudent.objects.filter(lesson=lesson, student=request.user)

    count = qa.count()
    mistake_colors = ['rgba(255, 99, 132, 0.2)', ] * count
    mistake_borders = ['rgba(255, 99, 132, 1)', ] * count
    mistake_data = [q.mistakes_count for q in qs]
    mistake_label = [q.question_text for q in qa]

    attendance_dict = [{'x': s.date_time.strftime('%Y-%m-%d %H:%M'), 'y': s.points} for s in scores]

    return render(request, 'yourvocab/lesson_stats.html', {'course': course,
                                                           'lesson': lesson,
                                                           'attendance_dict': attendance_dict,
                                                           'mistake_colors': mistake_colors,
                                                           'mistake_borders': mistake_borders,
                                                           'mistake_data': mistake_data,
                                                           'mistake_label': mistake_label})


def lesson_delete(request, course_id, lesson_id):
    course = models.Course.objects.get(pk=course_id)
    models.Lesson.objects.get(pk=lesson_id, course=course).delete()
    return JsonResponse({'result': 'ok'})
