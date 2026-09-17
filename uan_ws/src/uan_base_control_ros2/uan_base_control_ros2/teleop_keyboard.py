#!/usr/bin/env python3
"""Keyboard teleop for the LoCoBot Create3 base (ROS 2 Galactic port).

    w/s : forward / backward
    a/d : rotate left / right
    x or space : stop
    q : quit

Velocity is held until changed, and republished at a fixed rate so the base
watchdog stays satisfied. Releasing the key does not stop the robot - press x.

Behavior matches the ROS 1 uan_base_control/teleop_keyboard.py exactly;
only the ROS API (rclpy node/params instead of rospy) changed.
"""

import select
import sys
import termios
import time
import tty

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node

DEFAULT_TOPIC = "/mobile_base/cmd_vel"
MAX_LINEAR = 0.30
MAX_ANGULAR = 1.00
LINEAR_STEP = 0.05
ANGULAR_STEP = 0.20

BINDINGS = {
    "w": (LINEAR_STEP, 0.0),
    "s": (-LINEAR_STEP, 0.0),
    "a": (0.0, ANGULAR_STEP),
    "d": (0.0, -ANGULAR_STEP),
}


def get_key(settings, timeout=0.1):
    tty.setraw(sys.stdin.fileno())
    ready, _, _ = select.select([sys.stdin], [], [], timeout)
    key = sys.stdin.read(1) if ready else ""
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
    return key


def clamp(value, limit):
    return max(-limit, min(limit, value))


def main(argv=None):
    settings = termios.tcgetattr(sys.stdin)
    rclpy.init(args=argv)
    node = Node("uan_teleop_keyboard")

    node.declare_parameter("cmd_vel_topic", DEFAULT_TOPIC)
    node.declare_parameter("publish_rate", 20.0)
    topic = node.get_parameter("cmd_vel_topic").value
    rate_hz = node.get_parameter("publish_rate").value
    pub = node.create_publisher(Twist, topic, 1)

    linear = 0.0
    angular = 0.0
    period = 1.0 / rate_hz

    print(__doc__)
    print("publishing to %s\n" % topic)

    try:
        while rclpy.ok():
            key = get_key(settings)
            if key in BINDINGS:
                dl, da = BINDINGS[key]
                linear = clamp(linear + dl, MAX_LINEAR)
                angular = clamp(angular + da, MAX_ANGULAR)
                print("x=%+.2f m/s  z=%+.2f rad/s   \r" % (linear, angular), end="")
            elif key in ("x", " "):
                linear = angular = 0.0
                print("x=%+.2f m/s  z=%+.2f rad/s   \r" % (linear, angular), end="")
            elif key == "q" or key == "\x03":  # q or Ctrl-C
                break

            cmd = Twist()
            cmd.linear.x = linear
            cmd.angular.z = angular
            pub.publish(cmd)
            time.sleep(period)
    finally:
        for _ in range(5):
            pub.publish(Twist())
            time.sleep(0.05)
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
        print("\nstopped")
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
