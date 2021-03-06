import gym
import numpy as np
import pybullet as p

import time
import pybullet_data
import matplotlib.pyplot as plt


class HelloRLWorldEnv(gym.Env):
    '''
    Description here. Coming soon.
    '''

    def __init__(self):
        # self._action_spec = array_spec.BoundedArraySpec(
        #     shape=(2,), dtype=np.float32, minimum=-1.0, maximum=1.0, name='action')
        self.action_space = gym.spaces.box.Box(
            low=np.array([-1,-1], dtype=np.float32),
            high=np.array([1,1], dtype=np.float32)
        )  
        # self._observation_spec = array_spec.ArraySpec(
        #     shape=(8,), dtype=np.float32, name='observation')
        self.observation_space = gym.spaces.box.Box(
            low=np.array([-10, -10, -10, -10, -10, -10, -10, -10,], dtype=np.float32),
            high=np.array([10,10,10,10,10,10,10,10,], dtype=np.float32)
        )
        self.np_random, _ = gym.utils.seeding.np_random()
        self.client = p.connect(p.DIRECT)

        self._state = 0
        self.done = False
        self.rendered_img = None
        self.view_matrix = p.computeViewMatrixFromYawPitchRoll(cameraTargetPosition=[4,0,5],
                                                            distance=5,
                                                            yaw=90,
                                                            pitch=-50,
                                                            roll=0,
                                                            upAxisIndex=2)
        self.proj_matrix = p.computeProjectionMatrixFOV(fov=60,
                                                     aspect=float(960) /720,
                                                     nearVal=0.1,
                                                     farVal=100.0)
        
        p.setPhysicsEngineParameter(fixedTimeStep=0.1)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())

        planeId = p.createCollisionShape(p.GEOM_BOX, halfExtents=[5, 5, 0.1], )
        p.createMultiBody(
            0, planeId, baseOrientation=p.getQuaternionFromEuler([0, 0, 0]))

        sphereRadius = 0.5
        colSphereId = p.createCollisionShape(
            p.GEOM_SPHERE, radius=sphereRadius)
        colBoxId = p.createCollisionShape(p.GEOM_BOX,
                                          halfExtents=[sphereRadius, sphereRadius, sphereRadius])
        mass = 1
        visualShapeId = -1

        self.sphereUid = p.createMultiBody(
            mass,
            colSphereId,
            visualShapeId, [0, 0, 1])

        self.boxUid = p.createMultiBody(
            mass,
            colBoxId,
            visualShapeId,
            [0, 2, 1])
        p.changeVisualShape(planeId, -1, rgbaColor=[0.2, 0.2, 0.2, 1])
        p.changeVisualShape(colSphereId, -1, rgbaColor=[0.8, 0, 0, 1])
        p.changeVisualShape(colBoxId, -1, rgbaColor=[0, 0.55, 1, 1])

        p.setGravity(0, 0, -10)
        p.setRealTimeSimulation(0)
#        p.setPhysicsEngineParameter(numSolverIterations=10)
        self.ballPositionZ = 1

    def seed(self, seed=None):
        self.np_random, seed = gym.utils.seeding.np_random(seed)
        return [seed]

    def collectObservations(self):
        observations_list = []
        observations_list.append(
            p.getBasePositionAndOrientation(self.boxUid)[0]),
        observations_list.append(
            p.getBasePositionAndOrientation(self.sphereUid)[0])
        observations_list.append(p.getBaseVelocity(self.sphereUid)[0][:2])

        return [item for observation in observations_list for item in observation]

    def reset(self):
        p.resetBasePositionAndOrientation(self.boxUid,
                                          [np.random.uniform(-4.5, 4.5),
                                           np.random.uniform(-4.5, 4.5),
                                           0.8],
                                          p.getQuaternionFromEuler([0, 0, 0]))
        p.resetBasePositionAndOrientation(self.sphereUid,
                                          [0, 0, 0.6],
                                          p.getQuaternionFromEuler([0, 0, 0]))
        self._state = self.collectObservations()
        self.done = False
        self.episode_reward = 0
        self.ballPositionZ = 1
        self.step_counter = 0
        return np.array(self._state, dtype=np.float32)

    def step(self, action):
        reward = 0
        if self.done:
            # The last action ended the episode. Ignore the current action and start
            # a new episode.
            return self.reset()

        # Make sure episodes don't go on forever.
        if self.ballPositionZ < 0:
            reward = -1
            self.episode_reward -= 1
            self.done = True
        elif self.step_counter > 200:
            reward = -0.01
            self.episode_reward -= 0.01
            self.done = True
        elif p.getContactPoints(self.sphereUid, self.boxUid):
            reward = 1 
            self.episode_reward += 1
            self.step_counter += 1
            p.resetBasePositionAndOrientation(self.boxUid, [np.random.uniform(
                -5, 5), np.random.uniform(-4.5, 4.5), 0.8], p.getQuaternionFromEuler([0, 0, 0]))
            # p.stepSimulation()
        else:
            reward = -0.01
            self.episode_reward -= 0.01
            self.step_counter += 1
            self.ballPositionZ = p.getBasePositionAndOrientation(self.sphereUid)[
                0][2]
            p.applyExternalForce(objectUniqueId=self.sphereUid, linkIndex=-1, forceObj=(
                20*action[0], 20*action[1], 0), posObj=p.getBasePositionAndOrientation(self.sphereUid)[
                0], flags=p.WORLD_FRAME)
        p.stepSimulation()
        self._state = self.collectObservations()

        return np.array(self._state, dtype=np.float32), np.array(reward), self.done, dict()
    
    def render(self, mode='human'):
        if self.rendered_img is None:
            plt.axis('off')
            self.rendered_img = plt.imshow(np.zeros((720, 960, 4)))

        # Display image
        (_, _, px, _, _) = p.getCameraImage(width=960,
                                              height=720,
                                              viewMatrix=self.view_matrix,
                                              projectionMatrix=self.proj_matrix,
                                              renderer=p.ER_TINY_RENDERER)
        rgb_array = np.array(px, dtype=np.uint8)
        rgb_array = np.reshape(rgb_array, (720,960, 4))
        self.rendered_img.set_data(rgb_array)

        annotation = plt.annotate(f'Step: {self.step_counter}\nEpisode Reward: {self.episode_reward:.3f}', xy=(0,0))
        plt.draw()
        plt.pause(.00001)
        annotation.remove()

    def close(self):
        p.disconnect(self.client)

'''
# Demo

test = HelloRLWorldEnv()

time_step = test.reset()

reward = 0
total_steps = 0
while reward < 5:
    while not time_step[2] == True:
        time_step = test.step(
            [np.random.uniform(-1, 1), np.random.uniform(-1, 1)])
        total_steps += 1
        test.render()
        if time_step[1] > 0:
            print(time_step[1])
            print(f'total steps: {total_steps}')
            total_steps = 0
            reward += time_step[1]

    time_step = test.reset()
'''