import os # path.exists(), path.join()
import subprocess
import importlib
import sys
import argparse
from importlib.metadata import version, PackageNotFoundError

# Global Variables
dir_path = os.path.dirname(os.path.realpath(__file__))

argparser = argparse.ArgumentParser()
argparser.add_argument('--build', action='store_true', default=False)
args = argparser.parse_args()

def _create_env():
    venv = importlib.import_module("venv")
    pd_env = venv.EnvBuilder()
    context = pd_env.ensure_directories(os.path.join(dir_path, "venv/"))
    
    # FIX: Could possibly cause issues if calling this script from another environment? idk im too tired rn
    if not os.path.exists(context.env_exe):
        pd_env.setup_scripts(context)
        pd_env.create_configuration(context)
        pd_env.setup_python(context)
        pd_env.post_setup(context)
        
        res = subprocess.check_call([context.env_exe, "-m", "ensurepip", "--upgrade"])
        if res != 0:
            print("Could not install pip into virtual environment")
            _error(res)


    res = subprocess.run([context.env_exe, "-m", "pip", "install", "."])
    if res.returncode != 0:
        print("Could not install pyproject.toml dependencies")
        _error(res)
        
    return context.env_exe  

    #pdutil = importlib.import_module("PDUtilities")

def _error(errLevel):
    print("\nFailed with code: ", errLevel)
    exit(errLevel)


# If virtualenv doesn't exist, then install it
try:
    version("virtualenv")
except (PackageNotFoundError):
    print("Installing 'virtualenv'")
    res = subprocess.check_call([sys.executable, "-m", "pip", "install", "virtualenv"])
    if res != 0:
        print("Could not install Virtualenv")
        _error(res)


# Makes sure that virtualenv files are installed
env_exe = _create_env()

if args.build:
    ret = subprocess.run([os.path.join(os.path.dirname(env_exe), "pyinstaller"), "PDUtil.spec"])
    if ret.returncode != 0:
        print("Could not build exe")
        _error(ret.returncode)

res = subprocess.run([env_exe, "PDUtilities"])

#_main() # Calls the main function for PDUtilities
