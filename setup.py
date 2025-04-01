from setuptools import setup, find_packages

setup(
    name="genmusic",
    version="1.0.0",
    description="ระบบสร้างดนตรีอัตโนมัติด้วย AI",
    author="Genmusic Team",
    packages=find_packages(),
    install_requires=[
        "torch==2.0.1",
        "torchaudio==2.0.2",
        "transformers==4.31.0",
        "audiocraft==1.0.0",
        "numpy==1.24.3",
        "scipy==1.10.1",
        "librosa==0.10.0",
        "soundfile==0.12.1",
        "PyQt6==6.5.2",
        "matplotlib==3.7.2",
        "numba==0.57.1",
        "onnxruntime==1.15.1",
        "psutil==5.9.5",
        "tqdm==4.65.0"
    ],
    entry_points={
        'console_scripts': [
            'genmusic=app.main:main',
        ],
    },
    python_requires='>=3.10',
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
) 