import click
import unittest
import transcriptic
from click.testing import CliRunner
from transcriptic.config import Connection
from transcriptic.objects import Project
from transcriptic.cli import *


c = Connection("taliherzka@gmail.com", "xgpctuxy_J2ge7Ei92F1", organization="fake-and-co")
class ProjectTestCase(unittest.TestCase):
    def test_connection(self):
        self.assertTrue(c.email == "taliherzka@gmail.com")


