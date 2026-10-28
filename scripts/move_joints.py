import math
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import Float64

# Set these inside the joint limits from example_robot.urdf.xacro
SLIDER_MIN, SLIDER_MAX = 0.0, 0.1   # metres
ARM_MIN, ARM_MAX = 0.0, 0.5         # radians

# Seconds for one full back-and-forth cycle
SLIDER_PERIOD = 6.0
ARM_PERIOD = 4.0

DT = 0.05  # publish every 50 ms


class JointMover(Node):
    def __init__(self):
        super().__init__('joint_mover')
        self.slider_pub = self.create_publisher(Float64, '/slider_joint/cmd_pos', 10)
        self.arm_pub = self.create_publisher(Float64, '/arm_joint/cmd_pos', 10)
        self.t = 0.0
        self.create_timer(DT, self.tick)

    def target(self, low, high, period):
        # Smooth cosine sweep: starts at low, reaches high at half the period
        fraction = 0.5 * (1.0 - math.cos(2.0 * math.pi * self.t / period))
        return low + (high - low) * fraction

    def tick(self):
        slider = Float64()
        slider.data = self.target(SLIDER_MIN, SLIDER_MAX, SLIDER_PERIOD)
        self.slider_pub.publish(slider)

        arm = Float64()
        arm.data = self.target(ARM_MIN, ARM_MAX, ARM_PERIOD)
        self.arm_pub.publish(arm)

        self.t += DT


def main():
    rclpy.init()
    node = JointMover()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    node.destroy_node()
    if rclpy.ok():
        rclpy.shutdown()


if __name__ == '__main__':
    main()
