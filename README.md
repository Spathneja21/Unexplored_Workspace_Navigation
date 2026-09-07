# Unexplored Workspace Navigation (UAN)

Autonomous exploration of unknown indoor workspaces on a Trossen LoCoBot
(WX200 arm, iRobot Create3 base) running ROS Noetic on the robot's NUC.

Every step of this project is logged in [changes.md](changes.md).

## Layout

| Path | What it is |
| --- | --- |
| `uan_ws/` | Our catkin workspace — all project code lives here |
| `uan_ws/src/uan_base_control/` | Base bringup + velocity control (Step 1), SLAM mapping (Step 3) |
| `reference/` | Read-only copies of vendor files from `interbotix_ros_rovers` |

`reference/` is **not** a catkin source tree. The Interbotix packages are used
from the already-built `/home/locobot/interbotix_ws`; see changes.md for why.

## to use the ssh 

conda deactivate
ssh locobot@locobot.local
cd UAN/Unexplored_Workspace_Navigation/

## Setup (once per new terminal)

```bash
source /home/locobot/interbotix_ws/devel/setup.bash
source /home/locobot/UAN/Unexplored_Workspace_Navigation/uan_ws/devel/setup.bash
cd UAN/Unexplored_Workspace_Navigation/
```

## Rebuild

```bash
cd /home/locobot/UAN/Unexplored_Workspace_Navigation/uan_ws
source /home/locobot/interbotix_ws/devel/setup.bash
catkin_make
```

## Driving the base

**Terminal 1 — bringup** (leave running):

```bash
source /home/locobot/UAN/Unexplored_Workspace_Navigation/uan_ws/devel/setup.bash
roslaunch uan_base_control uan_bringup.launch robot_model:=locobot_wx200
```

**Terminal 2 — send velocities:**

```bash
source /home/locobot/UAN/Unexplored_Workspace_Navigation/uan_ws/devel/setup.bash

# drive forward 0.1 m/s for 3 s
rosrun uan_base_control velocity_publisher.py -x 0.1 -t 3

# rotate in place
rosrun uan_base_control velocity_publisher.py -z -0.5 -t 1

# keyboard teleop (w/s/a/d, x = stop, q = quit)
rosrun uan_base_control teleop_keyboard.py
```

Base topics: commands go to `/mobile_base/cmd_vel`, odometry comes back on
`/mobile_base/odom`.

## Emergency stop

```bash
rostopic pub -1 /mobile_base/cmd_vel geometry_msgs/Twist '{}'
```

## Mapping (SLAM)

Builds a map of the room using the lidar + RGBD camera (rtabmap). This
replaces `uan_bringup.launch` for the session - don't run both at once.

**Terminal 1 — SLAM + drive stack:**

```bash
source /home/locobot/UAN/Unexplored_Workspace_Navigation/uan_ws/devel/setup.bash
roslaunch uan_base_control uan_slam.launch
```

**Terminal 2 — drive it around** (teleop or `velocity_publisher.py`, see
above) to build up map coverage, or send `move_base` goals once enough of
the room is mapped.

**Save the map** once you're done exploring:

```bash
mkdir -p ~/maps
rosrun map_server map_saver -f ~/maps/my_room map:=/locobot/rtabmap/grid_map
```

`maps/` is gitignored (see changes.md Step 2) - the `.pgm`/`.yaml` pair are
run artifacts, save them outside the repo (as above) or use `git add -f` if
one needs to be committed as a reference map.
