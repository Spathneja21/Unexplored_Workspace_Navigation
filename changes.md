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

---

## Step 4 — First hardware test: robot did not move (2026-09-07)

### Symptom
`rosrun uan_base_control velocity_publisher.py -z 0.5 -t 5` ran cleanly and
logged `driving ... z=0.500 rad/s` then `stopped`, but the base never turned.

### Diagnosis: the Create3's ROS 2 stack is not on the DDS network

**The publishing script is not at fault.** The `ros1_bridge` advertises every
`/mobile_base/*` topic on *both* the ROS 1 and ROS 2 sides, so `rostopic list`
looks completely healthy while nothing is behind the topics.

Evidence gathered:

| Check | Result |
| --- | --- |
| `rostopic info /mobile_base/cmd_vel` | Publisher **and** subscriber are both `/ros_bridge` — the bridge is talking to itself |
| `rostopic echo -n 1 /mobile_base/odom` | Timed out, **zero** messages in 8 s — the base is silent, not merely refusing to drive |
| `ros2 node list --no-daemon` | Only `/ros_bridge`. The Create3's own node is **absent** |
| `ros2 topic info /mobile_base/odom --verbose` | Sole publisher is `ros_bridge` |

The odom result is the important one: it rules out the Step 1 caveats
(docked / hazard reflexes / kidnap). Those would block motion while odom kept
flowing. Nothing is flowing, so the base is not connected at all.

### Ruled out
- **Network** — `192.168.186.2` pings, 0% loss. NUC is `192.168.186.3/24` on `eno1`.
- **ROS Domain ID** — `0` on both sides (Create3 `/ros-config` shows `value="0"`).
- **RMW** — `rmw_fastrtps_cpp` on both (`~/.bashrc:129,151`; Create3 has it `selected`).
- **Namespace** — Create3 set to `/mobile_base`, matching `bridge.yaml`.
- **RMW profile override** — the Create3's override textarea is empty, so its
  default XML profile is in use.
- **Stale `ros2` daemon cache** — re-queried with `--no-daemon`, same result.

Create3 firmware: **G.5.3**, ROS 2 Galactic. Config genuinely matches on both
ends, which points at the robot's application not running rather than a
misconfiguration.

### Suspicious finding (not yet confirmed as the cause)
On the Create3 `/ros-config` page, the Fast DDS discovery server address field
contains a stale `10.36.209.237:11811` — an address on a **different subnet**,
left over from another network. The placeholder shows the correct
`192.168.186.3:11811`.

The `fast_discovery_server_enabled` checkbox renders **without** a `checked`
attribute, so it reads as disabled and the stale value should be inert. This
could not be fully confirmed from markup alone and **needs visual confirmation
in a browser**. If that box is actually ticked, it alone explains the whole
failure — the base would be trying to reach a discovery server on an
unreachable subnet.

### Recommended fix sequence (given to user, not yet applied)
1. **Wake the robot.** The Create3 sleeps when docked and idle and its ROS 2
   stack goes down with it. The web server runs on a separate processor and
   stays up regardless — which is why the config pages responded normally
   throughout this diagnosis. Press a button on the base or undock it.
2. If still absent: `http://192.168.186.2` → **Application → Restart
   application**, wait ~30 s. **Reboot robot** as fallback.
3. Clear the stale discovery-server address and confirm the checkbox is
   unchecked; Save, then restart the application.

Nothing was changed on the robot — all fixes are physical/web-UI actions for
the user to perform.

### Reusable lesson
`rostopic list` is **not** a liveness check on this platform; the bridge
advertises topics whether or not the base is connected. Use
`rostopic hz /mobile_base/odom` as the pre-flight check before any drive
command. If odom isn't flowing, no `cmd_vel` will ever work.

### Still open
Hardware motion test still unverified. Lidar still unplugged.

---

## Step 5 — Remote operation over SSH (2026-09-07)

### Goal
Drive the whole project from a laptop over SSH instead of a monitor plugged
into the NUC.

### NUC state surveyed (nothing changed yet)

| Item | Value |
| --- | --- |
| SSH server | installed, `enabled` + `active`, listening `0.0.0.0:22` and `[::]:22` |
| SSH user | `locobot` |
| Hostname | `locobot`; avahi-daemon active, `locobot.local` resolves |
| `X11Forwarding` | `yes` in `/etc/ssh/sshd_config` (RViz over SSH will work) |
| Password auth | default (enabled); `~/.ssh/authorized_keys` does **not** exist yet |
| `tmux` / `screen` / `byobu` | **none installed**; tmux candidate `3.0a-2ubuntu0.4` |
| Internet | reachable (apt install will work) |

### Key finding: the WiFi IP is not stable
`wlp0s20f3` changed address **within this session**:

- During Step 4 diagnosis: `172.31.249.247/22`
- During Step 5 survey: `10.166.124.85/24`, SSID **"Samsung S23 FE"** (a phone hotspot)

So the NUC hops networks and takes a new DHCP lease each time. Consequences:
- Any SSH command using a hard-coded WiFi IP will break without warning.
- Prefer `locobot.local` (mDNS via avahi, verified working) over a raw IP.
- For reliable work the NUC and laptop should sit on one stable network, ideally
  a real router rather than a phone hotspot.

`eno1` at `192.168.186.3/24` is the **wired link to the Create3 base** and is a
separate private subnet — it is not the way in from the laptop, and must not be
reconfigured.

### Design decision: run ROS entirely on the NUC
The laptop is used as a **terminal only**. No ROS install, no `ROS_MASTER_URI`
edits, no multi-machine ROS setup on the laptop.

**Why:** `ROS_IP` is pinned to `192.168.186.3` (the Create3 subnet) and
`ROS_MASTER_URI` to `http://localhost:11311`. Both are correct for
NUC-local operation and already work. Making the laptop a ROS node would mean
rewriting both on every network change, and the laptop cannot reach the
`192.168.186.x` base subnet anyway. Keeping ROS wholly on the NUC sidesteps all
of it.

### Safety note recorded for the operator
`tmux` sessions survive an SSH disconnect — that is exactly why bringup belongs
in one, and exactly why **teleop does not**:

- `teleop_keyboard.py` holds its last velocity and republishes at 20 Hz. Inside
  tmux, an SSH drop leaves it running and **the robot keeps driving**.
- Run outside tmux, an SSH drop sends SIGHUP, Python exits without running the
  `finally` block, `cmd_vel` goes stale, and the **Create3 watchdog halts the
  base**. This is the safe failure mode.

`velocity_publisher.py` is inherently safer either way since it is bounded by
its `-t` duration.

**Corollary learned the hard way (Step 4 → Step 5 transition):** the same
SIGHUP risk hit `git` itself — an SSH drop mid-`commit`/`pull` (no tmux
installed yet) truncated several working-tree files to 0 bytes and corrupted
local git objects. Reinforces #1 below: install tmux and run *any* foreground
command that matters (not just teleop) inside it.

### Actions required of the user (not applied — need sudo/laptop access)
1. `sudo apt install -y tmux` on the NUC.
2. Generate an SSH key on the laptop and `ssh-copy-id locobot@locobot.local`.
3. Put both machines on the same stable network.

### Still open
Hardware motion test still unverified (Step 4 Create3 discovery issue is
unresolved). Lidar now connected (Step 3); SLAM launch (`uan_slam.launch`)
not yet run on hardware. tmux not yet installed — see corollary above.

---

## Step 6 — Run rviz on the laptop instead of over X11 (2026-09-08)

### Goal
`uan_slam.launch` was run successfully with the lidar producing a real map,
but viewing it via `rosrun rviz rviz` over SSH `-X` forwarding was too slow
to be usable — X11 forwarding renders remotely and streams raw pixels over
WiFi, so a laptop's GPU is never actually used.

### Design decision: native ROS multi-machine rviz, not remote desktop
ROS already supports running a node on a separate machine against a remote
`roscore` via `ROS_MASTER_URI`/`ROS_IP` — this is the built-in mechanism for
exactly this, not a new tool or extra infra (no VNC, no streaming). rviz then
renders locally on the laptop's own GPU and only topic data (map + scan,
both small) crosses the network.

**Why not make the laptop a full ROS participant generally?** Step 5 already
decided against that for the whole stack, because `ROS_IP` would need
updating on every WiFi hop. That reasoning still holds for `cmd_vel`/bringup.
But running rviz alone as a temporary remote subscriber doesn't have that
cost — if the laptop's IP changes, only rviz needs restarting, not the whole
SLAM/base stack.

### Requirement discovered: `ROS_IP` must match the reachable interface
Confirmed reachability first (bidirectional `ping` between laptop and
`locobot.local` — both worked, same `172.27.244.x` subnet). But
`rostopic list` from the laptop still failed with "Unable to communicate
with master", and `curl http://locobot.local:11311/` returned **connection
refused** (not a timeout) — meaning nothing was listening on that port on
the WiFi interface at all.

Root cause: the NUC's `.bashrc` pins `ROS_IP=192.168.186.3` (the **wired**
Create3 subnet, per Step 1). `roscore`'s XML-RPC/TCPROS servers bind to
whatever `ROS_IP` says at process start, so it was only listening on the
wired interface — invisible to anything on WiFi, laptop included.

**Fix applied — session-scoped, not a `.bashrc` change:** relaunched with
`ROS_IP` overridden just for that process:

```bash
ROS_IP=172.27.244.85 roslaunch uan_base_control uan_slam.launch
```

This keeps the `.bashrc` default (needed for normal Create3/base operation)
untouched, at the cost of needing to redo this override — and re-export
`ROS_IP` on the laptop side too — any time the NUC's WiFi IP changes
(already a known instability from Step 5).

### Laptop-side setup
ROS Noetic (including `ros-noetic-rviz`) was already installed on the
laptop from an earlier unrelated setup — nothing new to install.

```bash
source /opt/ros/noetic/setup.bash
export ROS_MASTER_URI=http://locobot.local:11311
export ROS_IP=<laptop's LAN IP, e.g. 172.27.244.134>
rostopic list          # sanity check — should list /locobot/scan, /locobot/rtabmap/grid_map, etc.
rosrun rviz rviz -f map
```
Displays added: `Map` on `/locobot/rtabmap/grid_map`, `LaserScan` on
`/locobot/scan`.

### Verification performed
- `rostopic list` from the laptop returned the full NUC topic list after the
  `ROS_IP` override.
- rviz on the laptop rendered the live map smoothly, confirming the
  bottleneck was X11 forwarding, not rviz/rtabmap performance itself.

### Still open
Same as Step 5 (Create3 discovery issue, tmux). Additionally: this rviz
setup is per-session — both the NUC's launch-time `ROS_IP` override and the
laptop's exported env vars need to be redone if either machine's IP changes.

---

## Step 7 — Navigate a saved map (2026-09-10)

### Goal
After successfully building a map with `uan_slam.launch` and saving it
(`map_saver` against `/locobot/rtabmap/grid_map` → `my_room.pgm`/`.yaml`),
drive the robot around that map by clicking goals in rviz instead of
teleop.

### Design decision: reuse rtabmap's own database, not map_server + amcl
The obvious ROS-standard approach is `map_server` (republish the saved
`.pgm`) + `amcl` (localize against it) + `move_base`. Went with something
smaller instead: `xslocobot_nav.launch` (already wrapped by
`uan_slam.launch`) has a `localization` arg. Setting it `true` switches
rtabmap from *building* the map to *localizing* against the same
`~/.ros/rtabmap.db` the `.pgm` was exported from, and `move_base` is
already wired into that same launch.

**Why:** the `.pgm`/`.yaml` pair is just a flattened snapshot export — the
database is rtabmap's actual source of truth. Standing up `map_server` +
`amcl` would mean a second, independent localization stack duplicating what
rtabmap already does, for no benefit unless the database itself were lost
and only the exported map remained.

### Files created
- **`uan_ws/src/uan_base_control/launch/uan_localize.launch`** — same wrap
  as `uan_slam.launch`, with `localization:=true` added. Requires
  `uan_slam.launch` to have been run at least once already (needs a
  populated `~/.ros/rtabmap.db`).
- **README.md** — new "Traversing a saved map" section: launch + rviz Map/
  LaserScan displays + using the **2D Nav Goal** toolbar button.

### Not yet verified on hardware
Written from the laptop copy, not tested on the robot yet. Verify:
- `uan_localize.launch` comes up without rebuilding the map (mapping should
  stay frozen, not keep extending).
- A rviz "2D Nav Goal" click actually results in `move_base` driving the
  base via `/mobile_base/cmd_vel`.
