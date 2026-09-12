#!/usr/bin/env python3
"""Fake diff-drive simulator for uan_sim_navigate.launch.

Integrates /cmd_vel (geometry_msgs/Twist) into a pose and broadcasts it as
the odom->base_footprint transform, so move_base's plan actually drives a
visible robot instead of a fixed one. No real physics/collision - it will
happily drive through mapped walls, since there's no real robot here to
stop it.
"""

import math

import rospy
import tf2_ros
from geometry_msgs.msg import Twist, TransformStamped


class FakeBaseSim:
    def __init__(self):
        self.odom_frame = rospy.get_param("~odom_frame", "locobot/odom")
        self.base_frame = rospy.get_param("~base_frame", "locobot/base_footprint")

        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0
        self.vx = 0.0
        self.vth = 0.0

        self.broadcaster = tf2_ros.TransformBroadcaster()
        rospy.Subscriber("cmd_vel", Twist, self._cmd_vel_cb)

        self.last_time = rospy.Time.now()
        rospy.Timer(rospy.Duration(0.05), self._update)

    def _cmd_vel_cb(self, msg):
        self.vx = msg.linear.x
        self.vth = msg.angular.z

    def _update(self, _event):
        now = rospy.Time.now()
        dt = (now - self.last_time).to_sec()
        self.last_time = now

        self.x += self.vx * math.cos(self.theta) * dt
        self.y += self.vx * math.sin(self.theta) * dt
        self.theta += self.vth * dt

        t = TransformStamped()
        t.header.stamp = now
        t.header.frame_id = self.odom_frame
        t.child_frame_id = self.base_frame
        t.transform.translation.x = self.x
        t.transform.translation.y = self.y
        t.transform.translation.z = 0.0
        t.transform.rotation.z = math.sin(self.theta / 2.0)
        t.transform.rotation.w = math.cos(self.theta / 2.0)
        self.broadcaster.sendTransform(t)


if __name__ == "__main__":
    rospy.init_node("fake_base_sim")
    FakeBaseSim()
    rospy.spin()
