"""UAN navigate (ROS 2 Galactic port of uan_navigate.launch).

Drive the robot around a previously saved map (maps/my_room.yaml) by
clicking goals in rviz2, using Nav2 (nav2_bringup's map_server + amcl +
controller/planner/bt_navigator stack) - the ROS 2 equivalent of the ROS 1
map_server + amcl + move_base combo from uan_navigate.launch. Same design
choice as the ROS 1 project (changes.md Step 9): load the exact checked-in
.pgm/.yaml deterministically, rather than depending on whichever rtabmap
database happens to be on disk.

No camera needed - Nav2's amcl only needs the lidar scan + wheel odom, same
as the ROS 1 version.

PORT NOTE / things to verify on the robot:
  - nav2_bringup is installed for Galactic (`ros2 pkg prefix nav2_bringup`).
  - config/nav2_params.yaml's costmap/controller values are a generic
    starting point, NOT a port of the vendor's actual costmap yamls (those
    were never copied into this repo even on the ROS 1 side - see
    changes.md Step 3). Tune against real driving behavior.
  - `<robot_name>` frame prefixing: the ROS 1 stack namespaces TF frames as
    `<robot_name>/base_footprint` etc. but runs move_base/amcl *unnamespaced*
    (changes.md Step 9). This launch assumes the ROS 2 vendor stack keeps
    the same TF frame prefix; if the Galactic driver doesn't prefix frames
    at all, drop the `<robot_name>` rewriting below and use bare frame
    names in nav2_params.yaml instead.
  - `scan` topic relay below assumes the lidar publishes under
    `/<robot_name>/scan`, mirroring the ROS 1 launch's explicit
    `<remap from="scan" to="/$(arg robot_name)/scan"/>`. Confirm with
    `ros2 topic list` once uan_bringup.launch.py with use_lidar:=true is up.
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.descriptions import ParameterFile
from launch_ros.substitutions import FindPackageShare
from nav2_common.launch import RewrittenYaml


def generate_launch_description():
    robot_model = LaunchConfiguration('robot_model')
    robot_name = LaunchConfiguration('robot_name')
    use_rviz = LaunchConfiguration('use_rviz')
    map_file = LaunchConfiguration('map_file')
    params_file = LaunchConfiguration('params_file')

    # Substitute the `<robot_name>` placeholder in nav2_params.yaml with the
    # real robot_name argument, nav2_bringup's own pattern for namespaced
    # deployments (RewrittenYaml).
    configured_params = ParameterFile(
        RewrittenYaml(
            source_file=params_file,
            root_key='',
            param_rewrites={'<robot_name>': robot_name},
            convert_types=True,
        ),
        allow_substs=True,
    )

    return LaunchDescription([
        DeclareLaunchArgument('robot_model', default_value='locobot_wx200'),
        DeclareLaunchArgument('robot_name', default_value='locobot'),
        DeclareLaunchArgument('use_rviz', default_value='false'),
        DeclareLaunchArgument(
            'map_file',
            default_value=PathJoinSubstitution([
                FindPackageShare('uan_base_control_ros2'), 'maps', 'my_room.yaml',
            ]),
        ),
        DeclareLaunchArgument(
            'params_file',
            default_value=PathJoinSubstitution([
                FindPackageShare('uan_base_control_ros2'), 'config', 'nav2_params.yaml',
            ]),
        ),

        # base + lidar only, no camera - matches uan_bringup.launch's role here
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(PathJoinSubstitution([
                FindPackageShare('uan_base_control_ros2'), 'launch', 'uan_bringup.launch.py',
            ])),
            launch_arguments={
                'robot_model': robot_model,
                'robot_name': robot_name,
                'use_lidar': 'true',
                'use_camera': 'false',
                'use_rviz': use_rviz,
            }.items(),
        ),

        # PORT NOTE: only needed if the lidar is namespaced under /<robot_name>
        # while Nav2 itself runs unnamespaced (see PORT NOTE in the module
        # docstring). Remove if the driver already publishes plain /scan.
        Node(
            package='topic_tools',
            executable='relay',
            name='uan_scan_relay',
            arguments=[['/', robot_name, '/scan'], '/scan'],
            output='screen',
        ),

        # controller_server's default cmd_vel output -> the Create3's native
        # topic. ROS 2 launch can't remap a topic on a node defined inside an
        # included launch file, so bridge it the same way as the scan relay
        # above - equivalent to the ROS 1 launch's
        # <remap from="cmd_vel" to="/mobile_base/cmd_vel"/> on the move_base node.
        Node(
            package='topic_tools',
            executable='relay',
            name='uan_cmd_vel_relay',
            arguments=['cmd_vel', '/mobile_base/cmd_vel'],
            output='screen',
        ),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(PathJoinSubstitution([
                FindPackageShare('nav2_bringup'), 'launch', 'bringup_launch.py',
            ])),
            launch_arguments={
                'map': map_file,
                'params_file': configured_params,
                'use_sim_time': 'false',
                'autostart': 'true',
            }.items(),
        ),
    ])
