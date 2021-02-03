from gym.envs.registration import register
register(
    id='HelloRLWorldEnv-v0',
    entry_point='helloRLWorldEnv.envs:HelloRLWorldEnv'
)