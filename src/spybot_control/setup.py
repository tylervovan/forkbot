from setuptools import find_packages, setup

package_name = 'spybot_control'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/drive_bridge.launch.py']),
        ('share/' + package_name + '/config', ['config/drive_bridge.yaml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Tyler',
    maintainer_email='25tylerv@gmail.com',
    description='Control nodes for the Spy Bot (drive_bridge: ROS Twist/Int8 to Arduino USB serial).',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'drive_bridge = spybot_control.drive_bridge:main',
        ],
    },
)
