#!/usr/bin/env python3
"""Publish a constant Twist to the LoCoBot base for a fixed duration, then stop.

The Create3 base watchdogs cmd_vel, so the command has to be republished
continuously rather than latched once.

Examples:
    rosrun uan_base_control velocity_publisher.py -x 0.1 -t 3
    rosrun uan_base_control velocity_publisher.py -z 0.5 -t 2
    rosrun uan_base_control velocity_publisher.py -x 0.15 -z 0.3 -t 5
"""

import argparse
import sys

import rospy
from geometry_msgs.msg import Twist

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
    # strip roslaunch's remapping args
    return parser.parse_args(rospy.myargv(argv)[1:])


def clamp(value, limit, name):
    if abs(value) > limit:
        clamped = limit if value > 0 else -limit
        rospy.logwarn("%s %.3f exceeds limit %.3f, clamping to %.3f",
                      name, value, limit, clamped)
        return clamped
    return value


def main():
    args = parse_args(sys.argv)
    rospy.init_node("uan_velocity_publisher", anonymous=True)

    linear = clamp(args.linear, MAX_LINEAR, "linear x")
    angular = clamp(args.angular, MAX_ANGULAR, "angular z")

    pub = rospy.Publisher(args.topic, Twist, queue_size=1)
    stop = Twist()

    def send_stop():
        for _ in range(5):
            pub.publish(stop)
            rospy.sleep(0.05)

    rospy.on_shutdown(send_stop)

    # Give the bridge a moment to register the connection, otherwise the first
    # few messages are dropped and the base never moves.
    rospy.sleep(0.5)

    cmd = Twist()
    cmd.linear.x = linear
    cmd.angular.z = angular

    rospy.loginfo("driving x=%.3f m/s, z=%.3f rad/s for %.2f s on %s",
                  linear, angular, args.duration, args.topic)

    rate = rospy.Rate(args.rate)
    end_time = rospy.Time.now() + rospy.Duration(args.duration)
    while not rospy.is_shutdown() and rospy.Time.now() < end_time:
        pub.publish(cmd)
        rate.sleep()

    send_stop()
    rospy.loginfo("stopped")


if __name__ == "__main__":
    try:
        main()
    except rospy.ROSInterruptException:
        pass
