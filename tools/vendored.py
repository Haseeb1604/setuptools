import re
import sys
import subprocess

from path import Path


def remove_all(paths):
    for path in paths:
        path.rmtree() if path.isdir() else path.remove()


def update_vendored():
    update_pkg_resources()
    update_setuptools()


def rewrite_packaging(pkg_files, new_root):
    """
    Rewrite imports in packaging to redirect to vendored copies.
    """
    for file in pkg_files.glob('*.py'):
        text = file.text()
        text = re.sub(r' (pyparsing)', rf' {new_root}.\1', text)
        text = text.replace(
            'from six.moves.urllib import parse',
            'from urllib import parse',
        )
        file.write_text(text)


def rewrite_jaraco_text(pkg_files, new_root):
    """
    Rewrite imports in jaraco.text to redirect to vendored copies.
    """
    for file in pkg_files.glob('*.py'):
        text = file.read_text()
        text = re.sub(r' (jaraco\.)', rf' {new_root}.\1', text)
        text = re.sub(r' (importlib_resources)', rf' {new_root}.\1', text)
        # suppress loading of lorem_ipsum; ref #3072
        text = re.sub(r'^lorem_ipsum.*\n$', '', text, flags=re.M)
        file.write_text(text)


def rewrite_jaraco(pkg_files, new_root):
    """
    Rewrite imports in jaraco.functools to redirect to vendored copies.
    """
    for file in pkg_files.glob('*.py'):
        text = file.read_text()
        text = re.sub(r' (more_itertools)', rf' {new_root}.\1', text)
        file.write_text(text)
    # required for zip-packaged setuptools #3084
    pkg_files.joinpath('__init__.py').write_text('')


def rewrite_importlib_resources(pkg_files, new_root):
    """
    Rewrite imports in importlib_resources to redirect to vendored copies.
    """
    for file in pkg_files.glob('*.py'):
        text = file.read_text().replace('importlib_resources.abc', '.abc')
        text = text.replace('zipp', '..zipp')
        file.write_text(text)


def rewrite_more_itertools(pkg_files: Path):
    """
    Rewrite more_itertools to remove unused more_itertools.more
    """
    (pkg_files / "more.py").remove()
    init_file = pkg_files / "__init__.py"
    init_text = "".join(ln for ln in init_file.lines() if "from .more " not in ln)
    init_file.write_text(init_text)


def clean(vendor):
    """
    Remove all files out of the vendor directory except the meta
    data (as pip uninstall doesn't support -t).
    """
    remove_all(
        path
        for path in vendor.glob('*')
        if path.basename() != 'vendored.txt'
    )


def install(vendor):
    clean(vendor)
    install_args = [
        sys.executable,
        '-m', 'pip',
        'install',
        '-r', str(vendor / 'vendored.txt'),
        '-t', str(vendor),
    ]
    subprocess.check_call(install_args)
    (vendor / '__init__.py').write_text('')


def update_pkg_resources():
    vendor = Path('pkg_resources/_vendor')
    install(vendor)
    rewrite_packaging(vendor / 'packaging', 'pkg_resources.extern')
    rewrite_jaraco_text(vendor / 'jaraco/text', 'pkg_resources.extern')
    rewrite_jaraco(vendor / 'jaraco', 'pkg_resources.extern')
    rewrite_importlib_resources(vendor / 'importlib_resources', 'pkg_resources.extern')
    rewrite_more_itertools(vendor / "more_itertools")


def update_setuptools():
    vendor = Path('setuptools/_vendor')
    install(vendor)
    rewrite_packaging(vendor / 'packaging', 'setuptools.extern')
    rewrite_jaraco_text(vendor / 'jaraco/text', 'setuptools.extern')
    rewrite_jaraco(vendor / 'jaraco', 'setuptools.extern')
    rewrite_importlib_resources(vendor / 'importlib_resources', 'setuptools.extern')
    rewrite_more_itertools(vendor / "more_itertools")


__name__ == '__main__' and update_vendored()
