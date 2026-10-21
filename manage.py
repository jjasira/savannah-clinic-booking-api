#!/usr/bin/env python
import os
import sys


def main() -> None:
    """Run Django's command-line utility.

    This is the entry point for development and management commands such as
    ``runserver``, ``migrate``, ``createsuperuser``, and ``test``. It sets the
    default settings module before delegating the supplied command-line
    arguments to Django.
    """
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "clinic_project.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
