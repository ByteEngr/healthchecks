from __future__ import annotations

from datetime import timedelta as td

from django.utils.timezone import now

from hc.api.models import Check, MaintenanceWindow
from hc.test import BaseTestCase


class MaintenanceTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.check = Check.objects.create(project=self.project, name="Server Backup")
        self.url = f"/projects/{self.project.code}/maintenance/"
        self.add_url = f"/projects/{self.project.code}/maintenance/add/"

    def test_it_shows_maintenance_page(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Maintenance Windows")

    def test_it_creates_maintenance_window(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        starts = (now() + td(hours=1)).isoformat()
        ends = (now() + td(hours=3)).isoformat()

        payload = {
            "name": "DB Upgrade",
            "starts": starts,
            "ends": ends,
            "all_checks": "on",
        }
        r = self.client.post(self.add_url, payload)
        self.assertRedirects(r, self.url)

        mw = MaintenanceWindow.objects.get(project=self.project)
        self.assertEqual(mw.name, "DB Upgrade")
        self.assertTrue(mw.all_checks)

    def test_it_creates_maintenance_window_for_specific_checks(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        starts = (now() + td(hours=1)).isoformat()
        ends = (now() + td(hours=3)).isoformat()

        payload = {
            "name": "Specific Check Maintenance",
            "starts": starts,
            "ends": ends,
            "checks": [str(self.check.id)],
        }
        r = self.client.post(self.add_url, payload)
        self.assertRedirects(r, self.url)

        mw = MaintenanceWindow.objects.get(project=self.project)
        self.assertFalse(mw.all_checks)
        self.assertIn(self.check, mw.checks.all())

    def test_it_removes_maintenance_window(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        mw = MaintenanceWindow.objects.create(
            project=self.project,
            name="To Remove",
            starts=now() + td(hours=1),
            ends=now() + td(hours=2),
        )

        remove_url = f"/projects/{self.project.code}/maintenance/{mw.id}/remove/"
        r = self.client.post(remove_url)
        self.assertRedirects(r, self.url)
        self.assertFalse(MaintenanceWindow.objects.filter(id=mw.id).exists())
