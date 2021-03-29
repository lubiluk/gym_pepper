# Some bits are based on:
# https://github.com/softbankrobotics-research/qi_gym/blob/master/envs/throwing_env.py

import os.path

import gym
import numpy as np
import pybullet as p
from gym import spaces
from qibullet import Camera, PepperVirtual

from . import detection
from .pepper_reach_env import PepperReachEnv


class PepperReachDepthEnv(PepperReachEnv):
    def step(self, action):
        """
        Action in terms of desired joint positions. Last number is the speed of the movement.
        """
        self._perform_action(action)

        obs = self._get_observation()

        is_success = self._is_success()
        is_safety_violated = self._is_table_touched(
        ) or self._is_table_displaced()
        obj_pos = self._get_object_pos()
        is_object_in_sight = detection.is_object_in_sight(obs["camera"])

        info = {
            "is_success": is_success,
            "is_safety_violated": is_safety_violated,
            "object_position": obj_pos
        }
        reward = self._compute_reward(is_success, is_safety_violated,
                                      is_object_in_sight)
        done = is_success or is_safety_violated

        return (obs, reward, done, info)

    def _setup_scene(self):
        super(PepperReachEnv, self)._setup_scene()

        # Setup camera
        self._depth = self._robot.subscribeCamera(PepperVirtual.ID_CAMERA_DEPTH,
                                                resolution=Camera.K_QQVGA)

    def _get_observation_space(self):
        obs = self._get_observation()

        return spaces.Dict(
            dict(
                camera=spaces.Box(
                    0,
                    65535,
                    shape=obs["camera"].shape,
                    dtype=obs["camera"].dtype,
                ),
                camera_pose=spaces.Box(
                    -np.inf,
                    np.inf,
                    shape=obs["camera_pose"].shape,
                    dtype=obs["camera_pose"].dtype,
                ),
                joints_state=spaces.Box(
                    -np.inf,
                    np.inf,
                    shape=obs["joints_state"].shape,
                    dtype=obs["joints_state"].dtype,
                ),
            ))

    def _get_observation(self):
        img = self._robot.getCameraFrame(self._cam)

        joint_p = self._robot.getAnglesPosition(self.CONTROLLABLE_JOINTS)
        # joint velocities are not available on real Pepper
        # joint_v = self._robot.getAnglesVelocity(CONTROLLABLE_JOINTS)
        cam_pos = self._robot.getLinkPosition("CameraBottom_optical_frame")

        result = {
            "camera":
            img,
            "camera_pose":
            np.concatenate([cam_pos[0], cam_pos[1]]).astype(np.float32),
            "joints_state":
            np.array(joint_p, dtype=np.float32)
        }

        return result

    def _get_object_pos(self):
        goal_pos = p.getBasePositionAndOrientation(
            self._obj, physicsClientId=self._client)
        cam_idx = self._robot.link_dict["CameraBottom_optical_frame"].getIndex(
        )
        cam_pos = p.getLinkState(self._robot.getRobotModel(),
                                 cam_idx,
                                 physicsClientId=self._client)
        # Object position relative to camera
        inv = p.invertTransform(cam_pos[0], cam_pos[1])
        rel_pos = p.multiplyTransforms(inv[0], inv[1], goal_pos[0],
                                       goal_pos[1])

        return np.array(rel_pos[0])
