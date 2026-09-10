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

## Viewing rviz on your laptop (not over SSH -X)

SSH X11 forwarding renders rviz remotely and streams pixels - too slow for
the 3D map view. Instead run rviz natively on the laptop as a normal ROS
node against the NUC's `roscore`; see changes.md Step 6 for why this needs
a `ROS_IP` override on the NUC side.

**On the locobot** — relaunch SLAM with `ROS_IP` bound to its WiFi interface
(find it with `hostname -I`), not the wired Create3 subnet the `.bashrc`
default points to:

```bash
ROS_IP=172.27.244.85 roslaunch uan_base_control uan_slam.launch
```

**On the laptop** (requires `ros-noetic-rviz` installed locally):

```bash
source /opt/ros/noetic/setup.bash
export ROS_MASTER_URI=http://locobot.local:11311
export ROS_IP=172.27.244.134
rostopic list         
rosrun rviz rviz -f map
```

Add displays: **Map** on `/locobot/rtabmap/grid_map`, **LaserScan** on
`/locobot/scan`.

If either machine's IP changes mid-session, redo both the NUC relaunch and
the laptop's `export`s with the new IPs.

## Traversing a saved map

Once a map exists (built via `uan_slam.launch` above, saved to `~/.ros/rtabmap.db`),
drive the robot around it by clicking goals in rviz instead of teleop.

**On the locobot:**

```bash
source /home/locobot/UAN/Unexplored_Workspace_Navigation/uan_ws/devel/setup.bash
ROS_IP=<nuc's WiFi IP> roslaunch uan_base_control uan_localize.launch use_rviz:=false
```

**On the laptop** (same `ROS_MASTER_URI`/`ROS_IP` setup as the SLAM/rviz
section above):

```bash
rosrun rviz rviz -f map
```

This reuses the same `rtabmap.db` the map was built from, rather than
reloading the exported `.pgm`/`.yaml` through a separate `map_server`/`amcl`
stack - `localization:=true` just tells rtabmap to stop extending the map
and instead localize the robot against what's already there.

### rviz setup for navigating

Add displays:
- **Map** on `/locobot/rtabmap/grid_map`
- **LaserScan** on `/locobot/scan`
- **RobotModel** — set its **Robot Description** field to `locobot/robot_description`
  (not the default `robot_description`) since `robot_state_publisher` runs
  under the `/locobot` namespace. Tick its checkbox to enable.
- **Pose** — set its **Topic** to `/locobot/rtabmap/localization_pose`
  (`geometry_msgs/PoseWithCovarianceStamped`) to see rtabmap's live
  localization estimate as an arrow.

Skip an **Odometry** display on `/mobile_base/odom` — its message frame is
plain `odom` while this stack's TF tree uses `locobot/odom`, so it'll only
show a TF error, not useful data.

**rviz's click tools also need re-pointing**, since they default to
unnamespaced topics that nothing here subscribes to. Open
**Panels → Tool Properties**:
- **2D Pose Estimate** → Topic → `/locobot/initialpose`
- **2D Nav Goal** → Topic → `/locobot/move_base_simple/goal`

### Localizing and driving to a goal

1. **2D Pose Estimate**: click the toolbar button, then click-and-drag on
   the map at the robot's actual real-world position and facing direction.
   This seeds rtabmap's localization — without it, the robot's shown
   position can be arbitrarily wrong until enough matching scan/visual data
   accumulates on its own.
2. Confirm the RobotModel/Pose arrow settles onto the correct spot on the
   map.
3. **2D Nav Goal**: click the toolbar button, then click-and-drag elsewhere
   on the map — the drag sets the final facing angle, not just the
   destination point. `move_base` (already running) plans and drives there
   via `/mobile_base/cmd_vel`.

A goal inside mapped-obstacle space (black cells) or unmapped territory
will be rejected rather than attempted — pick a point clearly in open
(light gray) space, especially for the first try.

## Camera pan/tilt

The RealSense's pan/tilt mount is a normal Interbotix joint group, moved
the same way `xslocobot_nav.launch` tilts it down for mapping.

```bash
rostopic pub -1 /locobot/commands/joint_group interbotix_xs_msgs/JointGroupCommand "{name: 'camera', cmd: [<pan>, <tilt>]}"
```

Both values are in radians, position-controlled. `[0.0, 0.0]` is level/
centered; positive tilt looks down (confirmed: `0.3` ≈ 17° down). Move in
small steps (~±0.2-0.3 rad) rather than large jumps — exact mechanical
limits haven't been checked against the URDF.

Check current position:
```bash
rostopic echo -n 1 /locobot/joint_states
```
Look for `pan`/`tilt` in the `name` array and read the matching `position`
values.
