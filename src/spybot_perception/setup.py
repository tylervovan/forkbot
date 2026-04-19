from setuptools import find_packages, setup

package_name = 'spybot_perception'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/outlet_detector.launch.py']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Tyler',
    maintainer_email='25tylerv@gmail.com',
    description='Perception nodes for the Spy Bot (outlet detection via Roboflow inference).',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'outlet_detector = spybot_perception.outlet_detector:main',
            'usb_camera_publisher = spybot_perception.usb_camera_publisher:main',
            'detection_overlay = spybot_perception.detection_overlay:main',
        ],
    },
)
