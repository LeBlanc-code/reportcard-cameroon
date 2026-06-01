"""
Business logic layer for mark submission and validation.
"""

from django.db import transaction
from django.core.exceptions import ValidationError
from .models import Mark, StudentProfile, Subject, TermConfig
import datetime


class MarkSubmissionService:
    """
    Service for submitting and validating student marks.
    Handles validation, duplicate prevention, and persistence.
    """

    # Valid score range
    MIN_SCORE = 0
    MAX_SCORE = 100

    @staticmethod
    def validate_score(score):
        """
        Validate that a score is within the acceptable range.
        
        Args:
            score: The score to validate (int or float)
            
        Raises:
            ValidationError: If score is out of range
        """
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
        """
        Check if a mark already exists for this student-subject-term combination.
        
        Args:
            student: StudentProfile instance
            subject: Subject instance
            term: Term string (e.g., "Term 1")
            
        Returns:
            Mark instance if duplicate exists, None otherwise
        """
        return Mark.objects.filter(
            student=student,
            subject=subject,
            term=term
        ).first()

    @staticmethod
    def validate_student_authorization(user, student):
        """
        Verify that the user is authorized to submit marks for this student.
        
        Args:
            user: CustomUser instance
            student: StudentProfile instance
            
        Raises:
            ValidationError: If user is not authorized
        """
        if user.role == 'teacher':
            pass
        elif user.role == 'class_master':
            if student.school_class.class_master != user:
                raise ValidationError(
                    f"You can only enter marks for students in your class."
                )
        else:
            raise ValidationError(
                f"Your role ({user.role}) is not authorized to submit marks for students."
            )

    @staticmethod
    def check_marks_deadline(student, term):
        """
        Check if the marks submission deadline has passed for this student's term.
        
        Args:
            student: StudentProfile instance
            term: Term string
            
        Raises:
            ValidationError: If the deadline has passed
        """
        school = student.school_class.school if student.school_class else None
        if not school:
            return
        try:
            config = TermConfig.objects.get(school=school, term=term)
        except TermConfig.DoesNotExist:
            return
        if config.is_past_deadline():
            raise ValidationError(
                f"Marks submission deadline for {term} was {config.marks_deadline}. "
                f"Marks can no longer be entered."
            )
        elif user.role == 'class_master':
            # Class masters can enter marks for any subject in their class
            pass
        else:
            raise ValidationError(
                f"Your role ({user.role}) is not authorized to submit marks."
            )

    @staticmethod
    def validate_student_authorization(user, student):
        """
        Verify that the user is authorized to submit marks for this student.
        
        Args:
            user: CustomUser instance
            student: StudentProfile instance
            
        Raises:
            ValidationError: If user is not authorized
        """
        if user.role == 'teacher':
            # Teachers can submit for any student (subject filtering is separate)
            pass
        elif user.role == 'class_master':
            if student.school_class.class_master != user:
                raise ValidationError(
                    f"You can only enter marks for students in your class."
                )
        else:
            raise ValidationError(
                f"Your role ({user.role}) is not authorized to submit marks for students."
            )

    @staticmethod
    @transaction.atomic
    def submit_mark(user, student, subject, score, term, replace_existing=False):
        """
        Submit a student mark with full validation and duplicate prevention.
        
        Args:
            user: CustomUser instance (the one submitting the mark)
            student: StudentProfile instance
            subject: Subject instance
            score: Mark score (0-100)
            term: Term string (e.g., "Term 1")
            replace_existing: If True, replace existing mark; if False, raise error on duplicate
            
        Returns:
            tuple: (success: bool, message: str, mark: Mark or None)
            
        Raises:
            ValidationError: If validation fails
        """
        # Validate score
        MarkSubmissionService.validate_score(score)

        # Check deadline
        MarkSubmissionService.check_marks_deadline(student, term)

        # Check authorization
        MarkSubmissionService.validate_teacher_authorization(user, subject)
        MarkSubmissionService.validate_student_authorization(user, student)

        # Check for duplicates
        existing_mark = MarkSubmissionService.check_duplicate_mark(student, subject, term)

        if existing_mark:
            if not replace_existing:
                raise ValidationError(
                    f"A mark for this student in {subject.name} ({term}) already exists. "
                    f"Please update the existing mark or delete it first."
                )
            # Replace existing mark
            existing_mark.score = score
            existing_mark.save()
            return (
                True,
                f"Mark for {student.user.get_full_name()} in {subject.name} has been updated.",
                existing_mark
            )

        # Create new mark
        mark = Mark.objects.create(
            student=student,
            subject=subject,
            score=score,
            term=term
        )

        return (
            True,
            f"Mark for {student.user.get_full_name()} in {subject.name} has been saved.",
            mark
        )

    @staticmethod
    def get_submitted_marks(user, term=None):
        """
        Get marks submitted by a user (teacher/class_master).
        
        Args:
            user: CustomUser instance
            term: Optional term string filter
            
        Returns:
            QuerySet of Mark objects
        """
        marks = Mark.objects.select_related(
            'student__user',
            'student__school_class',
            'subject__teacher'
        )

        if user.role == 'teacher':
            marks = marks.filter(subject__teacher=user)
        elif user.role == 'class_master':
            marks = marks.filter(student__school_class__class_master=user)
        else:
            marks = marks.none()

        if term:
            marks = marks.filter(term=term)

        return marks.order_by('student__user__last_name', 'student__user__first_name')
