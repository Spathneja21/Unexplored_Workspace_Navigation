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

---

## Step 2 — Proper `.gitignore` (2026-09-07)

### Goal
Keep build artifacts and run outputs out of the GitHub repo.

### Starting state
Step 1 left a 6-line placeholder `.gitignore`. The repo had since been
committed, and that commit included `uan_ws/.catkin_workspace` — a file
`catkin_make` generates, which should never have been tracked.

### Changes
1. Rewrote `.gitignore` into a commented, ROS-aware ruleset grouped by
   category (build artifacts, ROS runtime, maps, recorded data, Python,
   editors, OS, local settings).
2. `git rm --cached uan_ws/.catkin_workspace` — stops tracking it without
   deleting the local file. **This is a deletion in the next commit**; that is
   intended, the file regenerates on every `catkin_make`.

### What is now ignored, and why

| Pattern | Reason |
| --- | --- |
| `build/`, `devel/`, `install/`, `logs/` | Regenerated by `catkin_make`. `devel/` bakes in absolute paths to this NUC and would break on any other machine. |
| `.catkin_workspace`, `.catkin_tools/` | catkin bookkeeping. |
| `uan_ws/src/CMakeLists.txt` | Symlink catkin drops in pointing at `/opt/ros/noetic/share/catkin/cmake/toplevel.cmake`. |
| `*.bag`, `.ros/`, `*.log` | Rosbags get large fast, and there are already several loose bags in `~` from earlier work. |
| `maps/`, `*.pgm`, `*.pbstream` | SLAM output. The `.pgm` is the occupancy image; its sidecar `.yaml` just points at it. Both are run artifacts. |
| `data/`, `results/`, `*.csv`, `*.npy` | Odometry / cmd_vel traces. Matches the existing habit of dumping `odom.csv`, `asd_cmdvel.csv` etc. |
| `__pycache__/`, `*.py[cod]`, `venv/` | Standard Python noise. |
| `.vscode/`, `.idea/`, `*.swp`, `*~` | Editor state. |

Note `*.csv` and `*.bag` are blanket rules. To commit a specific small
reference bag or dataset anyway: `git add -f <path>`. This is called out in a
comment at the top of the file.

### Verification performed
- `git ls-files | git check-ignore --stdin` → empty. No currently-tracked file
  is caught by the new rules, so nothing silently disappears from the repo.
- Spot-checked that `uan_ws/build/CMakeCache.txt`, `uan_ws/devel/setup.bash`,
  `uan_ws/src/CMakeLists.txt`, `uan_ws/.catkin_workspace`, `test.bag`,
  `odom.csv`, `maps/map.pgm` and `.vscode/settings.json` all match.
- Spot-checked that `base_params.yaml`, `uan_bringup.launch`,
  `velocity_publisher.py` and `changes.md` all stay visible — confirming the
  `*.pgm`/`maps/` rules don't swallow package config, and `logs/`/`*.log`
  don't swallow this log file.

### Still open from Step 1
Hardware motion test has **not** been run yet. Lidar still unplugged.

---

## Step 3 — SLAM mapping via lidar (2026-09-07)

### Goal
Use the now-connected RPLidar to build a map of a room.

### Platform facts established
Discovered by inspecting the NUC over SSH:

| Item | Value |
| --- | --- |
| Lidar | now connected, `/dev/rplidar -> ttyUSB1` |
| SLAM package | `interbotix_xslocobot_nav` at `interbotix_ros_rovers/interbotix_ros_xslocobots/interbotix_xslocobot_nav` (note: `xslocobots` plural, not `xslocobot` as guessed from the Step 1 vendor path for the control package) |
| SLAM launch file | `xslocobot_nav.launch` — there is no separate slam-only file |
| SLAM engine | **rtabmap** (RGBD camera + lidar fused), not gmapping/slam_toolbox |
| Occupancy grid topic | `/<robot_name>/rtabmap/grid_map` (what `move_base`'s `map` topic is remapped to) |

### Design decision: one wrapper launch, reuse rtabmap as-is
`xslocobot_nav.launch` hardcodes `use_camera:=true` — rtabmap needs the RGBD
camera alongside the lidar scan, it isn't a lidar-only stack. Mapping vs.
localization is just the `localization` arg (default `false` = build a new
map), so no separate "SLAM mode" file was needed — `uan_slam.launch` just
sets `use_lidar:=true` and passes through.

### Files created
- **`uan_ws/src/uan_base_control/launch/uan_slam.launch`** — wraps
  `interbotix_xslocobot_nav/xslocobot_nav.launch` with `use_lidar:=true`.
  Exposes `robot_model`, `robot_name`, `use_rviz`.
- **`reference/interbotix_xslocobot_nav/launch/xslocobot_nav.launch`** —
  read-only copy of the vendor launch file, same rationale as the
  `interbotix_xslocobot_control` copy from Step 1. The referenced costmap/
  planner config YAMLs were **not** copied — nothing in our own launch reads
  them, so there'd be nothing to check them against; add if that changes.
- **README.md** — new "Mapping (SLAM)" section: how to launch, drive around
  to cover the room, and save the map with `map_server`'s `map_saver`
  against the `rtabmap/grid_map` topic.

### Not yet verified on hardware
This step was written from the laptop copy of the repo (not over the SSH
session) and has **not been launched yet**. Push to GitHub, pull onto the
NUC, then verify:
- `roslaunch uan_base_control uan_slam.launch` comes up clean (camera +
  lidar + rtabmap + move_base, no missing-package errors).
- `/locobot/scan` is actually being published (confirms rplidar node started
  under `xslocobot_control.launch`'s `use_lidar` branch).
- Driving around visibly grows the map in rviz.
- `map_saver` against `/locobot/rtabmap/grid_map` produces a sane `.pgm`.
