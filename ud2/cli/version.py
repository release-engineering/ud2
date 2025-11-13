# This library is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this library; if not, see <http://www.gnu.org/licenses/>.

"""
Version resource command registrations.
"""

import click

from . import register_resource_group


def register(root: click.Group) -> None:
    """
    Attach all version related commands to the provided root group.

    Parameters
    ----------
    root:
        Root CLI group to attach commands to.
    """
    register_resource_group(root, 'version')


# The end.
