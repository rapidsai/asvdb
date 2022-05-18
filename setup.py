from setuptools import setup

setup(name="asvdb",
      version="0.4.2",
      packages=["asvdb"],
      install_requires=["botocore", "boto3"],
      description='ASV "database" interface',
      entry_points={
          "console_scripts": [
              "asvdb = asvdb.__main__:main"
          ]
      },
)
