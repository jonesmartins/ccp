import subprocess


def get_platform_tmp_dir(platform=None):
    """
    Get path of temporary files directory of a certain platform (Operating System).

    :param platform: Operating System platform
    :type platform: str

    :return: Temporary directory path.
    :rtype: str
    """
    if not platform:
        return ''

    if platform.startswith('linux') or platform.startswith('freebsd') or platform.startswith('darwin'):
        return '/tmp'

    if platform.startswith('cygwin') or platform.startswith('win32'):
        tmp_dir = subprocess.check_output('ECHO %Temp%')
        return str(tmp_dir)

    # aix, java, etc.
    raise ValueError(f'{platform} operating system not supported.')