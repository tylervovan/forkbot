"""Launch: drive_bridge node with drive_bridge.yaml params."""
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    config = Path(get_package_share_directory("spybot_control")) / "config" / "drive_bridge.yaml"
    return LaunchDescription(
        [
            Node(
                package="spybot_control",
                executable="drive_bridge",
                name="drive_bridge",
                output="screen",
                parameters=[str(config)],
            ),
        ]
    )
