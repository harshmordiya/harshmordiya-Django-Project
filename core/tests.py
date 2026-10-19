from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from decimal import Decimal

from core.models import Course, CourseContent, Instructor, UserProfile, Student, Enrollment, Payment
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


class AdminAuthenticationAndDashboardTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Create admin/superuser
        self.admin_user = User.objects.create_superuser(
            username="masteradmin",
            email="admin@edulearn.com",
            password="adminpassword123"
        )
        # Deliberately don't create or set wrong profile initially to test healing

        # Create a regular student
        self.student_user = User.objects.create_user(
            username="regularstudent",
            email="student@edulearn.com",
            password="studentpassword123"
        )
        self.student_profile = UserProfile.objects.create(
            user=self.student_user,
            role="student"
        )
        from core.models import Student
        self.student_record = Student.objects.create(
            first_name="Regular",
            last_name="Learner",
            email="student@edulearn.com",
            phone="9988776655",
            address="123 Learning Lane"
        )

        # Create an instructor
        self.instructor_user = User.objects.create_user(
            username="mathguru",
            email="math@edulearn.com",
            password="mathpassword123"
        )
        self.instructor_profile = UserProfile.objects.create(
            user=self.instructor_user,
            role="instructor"
        )
        self.instructor_record = Instructor.objects.create(
            first_name="Alan",
            last_name="Turing",
            email="math@edulearn.com",
            phone="9876543210",
            specialization="Mathematics"
        )

        # Create course
        self.course = Course.objects.create(
            title="Advanced Algorithms",
            category="programming",
            price=Decimal("999.00"),
            description="Deep dive into algorithms",
            duration="15 hours",
            instructor=self.instructor_record,
            is_active=True
        )

        # Create enrollment
        from core.models import Enrollment, Payment
        self.enrollment = Enrollment.objects.create(
            student=self.student_record,
            course=self.course,
            status="active"
        )

        # Create payment
        self.payment = Payment.objects.create(
            student=self.student_record,
            razorpay_order_id="order_test_12345",
            razorpay_payment_id="pay_test_67890",
            amount=Decimal("999.00"),
            status="paid"
        )

    def test_admin_login_role_detection_and_redirection(self):
        """Superuser logging in is recognized as Admin, profile healed, redirected to /admin-dashboard/."""
        response = self.client.post(reverse("login"), {
            "username": "masteradmin",
            "password": "adminpassword123"
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("admin_dashboard"))

        # Verify profile was healed to role='admin'
        profile = UserProfile.objects.get(user=self.admin_user)
        self.assertEqual(profile.role, "admin")

        # Verify user dashboard displays Role: Administrator, NOT student
        dash_response = self.client.get(reverse("dashboard"))
        self.assertEqual(dash_response.status_code, 200)
        self.assertContains(dash_response, "Role: Administrator")
        self.assertNotContains(dash_response, "Role: Student")
        # Verify card links to /admin-dashboard/
        self.assertContains(dash_response, reverse("admin_dashboard"))
        # Verify visible link to Django admin is removed from UI
        self.assertNotContains(dash_response, 'href="/admin/"')
        # Verify built-in Django admin at /admin/ remains functional via direct URL
        admin_direct_resp = self.client.get("/admin/")
        self.assertIn(admin_direct_resp.status_code, [200, 302])

    def test_admin_dashboard_metrics_rendered(self):
        """Admin can access /admin-dashboard/ and live statistics are displayed."""
        self.client.login(username="masteradmin", password="adminpassword123")
        response = self.client.get(reverse("admin_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "admin_dashboard.html")
        self.assertEqual(response.context["total_students"], 1)
        self.assertEqual(response.context["total_instructors"], 1)
        self.assertEqual(response.context["total_courses"], 1)
        self.assertEqual(response.context["total_enrollments"], 1)
        self.assertEqual(response.context["total_revenue"], Decimal("999.00"))
        self.assertContains(response, "EduLearn Operations Hub")
        self.assertContains(response, "Advanced Algorithms")

    def test_admin_management_subpages_accessible(self):
        """Admin can access all dedicated management subpages."""
        self.client.login(username="masteradmin", password="adminpassword123")

        for url_name in ["admin_students", "admin_instructors", "admin_courses", "admin_enrollments", "admin_payments"]:
            resp = self.client.get(reverse(url_name))
            self.assertEqual(resp.status_code, 200, f"Failed accessing {url_name}")

    def test_unauthorized_student_strictly_denied_from_admin_dashboard(self):
        """Regular student cannot access admin dashboard or subpages."""
        self.client.login(username="regularstudent", password="studentpassword123")

        for url_name in ["admin_dashboard", "admin_students", "admin_courses"]:
            resp = self.client.get(reverse(url_name))
            self.assertEqual(resp.status_code, 302)
            self.assertRedirects(resp, reverse("dashboard"))

    def test_unauthorized_instructor_strictly_denied_from_admin_dashboard(self):
        """Instructor cannot access custom admin dashboard."""
        self.client.login(username="mathguru", password="mathpassword123")
        resp = self.client.get(reverse("admin_dashboard"))
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, reverse("dashboard"))

    def test_course_toggle_status_action(self):
        """Admin can toggle course between Active and Draft."""
        self.client.login(username="masteradmin", password="adminpassword123")
        toggle_url = reverse("admin_course_toggle_status", kwargs={"course_id": self.course.course_id})

        # Toggle to draft
        response = self.client.get(toggle_url)
        self.assertEqual(response.status_code, 302)
        self.course.refresh_from_db()
        self.assertFalse(self.course.is_active)

        # Toggle back to active
        response = self.client.get(toggle_url)
        self.assertEqual(response.status_code, 302)
        self.course.refresh_from_db()
        self.assertTrue(self.course.is_active)

    def test_enrollment_update_status_action(self):
        """Admin can change enrollment status."""
        self.client.login(username="masteradmin", password="adminpassword123")
        update_url = reverse("admin_enrollment_update_status", kwargs={"enrollment_id": self.enrollment.enrollment_id, "new_status": "completed"})

        response = self.client.get(update_url)
        self.assertEqual(response.status_code, 302)
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.status, "completed")

    def test_django_builtin_admin_accessible(self):
        """Django built-in admin (/admin/) remains fully accessible."""
        self.client.login(username="masteradmin", password="adminpassword123")
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 200)


class StudentAndInstructorModelTests(TestCase):
    """
    Test suite verifying Student and Instructor model functionality,
    methods, properties, and helper workflows.
    """

    def setUp(self):
        self.instructor = Instructor.objects.create(
            first_name="Ada",
            last_name="Lovelace",
            email="ada@edulearn.com",
            phone="9876543210",
            specialization="Computer Science",
        )
        self.student = Student.objects.create(
            first_name="Charles",
            last_name="Babbage",
            email="charles@edulearn.com",
            phone="9123456789",
        )
        self.course = Course.objects.create(
            title="Analytical Engines 101",
            category="programming",
            price=Decimal("499.00"),
            description="Introduction to computing hardware.",
            duration="6 weeks",
            instructor=self.instructor,
        )
        self.enrollment = Enrollment.objects.create(
            student=self.student,
            course=self.course,
            status="active",
        )
        self.payment = Payment.objects.create(
            student=self.student,
            razorpay_order_id="order_engine_001",
            razorpay_payment_id="pay_engine_001",
            amount=Decimal("499.00"),
            status="paid",
        )

    def test_student_properties_and_string_representation(self):
        """Verify Student __str__, full_name, enrolled_courses_count, and total_paid_amount."""
        self.assertEqual(str(self.student), "Charles Babbage")
        self.assertEqual(self.student.full_name, "Charles Babbage")
        self.assertEqual(self.student.enrolled_courses_count, 1)
        self.assertEqual(self.student.enrollments_count, 1)
        self.assertEqual(self.student.total_paid_amount, Decimal("499.00"))
        self.assertEqual(self.student.paid_total, Decimal("499.00"))
        self.assertIsNotNone(self.student.enrollment_date)

    def test_student_single_name_fallback(self):
        """Single name student does not contain trailing space and falls back gracefully."""
        single_student = Student.objects.create(
            first_name="Euclid",
            email="euclid@edulearn.com",
        )
        self.assertEqual(str(single_student), "Euclid")
        self.assertEqual(single_student.full_name, "Euclid")

    def test_instructor_properties_and_string_representation(self):
        """Verify Instructor __str__, full_name, courses_count, and students_count."""
        self.assertEqual(str(self.instructor), "Ada Lovelace")
        self.assertEqual(self.instructor.full_name, "Ada Lovelace")
        self.assertEqual(self.instructor.courses_count, 1)
        self.assertEqual(self.instructor.students_count, 1)
        self.assertIn(self.course, self.instructor.courses)

    def test_get_student_for_user_auto_healing(self):
        """A User with student role lacking Student record is safely auto-healed."""
        from core.views import get_student_for_user
        new_user = User.objects.create_user(
            username="healedstudent",
            email="healed@edulearn.com",
            password="testpassword123",
            first_name="Grace",
            last_name="Hopper",
        )
        UserProfile.objects.create(user=new_user, role="student")

        # Initially no Student record exists
        self.assertFalse(Student.objects.filter(email="healed@edulearn.com").exists())

        # Auto-healing creates Student profile
        student_obj = get_student_for_user(new_user)
        self.assertIsNotNone(student_obj)
        self.assertEqual(student_obj.email, "healed@edulearn.com")
        self.assertEqual(student_obj.full_name, "Grace Hopper")
        self.assertTrue(Student.objects.filter(email="healed@edulearn.com").exists())


class StudentAndInstructorListDirectoryViewsTests(TestCase):
    """
    Test suite verifying public / directory views listing all registered
    students and instructors.
    """

    def setUp(self):
        self.instructor1 = Instructor.objects.create(
            first_name="Marie",
            last_name="Curie",
            email="marie.curie@edulearn.com",
            phone="9876543210",
            specialization="Physics",
        )
        self.instructor2 = Instructor.objects.create(
            first_name="Albert",
            last_name="Einstein",
            email="albert.einstein@edulearn.com",
            phone="9876543211",
            specialization="Theoretical Physics",
        )
        self.student1 = Student.objects.create(
            first_name="Isaac",
            last_name="Newton",
            email="isaac.newton@edulearn.com",
            phone="9123456780",
            address="Cambridge",
        )
        self.student2 = Student.objects.create(
            first_name="Galileo",
            last_name="Galilei",
            email="galileo@edulearn.com",
            phone="9123456781",
            address="Pisa",
        )
        self.course = Course.objects.create(
            title="General Relativity",
            category="programming",
            price=Decimal("899.00"),
            description="Deep dive into modern physics.",
            duration="10 weeks",
            instructor=self.instructor2,
        )
        self.enrollment = Enrollment.objects.create(
            student=self.student1,
            course=self.course,
            status="active",
        )

    def test_instructor_list_view_renders_all_instructors(self):
        """instructor_list view returns 200, uses template, and displays all instructors."""
        response = self.client.get(reverse("instructor_list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "instructor_list.html")
        self.assertContains(response, "Marie Curie")
        self.assertContains(response, "Albert Einstein")
        self.assertContains(response, "Theoretical Physics")

    def test_instructor_list_view_search_and_filter(self):
        """instructor_list search filters by name or specialization."""
        # Search by query
        response = self.client.get(reverse("instructor_list") + "?q=Curie")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Marie Curie")
        self.assertNotContains(response, "Albert Einstein")

        # Filter by specialization
        response_spec = self.client.get(reverse("instructor_list") + "?specialization=Physics")
        self.assertEqual(response_spec.status_code, 200)
        self.assertContains(response_spec, "Marie Curie")

    def test_student_list_view_renders_all_students(self):
        """student_list view returns 200, uses template, and displays all students."""
        response = self.client.get(reverse("student_list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "student_list.html")
        self.assertContains(response, "Isaac Newton")
        self.assertContains(response, "Galileo Galilei")
        self.assertContains(response, "Cambridge")

    def test_student_list_view_search(self):
        """student_list search filters by student name."""
        response = self.client.get(reverse("student_list") + "?q=Isaac")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Isaac Newton")
        self.assertNotContains(response, "Galileo Galilei")

    def test_directory_view_renders_both_and_supports_tabs(self):
        """directory view returns 200 and supports all/instructors/students tabs."""
        # All members tab
        resp_all = self.client.get(reverse("directory"))
        self.assertEqual(resp_all.status_code, 200)
        self.assertTemplateUsed(resp_all, "directory.html")
        self.assertContains(resp_all, "Marie Curie")
        self.assertContains(resp_all, "Isaac Newton")

        # Instructors tab
        resp_inst = self.client.get(reverse("directory") + "?tab=instructors")
        self.assertEqual(resp_inst.status_code, 200)
        self.assertContains(resp_inst, "Marie Curie")

        # Students tab
        resp_stud = self.client.get(reverse("directory") + "?tab=students")
        self.assertEqual(resp_stud.status_code, 200)
        self.assertContains(resp_stud, "Isaac Newton")


class ManageAllCoursesTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Admin user
        self.admin_user = User.objects.create_superuser(
            username="adminuser",
            email="admin@example.com",
            password="adminpassword123"
        )
        UserProfile.objects.create(user=self.admin_user, role="admin")

        # Instructor user & profile
        self.inst_user = User.objects.create_user(
            username="prof_turing",
            email="alan.turing@example.com",
            password="turingpassword123"
        )
        UserProfile.objects.create(user=self.inst_user, role="instructor")
        self.instructor = Instructor.objects.create(
            first_name="Alan",
            last_name="Turing",
            email="alan.turing@example.com",
            specialization="Computation"
        )

        # Student user
        self.student_user = User.objects.create_user(
            username="student_user",
            email="student@example.com",
            password="studentpassword123"
        )
        UserProfile.objects.create(user=self.student_user, role="student")

        # Create active and draft courses
        self.active_course = Course.objects.create(
            title="Automata and Turing Machines",
            category="programming",
            price=Decimal("499.00"),
            description="Foundations of computer science.",
            duration="8 weeks",
            instructor=self.instructor,
            is_active=True
        )
        self.draft_course = Course.objects.create(
            title="Quantum Decryption Draft",
            category="data_science",
            price=Decimal("999.00"),
            description="Advanced cryptographic analysis.",
            duration="12 weeks",
            instructor=self.instructor,
            is_active=False
        )

    def test_anonymous_redirected(self):
        """Anonymous users must be redirected to login."""
        response = self.client.get(reverse("course_manage_all"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_student_forbidden_redirect(self):
        """Regular students cannot access course management table."""
        self.client.login(username="student_user", password="studentpassword123")
        response = self.client.get(reverse("course_manage_all"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/courses/", response.url)

    def test_instructor_access_and_renders_actions(self):
        """Instructor can access and sees Edit & Delete options for their courses."""
        self.client.login(username="prof_turing", password="turingpassword123")
        response = self.client.get(reverse("course_manage_all"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "course_manage_all.html")
        self.assertContains(response, "Automata and Turing Machines")
        self.assertContains(response, "Quantum Decryption Draft")
        # Check that Edit and Delete action URLs are present
        self.assertContains(response, reverse("course_edit", args=[self.active_course.course_id]))
        self.assertContains(response, reverse("course_delete", args=[self.active_course.course_id]))

    def test_search_filter(self):
        """Search query filters by course title."""
        self.client.login(username="prof_turing", password="turingpassword123")
        response = self.client.get(reverse("course_manage_all") + "?q=Automata")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Automata and Turing Machines")
        self.assertNotContains(response, "Quantum Decryption Draft")

    def test_status_filter(self):
        """Status filter separates active and draft courses."""
        self.client.login(username="prof_turing", password="turingpassword123")
        resp_active = self.client.get(reverse("course_manage_all") + "?status=active")
        self.assertEqual(resp_active.status_code, 200)
        self.assertContains(resp_active, "Automata and Turing Machines")
        self.assertNotContains(resp_active, "Quantum Decryption Draft")

        resp_draft = self.client.get(reverse("course_manage_all") + "?status=inactive")
        self.assertEqual(resp_draft.status_code, 200)
        self.assertContains(resp_draft, "Quantum Decryption Draft")
        self.assertNotContains(resp_draft, "Automata and Turing Machines")


class UserDeactivationReactivationTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Admin user
        self.admin_user = User.objects.create_superuser(
            username="admin_boss",
            email="admin.boss@example.com",
            password="adminpassword123"
        )
        UserProfile.objects.create(user=self.admin_user, role="admin")

        # Standard student user & Student record
        self.student_user = User.objects.create_user(
            username="active_student",
            email="student.test@example.com",
            password="studentpassword123"
        )
        UserProfile.objects.create(user=self.student_user, role="student")
        self.student = Student.objects.create(
            first_name="Active",
            last_name="Learner",
            email="student.test@example.com",
        )

    def test_admin_can_deactivate_and_reactivate_user(self):
        """Admin can toggle user active state between False and True."""
        self.client.login(username="admin_boss", password="adminpassword123")

        # 1. Deactivate
        resp_deact = self.client.get(reverse("admin_user_toggle_status", args=[self.student_user.id]))
        self.assertEqual(resp_deact.status_code, 302)
        self.student_user.refresh_from_db()
        self.assertFalse(self.student_user.is_active)

        # 2. Reactivate
        resp_react = self.client.get(reverse("admin_user_toggle_status", args=[self.student_user.id]))
        self.assertEqual(resp_react.status_code, 302)
        self.student_user.refresh_from_db()
        self.assertTrue(self.student_user.is_active)

    def test_admin_cannot_deactivate_self(self):
        """Admin cannot deactivate their own administrative account."""
        self.client.login(username="admin_boss", password="adminpassword123")
        resp = self.client.get(reverse("admin_user_toggle_status", args=[self.admin_user.id]))
        self.assertEqual(resp.status_code, 302)
        self.admin_user.refresh_from_db()
        self.assertTrue(self.admin_user.is_active)

    def test_non_admin_cannot_toggle_user_status(self):
        """Non-admin user is rejected when trying to toggle account status."""
        self.client.login(username="active_student", password="studentpassword123")
        resp = self.client.get(reverse("admin_user_toggle_status", args=[self.student_user.id]))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/dashboard/", resp.url)
        self.student_user.refresh_from_db()
        self.assertTrue(self.student_user.is_active)

    def test_deactivated_user_login_fails_with_message(self):
        """Deactivated user receives clear notification that account is deactivated."""
        self.student_user.is_active = False
        self.student_user.save()

        response = self.client.post(reverse("login"), {
            "username": "active_student",
            "password": "studentpassword123"
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Your account has been deactivated")


class AdminFilterAndSearchTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            username="admin_search",
            email="admin.search@example.com",
            password="adminpassword123"
        )
        UserProfile.objects.create(user=self.admin_user, role="admin")

        self.student1 = Student.objects.create(
            first_name="Alice",
            last_name="Wonderland",
            email="alice@example.com"
        )
        self.student2 = Student.objects.create(
            first_name="Bob",
            last_name="Builder",
            email="bob@example.com"
        )
        self.user_alice = User.objects.create_user(
            username="alice",
            email="alice@example.com",
            password="password123",
            is_active=True
        )
        self.user_bob = User.objects.create_user(
            username="bob",
            email="bob@example.com",
            password="password123",
            is_active=False
        )

        self.instructor = Instructor.objects.create(
            first_name="Grace",
            last_name="Hopper",
            email="grace@example.com",
            specialization="Computer Science"
        )
        self.course_free = Course.objects.create(
            title="Intro to Programming",
            category="programming",
            price=0,
            duration="2 hours",
            instructor=self.instructor,
            is_active=True
        )
        self.course_paid = Course.objects.create(
            title="Advanced Algorithms",
            category="data_science",
            price=999,
            duration="10 hours",
            instructor=self.instructor,
            is_active=True
        )

    def test_django_admin_changelist_pages_load(self):
        """Django admin changelist pages with filters and search load with 200 OK."""
        self.client.login(username="admin_search", password="adminpassword123")
        for model in ["student", "instructor", "course", "enrollment", "payment"]:
            url = reverse(f"admin:core_{model}_changelist")
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 200)

    def test_django_admin_student_custom_filter(self):
        """Custom StudentAccountStatusFilter filters active and deactivated students in Django admin."""
        self.client.login(username="admin_search", password="adminpassword123")
        url = reverse("admin:core_student_changelist")

        resp_active = self.client.get(url + "?account_status=active")
        self.assertEqual(resp_active.status_code, 200)
        self.assertContains(resp_active, "alice@example.com")
        self.assertNotContains(resp_active, "bob@example.com")

        resp_deact = self.client.get(url + "?account_status=deactivated")
        self.assertEqual(resp_deact.status_code, 200)
        self.assertContains(resp_deact, "bob@example.com")
        self.assertNotContains(resp_deact, "alice@example.com")

    def test_django_admin_course_price_tier_filter(self):
        """CoursePriceTierFilter separates free and paid courses in Django admin."""
        self.client.login(username="admin_search", password="adminpassword123")
        url = reverse("admin:core_course_changelist")

        resp_free = self.client.get(url + "?price_tier=free")
        self.assertEqual(resp_free.status_code, 200)
        self.assertContains(resp_free, "Intro to Programming")
        self.assertNotContains(resp_free, "Advanced Algorithms")

        resp_paid = self.client.get(url + "?price_tier=500_to_1500")
        self.assertEqual(resp_paid.status_code, 200)
        self.assertContains(resp_paid, "Advanced Algorithms")
        self.assertNotContains(resp_paid, "Intro to Programming")


class CustomDashboardSearchAndSortTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(
            username="admin_dash_sort",
            email="admin.dash@example.com",
            password="adminpassword123"
        )
        UserProfile.objects.create(user=self.admin, role="admin")

        self.st1 = Student.objects.create(first_name="Zara", last_name="Alpha", email="zara@example.com")
        self.st2 = Student.objects.create(first_name="Aaron", last_name="Beta", email="aaron@example.com")

        self.inst1 = Instructor.objects.create(first_name="Zoe", last_name="X", email="zoe@example.com")
        self.inst2 = Instructor.objects.create(first_name="Alan", last_name="Y", email="alan@example.com")

        self.c1 = Course.objects.create(
            title="Zenith AI",
            category="data_science",
            price=2000,
            duration="5 hours",
            instructor=self.inst1
        )
        self.c2 = Course.objects.create(
            title="Alpha Web Dev",
            category="web_development",
            price=500,
            duration="3 hours",
            instructor=self.inst2
        )

    def test_admin_students_sort_and_search(self):
        """Students can be sorted by name A-Z and filtered by search query."""
        self.client.login(username="admin_dash_sort", password="adminpassword123")

        # Sort name ascending
        resp = self.client.get(reverse("admin_students") + "?sort=name_asc")
        self.assertEqual(resp.status_code, 200)
        students = resp.context["students"]
        self.assertEqual(students[0].first_name, "Aaron")
        self.assertEqual(students[1].first_name, "Zara")

        # Search query
        resp_q = self.client.get(reverse("admin_students") + "?q=Zara")
        self.assertEqual(resp_q.status_code, 200)
        self.assertEqual(len(resp_q.context["students"]), 1)
        self.assertEqual(resp_q.context["students"][0].first_name, "Zara")

    def test_admin_courses_sort_and_category_filter(self):
        """Courses can be sorted by price ascending/descending and filtered by category."""
        self.client.login(username="admin_dash_sort", password="adminpassword123")

        # Sort price asc
        resp_price = self.client.get(reverse("admin_courses") + "?sort=price_asc")
        self.assertEqual(resp_price.status_code, 200)
        courses = list(resp_price.context["courses"])
        self.assertEqual(courses[0].title, "Alpha Web Dev")
        self.assertEqual(courses[1].title, "Zenith AI")

        # Category filter
        resp_cat = self.client.get(reverse("admin_courses") + "?category=data_science")
        self.assertEqual(resp_cat.status_code, 200)
        cat_courses = list(resp_cat.context["courses"])
        self.assertEqual(len(cat_courses), 1)
        self.assertEqual(cat_courses[0].title, "Zenith AI")


class StudentModelAndProfileTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Student user
        self.student_user = User.objects.create_user(
            username="john_doe",
            email="john.doe@example.com",
            password="securepassword123",
            first_name="John",
            last_name="Doe",
        )
        UserProfile.objects.create(user=self.student_user, role="student")
        self.student = Student.objects.create(
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            phone="+919876543210",
            address="Mumbai, India",
            bio="Aspiring full-stack engineer and Python enthusiast.",
        )

        # Other student for email collision test
        self.other_user = User.objects.create_user(
            username="jane_smith",
            email="jane.smith@example.com",
            password="securepassword123",
        )
        UserProfile.objects.create(user=self.other_user, role="student")
        self.other_student = Student.objects.create(
            first_name="Jane",
            last_name="Smith",
            email="jane.smith@example.com",
        )

        # Admin user
        self.admin_user = User.objects.create_superuser(
            username="super_admin",
            email="admin@example.com",
            password="adminpassword123",
        )
        UserProfile.objects.create(user=self.admin_user, role="admin")

        # Instructor & Course
        self.instructor = Instructor.objects.create(
            first_name="Guido",
            last_name="Rossum",
            email="guido@example.com",
        )
        self.course = Course.objects.create(
            title="Mastering Django 5",
            category="web_development",
            price=1499,
            duration="20 hours",
            instructor=self.instructor,
        )
        self.enrollment = Enrollment.objects.create(
            student=self.student,
            course=self.course,
            status="active",
        )

    def test_student_model_properties_and_str(self):
        """Student model string representation, full_name, and user link."""
        self.assertEqual(str(self.student), "John Doe")
        self.assertEqual(self.student.full_name, "John Doe")
        self.assertEqual(self.student.user, self.student_user)
        self.assertEqual(self.student.enrolled_courses_count, 1)

    def test_student_profile_view_requires_login(self):
        """Unauthenticated user is redirected to login page when accessing profile."""
        response = self.client.get(reverse("student_profile"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_student_profile_view_loads_for_student(self):
        """Authenticated student can view their profile with courses, bio, and stats."""
        self.client.login(username="john_doe", password="securepassword123")
        response = self.client.get(reverse("student_profile"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "John Doe")
        self.assertContains(response, "Aspiring full-stack engineer")
        self.assertContains(response, "Mastering Django 5")
        self.assertEqual(response.context["total_enrolled"], 1)

    def test_student_profile_edit_form_get(self):
        """Edit profile form loads with current student data pre-filled."""
        self.client.login(username="john_doe", password="securepassword123")
        response = self.client.get(reverse("student_profile_edit"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "John")
        self.assertContains(response, "Doe")
        self.assertContains(response, "john.doe@example.com")
        self.assertContains(response, "Aspiring full-stack engineer")

    def test_student_profile_edit_form_post_success(self):
        """Submitting valid profile form updates Student model and auth.User."""
        self.client.login(username="john_doe", password="securepassword123")
        update_data = {
            "first_name": "Johnny",
            "last_name": "Doestar",
            "email": "johnny.doestar@example.com",
            "phone": "+919999888877",
            "date_of_birth": "2000-05-15",
            "address": "Bangalore, Karnataka",
            "bio": "Updated bio: Full-stack developer in training.",
        }
        response = self.client.post(reverse("student_profile_edit"), update_data)
        self.assertRedirects(response, reverse("student_profile"))

        # Verify Student model was updated
        self.student.refresh_from_db()
        self.assertEqual(self.student.first_name, "Johnny")
        self.assertEqual(self.student.last_name, "Doestar")
        self.assertEqual(self.student.email, "johnny.doestar@example.com")
        self.assertEqual(self.student.phone, "+919999888877")
        self.assertEqual(str(self.student.date_of_birth), "2000-05-15")
        self.assertEqual(self.student.address, "Bangalore, Karnataka")
        self.assertEqual(self.student.bio, "Updated bio: Full-stack developer in training.")

        # Verify auth.User was synchronized
        self.student_user.refresh_from_db()
        self.assertEqual(self.student_user.first_name, "Johnny")
        self.assertEqual(self.student_user.last_name, "Doestar")
        self.assertEqual(self.student_user.email, "johnny.doestar@example.com")

    def test_student_profile_edit_duplicate_email_fails(self):
        """Attempting to use an email already taken by another user fails with validation error."""
        self.client.login(username="john_doe", password="securepassword123")
        update_data = {
            "first_name": "Johnny",
            "last_name": "Doe",
            "email": "jane.smith@example.com",  # Already taken
            "phone": "+919999888877",
            "address": "Delhi",
            "bio": "Testing duplicate email",
        }
        response = self.client.post(reverse("student_profile_edit"), update_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This email is already associated with another account")

        # Verify no changes made
        self.student.refresh_from_db()
        self.assertEqual(self.student.email, "john.doe@example.com")

    def test_admin_can_view_student_profile_detail(self):
        """Admin can view any student's profile via student_profile_detail."""
        self.client.login(username="super_admin", password="adminpassword123")
        url = reverse("student_profile_detail", args=[self.student.student_id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "John Doe")

    def test_unauthenticated_profile_redirects_to_custom_login_not_404(self):
        """Unauthenticated access to profile redirects to /login/?next=/profile/ (never 404)."""
        response = self.client.get("/profile/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/login/?next=/profile/")

    def test_accounts_login_redirects_to_login_with_query_params(self):
        """Legacy /accounts/login/?next=/profile/ smoothly redirects to /login/?next=/profile/."""
        response = self.client.get("/accounts/login/?next=/profile/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/login/?next=/profile/")

    def test_deactivated_logged_in_student_redirected_with_message(self):
        """A student deactivated while logged in is safely redirected to login with an alert, no 404."""
        self.client.login(username="john_doe", password="securepassword123")

        # Admin deactivates student
        self.student_user.is_active = False
        self.student_user.save()

        # Student attempts to navigate to /profile/
        response = self.client.get("/profile/", follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("/login/", response.request["PATH_INFO"])
        self.assertContains(response, "Your account has been deactivated by an administrator")

    def test_student_profile_edit_page_contains_preview_ui_and_enctype(self):
        """Edit profile template renders multipart form, preview UI, and file input."""
        self.client.login(username="john_doe", password="securepassword123")
        response = self.client.get(reverse("student_profile_edit"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'enctype="multipart/form-data"')
        self.assertContains(response, 'id="id_profile_picture"')
        self.assertContains(response, 'id="previewImg"')
        self.assertContains(response, 'id="previewFallback"')
        self.assertContains(response, 'id="pictureDropzone"')
        self.assertContains(response, "📷 Profile Picture")

    def test_student_can_upload_valid_profile_picture(self):
        """Student can upload a valid image file, which is saved to Student.profile_picture."""
        import io
        from PIL import Image

        self.client.login(username="john_doe", password="securepassword123")

        img_byte_arr = io.BytesIO()
        img = Image.new("RGB", (100, 100), color="green")
        img.save(img_byte_arr, format="PNG")
        uploaded_image = SimpleUploadedFile(
            name="avatar.png",
            content=img_byte_arr.getvalue(),
            content_type="image/png"
        )

        update_data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com",
            "phone": "+919876543210",
            "bio": "Studying with a new avatar!",
            "profile_picture": uploaded_image,
        }

        response = self.client.post(reverse("student_profile_edit"), update_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Your student profile has been updated successfully!")

        self.student.refresh_from_db()
        self.assertTrue(bool(self.student.profile_picture))
        self.assertIn("profile_pics/", self.student.profile_picture.name)

        # Profile page should now render the image tag
        profile_response = self.client.get(reverse("student_profile"))
        self.assertContains(profile_response, self.student.profile_picture.url)

        # Clean up uploaded file
        if self.student.profile_picture:
            self.student.profile_picture.delete(save=False)

    def test_student_profile_picture_invalid_file_rejected(self):
        """Uploading a non-image file fails form validation."""
        self.client.login(username="john_doe", password="securepassword123")

        invalid_file = SimpleUploadedFile(
            name="document.txt",
            content=b"This is a text file, not an image.",
            content_type="text/plain"
        )

        update_data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com",
            "profile_picture": invalid_file,
        }

        response = self.client.post(reverse("student_profile_edit"), update_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "The uploaded file is not a valid image")

    def test_student_can_clear_profile_picture(self):
        """Student can remove their uploaded profile picture."""
        import io
        from PIL import Image

        self.client.login(username="john_doe", password="securepassword123")

        # Set an initial picture
        img_byte_arr = io.BytesIO()
        img = Image.new("RGB", (50, 50), color="blue")
        img.save(img_byte_arr, format="PNG")
        uploaded_image = SimpleUploadedFile(
            name="initial_avatar.png",
            content=img_byte_arr.getvalue(),
            content_type="image/png"
        )
        self.student.profile_picture = uploaded_image
        self.student.save()
        self.assertTrue(bool(self.student.profile_picture))

        # Clear it via form
        clear_data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com",
            "clear_profile_picture": "on",
        }
        response = self.client.post(reverse("student_profile_edit"), clear_data, follow=True)
        self.assertEqual(response.status_code, 200)

        self.student.refresh_from_db()
        self.assertFalse(bool(self.student.profile_picture))





