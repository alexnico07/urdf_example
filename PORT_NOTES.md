# Porting `urdf_example` from Gazebo Classic to Gazebo Harmonic (ROS 2 Jazzy)

This is a fork of [joshnewans/urdf_example](https://github.com/joshnewans/urdf_example), the example robot from the [Articulated Robotics](https://articulatedrobotics.xyz/) tutorials. The original was written for Gazebo Classic. On the `jazzy-gz` branch I ported it to the new Gazebo (Harmonic) so it runs on ROS 2 Jazzy.

All credit for the robot, the URDF/xacro structure and the original tutorial goes to Josh Newans. The changes below are only the parts needed to make it work with the new Gazebo.

## Quick start

```bash
cd ~/dev_ws
colcon build --symlink-install --packages-select urdf_example
source install/setup.bash
ros2 launch urdf_example rsp_sim_gz.launch.py
```

Required packages: `ros_gz_sim`, `ros_gz_bridge`, `ros_gz_image` (listed as `exec_depend` in `package.xml`).

Test a joint controller from a second terminal (use values inside the joint limits set in the URDF):

```bash
ros2 topic pub -1 /slider_joint/cmd_pos std_msgs/msg/Float64 "{data: 0.2}"
ros2 topic pub -1 /arm_joint/cmd_pos std_msgs/msg/Float64 "{data: 0.5}"
```

Check the camera with `ros2 topic list | grep camera` and open `/camera/image_raw` in RViz2 or `rqt_image_view`.

## The big idea: two separate worlds, joined by a bridge

In Classic, plugins such as `libgazebo_ros_*.so` talked to ROS directly. The new Gazebo has its own message system (Gazebo Transport) that is separate from ROS. A plugin now publishes a Gazebo message, and the `ros_gz` bridge translates it into a ROS message (and the other way round). Almost every change below follows from this.

## What I changed and why

### 1. Materials (`description/example_gazebo.xacro`)

- **Before:** each link needed a `<gazebo reference="..."><material>Gazebo/Green</material></gazebo>` block, because Classic used its own material library.
- **After:** these blocks are deleted. The new Gazebo converts the URDF to SDF and takes the colours from the URDF's own `<material>` tags, so RViz and Gazebo now match without extra tags.

### 2. Joint states (`description/example_gazebo.xacro`)

- **Before:** `libgazebo_ros_joint_state_publisher.so` published `joint_states` straight onto a ROS topic.
- **After:** `gz-sim-joint-state-publisher-system` (`gz::sim::systems::JointStatePublisher`) publishes on Gazebo's transport as a `gz.msgs.Model`. The bridge converts it to `sensor_msgs/JointState`, which `robot_state_publisher` uses to broadcast the tf.

### 3. Joint position controllers (`description/example_gazebo.xacro`)

- **Before:** one plugin, `libgazebo_ros_joint_pose_trajectory.so`, took a `JointTrajectory` message on `/set_joint_trajectory`.
- **After:** one `gz::sim::systems::JointPositionController` per joint. Each listens for a single number on its own topic:
  - `/slider_joint/cmd_pos`
  - `/arm_joint/cmd_pos`
- Each controller has its own PID gains (`p_gain` 50, `i_gain` 0.1, `d_gain` 1). These are starting guesses and have not been tuned. If a joint jitters or lags, adjust them.
- The commands arrive from ROS as `std_msgs/Float64` and the bridge turns them into `gz.msgs.Double`.

### 4. Camera (`description/example_gazebo.xacro`)

- **Before:** a `depth` sensor with `libgazebo_ros_camera.so`.
- **After:** a plain RGB `camera` sensor. The ROS camera plugin is no longer needed, because the new Gazebo has camera sensors built in. The sensor now sets its own topics (`camera/image_raw`, `camera/camera_info`) and uses `<gz_frame_id>` to point at the optical frame so the image is oriented correctly in ROS.
- I also fixed a typo in the old file: the image format `R8B8G8` is now `R8G8B8`.
- **Not ported yet:** the depth camera. In Harmonic it is a different sensor type (`depth_camera`), so I left it for later.

### 5. World (`worlds/gz_empty.sdf`, new)

A minimal SDF world: ground plane, a sun, and the systems Gazebo needs to run. Two of them are easy to miss:

- `gz-sim-scene-broadcaster-system` lets the GUI show the scene.
- `gz-sim-sensors-system` (with `ogre2`) is what actually renders the camera. Without it the camera sensor produces no images.

### 6. Launch file (`launch/rsp_sim_gz.launch.py`, new)

It starts, in order:

1. `rsp.launch.py` with `use_sim_time: true`, so ROS nodes follow Gazebo's clock.
2. Gazebo, through `ros_gz_sim`'s `gz_sim.launch.py`, with `-r` (start running immediately), `-v4` (verbose logging) and the world above.
3. The `create` node from `ros_gz_sim`, which spawns the robot from the `robot_description` topic.
4. `parameter_bridge`, configured by `params/gz_bridge.yaml`.
5. `image_bridge` for `/camera/image_raw`. Images use a dedicated bridge node, separate from the generic one.

### 7. Bridge configuration (`params/gz_bridge.yaml`, new)

Each entry pairs a ROS topic and type with a Gazebo topic and type, plus a direction.

| Topic | ROS type | Gazebo type | Direction |
|---|---|---|---|
| `clock` | `rosgraph_msgs/msg/Clock` | `gz.msgs.Clock` | Gazebo to ROS |
| `joint_states` | `sensor_msgs/msg/JointState` | `gz.msgs.Model` | Gazebo to ROS |
| `slider_joint/cmd_pos` | `std_msgs/msg/Float64` | `gz.msgs.Double` | ROS to Gazebo |
| `arm_joint/cmd_pos` | `std_msgs/msg/Float64` | `gz.msgs.Double` | ROS to Gazebo |
| `camera/camera_info` | `sensor_msgs/msg/CameraInfo` | `gz.msgs.CameraInfo` | Gazebo to ROS |

The `clock` entry matters: with `use_sim_time: true`, ROS nodes wait for the simulated clock, so without it things like tf stay stuck.

### 8. Build and package changes

- `CMakeLists.txt`: the `params` folder is now installed alongside `description`, `launch` and `worlds`, so the launch file can find `gz_bridge.yaml`.
- `package.xml`: added `ros_gz_sim`, `ros_gz_bridge` and `ros_gz_image` as `exec_depend`.

## Known gaps

- Depth camera not ported (see section 4).
- PID gains are untuned.
- `scripts/move_joints.py` is [describe what it does and how to run it].

## Environment

ROS 2 Jazzy, Gazebo Harmonic, Ubuntu on WSL2 (GPU rendering through D3D12).
