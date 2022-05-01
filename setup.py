from setuptools import setup, find_packages
 
classifiers = [
  'Development Status :: 5 - Production/Stable',
  'Intended Audience :: Education',
  'Operating System :: Microsoft :: Windows :: Windows 10',
  'License :: OSI Approved :: MIT License',
  'Programming Language :: Python :: 3'
]
 
setup(
  name='open6118',
  version='0.0.1',
  description='6118 em Python',
  long_description=open('README.txt').read() + '\n\n' + open('CHANGELOG.txt').read(),
  url='',  
  author='Gustavo Bragato',
  author_email='brgt@brgt.com.br',
  license='MIT', 
  classifiers=classifiers,
  keywords='6118', 
  packages=find_packages(),
  install_requires=[''] 
)