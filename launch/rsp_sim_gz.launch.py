import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
# DeclareLaunchArgument defines an argument that can be set on the command line
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
# LaunchConfiguration reads an argument's value; PathJoinSubstitution joins path
# pieces once that value is known (it is not known yet when this file is parsed)
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node


def generate_launch_description():
    # Install locations of this package and of ros_gz_sim
    pkg_path = get_package_share_directory('urdf_example')
    ros_gz_sim = get_package_share_directory('ros_gz_sim')

    # Arguments: the command line values are read by LaunchConfiguration below
    use_sim_time = LaunchConfiguration('use_sim_time')
    world = LaunchConfiguration('world')
    robot_name = LaunchConfiguration('robot_name')

    # Declare the arguments with a default and a description (shown by --show-args)
    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time', default_value='true',
        description='Use the simulated clock from Gazebo (true) or the system clock (false)')
    world_arg = DeclareLaunchArgument(
        'world', default_value='gz_empty.sdf',
        description='World file name, looked up in this package\'s worlds/ folder')
    robot_name_arg = DeclareLaunchArgument(
        'robot_name', default_value='my_bot',
        description='Name given to the robot when it is spawned in Gazebo')

    # Robot state publisher, now using whatever use_sim_time was set to
    rsp = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_path, 'launch', 'rsp.launch.py')),
        launch_arguments={'use_sim_time': use_sim_time}.items()
    )

    # Build the full world path from the chosen file name
    world_path = PathJoinSubstitution([pkg_path, 'worlds', world])

    # Start Gazebo: -r runs the simulation immediately, -v4 sets verbose logging
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(ros_gz_sim, 'launch', 'gz_sim.launch.py')),
        launch_arguments={'gz_args': ['-r -v4 ', world_path]}.items()
    )

    # Spawn the robot from the robot_description topic, with the chosen name
    spawn = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=['-topic', 'robot_description', '-name', robot_name],
        output='screen'
    )

    # ROS <-> Gazebo bridge, configured by params/gz_bridge.yaml
    bridge_params = os.path.join(pkg_path, 'params', 'gz_bridge.yaml')
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=['--ros-args', '-p', f'config_file:={bridge_params}'],
        output='screen'
    )

    # Camera images go through their own dedicated bridge node
    image_bridge = Node(
        package='ros_gz_image',
        executable='image_bridge',
        arguments=['/camera/image_raw'],
        output='screen'
    )

    return LaunchDescription([
        use_sim_time_arg, world_arg, robot_name_arg,
        rsp, gazebo, spawn, bridge, image_bridge
    ])