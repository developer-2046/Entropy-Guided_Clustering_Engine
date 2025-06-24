from setuptools import setup, find_packages

setup(
    name="market-entropy",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.104.1",
        "uvicorn[standard]>=0.24.0",
        "redis>=5.0.1",
        "pandas>=2.1.3",
        "numpy>=1.25.2",
        "scipy>=1.11.4",
        "scikit-learn>=1.3.2",
    ],
    author="Yuvraj Malik",
    author_email="yuvrajmalik2046@gmail.com",
    description="Real-time market regime detection using spectral entropy",
)