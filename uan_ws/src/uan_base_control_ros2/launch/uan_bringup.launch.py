"""UAN bringup (ROS 2 Galactic port of uan_bringup.launch).

Starts the LoCoBot control stack with the mobile base enabled. Wraps
interbotix_xslocobot_control/launch/xslocobot_control.launch.py (from the
robot's ROS 2 Galactic system workspace) so the whole project has one entry
point, same role as the ROS 1 version.

PORT NOTE: this assumes the Galactic branch of interbotix_ros_rovers /
interbotix_ros_xslocobots is installed on the robot and exposes a
`xslocobot_control.launch.py` with the same launch arguments as the ROS 1
`xslocobot_control.launch` (robot_model, robot_name, base_type, use_base,
use_lidar, use_camera, use_rviz). This has NOT been confirmed on this robot's
Galactic install - verify with:
    ros2 pkg prefix interbotix_xslocobot_control
    ros2 launch interbotix_xslocobot_control xslocobot_control.launch.py --show-args
and adjust the argument names below if they differ.

Unlike the ROS 1 version, the Create3 base itself does NOT need this launch
at all for plain velocity control - /mobile_base/cmd_vel and
/mobile_base/odom are native ROS 2 Galactic topics on the robot already (see
reference/interbotix_xslocobot_control/config/bridge.yaml, which only exists
to expose those same topics to ROS 1). This launch is only needed once the
arm, lidar or camera are involved.
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import EnvironmentVariable, LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    robot_model = LaunchConfiguration('robot_model')
    robot_name = LaunchConfiguration('robot_name')
    base_type = LaunchConfiguration('base_type')
    use_base = LaunchConfiguration('use_base')
    use_lidar = LaunchConfiguration('use_lidar')
    use_camera = LaunchConfiguration('use_camera')
    use_rviz = LaunchConfiguration('use_rviz')

    return LaunchDescription([
        DeclareLaunchArgument('robot_model', default_value='locobot_wx200'),
        DeclareLaunchArgument('robot_name', default_value='locobot'),
        DeclareLaunchArgument(
            'base_type',
            default_value=EnvironmentVariable(
                'INTERBOTIX_XSLOCOBOT_BASE_TYPE', default_value='create3'),
        ),
        DeclareLaunchArgument('use_base', default_value='true'),
        DeclareLaunchArgument('use_lidar', default_value='false'),
        DeclareLaunchArgument('use_camera', default_value='false'),
        DeclareLaunchArgument('use_rviz', default_value='false'),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(PathJoinSubstitution([
                FindPackageShare('interbotix_xslocobot_control'),
                'launch', 'xslocobot_control.launch.py',
            ])),
            launch_arguments={
                'robot_model': robot_model,
                'robot_name': robot_name,
                'base_type': base_type,
                'use_base': use_base,
                'use_lidar': use_lidar,
                'use_camera': use_camera,
                'use_rviz': use_rviz,
            }.items(),
        ),
    ])
