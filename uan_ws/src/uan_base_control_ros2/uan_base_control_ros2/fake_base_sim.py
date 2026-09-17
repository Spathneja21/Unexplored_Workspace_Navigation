#!/usr/bin/env python3
"""Fake diff-drive simulator for uan_sim_navigate.launch.py (ROS 2 port).

Integrates /cmd_vel (geometry_msgs/Twist) into a pose and broadcasts it as
the odom->base_footprint transform, so Nav2's plan actually drives a
visible robot instead of a fixed one. No real physics/collision - it will
happily drive through mapped walls, since there's no real robot here to
stop it. Same behavior as the ROS 1 uan_base_control/fake_base_sim.py.
"""

import math

import rclpy
import tf2_ros
from geometry_msgs.msg import Twist, TransformStamped
from rclpy.node import Node


class FakeBaseSim(Node):
    def __init__(self):
        super().__init__("fake_base_sim")

        self.declare_parameter("odom_frame", "locobot/odom")
        self.declare_parameter("base_frame", "locobot/base_footprint")
        self.odom_frame = self.get_parameter("odom_frame").value
        self.base_frame = self.get_parameter("base_frame").value

        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0
        self.vx = 0.0
        self.vth = 0.0

        self.broadcaster = tf2_ros.TransformBroadcaster(self)
        self.create_subscription(Twist, "cmd_vel", self._cmd_vel_cb, 10)

        self.last_time = self.get_clock().now()
        self.create_timer(0.05, self._update)

    def _cmd_vel_cb(self, msg):
        self.vx = msg.linear.x
        self.vth = msg.angular.z

    def _update(self):
        now = self.get_clock().now()
        dt = (now - self.last_time).nanoseconds / 1e9
        self.last_time = now

        self.x += self.vx * math.cos(self.theta) * dt
        self.y += self.vx * math.sin(self.theta) * dt
        self.theta += self.vth * dt

        t = TransformStamped()
        t.header.stamp = now.to_msg()
        t.header.frame_id = self.odom_frame
        t.child_frame_id = self.base_frame
        t.transform.translation.x = self.x
        t.transform.translation.y = self.y
        t.transform.translation.z = 0.0
        t.transform.rotation.z = math.sin(self.theta / 2.0)
        t.transform.rotation.w = math.cos(self.theta / 2.0)
        self.broadcaster.sendTransform(t)


def main(args=None):
    rclpy.init(args=args)
    node = FakeBaseSim()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
