import os
from glob import glob

from setuptools import find_packages, setup

package_name = 'uan_base_control_ros2'

setup(
    name=package_name,
    version='0.0.1',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
        (os.path.join('share', package_name, 'maps'), glob('maps/*.pgm') + glob('maps/*.yaml')),
        (os.path.join('lib', package_name), glob('scripts/*.sh')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Shubham Pathneja',
    maintainer_email='shubhampathneja123@gmail.com',
    description=(
        'ROS 2 Galactic port of uan_base_control: base velocity control, '
        'SLAM and navigation for the Unexplored Area Navigation project.'
    ),
    license='BSD',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'velocity_publisher = uan_base_control_ros2.velocity_publisher:main',
            'teleop_keyboard = uan_base_control_ros2.teleop_keyboard:main',
            'fake_base_sim = uan_base_control_ros2.fake_base_sim:main',
            'cloud_stats = uan_base_control_ros2.cloud_stats:main',
        ],
    },
)
