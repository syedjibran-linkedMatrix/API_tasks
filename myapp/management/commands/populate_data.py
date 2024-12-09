import asyncio
from datetime import datetime, timedelta

from asgiref.sync import sync_to_async
from django.core.management.base import BaseCommand
from django.db import IntegrityError
from django.utils.timezone import make_aware
from faker import Faker

from myapp.models import Comment, Document, Project, Task, TaskStatus, User, UserRole

fake = Faker()


class Command(BaseCommand):
    help = "Populate the database with fake data for testing or development"

    def handle(self, *args, **kwargs):
        self.stdout.write(
            self.style.SUCCESS("Starting to populate the database with fake data...")
        )
        asyncio.run(self.populate_data())
        self.stdout.write(self.style.SUCCESS("Database population complete."))

    async def populate_data(self):
        num_users = 10
        num_projects = 10
        num_tasks = 10
        num_documents = 10
        num_comments = 10

        self.stdout.write(self.style.SUCCESS("Creating users..."))
        await self.create_fake_users(num_users)

        users = await self.async_fetch_users()

        self.stdout.write(self.style.SUCCESS("Creating projects..."))
        projects = await self.create_fake_projects(num_projects, users)

        self.stdout.write(self.style.SUCCESS("Creating tasks..."))
        await self.create_fake_tasks(num_tasks, projects, users)

        tasks = await self.async_fetch_tasks()

        self.stdout.write(self.style.SUCCESS("Creating documents..."))
        await self.create_fake_documents(num_documents, tasks, users)

        self.stdout.write(self.style.SUCCESS("Creating comments..."))
        await self.create_fake_comments(num_comments, tasks, users)

    @sync_to_async
    def async_fetch_users(self):
        return list(User.objects.all())

    @sync_to_async
    def async_fetch_tasks(self):
        return list(Task.objects.all())

    async def create_fake_users(self, num_users):
        users = []
        for _ in range(num_users):
            username = fake.user_name()
            email = fake.email()
            password = fake.password()
            role = fake.random_element([role.name.lower() for role in UserRole])
            user = User(username=username, email=email, password=password, role=role)
            user.set_password(password)
            users.append(user)
        await asyncio.gather(*(self.async_create_user(user) for user in users))

    @sync_to_async
    def async_create_user(self, user):
        try:
            user.save()
        except IntegrityError:
            pass

    async def create_fake_projects(self, num_projects, users):
        projects = []
        for _ in range(num_projects):
            manager = fake.random_element(users)
            title = fake.company()
            description = fake.text(max_nb_chars=200)
            project = Project(title=title, description=description, manager=manager)

            await self.async_create_project(project)

            members = []
            for _ in range(fake.random_int(1, 5)):
                member = fake.random_element(users)
                if member != manager and member not in members:
                    members.append(member)

            await self.async_add_project_members(project, members)

            projects.append(project)

        return projects

    @sync_to_async
    def async_create_project(self, project):
        try:
            project.save()
        except IntegrityError:
            pass

    @sync_to_async
    def async_add_project_members(self, project, members):
        for member in members:
            project.project_members.add(member)

    async def create_fake_tasks(self, num_tasks, projects, users):
        tasks = []
        for _ in range(num_tasks):
            project = fake.random_element(projects)
            assignee = fake.random_element(users)
            title = fake.bs()
            description = fake.text(max_nb_chars=200)
            status = fake.random_element([status.name.lower() for status in TaskStatus])
            due_date = make_aware(
                datetime.now() + timedelta(days=fake.random_int(1, 30))
            )
            task = Task(
                title=title,
                description=description,
                project=project,
                assignee=assignee,
                status=status,
                due_date=due_date,
            )
            tasks.append(task)
        await asyncio.gather(*(self.async_create_task(task) for task in tasks))

    @sync_to_async
    def async_create_task(self, task):
        try:
            task.save()
        except IntegrityError:
            pass

    async def create_fake_documents(self, num_documents, tasks, users):
        documents = []
        for _ in range(num_documents):
            task = fake.random_element(tasks)
            uploaded_by = fake.random_element(users)
            file = fake.file_name(extension="pdf")
            document = Document(file=file, uploaded_by=uploaded_by, task=task)
            documents.append(document)
        await asyncio.gather(
            *(self.async_create_document(document) for document in documents)
        )

    @sync_to_async
    def async_create_document(self, document):
        try:
            document.save()
        except IntegrityError:
            pass

    async def create_fake_comments(self, num_comments, tasks, users):
        comments = []
        for _ in range(num_comments):
            task = fake.random_element(tasks)
            created_by = fake.random_element(users)
            content = fake.text(max_nb_chars=200)
            comment = Comment(content=content, task=task, created_by=created_by)
            comments.append(comment)
        await asyncio.gather(
            *(self.async_create_comment(comment) for comment in comments)
        )

    @sync_to_async
    def async_create_comment(self, comment):
        try:
            comment.save()
        except IntegrityError:
            pass


class Command(BaseCommand):
    help = "Populate the database with fake data for testing or development"

    def handle(self, *args, **kwargs):
        self.stdout.write(
            self.style.SUCCESS("Starting to populate the database with fake data...")
        )
        asyncio.run(self.populate_data())
        self.stdout.write(self.style.SUCCESS("Database population complete."))

    async def populate_data(self):
        num_users = 10
        num_projects = 10
        num_tasks = 10
        num_documents = 10
        num_comments = 10

        self.stdout.write(self.style.SUCCESS("Creating users..."))
        await self.create_fake_users(num_users)

        users = await self.async_fetch_users()

        self.stdout.write(self.style.SUCCESS("Creating projects..."))
        projects = await self.create_fake_projects(num_projects, users)

        self.stdout.write(self.style.SUCCESS("Creating tasks..."))
        await self.create_fake_tasks(num_tasks, projects, users)

        tasks = await self.async_fetch_tasks()

        self.stdout.write(self.style.SUCCESS("Creating documents..."))
        await self.create_fake_documents(num_documents, tasks, users)

        self.stdout.write(self.style.SUCCESS("Creating comments..."))
        await self.create_fake_comments(num_comments, tasks, users)

    @sync_to_async
    def async_fetch_users(self):
        return list(User.objects.all())

    @sync_to_async
    def async_fetch_tasks(self):
        return list(Task.objects.all())

    async def create_fake_users(self, num_users):
        users = []
        for _ in range(num_users):
            username = fake.user_name()
            email = fake.email()
            password = fake.password()
            role = fake.random_element([role.name.lower() for role in UserRole])
            user = User(username=username, email=email, password=password, role=role)
            user.set_password(password)
            users.append(user)
        await asyncio.gather(*(self.async_create_user(user) for user in users))

    @sync_to_async
    def async_create_user(self, user):
        try:
            user.save()
        except IntegrityError:
            pass

    async def create_fake_projects(self, num_projects, users):
        projects = []
        for _ in range(num_projects):
            manager = fake.random_element(users)
            title = fake.company()
            description = fake.text(max_nb_chars=200)
            project = Project(title=title, description=description, manager=manager)

            await self.async_create_project(project)

            members = []
            for _ in range(fake.random_int(1, 5)):
                member = fake.random_element(users)
                if member != manager and member not in members:
                    members.append(member)

            await self.async_add_project_members(project, members)

            projects.append(project)

        return projects

    @sync_to_async
    def async_create_project(self, project):
        try:
            project.save()
        except IntegrityError:
            pass

    @sync_to_async
    def async_add_project_members(self, project, members):
        for member in members:
            project.project_members.add(member)

    async def create_fake_tasks(self, num_tasks, projects, users):
        tasks = []
        for _ in range(num_tasks):
            project = fake.random_element(projects)
            assignee = fake.random_element(users)
            title = fake.bs()
            description = fake.text(max_nb_chars=200)
            status = fake.random_element([status.name.lower() for status in TaskStatus])
            due_date = make_aware(
                datetime.now() + timedelta(days=fake.random_int(1, 30))
            )
            task = Task(
                title=title,
                description=description,
                project=project,
                assignee=assignee,
                status=status,
                due_date=due_date,
            )
            tasks.append(task)
        await asyncio.gather(*(self.async_create_task(task) for task in tasks))

    @sync_to_async
    def async_create_task(self, task):
        try:
            task.save()
        except IntegrityError:
            pass

    async def create_fake_documents(self, num_documents, tasks, users):
        documents = []
        for _ in range(num_documents):
            task = fake.random_element(tasks)
            uploaded_by = fake.random_element(users)
            file = fake.file_name(extension="pdf")
            document = Document(file=file, uploaded_by=uploaded_by, task=task)
            documents.append(document)
        await asyncio.gather(
            *(self.async_create_document(document) for document in documents)
        )

    @sync_to_async
    def async_create_document(self, document):
        try:
            document.save()
        except IntegrityError:
            pass

    async def create_fake_comments(self, num_comments, tasks, users):
        comments = []
        for _ in range(num_comments):
            task = fake.random_element(tasks)
            created_by = fake.random_element(users)
            content = fake.text(max_nb_chars=200)
            comment = Comment(content=content, task=task, created_by=created_by)
            comments.append(comment)
        await asyncio.gather(
            *(self.async_create_comment(comment) for comment in comments)
        )

    @sync_to_async
    def async_create_comment(self, comment):
        try:
            comment.save()
        except IntegrityError:
            pass
