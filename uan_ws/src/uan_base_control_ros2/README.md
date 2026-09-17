# uan_base_control_ros2

ROS 2 Galactic port of [`uan_base_control`](../uan_base_control/) (ROS 1
Noetic) — base velocity control, SLAM and navigation for the Unexplored
Area Navigation project, for the LoCoBot's native Galactic side instead of
going through `ros1_bridge`.

Ported for **the same functionality** as the ROS 1 package: base
teleop/velocity control, 2D SLAM, 3D SLAM (rtabmap), 2D navigation on a
saved map, and a laptop-only no-hardware sim/navigation demo. See
`../../../changes.md` and `../../../README.md` for the full history and
design rationale each ROS 1 launch file was built against — this port
follows the same decisions (deterministic map_server+localization over
reusing a live database, per-map 3D database files, etc.) unless a PORT
NOTE below says otherwise.

## Why a separate package/workspace, not literally the same `uan_base_control`

A ROS 1 catkin package and a ROS 2 ament package can't safely share one
name in a workspace that might be built by either `catkin_make` or
`colcon build` — neither build tool understands the other's package
manifest, so mixing them in one `src/` and building it as one workspace
will fail (or silently pick the wrong one, per the same
`rospack`/ambiguity problem the ROS 1 README's "reference copy, not a
rebuild" section already ran into with `interbotix_xslocobot_control`).

**On the LoCoBot**, put this folder in its own ROS 2 colcon workspace
(e.g. `~/uan_ros2_ws/src/uan_base_control_ros2`, alongside wherever
`create3_ros2_ws` already lives) — don't add it to the existing catkin
`uan_ws`. It's kept inside this repo's `uan_ws/src/` here only so the ROS 1
and ROS 2 versions live side by side for reference/diffing.

## What ported directly vs. what needed a design change

| ROS 1 | ROS 2 Galactic | Notes |
| --- | --- | --- |
| `velocity_publisher.py` | `velocity_publisher.py` | Same behavior. No bridge-registration sleep needed — Galactic talks to `/mobile_base/cmd_vel` natively. |
| `teleop_keyboard.py` | `teleop_keyboard.py` | Line-for-line equivalent, `rclpy` instead of `rospy`. |
| `fake_base_sim.py` | `fake_base_sim.py` | Same integrator, `rclpy` Node + timer instead of `rospy.Timer`. |
| `cloud_stats.py` | `cloud_stats.py` | Unchanged — no ROS dependency either version. |
| `export_3d_map.sh` | `export_3d_map.sh` | Unchanged — `rtabmap-export` is the same CLI tool regardless of ROS version. |
| `uan_bringup.launch` | `uan_bringup.launch.py` | Wraps the Galactic branch of `interbotix_xslocobot_control` — **unverified on this robot, see Port notes**. |
| `uan_slam.launch` | `uan_slam.launch.py` | Wraps the Galactic `interbotix_xslocobot_nav` (expected to run `rtabmap_ros` + Nav2) — **unverified**. |
| `uan_slam_3d.launch` | `uan_slam_3d.launch.py` | Same rtabmap core-parameter overrides (`Grid/Sensor`, `Grid/3D`, etc. are library-level names, unchanged across ROS versions) — **unverified whether the vendor launch forwards `cloud_voxel_size` etc.** |
| `uan_navigate.launch` (map_server+amcl+move_base) | `uan_navigate.launch.py` (nav2_bringup) | Nav2's `bringup_launch.py` replaces the ROS 1 map_server/amcl/move_base trio. `config/nav2_params.yaml` is a **new, generic** costmap/controller config, not a port of vendor values (those were never in this repo — see `changes.md` Step 3). |
| `uan_sim_navigate.launch` | `uan_sim_navigate.launch.py` | Same no-hardware design: map_server + static transform + `fake_base_sim` + robot mesh + planner/controller only (no AMCL). Uses Nav2's `navigation_launch.py`, not the full `bringup_launch.py`, since there's no real scan for AMCL to use. |

## Port notes — verify before relying on these (not done from this session)

This was written without SSH access to the LoCoBot, so nothing here has
run against the robot's actual Galactic install. Concretely still open:

1. **Do the Galactic `interbotix_xslocobot_control` / `interbotix_xslocobot_nav`
   packages exist on this robot, and do their launch files use the same
   argument names as the ROS 1 versions?**
   ```bash
   ros2 pkg prefix interbotix_xslocobot_control interbotix_xslocobot_nav
   ros2 launch interbotix_xslocobot_control xslocobot_control.launch.py --show-args
   ros2 launch interbotix_xslocobot_nav xslocobot_nav.launch.py --show-args
   ```
   If either package is missing, `uan_bringup.launch.py` / `uan_slam*.launch.py`
   won't resolve — `uan_navigate.launch.py` and `uan_sim_navigate.launch.py`
   don't depend on them (bringup's include aside) so navigation-only testing
   can proceed independently.
2. **Is `nav2_bringup` (and the rest of the Nav2 Galactic stack) installed?**
   `ros2 pkg prefix nav2_bringup`.
3. **Frame naming**: does the Galactic driver prefix TF frames with
   `<robot_name>/` the way the ROS 1 stack does (`locobot/base_footprint`,
   `locobot/odom`), or run everything unprefixed? `config/nav2_params.yaml`
   assumes the prefixed convention (rewritten at launch time via
   `nav2_common.launch.RewrittenYaml`); if wrong, edit the `<robot_name>`
   placeholders to bare frame names instead.
4. **Topic namespacing**: `uan_navigate.launch.py` assumes the lidar
   publishes under `/<robot_name>/scan` (matching the ROS 1 `amcl` remap)
   and relays it to the unnamespaced `/scan` Nav2 expects, plus relays
   Nav2's `cmd_vel` output to `/mobile_base/cmd_vel`. Confirm both topic
   names with `ros2 topic list` once bringup is up, and delete either relay
   if the real topic is already what Nav2/the robot expects.
5. **`config/nav2_params.yaml` is a generic starting configuration**, not a
   tuned port — the vendor's actual move_base costmap/planner yamls were
   never available to port (not copied into `reference/` even for ROS 1,
   per `changes.md` Step 3). Expect to tune `controller_server`/costmap
   values against real driving behavior, the same iteration the ROS 1
   project went through in Steps 9–11.
6. **rtabmap 3D flags** (`uan_slam_3d.launch.py`): confirmed to be the same
   core `rtabmap` parameter names as the ROS 1 version, since `rtabmap`
   itself is one C++ library shared by both ROS wrappers — but whether
   `xslocobot_nav.launch.py` still applies user args *before* its own
   hardcoded flags (the ROS 1 bug this file works around) is unverified for
   the Galactic branch.

## Building (on the robot, in its own ROS 2 workspace)

```bash
mkdir -p ~/uan_ros2_ws/src
cp -r uan_ws/src/uan_base_control_ros2 ~/uan_ros2_ws/src/
cd ~/uan_ros2_ws
source /opt/ros/galactic/setup.bash
colcon build --symlink-install
source install/setup.bash
```

## Driving the base (no vendor stack needed for this part)

```bash
ros2 run uan_base_control_ros2 velocity_publisher -x 0.1 -t 3
ros2 run uan_base_control_ros2 teleop_keyboard
```

Same topics, same limits as the ROS 1 version: `/mobile_base/cmd_vel`
(0.30 m/s / 1.00 rad/s caps), `/mobile_base/odom`.

## Emergency stop

```bash
ros2 topic pub -1 /mobile_base/cmd_vel geometry_msgs/msg/Twist '{}'
```

## SLAM / 3D SLAM / navigation / sim

```bash
ros2 launch uan_base_control_ros2 uan_slam.launch.py
ros2 launch uan_base_control_ros2 uan_slam_3d.launch.py map_name:=my_room_3d
ros2 launch uan_base_control_ros2 uan_navigate.launch.py
ros2 launch uan_base_control_ros2 uan_sim_navigate.launch.py map_file:=<path>/maps/hall.yaml
```

`maps/hall.yaml`/`my_room.yaml` here are plain copies of the ROS 1
package's exported maps — the `.yaml` format (`image`/`resolution`/`origin`/
`negate`/`occupied_thresh`/`free_thresh`) is identical between ROS 1
`map_server` and ROS 2 `nav2_map_server`, no conversion needed.
