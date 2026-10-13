from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from decimal import Decimal

from core.models import Course, CourseContent, Instructor, UserProfile
from core.forms import CourseContentForm


class CourseContentManagementTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Create instructor user and profile
        self.instructor_user = User.objects.create_user(
            username="testinstructor",
            email="instructor@example.com",
            password="testpassword123"
        )
        self.instructor_profile = UserProfile.objects.create(
            user=self.instructor_user,
            role="instructor"
        )
        self.instructor = Instructor.objects.create(
            first_name="Test",
            last_name="Instructor",
            email="instructor@example.com",
            phone="1234567890",
            specialization="Computer Science"
        )

        # Create another student user
        self.student_user = User.objects.create_user(
            username="teststudent",
            email="student@example.com",
            password="testpassword123"
        )
        self.student_profile = UserProfile.objects.create(
            user=self.student_user,
            role="student"
        )

        # Create test course
        self.course = Course.objects.create(
            title="Bootstrap Mastery",
            category="programming",
            price=Decimal("499.00"),
            description="Complete Bootstrap 5 frontend course",
            duration="10 hours",
            instructor=self.instructor,
            is_active=True
        )

        # Create 2 initial lessons
        self.lesson1 = CourseContent.objects.create(
            course=self.course,
            title="Lesson 1: Introduction to Bootstrap",
            content_type="video",
            order=1,
            duration="15 mins",
            is_free_preview=True,
            video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        )
        self.lesson2 = CourseContent.objects.create(
            course=self.course,
            title="Lesson 2: Grid and Flexbox",
            content_type="document",
            order=2,
            duration="20 mins",
            is_free_preview=False
        )

    def test_form_widgets_have_bootstrap_classes(self):
        """Verify CourseContentForm fields have proper Bootstrap 5 classes."""
        form = CourseContentForm()
        self.assertIn("form-control", form.fields["title"].widget.attrs["class"])
        self.assertIn("form-select", form.fields["content_type"].widget.attrs["class"])
        self.assertIn("form-control", form.fields["order"].widget.attrs["class"])
        self.assertIn("form-control", form.fields["duration"].widget.attrs["class"])
        self.assertIn("form-check-input", form.fields["is_free_preview"].widget.attrs["class"])
        self.assertIn("form-control", form.fields["video_url"].widget.attrs["class"])
        self.assertIn("form-control", form.fields["notes_file"].widget.attrs["class"])
        self.assertIn("form-control", form.fields["file_url"].widget.attrs["class"])
        self.assertIn("form-control", form.fields["description"].widget.attrs["class"])
        self.assertIn("form-control", form.fields["text_content"].widget.attrs["class"])

    def test_unauthorized_user_cannot_access_curriculum_manage(self):
        """Student or unauthenticated user cannot view or manage curriculum."""
        # Unauthenticated
        url = reverse("course_content_manage", kwargs={"course_id": self.course.course_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

        # Logged in as student
        self.client.login(username="teststudent", password="testpassword123")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("instructor_courses"), target_status_code=302)

    def test_instructor_can_access_curriculum_manage_with_metrics(self):
        """Authorized instructor sees curriculum management dashboard and stats."""
        self.client.login(username="testinstructor", password="testpassword123")
        url = reverse("course_content_manage", kwargs={"course_id": self.course.course_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "course_content_manage.html")
        self.assertEqual(response.context["total_lessons"], 2)
        self.assertEqual(response.context["video_count"], 1)
        self.assertEqual(response.context["document_count"], 1)
        self.assertEqual(response.context["preview_count"], 1)
        self.assertContains(response, "Lesson 1: Introduction to Bootstrap")
        self.assertContains(response, "Lesson 2: Grid and Flexbox")

    def test_reorder_lessons_up_and_down(self):
        """Test moving lessons up and down."""
        self.client.login(username="testinstructor", password="testpassword123")
        
        # Lesson 2 is currently order 2. Move it up.
        reorder_up_url = reverse("course_content_reorder", kwargs={"content_id": self.lesson2.content_id, "direction": "up"})
        response = self.client.get(reorder_up_url)
        self.assertEqual(response.status_code, 302)

        self.lesson1.refresh_from_db()
        self.lesson2.refresh_from_db()
        self.assertEqual(self.lesson2.order, 1)
        self.assertEqual(self.lesson1.order, 2)

        # Now move lesson 2 back down
        reorder_down_url = reverse("course_content_reorder", kwargs={"content_id": self.lesson2.content_id, "direction": "down"})
        response = self.client.get(reorder_down_url)
        self.assertEqual(response.status_code, 302)

        self.lesson1.refresh_from_db()
        self.lesson2.refresh_from_db()
        self.assertEqual(self.lesson1.order, 1)
        self.assertEqual(self.lesson2.order, 2)

    def test_add_lesson_with_valid_pdf_notes(self):
        """Adding a lesson with a valid PDF file succeeds."""
        self.client.login(username="testinstructor", password="testpassword123")
        url = reverse("course_content_add", kwargs={"course_id": self.course.course_id})

        pdf_content = b"%PDF-1.4 Mock PDF content for testing course notes"
        pdf_file = SimpleUploadedFile("lecture_notes.pdf", pdf_content, content_type="application/pdf")

        data = {
            "title": "Lesson 3: Advanced Components",
            "content_type": "document",
            "order": 3,
            "duration": "30 mins",
            "notes_file": pdf_file,
            "description": "Deep dive into modals, tooltips, and carousels.",
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.course.contents.count(), 3)
        new_lesson = self.course.contents.get(order=3)
        self.assertEqual(new_lesson.title, "Lesson 3: Advanced Components")
        self.assertTrue(bool(new_lesson.notes_file))

    def test_add_lesson_with_invalid_file_extension_rejected(self):
        """Uploading an unauthorized file extension (.exe) triggers validation error."""
        self.client.login(username="testinstructor", password="testpassword123")
        url = reverse("course_content_add", kwargs={"course_id": self.course.course_id})

        bad_file = SimpleUploadedFile("danger.exe", b"executable bytes", content_type="application/octet-stream")

        data = {
            "title": "Lesson 4: Invalid File Test",
            "content_type": "document",
            "order": 4,
            "notes_file": bad_file,
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context["form"], "notes_file", "Unsupported file format '.exe'. Allowed formats: PDF, DOCX, TXT, PPTX.")

    def test_delete_lesson(self):
        """Deleting a lesson removes it and redirects to management view."""
        self.client.login(username="testinstructor", password="testpassword123")
        delete_url = reverse("course_content_delete", kwargs={"content_id": self.lesson2.content_id})

        # GET shows confirm page
        get_response = self.client.get(delete_url)
        self.assertEqual(get_response.status_code, 200)
        self.assertTemplateUsed(get_response, "course_content_confirm_delete.html")
        self.assertContains(get_response, "Delete Lesson?")

        # POST confirms deletion
        post_response = self.client.post(delete_url)
        self.assertEqual(post_response.status_code, 302)
        self.assertFalse(CourseContent.objects.filter(content_id=self.lesson2.content_id).exists())
