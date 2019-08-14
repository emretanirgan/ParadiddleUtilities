from fbs.installer.linux import generate_installer_files, run_fpm

def create_installer_ubuntu():
    generate_installer_files()
    run_fpm('deb')