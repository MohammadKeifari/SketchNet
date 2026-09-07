"""Wipe non-admin users and seed the public SketchNet catalog."""

from __future__ import annotations

import shutil
from pathlib import Path

from allauth.account.models import EmailAddress
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError

from accounts.seed.catalog import (
    DATASETS,
    MODELS,
    STARTER_BIO,
    STARTER_EMAIL,
    STARTER_USERNAME,
    build_model_graph,
)
from accounts.seed.graphs import attach_dataset, validate_graph
from bug_reports.models import BugReport
from data_manager.models import Dataset
from data_manager.services import infer_dataset_shape
from models_library.models import SketchModel

User = get_user_model()


class Command(BaseCommand):
    help = (
        "Delete all datasets, models, and non-superuser accounts, then seed "
        "the public SketchNet catalog. Requires --wipe."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--wipe",
            action="store_true",
            help="Required. Delete catalogs and non-admin users before seeding.",
        )

    def handle(self, *args, **options):
        if not options["wipe"]:
            raise CommandError(
                "Refusing to run without --wipe. "
                "This command deletes datasets, models, and non-admin users."
            )
        self._wipe()
        self._seed()

    def _wipe(self):
        dataset_count = Dataset.objects.count()
        for dataset in Dataset.objects.all():
            dataset.delete()
        self.stdout.write(f"Deleted {dataset_count} dataset(s).")

        model_count = SketchModel.objects.count()
        for model in SketchModel.objects.all():
            if model.cover_image:
                model.cover_image.delete(save=False)
            model.delete()
        self.stdout.write(f"Deleted {model_count} model(s).")

        reports = BugReport.objects.count()
        BugReport.objects.all().delete()
        self.stdout.write(f"Deleted {reports} bug report(s).")

        removed_users = User.objects.filter(is_superuser=False).count()
        User.objects.filter(is_superuser=False).delete()
        Session.objects.all().delete()
        self.stdout.write(f"Deleted {removed_users} non-admin user(s).")

        media = Path(settings.MEDIA_ROOT)
        for rel in ("datasets", "models", "avatars"):
            path = media / rel
            if path.exists():
                shutil.rmtree(path)
        self.stdout.write(f"Cleared catalog media under {media}.")

    def _seed(self):
        owner = self._ensure_starter_user()
        datasets = {}
        for spec in DATASETS:
            dataset = self._create_dataset(owner, spec)
            datasets[spec["name"]] = dataset
            self.stdout.write(f"Dataset {dataset.name} ({dataset.dataset_id})")

        for spec in MODELS:
            dataset = datasets[spec["dataset"]]
            n_features = _feature_count(dataset)
            n_classes = _class_count(dataset)
            graph = build_model_graph(spec["name"], n_features, n_classes)
            graph = attach_dataset(graph, dataset)
            errors = validate_graph(graph)
            if errors:
                messages = [item.get("message", item) for item in errors]
                raise CommandError(
                    f"Starter model '{spec['name']}' failed validation: {messages}"
                )
            model = SketchModel.objects.create(
                name=spec["name"],
                description=spec["description"],
                graph_data=graph,
                owner=owner,
                view_access="public",
                fork_access="public",
            )
            self.stdout.write(f"Model {model.name} ({model.model_id})")

        self.stdout.write(self.style.SUCCESS("Starter catalog is ready."))

    def _ensure_starter_user(self):
        user, created = User.objects.get_or_create(
            username=STARTER_USERNAME,
            defaults={"email": STARTER_EMAIL},
        )
        if user.is_superuser:
            raise CommandError(
                f"User '{STARTER_USERNAME}' is a superuser; "
                "will not convert it to the catalog account."
            )
        if not created and user.email != STARTER_EMAIL:
            if User.objects.filter(email=STARTER_EMAIL).exclude(pk=user.pk).exists():
                raise CommandError(f"Email {STARTER_EMAIL} is already in use.")
            user.email = STARTER_EMAIL
        user.set_unusable_password()
        user.is_staff = False
        user.is_superuser = False
        user.bio = STARTER_BIO
        user.save()
        if user.avatar:
            user.avatar.delete(save=False)
            user.avatar = None
            user.save(update_fields=["avatar"])
        EmailAddress.objects.update_or_create(
            user=user,
            email=user.email,
            defaults={"verified": True, "primary": True},
        )
        settings_obj = user.settings
        settings_obj.public_profile = True
        settings_obj.save()
        self.stdout.write(f"Catalog user {user.username} ({'created' if created else 'updated'}).")
        return user

    def _create_dataset(self, owner, spec):
        frame = spec["loader"]()
        dataset = Dataset(
            name=spec["name"],
            description=spec["description"],
            format="csv",
            owner=owner,
            is_private=False,
        )
        dataset.save()
        payload = frame.to_csv(index=False).encode("utf-8")
        dataset.file.save(
            f"{dataset.dataset_id}.csv",
            ContentFile(payload),
            save=True,
        )
        shape, known = infer_dataset_shape(dataset)
        if shape:
            dataset.inferred_shape = shape
            dataset.shape_known = known
            dataset.save()
        return dataset


def _feature_count(dataset) -> int:
    import pandas as pd

    frame = pd.read_csv(dataset.file.path, nrows=0)
    return max(len(frame.columns) - 1, 0)


def _class_count(dataset) -> int:
    import pandas as pd

    frame = pd.read_csv(dataset.file.path, usecols=lambda name: name == "target")
    if "target" not in frame.columns:
        return 1
    unique = frame["target"].nunique()
    return int(unique) if unique else 1
