from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.exceptions import ValidationError
from .models import CustomUser, Mark, Subject, StudentProfile, School, Class, TermConfig
from .services import MarkSubmissionService


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label='Username or Email',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username or email',
            'autofocus': True
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        })
    )

    def clean(self):
        username = self.cleaned_data.get('username')
        if username and '@' in username:
            try:
                user = CustomUser.objects.get(email__iexact=username)
                self.cleaned_data['username'] = user.get_username()
            except CustomUser.DoesNotExist:
                pass
        return super().clean()


class CreateUserForm(UserCreationForm):
    school = forms.ModelChoiceField(
        queryset=School.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    assigned_class = forms.ModelChoiceField(
        queryset=Class.objects.none(),
        required=False,
        label='Assign to Class',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = CustomUser
        fields = [
            'username', 'first_name', 'last_name',
            'email', 'role', 'school', 'phone_number',
            'password1', 'password2'
        ]
        widgets = {
            'username':     forms.TextInput(attrs={'class': 'form-control'}),
            'first_name':   forms.TextInput(attrs={'class': 'form-control'}),
            'last_name':    forms.TextInput(attrs={'class': 'form-control'}),
            'email':        forms.EmailInput(attrs={'class': 'form-control'}),
            'role':         forms.Select(attrs={'class': 'form-select', 'id': 'id_role'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs['class'] = 'form-control'
        self.fields['password2'].widget.attrs['class'] = 'form-control'

        if 'school' in self.data:
            try:
                school_id = int(self.data.get('school'))
                self.fields['assigned_class'].queryset = Class.objects.filter(school_id=school_id)
            except (ValueError, TypeError):
                pass
        elif self.initial.get('school'):
            self.fields['assigned_class'].queryset = Class.objects.filter(
                school=self.initial['school']
            )

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        school = cleaned_data.get('school')

        if role == 'vice_principal' and school:
            existing_vps = CustomUser.objects.filter(
                role='vice_principal',
                school=school
            ).count()
            if existing_vps >= 2:
                raise ValidationError(
                    f"School '{school.name}' already has the maximum of 2 vice principals."
                )

        if role in ('principal', 'vice_principal', 'school_admin') and not school:
            raise ValidationError(
                f"A {role.replace('_', ' ').title()} must be assigned to a school."
            )

        assigned_class = cleaned_data.get('assigned_class')
        if role == 'student' and not assigned_class:
            raise ValidationError('A student must be assigned to a class.')
        if role == 'class_master' and not assigned_class:
            raise ValidationError('A class master must be assigned to a class.')

        return cleaned_data


class MarkForm(forms.ModelForm):
    def __init__(self, *args, user=None, class_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.target_class = None

        subject_qs = Subject.objects.all()
        student_qs = StudentProfile.objects.all()

        if user is not None:
            if user.role == 'teacher':
                teacher_classes = Class.objects.filter(subjects__teacher=user).distinct()
                if class_id:
                    self.target_class = teacher_classes.filter(id=class_id).first()
                else:
                    self.target_class = teacher_classes.first()

                if self.target_class:
                    subject_qs = self.target_class.subjects.filter(teacher=user)
                    student_qs = StudentProfile.objects.filter(school_class=self.target_class)
                else:
                    subject_qs = Subject.objects.filter(teacher=user)
                    student_qs = StudentProfile.objects.filter(
                        school_class__in=teacher_classes
                    )
            elif user.role == 'class_master':
                student_qs = StudentProfile.objects.filter(school_class__class_master=user)
                my_class = Class.objects.filter(class_master=user).first()
                if my_class:
                    self.target_class = my_class
                    subject_qs = my_class.subjects.all()
            elif user.role in ('principal', 'vice_principal', 'school_admin'):
                if class_id:
                    self.target_class = Class.objects.filter(
                        id=class_id, school=user.school
                    ).first()
                if self.target_class:
                    subject_qs = self.target_class.subjects.all()
                    student_qs = StudentProfile.objects.filter(school_class=self.target_class)
                else:
                    student_qs = StudentProfile.objects.filter(
                        school_class__school=user.school
                    )

        self.fields['subject'].queryset = subject_qs
        self.fields['student'].queryset = student_qs

    def clean(self):
        cleaned_data = super().clean()
        score = cleaned_data.get('score')
        student = cleaned_data.get('student')
        subject = cleaned_data.get('subject')
        term = cleaned_data.get('term')

        if score and student and subject and term:
            try:
                MarkSubmissionService.validate_score(score)
            except ValidationError as e:
                self.add_error('score', e)

            existing_mark = MarkSubmissionService.check_duplicate_mark(
                student, subject, term
            )
            if existing_mark:
                self.add_error(
                    None,
                    ValidationError(
                        f"A mark for {student.user.get_full_name()} in {subject.name} ({term}) "
                        f"already exists. You can update it directly.",
                        code='duplicate_mark'
                    )
                )

            if self.user:
                try:
                    MarkSubmissionService.validate_teacher_authorization(self.user, subject)
                except ValidationError as e:
                    self.add_error('subject', e)

                try:
                    MarkSubmissionService.validate_student_authorization(self.user, student)
                except ValidationError as e:
                    self.add_error('student', e)

            try:
                MarkSubmissionService.check_marks_deadline(student, term)
            except ValidationError as e:
                self.add_error(None, e)

        return cleaned_data

    class Meta:
        model = Mark
        fields = ["student", "subject", "score", "term"]
        widgets = {
            "student": forms.Select(attrs={"class": "form-control"}),
            "subject": forms.Select(attrs={"class": "form-control"}),
            "score": forms.NumberInput(attrs={"class": "form-control", "placeholder": "Enter score (0-100)"}),
            "term": forms.TextInput(attrs={"class": "form-control", "placeholder": "Term name"}),
        }
        help_texts = {
            'score': 'Enter a score between 0 and 100.',
        }


class TermConfigForm(forms.ModelForm):
    class Meta:
        model = TermConfig
        fields = ['term', 'closing_date', 'closing_time', 'marks_deadline']
        widgets = {
            'term': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Term 1, First Term'}),
            'closing_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'closing_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time', 'value': '15:30'}),
            'marks_deadline': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
        help_texts = {
            'marks_deadline': 'Last day for teachers to upload marks (max 3 days before closing).',
        }
