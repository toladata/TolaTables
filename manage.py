#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    reload(sys)
    sys.setdefaultencoding('utf-8')

    if 'test' in sys.argv:
        settings = 'tola.settings.test'
        os.environ['DJANGO_SETTINGS_MODULE'] = settings
    else:
        settings = os.environ.get("DJANGO_SETTINGS_MODULE",
                                  'tola.settings.local')

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings)

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
