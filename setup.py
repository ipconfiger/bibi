#coding=utf8
__author__ = 'liming'

from setuptools import setup

setup(name='bibi',
      version='0.1.6',
      description='Simple way to publish your blog',
      url='https://github.com/ipconfiger/bibi',
      author='Alexander.Li',
      author_email='superpowerlee@gmail.com',
      license='MIT',
      packages=['bibi'],
      install_requires=[
          'markdown',
          'importlib',
          'flask',
          'flask-script',
          'GitPython',
          'pygments',
          'PyYAML'
      ],
      entry_points = {
        'console_scripts': ['bibi=bibi.bibi:main'],
      },
      zip_safe=False)