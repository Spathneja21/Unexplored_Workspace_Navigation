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

Once a map is saved (`uan_ws/src/uan_base_control/maps/my_room.pgm`/`.yaml`),
drive the robot around it by clicking goals in rviz instead of teleop.

Use **`uan_navigate.launch`** — it loads that exact `.pgm`/`.yaml` via
`map_server` + `amcl` + `move_base`, so the map shown is always the one
checked into the repo, deterministically.

> `uan_localize.launch` (an earlier approach, reusing rtabmap's own
> `~/.ros/rtabmap.db` instead of the exported `.pgm`) is **superseded** —
> it kept loading whichever database happened to be on disk, which produced
> a different/wrong-looking map depending on what had run most recently.
> Kept in the repo for reference but `uan_navigate.launch` is the one to use.

**On the locobot** — make sure nothing else (`uan_bringup.launch`,
`uan_slam.launch`, another `uan_navigate.launch`) is already running first;
running two base/lidar launches at once causes node conflicts:

```bash
ps aux | grep -i roslaunch | grep -v grep   # confirm nothing else is up
source /home/locobot/UAN/Unexplored_Workspace_Navigation/uan_ws/devel/setup.bash
ROS_IP=172.27.244.85 roslaunch uan_base_control uan_navigate.launch
```

No camera needed for this path — `amcl` only uses the lidar scan + wheel
odom, not RGBD.

**On the laptop** (same `ROS_MASTER_URI`/`ROS_IP` setup as the SLAM/rviz
section above):

```bash
rosrun rviz rviz -f map
```

### rviz setup for navigating

Add displays:
- **Map** on `/map` (global topic here, not `/locobot/rtabmap/grid_map` —
  no rtabmap running in this path)
- **LaserScan** on `/locobot/scan`

`RobotModel` and camera-related displays aren't relevant here since no
camera node is running. `2D Pose Estimate` and `2D Nav Goal` should work
with rviz's **default** topics in this launch (`initialpose`,
`move_base_simple/goal`) since neither `amcl` nor `move_base` are inside
the `/locobot` namespace here — unlike the old `uan_localize.launch` path,
no Tool Properties changes should be needed. Verify this before relying on
it; if clicks don't do anything, check **Panels → Tool Properties** the
same way as before.

### Localizing and driving to a goal

1. **2D Pose Estimate**: click the toolbar button, then click-and-drag on
   the map at the robot's actual real-world position and facing direction.
   This seeds `amcl`'s localization — without it, the robot's shown
   position can be arbitrarily wrong until enough matching scan data
   accumulates on its own.
2. Confirm the pose (or RobotModel, if you add one back with the
   `locobot/robot_description` param) settles onto the correct spot on the
   map.
3. **2D Nav Goal**: click the toolbar button, then click-and-drag elsewhere
   on the map — the drag sets the final facing angle, not just the
   destination point. `move_base` (already running) plans and drives there
   via `/mobile_base/cmd_vel`.

A goal inside mapped-obstacle space (black cells) or unmapped territory
will be rejected rather than attempted — pick a point clearly in open
(light gray) space, especially for the first try.

You may see intermittent `amcl` warnings like `Failed to compute odom pose,
skipping scan (... extrapolation ... into the future)` — this is a small,
recurring timing race between the Create3 bridge's odom/tf delivery and the
lidar's own scan timestamps (roughly 1 in every 13-16 scans at a 10Hz scan
rate). It's cosmetic as long as goals still get planned and driven; only
worth chasing further if navigation actually stalls.

## Simulated navigation (no robot, laptop-only)

For tracing a planned path (with the real robot mesh visible) on a map
without connecting to the locobot at all — e.g. testing a new map like
`hall.pgm` before ever driving the real robot there. Runs entirely on
whatever machine launches it (tested on the laptop): `map_server` + the
real robot model (via `interbotix_xslocobot_descriptions`, copied into
`reference/`) fixed at a static position + `move_base` (global planner
only — there's no real lidar/camera here, so obstacle avoidance only sees
what's baked into the static map image).

There's no Gazebo/physics simulator in this project — "simulation" here
means move_base computing and showing a plan (with a robot mesh sitting on
the map for context), not the robot actually moving anywhere.

**Two known machine-specific gotchas, check both before debugging further:**
1. **conda shadows `python3`.** If your shell prompt starts with `(base)`
   (or another conda env), `python3`/pure-Python ROS nodes (`joint_state_publisher`,
   `rostopic`, anything with a `python3` shebang) can silently fail with
   `ModuleNotFoundError: No module named 'yaml'` — conda's Python doesn't
   have the system's `python3-yaml` installed. Fix: `conda deactivate`
   before sourcing ROS, or strip conda from `PATH` for that shell.
2. **Two extra packages must be on `ROS_PACKAGE_PATH` before roslaunch runs**
   (the launch file's own `$(find interbotix_xslocobot_descriptions)` is
   resolved at parse time, so this can't be set from inside the launch file):
   - `reference/interbotix_xslocobot_descriptions` (the robot mesh/URDF,
     copied in for this)
   - `/opt/ros/galactic/share` (`irobot_create_description` — the Create3
     base's own meshes live in this *separate* package; on this laptop it's
     already present as a ROS2 Galactic `.deb` from earlier bridge setup
     work, and plain directory-based ROS1 `rospack` resolves it fine
     without any ROS2 tooling being invoked)

```bash
conda deactivate   # skip if you're not in a conda env
source /opt/ros/noetic/setup.bash
export ROS_PACKAGE_PATH=$ROS_PACKAGE_PATH:/path/to/Unexplored_Workspace_Navigation/reference:/opt/ros/galactic/share

roslaunch /path/to/Unexplored_Workspace_Navigation/uan_ws/src/uan_base_control/launch/uan_sim_navigate.launch \
  map_file:=/path/to/Unexplored_Workspace_Navigation/uan_ws/src/uan_base_control/maps/hall.yaml
```

Launched by direct file path (not `roslaunch uan_base_control ...`) since
it doesn't need `uan_ws` built/sourced — everything it uses (`map_server`,
`move_base`, `tf2_ros`, `robot_state_publisher`) is a plain ROS package.
`map_file` is required (no default) since this launch is meant to be run
from any checkout location. Use `$HOME/...`, not `~/...`, for the
`map_file:=` value — a bare `~` after `:=` isn't shell-expanded, only one
at the very start of an argument is.

rviz opens automatically (`use_rviz:=true` by default). Add displays:
- **Map** on `/map`
- **RobotModel** (Robot Description: `robot_description`, the default —
  no namespace override needed here, unlike the real-robot launches)
- **Path** on `/move_base/NavfnROS/plan` — the full route from start to
  goal, published once per goal. Add a second **Path** on
  `/move_base/TrajectoryPlannerROS/global_plan` too if you also want to see
  what the local controller is currently tracking — that one gets pruned
  as the robot advances, so it visually shrinks over time instead of
  staying as one full line the way `NavfnROS/plan` does

The robot starts at map-frame `(0, 0)`. Click **2D Nav Goal** to set a
destination — `move_base` plans, and `fake_base_sim.py` (a small dead-
reckoning integrator) drives the robot mesh there by integrating
`move_base`'s `/cmd_vel` output, so it visibly moves along the path rather
than just showing a static line.

`2D Pose Estimate` clicks still do nothing here — nothing subscribes to
`initialpose`, since there's no real localization system (see the
`fake_localization` dead-end noted in changes.md). The robot always starts
at `(0, 0)`; to change that, edit the `map_to_odom` `static_transform_publisher`
args in `uan_sim_navigate.launch`.

**No collision checking** — `fake_base_sim.py` just integrates velocity,
it doesn't know where the mapped walls are. It'll happily drive straight
through them if a goal or an aggressive local-planner detour sends it
there. Fine for tracing/demoing a path, not a real physics sim.

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
