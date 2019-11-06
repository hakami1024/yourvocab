# -*- coding: utf-8 -*-
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from yourvocab import models


class SignUpForm(UserCreationForm):
    email = forms.EmailField(max_length=254, help_text='Required. Inform a valid email address.')

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2', )


class CourseForm(forms.ModelForm):
    right_answer_bonus = forms.IntegerField(min_value=0, max_value=10, initial=5, help_text='How much should we increase your score after right answer?')
    wrong_answer_penalty = forms.IntegerField(min_value=0, max_value=10, initial=1, help_text='How much should we decrease your score after wrong answer?')
    show_answer_penalty = forms.IntegerField(min_value=0, max_value=10, initial=2, help_text='How much should we decrease your score after showing the answer as a hint?')

    class Meta:
        model = models.Course
        fields = ('name', 'public', 'helper_symbols', 'right_answer_bonus', 'wrong_answer_penalty', 'show_answer_penalty')
        help_texts = {
            'helper_symbols': 'For example, for German that could be: ÄäÖöÜüß (no spaces or commas are required)',
            'public': 'Check, if you want to share the course with everyone',
        }


class LessonForm(forms.ModelForm):
    questions = forms.CharField(widget=forms.Textarea())
    answers = forms.CharField(widget=forms.Textarea())

    class Meta:
        model = models.Lesson
        fields = ('name', 'questions', 'answers')

    def is_valid(self):
        """Check if value consists only of valid emails."""
        # Use the parent's handling of required fields, etc.
        is_valid = super().is_valid()
        questions = self.cleaned_data['questions'].split('\r\n')
        answers = self.cleaned_data['answers'].split('\r\n')

        if len(questions) != len(answers):
            if len(questions) < len(answers):
                self.add_error('questions', 'Questions should have as many lines as answers')
            else:
                self.add_error('answers', 'Answers should have as many lines as questions')
            is_valid = False

        if any([not q.strip() for q in questions]):
            self.add_error('questions', 'Empty lines are not permitted')
            is_valid = False

        if any([not a.strip() for a in answers]):
            self.add_error('answers', 'Empty lines are not permitted')
            is_valid = False

        return is_valid

