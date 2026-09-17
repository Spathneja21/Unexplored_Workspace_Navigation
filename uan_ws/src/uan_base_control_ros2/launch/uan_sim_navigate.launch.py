"""UAN sim navigate (ROS 2 Galactic port of uan_sim_navigate.launch).

No robot, no locobot connection - trace Nav2's planned path on a saved map,
entirely on the machine running this launch (laptop or otherwise). Same
role and same simplifications as the ROS 1 version:

  - map_server (nav2_map_server) + a static map-><robot_name>/odom transform
    + fake_base_sim.py (integrates Nav2's /cmd_vel into a moving
    <robot_name>/odom-><robot_name>/base_footprint transform) + the real
    robot mesh (via interbotix_xslocobot_descriptions, copied into
    reference/) + Nav2's planner/controller only - no lidar/depth sensors
    exist here, so obstacle avoidance only sees whatever's baked into the
    static map, and fake_base_sim.py has no collision checking.
  - No AMCL/localization here either, same reasoning as the ROS 1 version:
    the robot always starts at map-frame (0,0) via the static transform:
    there's nothing to localize against without real sensors.
  - Deliberately does NOT use nav2_bringup's full bringup_launch.py (that
    pulls in amcl, which needs a real scan topic to do anything useful).
    Uses Nav2's navigation_launch.py instead (planner_server,
    controller_server, recoveries_server, bt_navigator, waypoint_follower -
    no map_server/amcl), plus a standalone map_server + lifecycle_manager
    for just the map.

PORT NOTE: Galactic's Nav2 does not ship velocity_smoother/collision_monitor
(added in later distros) - controller_server publishes cmd_vel directly,
which fake_base_sim.py subscribes to un-remapped, same as the ROS 1 version's
plain `cmd_vel` (no /mobile_base prefix - this is the simulated, no-hardware
path, so there's no real Create3 to talk to).

Run (from this package, once built - or by direct file path exactly like
the ROS 1 version's laptop-only workflow if uan_ws isn't built/sourced):

    ros2 launch uan_base_control_ros2 uan_sim_navigate.launch.py \\
        map_file:=$(ros2 pkg prefix uan_base_control_ros2)/share/uan_base_control_ros2/maps/hall.yaml
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import (
    Command,
    LaunchConfiguration,
    PathJoinSubstitution,
    PythonExpression,
)
from launch_ros.actions import Node
from launch_ros.descriptions import ParameterFile
from launch_ros.substitutions import FindPackageShare
from nav2_common.launch import RewrittenYaml


def generate_launch_description():
    map_file = LaunchConfiguration('map_file')  # required, e.g. .../maps/hall.yaml
    robot_model = LaunchConfiguration('robot_model')
    robot_name = LaunchConfiguration('robot_name')
    base_type = LaunchConfiguration('base_type')
    use_rviz = LaunchConfiguration('use_rviz')

    arm_model = PythonExpression([
        "'mobile_' + '", robot_model, "'.split('_')[1]",
    ])

    robot_description = Command([
        'xacro ',
        PathJoinSubstitution([
            FindPackageShare('interbotix_xslocobot_descriptions'),
            'urdf', 'locobot.urdf.xacro',
        ]),
        ' arm_model:=', arm_model,
        ' base_model:=', base_type,
        ' robot_model:=', robot_model,
        ' robot_name:=', robot_name,
        ' show_lidar:=true',
        ' show_gripper_bar:=true',
        ' show_gripper_fingers:=true',
        ' external_urdf_loc:=',
    ])

    odom_frame = [robot_name, '/odom']
    base_frame = [robot_name, '/base_footprint']

    configured_params = ParameterFile(
        RewrittenYaml(
            source_file=LaunchConfiguration('params_file'),
            root_key='',
            param_rewrites={'<robot_name>': robot_name},
            convert_types=True,
        ),
        allow_substs=True,
    )

    return LaunchDescription([
        DeclareLaunchArgument('map_file', description='e.g. .../uan_base_control_ros2/maps/hall.yaml'),
        DeclareLaunchArgument('robot_model', default_value='locobot_wx200'),
        DeclareLaunchArgument('robot_name', default_value='locobot'),
        DeclareLaunchArgument('base_type', default_value='create3'),
        DeclareLaunchArgument('use_rviz', default_value='true'),
        DeclareLaunchArgument(
            'params_file',
            default_value=PathJoinSubstitution([
                FindPackageShare('uan_base_control_ros2'), 'config', 'nav2_params.yaml',
            ]),
        ),

        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            output='screen',
            parameters=[{'robot_description': robot_description}],
        ),
        Node(
            package='joint_state_publisher',
            executable='joint_state_publisher',
            name='joint_state_publisher',
            output='screen',
        ),

        Node(
            package='nav2_map_server',
            executable='map_server',
            name='map_server',
            output='screen',
            parameters=[{'yaml_filename': map_file, 'use_sim_time': False}],
        ),
        # map_server (like every Nav2 node) starts unconfigured/inactive until
        # a lifecycle manager brings it up - unlike ROS 1's map_server, which
        # was always active once launched.
        Node(
            package='nav2_lifecycle_manager',
            executable='lifecycle_manager',
            name='lifecycle_manager_map',
            output='screen',
            parameters=[{
                'use_sim_time': False,
                'autostart': True,
                'node_names': ['map_server'],
            }],
        ),

        # fake robot starts at map-frame (0,0) - within the map's bounds.
        # Edit robot_name or re-parent this transform to change the starting
        # position.
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='map_to_odom',
            arguments=['0', '0', '0', '0', '0', '0', 'map', odom_frame],
        ),

        Node(
            package='uan_base_control_ros2',
            executable='fake_base_sim',
            name='fake_base_sim',
            output='screen',
            parameters=[{'odom_frame': odom_frame, 'base_frame': base_frame}],
        ),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(PathJoinSubstitution([
                FindPackageShare('nav2_bringup'), 'launch', 'navigation_launch.py',
            ])),
            launch_arguments={
                'params_file': configured_params,
                'use_sim_time': 'false',
                'autostart': 'true',
            }.items(),
        ),

        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen',
            arguments=['-f', 'map'],
            condition=IfCondition(use_rviz),
        ),
    ])
