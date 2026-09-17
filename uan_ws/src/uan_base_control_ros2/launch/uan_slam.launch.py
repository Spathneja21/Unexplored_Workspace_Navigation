"""UAN SLAM (ROS 2 Galactic port of uan_slam.launch).

Builds a map of the current room with the lidar + RGBD camera. Wraps
interbotix_xslocobot_nav/launch/xslocobot_nav.launch.py, which on Galactic
is expected to run rtabmap_ros (RGBD+lidar SLAM) and Nav2 - the ROS 2
equivalent of the ROS 1 version's rtabmap + move_base combo. Mapping vs.
localization is just the `localization` launch argument (default false),
same as the ROS 1 launch.

PORT NOTE: verify against the actual installed package -
`ros2 launch interbotix_xslocobot_nav xslocobot_nav.launch.py --show-args` -
and adjust argument names if this vendor launch differs from its ROS 1
namesake. Also verify it still hardcodes use_camera:=true internally like
the ROS 1 version (rtabmap needs the RGBD camera alongside the lidar scan).
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    robot_model = LaunchConfiguration('robot_model')
    robot_name = LaunchConfiguration('robot_name')
    use_rviz = LaunchConfiguration('use_rviz')

    return LaunchDescription([
        DeclareLaunchArgument('robot_model', default_value='locobot_wx200'),
        DeclareLaunchArgument('robot_name', default_value='locobot'),
        DeclareLaunchArgument('use_rviz', default_value='true'),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(PathJoinSubstitution([
                FindPackageShare('interbotix_xslocobot_nav'),
                'launch', 'xslocobot_nav.launch.py',
            ])),
            launch_arguments={
                'robot_model': robot_model,
                'robot_name': robot_name,
                'use_lidar': 'true',
                'use_rviz': use_rviz,
            }.items(),
        ),
    ])
