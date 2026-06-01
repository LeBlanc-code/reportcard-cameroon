import datetime
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator


class School(models.Model):
    name = models.CharField(max_length=200)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        permissions = [
            ("manage_school", "Can manage school settings"),
        ]


class CustomUser(AbstractUser):

    ROLE_CHOICES = [
        ('teacher', 'Teacher'),
        ('class_master', 'Class Master'),
        ('principal', 'Principal'),
        ('vice_principal', 'Vice Principal'),
        ('school_admin', 'School Admin'),
        ('student', 'Student'),
    ]

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='student'
    )
    phone_number = models.CharField(max_length=20, blank=True)
    school = models.ForeignKey(
        School,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='staff'
    )

    def is_teacher(self):
        return self.role == 'teacher'

    def is_class_master(self):
        return self.role == 'class_master'

    def is_principal(self):
        return self.role == 'principal'

    def is_vice_principal(self):
        return self.role == 'vice_principal'

    def is_school_admin(self):
        return self.role == 'school_admin'

    def is_student(self):
        return self.role == 'student'

    def can_act_as_principal(self):
        return self.role in ('principal', 'vice_principal') or self.is_superuser or self.is_staff

    def clean(self):
        if self.role == 'vice_principal' and self.school:
            existing_vps = CustomUser.objects.filter(
                role='vice_principal',
                school=self.school
            ).exclude(pk=self.pk).count()
            if existing_vps >= 2:
                raise ValidationError(
                    f"School '{self.school.name}' already has the maximum of 2 vice principals."
                )
        super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_full_name()} ({self.get_role_display()})"


class Class(models.Model):
    SERIES_CHOICES = [
        ('', '---'),
        ('A', 'Arts (A)'),
        ('C', 'Science (C)'),
        ('D', 'Mathematics & Physics (D)'),
        ('TI', 'Industrial Technology (TI)'),
        ('A1', 'Arts A1 - Literature'),
        ('A2', 'Arts A2 - Bilingual Letters'),
        ('A3', 'Arts A3 - Philosophy'),
        ('A4', 'Arts A4 - Modern Letters'),
        ('S1', 'Science S1 - Maths/Physics'),
        ('S2', 'Science S2 - Life Sciences'),
        ('S3', 'Science S3 - Physical Sciences'),
        ('S4', 'Science S4 - Maths/Technology'),
        ('Other', 'Other'),
    ]

    name = models.CharField(max_length=100)
    series = models.CharField(max_length=20, choices=SERIES_CHOICES, blank=True, default='')
    section = models.CharField(max_length=20, blank=True)
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="classes")
    class_master = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'role': 'class_master'}
    )
    subjects = models.ManyToManyField('Subject', blank=True, related_name='classes')

    def __str__(self):
        parts = [self.name]
        if self.series:
            parts.append(f"Series {self.series}")
        if self.section:
            parts.append(f"Sec. {self.section}")
        parts.append(f"- {self.school.name}")
        return " ".join(parts)

    class Meta:
        permissions = [
            ("manage_class", "Can manage class and assignments"),
        ]


class StudentProfile(models.Model):
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'student'}
    )
    school_class = models.ForeignKey(
        Class,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.school_class})"


class Subject(models.Model):
    name = models.CharField(max_length=100)
    teacher = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'role': 'teacher'}
    )
    school_class = models.ForeignKey(
        Class,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='class_subjects'
    )

    def __str__(self):
        return self.name

    class Meta:
        permissions = [
            ("manage_subjects", "Can add/edit subjects and assign teachers"),
        ]


class Activity(models.Model):
    name = models.CharField(max_length=100)
    school_class = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='activities')
    max_score = models.DecimalField(max_digits=5, decimal_places=2, default=20.00)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.school_class.name})"

    class Meta:
        unique_together = ['name', 'school_class']


class Mark(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="marks")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[
            MinValueValidator(0, "Score cannot be less than 0."),
            MaxValueValidator(100, "Score cannot be more than 100.")
        ]
    )
    term = models.CharField(max_length=20, default="Term 1")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.student.user.get_full_name()} - {self.subject.name}: {self.score}"

    class Meta:
        permissions = [
            ("enter_marks", "Can enter and edit student marks"),
        ]
        unique_together = ['student', 'subject', 'term']
        indexes = [
            models.Index(fields=['student', 'term']),
            models.Index(fields=['subject', 'term']),
        ]


class ReportCard(models.Model):
    student = models.OneToOneField(StudentProfile, on_delete=models.CASCADE)
    term = models.CharField(max_length=20, default="Term 1")
    validated = models.BooleanField(default=False)
    validated_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='validated_reportcards',
        limit_choices_to={'role__in': ['principal', 'vice_principal']}
    )
    validated_at = models.DateTimeField(null=True, blank=True)
    print_permission = models.BooleanField(default=False)
    print_permission_granted_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='print_granted_reportcards',
        limit_choices_to={'role__in': ['principal', 'vice_principal']}
    )
    print_permission_granted_at = models.DateTimeField(null=True, blank=True)

    def total_score(self):
        return sum(mark.score for mark in self.student.marks.filter(term=self.term))

    def average_score(self):
        marks = self.student.marks.filter(term=self.term)
        return sum(mark.score for mark in marks) / marks.count() if marks.exists() else 0

    def __str__(self):
        return f"{self.student.user.get_full_name()} - {self.term}"

    class Meta:
        permissions = [
            ("validate_reportcard", "Can validate/approve report cards"),
        ]


class TermConfig(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='term_configs')
    term = models.CharField(max_length=50)
    closing_date = models.DateField()
    closing_time = models.TimeField(default=datetime.time(15, 30))
    marks_deadline = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.marks_deadline and self.closing_date:
            delta = self.closing_date - self.marks_deadline
            if delta.days < 0:
                raise ValidationError('Marks deadline cannot be after the closing date.')
            if delta.days > 3:
                raise ValidationError('Marks deadline must be at most 3 days before the closing date.')
        super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def is_past_deadline(self):
        if not self.marks_deadline:
            return False
        return datetime.date.today() > self.marks_deadline

    def __str__(self):
        return f"{self.school.name} - {self.term} (closes {self.closing_date} at {self.closing_time})"

    class Meta:
        unique_together = ['school', 'term']
        permissions = [
            ("manage_term_config", "Can configure term closing dates and times"),
        ]


class Transcript(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='transcripts')
    generated_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='generated_transcripts'
    )
    validated = models.BooleanField(default=False)
    validated_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='validated_transcripts',
        limit_choices_to={'role__in': ['principal', 'vice_principal']}
    )
    validated_at = models.DateTimeField(null=True, blank=True)
    print_permission = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Transcript - {self.student.user.get_full_name()}"

    class Meta:
        permissions = [
            ("manage_transcript", "Can generate and manage transcripts"),
            ("validate_transcript", "Can validate transcripts"),
        ]
