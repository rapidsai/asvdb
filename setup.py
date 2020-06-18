from setuptools import setup

import asvdb

setup(name="asvdb",
      version=asvdb.__version__,
      packages=["asvdb"],
      description='ASV "database" interface',
      entry_points={
          "console_scripts": [
              "asvdb = asvdb.__main__:main"
          ]
      },
)
