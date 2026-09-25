from __future__ import annotations

from datetime import timedelta as td

from django.utils.timezone import now

from hc.api.management.commands.sendalerts import Command
from hc.api.models import Check, Flip, MaintenanceWindow
from hc.test import BaseTestCase


class MaintenanceWindowTestCase(BaseTestCase):
    def test_is_active(self) -> None:
        mw = MaintenanceWindow.objects.create(
            project=self.project,
            name="Test Window",
            starts=now() - td(hours=1),
            ends=now() + td(hours=1),
        )
        self.assertTrue(mw.is_active())
        self.assertFalse(mw.is_active(now() - td(hours=2)))
        self.assertFalse(mw.is_active(now() + td(hours=2)))

    def test_check_is_in_maintenance_all_checks(self) -> None:
        check = Check.objects.create(project=self.project, status="up")
        MaintenanceWindow.objects.create(
            project=self.project,
            name="All Checks Window",
            starts=now() - td(hours=1),
            ends=now() + td(hours=1),
            all_checks=True,
        )
        self.assertTrue(check.is_in_maintenance())

    def test_check_is_in_maintenance_specific_checks(self) -> None:
        check1 = Check.objects.create(project=self.project, status="up", name="C1")
        check2 = Check.objects.create(project=self.project, status="up", name="C2")

        mw = MaintenanceWindow.objects.create(
            project=self.project,
            name="Specific Window",
            starts=now() - td(hours=1),
            ends=now() + td(hours=1),
            all_checks=False,
        )
        mw.checks.add(check1)

        self.assertTrue(check1.is_in_maintenance())
        self.assertFalse(check2.is_in_maintenance())

    def test_sendalerts_suppresses_alerts_in_maintenance(self) -> None:
        check = Check.objects.create(project=self.project, status="up")
        check.last_ping = now() - td(days=2)
        check.alert_after = check.last_ping + td(days=1, hours=1)
        check.save()

        # Create active maintenance window covering the downtime flip time
        MaintenanceWindow.objects.create(
            project=self.project,
            name="Maintenance Window",
            starts=now() - td(days=3),
            ends=now() + td(hours=5),
            all_checks=True,
        )

        result = Command().handle_going_down()
        self.assertTrue(result)

        # Check status should update to down
        check.refresh_from_db()
        self.assertEqual(check.status, "down")

        # Flip should be created with reason="maintenance" and marked as processed!
        flip = Flip.objects.get(owner=check)
        self.assertEqual(flip.reason, "maintenance")
        self.assertIsNotNone(flip.processed)
