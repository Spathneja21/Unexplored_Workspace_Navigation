# Change Log — Unexplored Workspace Navigation

Running log of every step taken on this project. Newest entries at the bottom.

---

## Step 1 — Project scaffold + base velocity control (2026-09-07)

### Goal
Set up the project folder as the single home for all UAN work, and get velocity
commands flowing to the LoCoBot base.

### Platform facts established
Discovered by inspecting the NUC, recorded here so later steps don't re-derive them:

| Item | Value |
| --- | --- |
| ROS 1 distro | `noetic` (`ROS_VERSION=1`, Python 3) |
| ROS 2 distro | `galactic` (used only by the bridge) |
| Robot model | `locobot_wx200` (most-used model in shell history) |
| Base type | `create3` (`INTERBOTIX_XSLOCOBOT_BASE_TYPE=create3` in `~/.bashrc:130,152`) |
| System workspace | `/home/locobot/interbotix_ws` (already built, sourced from `.bashrc`) |
| Bridge workspaces | `/home/locobot/ros1_bridge_ws`, `create3_ros1_ws`, `create3_ros2_ws` |
| `ROS_IP` | `192.168.186.3` |
| Arm serial port | `/dev/ttyDXL` → `ttyUSB0` (present) |
| Lidar | `/dev/rplidar` **not present** — RPLidar was not plugged in at setup time |
| **cmd_vel topic** | **`/mobile_base/cmd_vel`** (global, not under `/locobot`) |
| Odom topic | `/mobile_base/odom` |

The cmd_vel topic name was confirmed from two places in the vendor repo:
`interbotix_xslocobot_control/config/bridge.yaml:12` (the ROS1↔ROS2 bridge
topic list) and `interbotix_xslocobot_nav/launch/xslocobot_nav.launch:19`
(`move_base_cmd_vel_topic` for `base_type == create3`).

### Files created

```
Unexplored_Workspace_Navigation/
├── changes.md                          # this file
├── README.md
├── reference/                          # copied from interbotix_ros_rovers, READ-ONLY
│   ├── move_base.py
│   └── interbotix_xslocobot_control/
│       ├── CMakeLists.txt
│       ├── package.xml
│       ├── config/{bridge,locobot_base,locobot_px100,locobot_wx200,
│       │           locobot_wx250s,modes_all,modes_base,tf_rebroadcaster}.yaml
│       ├── launch/{xslocobot_control,xslocobot_python}.launch
│       └── scripts/startup_bridge.sh
└── uan_ws/                             # our catkin workspace
    └── src/uan_base_control/
        ├── CMakeLists.txt
        ├── package.xml
        ├── config/base_params.yaml
        ├── launch/uan_bringup.launch
        └── scripts/
            ├── velocity_publisher.py
            └── teleop_keyboard.py
```

### Design decision: reference copy, not a rebuild

The vendor packages were copied into `reference/` **for reading only**, and
deliberately **not** placed into `uan_ws/src/`.

**Why:** `interbotix_xslocobot_control` is already built and on the
`ROS_PACKAGE_PATH` from `/home/locobot/interbotix_ws`. A second copy of the same
package name in our workspace would make `rospack find` ambiguous and could
silently launch the wrong one. Rebuilding it here would also drag in the whole
dependency chain (`interbotix_xs_sdk`, `interbotix_xslocobot_descriptions` and
its meshes, `interbotix_tf_tools`, `realsense2_camera`, `rplidar_ros`).

Instead, `uan_bringup.launch` `<include>`s the system-installed launch file via
`$(find interbotix_xslocobot_control)`. Our workspace overlays the system one,
so both resolve. The `reference/` copy exists so the vendor args and configs can
be read without leaving the project folder.

### What each new file does

- **`launch/uan_bringup.launch`** — single entry point for the project. Wraps
  `interbotix_xslocobot_control/xslocobot_control.launch` with
  `use_base:=true` and defaults `robot_model:=locobot_wx200`. Exposes
  `use_lidar` / `use_camera` / `use_rviz` for later steps (both default `false`
  for now since the lidar is unplugged).
- **`scripts/velocity_publisher.py`** — drives a constant Twist for a fixed
  duration then stops. Republishes at 20 Hz because the Create3 watchdogs
  `cmd_vel` and halts on stale commands. Sleeps 0.5 s before the first publish
  (the bridge drops messages sent before the connection registers), clamps to
  0.30 m/s and 1.00 rad/s, and sends a zero Twist on both normal exit and
  `rospy.on_shutdown` so Ctrl-C stops the robot.
- **`scripts/teleop_keyboard.py`** — WASD teleop, velocity held between
  keypresses and republished at 20 Hz. `x`/space stops, `q` quits with a zero
  Twist.
- **`config/base_params.yaml`** — topic names and velocity limits in one place.

### Verification performed
- `catkin_make` in `uan_ws` — succeeded, both scripts installed as devel-space wrappers.
- `rospack find uan_base_control` — resolves to our workspace.
- `roslaunch --nodes uan_base_control uan_bringup.launch` — lists
  `/locobot/xs_sdk`, `/locobot/robot_state_publisher`,
  `/locobot/joint_state_publisher`, `/parameter_bridge`, `/tf_rebroadcaster`.
  The last two confirm the Create3 branch of the vendor launch is being taken.

**Not yet verified on hardware** — the robot was not driven as part of this
step. `roscore` was not running during setup (`rostopic list` returned
"Unable to communicate with master"), so the actual motion test is the first
thing to do in Step 2.

### Known caveats for the next step
- The Create3 refuses to drive while docked, and its hazard/cliff reflexes will
  override `cmd_vel`. Check `/mobile_base/hazard_detection` if the base ignores
  commands.
- The lidar is not connected; `use_lidar:=true` will fail until `/dev/rplidar`
  exists. Needed before any actual exploration work.
