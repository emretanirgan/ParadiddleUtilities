# Copyright (C) 2020 Emre Tanirgan <emre@paradiddleapp.com>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import sys
from PyQt5 import QtWidgets
from pd_gui import PD_GUI

if __name__ == '__main__':
    # Sets primary window for the application
    app = QtWidgets.QApplication(sys.argv)
    window = PD_GUI()
    app.exec_()