from fbs_runtime.application_context.PyQt5 import ApplicationContext
from PyQt5.QtWidgets import QMainWindow
import midiconvert

import sys

if __name__ == '__main__':
    appctxt = ApplicationContext()       # 1. Instantiate ApplicationContext
    # get_resource 
    application = midiconvert.MainWindow()
    default_set = appctxt.get_resource('drum_sets/defaultset.rlrr')
    application.set_default_set(default_set)
    application.show()
    exit_code = appctxt.app.exec_()      # 2. Invoke appctxt.app.exec_()
    sys.exit(exit_code)