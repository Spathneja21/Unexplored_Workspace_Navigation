"""UAN 3D SLAM (ROS 2 Galactic port of uan_slam_3d.launch).

Builds a 3D map (OctoMap + point cloud) with the lidar + RealSense D435,
same rtabmap flag overrides as the ROS 1 version and for the same reasons
(see changes.md Steps 13-14 in the ROS 1 project for the full rationale):

  - Grid/Sensor 2            laser + depth (vendor lidar branch uses
                              Grid/FromDepth false == Grid/Sensor 0, laser
                              only, which leaves the OctoMap flat).
  - Grid/3D true             3D occupancy grid, required for the OctoMap.
  - Grid/MaxObstacleHeight   vendor default 0.7 m truncates the 3D map;
                              raised here (max_obstacle_height arg).
  - Grid/RangeMax            D435 depth noise grows with range squared, so
                              capped (grid_range_max arg). Also caps the
                              lidar's contribution to the 2D grid.

These are core rtabmap parameter names, unchanged between the ROS 1 and
ROS 2 wrappers (rtabmap itself is the same C++ library either way) - only
the surrounding ROS API differs.

PORT NOTE: same caveat as uan_slam.launch.py - verify
interbotix_xslocobot_nav's ROS 2 launch file accepts `rtabmap_args`/
`database_path`/`camera_tilt_angle` launch arguments with the same names
as the ROS 1 xslocobot_nav.launch, and check whether the *default* rtabmap
args still need to be overridden in full (as here) or whether this
argument is applied after the vendor's own flags on Galactic - if the
vendor launch places user args AFTER its own hardcoded flags (opposite of
the ROS 1 ordering bug this works around), passing only the deltas via
`rtabmap_args` might work instead of a full override.
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import (
    EnvironmentVariable,
    LaunchConfiguration,
    PathJoinSubstitution,
    PythonExpression,
)
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    robot_model = LaunchConfiguration('robot_model')
    robot_name = LaunchConfiguration('robot_name')
    use_rviz = LaunchConfiguration('use_rviz')

    map_name = LaunchConfiguration('map_name')
    database_path = LaunchConfiguration('database_path')
    fresh_db = LaunchConfiguration('fresh_db')
    localization = LaunchConfiguration('localization')

    camera_tilt_angle = LaunchConfiguration('camera_tilt_angle')
    grid_cell_size = LaunchConfiguration('grid_cell_size')
    grid_range_max = LaunchConfiguration('grid_range_max')
    max_obstacle_height = LaunchConfiguration('max_obstacle_height')

    cloud_voxel_size = LaunchConfiguration('cloud_voxel_size')
    cloud_max_depth = LaunchConfiguration('cloud_max_depth')

    # true = start a new map, same as the ROS 1 `db_flag` $(eval ...) arg.
    delete_db_flag = PythonExpression([
        "'--delete_db_on_start' if ('", fresh_db, "' == 'true' and '",
        localization, "' == 'false') else ''",
    ])

    rtabmap_3d_args = [
        delete_db_flag,
        ' --RGBD/NeighborLinkRefining true',
        '--RGBD/ProximityBySpace true',
        '--RGBD/ProximityPathMaxNeighbors 10',
        '--RGBD/AngularUpdate 0.01',
        '--RGBD/LinearUpdate 0.01',
        '--RGBD/LocalRadius 5',
        '--RGBD/OptimizeFromGraphEnd false',
        '--Grid/Sensor 2',
        '--Grid/3D true',
        '--Grid/CellSize ', grid_cell_size,
        ' --Grid/MaxObstacleHeight ', max_obstacle_height,
        ' --Grid/RayTracing true',
        ' --Grid/RangeMax ', grid_range_max,
        ' --Reg/Force3DoF true',
        ' --Reg/Strategy 1',
        ' --Mem/STMSize 30',
        ' --Icp/VoxelSize 0.05',
        ' --Icp/CorrespondenceRatio 0.4',
        ' --Icp/MaxCorrespondenceDistance 0.1',
    ]

    return LaunchDescription([
        DeclareLaunchArgument('robot_model', default_value='locobot_wx200'),
        DeclareLaunchArgument('robot_name', default_value='locobot'),
        DeclareLaunchArgument('use_rviz', default_value='false'),

        DeclareLaunchArgument('map_name', default_value='room_3d'),
        DeclareLaunchArgument(
            'database_path',
            default_value=[
                EnvironmentVariable('HOME'), '/uan_maps/', map_name, '.db',
            ],
        ),
        # true = start a new map. Ignored (never wipes) when localization:=true.
        DeclareLaunchArgument('fresh_db', default_value='true'),
        DeclareLaunchArgument('localization', default_value='false'),

        # 0 = level. Vendor default 0.2618 (15 deg down) misses the upper walls.
        DeclareLaunchArgument('camera_tilt_angle', default_value='0.1'),
        DeclareLaunchArgument('grid_cell_size', default_value='0.05'),
        DeclareLaunchArgument('grid_range_max', default_value='4.0'),
        DeclareLaunchArgument('max_obstacle_height', default_value='2.0'),

        # Live cloud_map published for viewing. Kept coarse so it survives WiFi.
        # PORT NOTE: the ROS 1 version set these as private params directly on
        # the vendor's rtabmap node via a <group ns=".../rtabmap/rtabmap">
        # block - roslaunch lets you pre-set another node's params that way.
        # ROS 2 launch has no equivalent for a node defined inside an
        # *included* launch file; this only takes effect if
        # xslocobot_nav.launch.py forwards these names through to the
        # rtabmap_ros node's parameters. Verify with
        # `ros2 launch interbotix_xslocobot_nav xslocobot_nav.launch.py --show-args`;
        # if it doesn't forward them, set them via `ros2 param set
        # /<robot_name>/rtabmap/rtabmap cloud_voxel_size 0.05` after launch instead.
        DeclareLaunchArgument('cloud_voxel_size', default_value='0.05'),
        DeclareLaunchArgument('cloud_max_depth', default_value='4.0'),

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
                'localization': localization,
                'database_path': database_path,
                'camera_tilt_angle': camera_tilt_angle,
                'cloud_voxel_size': cloud_voxel_size,
                'cloud_max_depth': cloud_max_depth,
                # Deliberately overrides the vendor's *entire* default arg
                # string, not just appends - see PORT NOTE above and the
                # ROS 1 launch's own comment for why appending isn't safe
                # if the vendor places later flags after user-supplied ones.
                'rtabmap_default_args': rtabmap_3d_args,
            }.items(),
        ),
    ])
