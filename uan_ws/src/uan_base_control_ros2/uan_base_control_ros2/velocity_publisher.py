#!/usr/bin/env python3
"""Publish a constant Twist to the LoCoBot base for a fixed duration, then stop.

ROS 2 Galactic port of the ROS 1 uan_base_control/velocity_publisher.py.
On Galactic this talks to the Create3's *native* ROS 2 topics directly -
no ros1_bridge involved - so the 0.5 s startup sleep the ROS 1 version
needed (to let the bridge register the connection) is dropped here; a
short sleep is kept only so late subscriber discovery doesn't drop the
first few messages, which is a normal DDS discovery latency, not a
bridge-specific issue.

The Create3 base watchdogs cmd_vel, so the command has to be republished
continuously rather than published once.

Examples:
    ros2 run uan_base_control_ros2 velocity_publisher -x 0.1 -t 3
    ros2 run uan_base_control_ros2 velocity_publisher -z 0.5 -t 2
    ros2 run uan_base_control_ros2 velocity_publisher -x 0.15 -z 0.3 -t 5
"""

import argparse
import sys
import time

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node

DEFAULT_TOPIC = "/mobile_base/cmd_vel"
MAX_LINEAR = 0.30
MAX_ANGULAR = 1.00


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-x", "--linear", type=float, default=0.0,
                        help="linear x velocity in m/s")
    parser.add_argument("-z", "--angular", type=float, default=0.0,
                        help="angular z velocity in rad/s")
    parser.add_argument("-t", "--duration", type=float, default=2.0,
                        help="how long to drive, in seconds")
    parser.add_argument("-r", "--rate", type=float, default=20.0,
                        help="publish rate in Hz")
    parser.add_argument("--topic", default=DEFAULT_TOPIC,
                        help="cmd_vel topic to publish on")
    # strip ROS 2's --ros-args remapping/parameter block, same purpose as
    # rospy.myargv() did for roslaunch's remapping args in the ROS 1 version
    return parser.parse_known_args(argv[1:])[0]


def clamp(node, value, limit, name):
    if abs(value) > limit:
        clamped = limit if value > 0 else -limit
        node.get_logger().warn(
            "%s %.3f exceeds limit %.3f, clamping to %.3f" % (name, value, limit, clamped))
        return clamped
    return value


def main(argv=None):
    argv = argv if argv is not None else sys.argv
    args = parse_args(argv)

    rclpy.init(args=argv)
    node = Node("uan_velocity_publisher")

    linear = clamp(node, args.linear, MAX_LINEAR, "linear x")
    angular = clamp(node, args.angular, MAX_ANGULAR, "angular z")

    pub = node.create_publisher(Twist, args.topic, 1)
    stop = Twist()

    def send_stop():
        for _ in range(5):
            pub.publish(stop)
            time.sleep(0.05)

    try:
        # Give discovery a moment, same reasoning as the ROS 1 version's
        # pre-publish sleep, minus the bridge-specific cause.
        time.sleep(0.5)

        cmd = Twist()
        cmd.linear.x = linear
        cmd.angular.z = angular

        node.get_logger().info(
            "driving x=%.3f m/s, z=%.3f rad/s for %.2f s on %s" %
            (linear, angular, args.duration, args.topic))

        period = 1.0 / args.rate
        end_time = time.monotonic() + args.duration
        while rclpy.ok() and time.monotonic() < end_time:
            pub.publish(cmd)
            time.sleep(period)

        send_stop()
        node.get_logger().info("stopped")
    except KeyboardInterrupt:
        send_stop()
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
