import random

from celery import shared_task
from faker import Faker

from .models import Comment, Document, Project, Task, TaskStatus, User, UserRole

fake = Faker()


@shared_task
def populate_data():
    users = []
    for _ in range(10):
        user = User.objects.create(
            username=fake.user_name(),
            email=fake.email(),
            password=fake.password(),
            role=random.choice([role.name.lower() for role in UserRole]),
        )
        users.append(user)

    projects = []
    for _ in range(5):
        project = Project.objects.create(
            title=fake.company(),
            description=fake.paragraph(),
            manager=random.choice(users),
        )
        projects.append(project)
        project.project_members.set(random.sample(users, 3))

    tasks = []
    for project in projects:
        for _ in range(3):
            task = Task.objects.create(
                title=fake.bs(),
                description=fake.text(),
                project=project,
                assignee=random.choice(users),
                status=random.choice([status.name.lower() for status in TaskStatus]),
                due_date=fake.date_this_month(),
            )
            tasks.append(task)

    for task in tasks:
        Document.objects.create(
            file=fake.file_name(extension="pdf"),
            uploaded_by=random.choice(users),
            task=task,
        )

    for task in tasks:
        for _ in range(2):
            Comment.objects.create(
                content=fake.sentence(),
                task=task,
                created_by=random.choice(users),
            )

    return "Data population complete"
