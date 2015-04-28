from sys import version_info


if version_info.major > 2:
    b = lambda x: x.encode('ascii')
else:
    b = lambda x: x
