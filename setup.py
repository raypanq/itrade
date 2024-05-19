from setuptools import setup, find_packages

setup(
    name='itrade',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        # list your project's dependencies here
        # e.g., 'requests >= 2.23.0',
        'pandas',
        'plotly'
    ],
    entry_points={
        'console_scripts': [
            # if your package has scripts, list them here
            # e.g., 'script_name = your_package.module:function',
        ],
    },
    # additional metadata about your package
    author='ray',
    author_email='raypang@tuta.io',
    description='itrade contains backtest, trade tools',
    long_description="",
    long_description_content_type='text/markdown',  # This is important!
    url='https://github.com/raypanq/itrade',
    classifiers=[
        # Trove classifiers
        # Full list: https://pypi.org/classifiers/
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.12',
)
