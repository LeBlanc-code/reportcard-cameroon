"""
Business logic layer for mark submission and validation.
"""

from django.db import transaction
from django.core.exceptions import ValidationError
from .models import Mark, StudentProfile, Subject, Class, TermConfig, CustomUser, ReportCard
import datetime


class MarkSubmissionService:
    """
    Service for submitting and validating student marks.
    Handles validation, duplicate prevention, and persistence.
    """

    MIN_SCORE = 0
    MAX_SCORE = 100

    @staticmethod
    def validate_score(score):
        try:
            score_float = float(score)
        except (ValueError, TypeError):
            raise ValidationError("Score must be a valid number.")

        if score_float < MarkSubmissionService.MIN_SCORE:
            raise ValidationError(
                f"Score cannot be less than {MarkSubmissionService.MIN_SCORE}."
            )
        if score_float > MarkSubmissionService.MAX_SCORE:
            raise ValidationError(
                f"Score cannot be more than {MarkSubmissionService.MAX_SCORE}."
            )

    @staticmethod
    def check_duplicate_mark(student, subject, term):
        return Mark.objects.filter(
            student=student,
            subject=subject,
            term=term
        ).first()

    @staticmethod
    def validate_teacher_authorization(user, subject):
        if user.is_staff_member():
            if user.role == 'teacher' and subject.teacher != user:
                raise ValidationError(
                    "You are only authorized to enter marks for subjects you teach."
                )
        else:
            raise ValidationError(
                f"Your role ({user.role}) is not authorized to submit marks."
            )

    @staticmethod
    def validate_student_authorization(user, student):
        if user.is_staff_member():
            if user.role == 'class_master':
                if student.school_class and student.school_class.class_master != user:
                    raise ValidationError(
                        "You can only enter marks for students in your class."
                    )
            elif user.role == 'teacher':
                if student.school_class:
                    teacher_classes = Class.objects.filter(
                        subjects__teacher=user
                    ).distinct()
                    if student.school_class not in teacher_classes:
                        raise ValidationError(
                            "You can only enter marks for students in classes where you teach."
                        )
        else:
            raise ValidationError(
                f"Your role ({user.role}) is not authorized to submit marks for students."
            )

    @staticmethod
    def check_marks_deadline(student, term):
        if not student.school_class:
            return
        school = student.school_class.school
        try:
            config = TermConfig.objects.get(school=school, term=term)
        except TermConfig.DoesNotExist:
            return
        if config.is_past_deadline():
            raise ValidationError(
                f"Marks submission deadline for {term} was {config.marks_deadline}. "
                f"Marks can no longer be entered."
            )

    @staticmethod
    def get_or_create_student(first_name, last_name, school_class):
        first_name = first_name.strip().title()
        last_name = last_name.strip().title()

        existing = StudentProfile.objects.filter(
            user__first_name__iexact=first_name,
            user__last_name__iexact=last_name,
            school_class=school_class
        ).first()

        if existing:
            return existing.user, existing, False

        school = school_class.school
        username_base = f"{first_name.lower()}.{last_name.lower()}"
        username = username_base
        counter = 1
        while CustomUser.objects.filter(username=username).exists():
            username = f"{username_base}{counter}"
            counter += 1

        password = 'student123'
        user = CustomUser(
            username=username,
            first_name=first_name,
            last_name=last_name,
            role='student',
            school=school,
        )
        user.set_password(password)
        user.save()

        profile = StudentProfile.objects.create(
            user=user,
            school_class=school_class
        )

        return user, profile, True

    @staticmethod
    @transaction.atomic
    def submit_mark(user, student, subject, score, term, replace_existing=False):
        MarkSubmissionService.validate_score(score)
        MarkSubmissionService.check_marks_deadline(student, term)
        MarkSubmissionService.validate_teacher_authorization(user, subject)
        MarkSubmissionService.validate_student_authorization(user, student)

        existing_mark = MarkSubmissionService.check_duplicate_mark(student, subject, term)

        if existing_mark:
            if not replace_existing:
                raise ValidationError(
                    f"A mark for this student in {subject.name} ({term}) already exists. "
                    f"Please update the existing mark or delete it first."
                )
            existing_mark.score = score
            existing_mark.save()
            return (
                True,
                f"Mark for {student.user.get_full_name()} in {subject.name} has been updated.",
                existing_mark
            )

        mark = Mark.objects.create(
            student=student,
            subject=subject,
            score=score,
            term=term
        )

        ReportCard.objects.get_or_create(
            student=student,
            defaults={'term': term}
        )

        return (
            True,
            f"Mark for {student.user.get_full_name()} in {subject.name} has been saved.",
            mark
        )

    @staticmethod
    def get_submitted_marks(user, term=None):
        marks = Mark.objects.select_related(
            'student__user',
            'student__school_class',
            'subject__teacher'
        )

        if user.role == 'teacher':
            marks = marks.filter(subject__teacher=user)
        elif user.role == 'class_master':
            marks = marks.filter(student__school_class__class_master=user)
        elif user.is_staff_member():
            marks = marks.filter(student__school_class__school=user.school)
        else:
            marks = marks.none()

        if term:
            marks = marks.filter(term=term)

        return marks.order_by('student__user__last_name', 'student__user__first_name')
