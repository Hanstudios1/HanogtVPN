"""HanogtVPN — Professional VPN Client and Server."""

from setuptools import setup, find_packages

with open("requirements.txt", encoding="utf-8") as f:
    requirements = [
        line.strip() for line in f if line.strip() and not line.startswith("#")
    ]

with open("README.md", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="hanogtvpn",
    version="0.0.1",
    author="HanogtVPN Team",
    description="Güvenli, hızlı ve modern VPN çözümü",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/hanogtvpn/HanogtVPN",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "hanogtvpn-client=hanogtvpn.client.app:main",
            "hanogtvpn-server=hanogtvpn.server.server:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Internet :: Proxy Servers",
        "Topic :: Security",
        "Operating System :: OS Independent",
    ],
    keywords="vpn security encryption ecdh aes",
)
