#!/usr/bin/env python3
"""Keyboard teleop for the LoCoBot Create3 base.

    w/s : forward / backward
    a/d : rotate left / right
    x or space : stop
    q : quit

Velocity is held until changed, and republished at a fixed rate so the base
watchdog stays satisfied. Releasing the key does not stop the robot - press x.
"""

import select
import sys
import termios
import tty

import rospy
from geometry_msgs.msg import Twist

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


def main():
    settings = termios.tcgetattr(sys.stdin)
    rospy.init_node("uan_teleop_keyboard")

    topic = rospy.get_param("~cmd_vel_topic", DEFAULT_TOPIC)
    rate_hz = rospy.get_param("~publish_rate", 20.0)
    pub = rospy.Publisher(topic, Twist, queue_size=1)

    linear = 0.0
    angular = 0.0
    rate = rospy.Rate(rate_hz)

    print(__doc__)
    print("publishing to %s\n" % topic)

    try:
        while not rospy.is_shutdown():
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
            rate.sleep()
    finally:
        for _ in range(5):
            pub.publish(Twist())
            rospy.sleep(0.05)
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
        print("\nstopped")


if __name__ == "__main__":
    try:
        main()
    except rospy.ROSInterruptException:
        pass
