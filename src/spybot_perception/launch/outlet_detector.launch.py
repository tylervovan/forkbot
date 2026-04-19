"""Launch: outlet_detector alone (assumes camera + inference server already running)."""
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription(
        [
            Node(
                package="spybot_perception",
                executable="outlet_detector",
                name="outlet_detector",
                output="screen",
            ),
        ]
    )
