#coding=utf8
__author__ = 'liming'

from setuptools import setup

setup(name='bibi',
      version='0.2.2',
      description='Simple way to publish your blog',
      url='https://github.com/ipconfiger/bibi',
      author='Alexander.Li',
      author_email='superpowerlee@gmail.com',
      license='MIT',
      packages=['bibi'],
      install_requires=[
          'markdown',
          'jinja2',
          'click',
          'PyYAML',
          'six'
      ],
      entry_points = {
        'console_scripts': ['bibi=bibi.bibi:main'],
      },
      zip_safe=False)