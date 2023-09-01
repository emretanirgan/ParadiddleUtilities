@ECHO OFF
call :activate_env || goto :init
goto :run

:init
    :: Ensures all dependencies are met before continuing application
    call :check_deps
    call :create_env
:run
    :: Run ParadiddleUtilities application
    python -m PDUtilities
    exit /b 0

:create_env
    :: Creates a new virtual environment
    python -m virtualenv env 2>nul 
    call :activate_env
    :: Installs all packages listed in 'requirements.txt'
    python -m pip install -r requirements.txt
    exit /b 0

:activate_env
    :: Activates new environment
    call env\Scripts\activate.bat
    :: The normal || used for checking ERRORLEVEL doesn't work with virtualenv's "activate.bat" so I have to use this conditional
    IF %ERRORLEVEL% NEQ 0 exit /b %ERRORLEVEL% 
    exit /b 0

:check_deps
    :: Checks to see if python is installed and easily accessible through $PATH
    where /q python || (
        echo Python 3 must be installed to run this application
        goto :error
    )
    :: Checks to see if pip is installed with python
    python -m pip --version || (
        echo pip could not be found or is not installed.
        goto :error
    )
    :: Checks if virtualenv is installed
    python -m virtualenv --version || (
        echo Installing 'virtualenv'
        :: IF 'virtualenv' isn't found, install it
        python -m pip install virtualenv || goto :error
    )
    exit /b 0

:error
    echo.
    echo Failed with code %ERRORLEVEL%
    exit /b %ERRORLEVEL%