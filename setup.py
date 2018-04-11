#!/usr/bin/env python

"Setuptools params"

from setuptools import setup, find_packages

VERSION = '0.1.0'

modname = distname = 'sr6mininet'

setup(
	name=distname,
	version=VERSION,
	description='A IPMininet extension providing components to emulate IPv6'
	            'Segment Routing networks.',
	author='Mathieu Jadin',
	author_email='mathieu.jadin@uclouvain.be',
	packages=find_packages(),
	include_package_data=True,
	classifiers=[
		"License :: OSI Approved :: GNU General Public License v2 (GPLv2)",
		"Programming Language :: Python",
		"Development Status :: 2 - Pre-Alpha",
		"Intended Audience :: Developers",
		"Topic :: System :: Networking",
		'Programming Language :: Python :: 2',
		'Programming Language :: Python :: 2.7'
		],
	keywords='networking SRv6 IPMininet OSPF IP BGP quagga mininet',
	license='GPLv2',
	install_requires=[
		'setuptools',
		'ipmininet'
	],
    tests_require=[],
    setup_requires=[],
	url='https://bitbucket.org/jadinm/sr6mininet'
)
