cmake_minimum_required(VERSION 3.0.2)
project(uan_base_control)

find_package(catkin REQUIRED COMPONENTS
  rospy
  geometry_msgs
  nav_msgs
)

catkin_package()

catkin_install_python(PROGRAMS
  scripts/velocity_publisher.py
  scripts/teleop_keyboard.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

install(DIRECTORY launch config
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
)
