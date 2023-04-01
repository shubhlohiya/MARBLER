import rps.robotarium as robotarium
from rps.utilities.transformations import *
from rps.utilities.barrier_certificates import *
from rps.utilities.misc import *
from rps.utilities.controllers import *

import numpy as np
import random
import time
from gym import spaces

from pcpAgents import *
from utilities import *

class PCPEnv:
    def __init__(self, pcpAgents, args):
        '''
        Inputs: object of the PCPAgents class and an argparse object
        Argparse object must at least contain:
            Number of predator robots as args.predator
            Number of capture robots as args.capture
            Radii for the predator and capture agents as args.predator_radius and args.capture radius respectively
            Whether or not to show the figure as args.show_figure
            Whether or not to run the simulation in real time as args.real_time
        '''
        self.args = args
        self.agents = pcpAgents
        self.num_prey = self.args.num_prey
        self.prey_captured = [False] * self.num_prey
        self.prey_sensed = [False] * self.num_prey
        self.num_robots = self.args.predator + self.args.capture
        self.first_run = True 
        self.episodes = 0

        self.single_integrator_position_controller = create_si_position_controller()
        self.si_to_uni_dyn, self.uni_to_si_states = create_si_to_uni_mapping()
        self.si_barrier_cert = create_single_integrator_barrier_certificate_with_boundary()

        self.width = self.args.grid_size * 3
        self.height = self.args.grid_size * 2
        self.grid_locations = []
        for i in range(self.height):
            row = []
            for j in range(self.width):
                row.append(self._get_real_width_height(j, i))
            self.grid_locations.append(row)
        
        #Will spawn agents in left third of the robotarium
        if self.num_robots > 2 * self.args.grid_size ** 2:
            print('Error, too many agents for the grid size')
            exit(-1)
        self.agent_poses = [[0,0]] * self.num_robots

        self.predator_marker_size_m = (self.args.predator_radius - .5) / self.args.grid_size 
        self.capture_marker_size_m = (.05 if self.args.capture_radius == 0 else (self.args.capture_radius - .5) / self.args.grid_size)
        self.goal_marker_size_m = .05
        self.line_width = 5
        self.CM = plt.cm.get_cmap('hsv', 4) # Agent/goal color scheme
        
        # define the observation space & action space for the agents
        self.action_space = []
        self.observation_space = []
        
        for agent in self.agents.agents:
            self.action_space.append(spaces.Discrete(5))
            obs_dim = 6 * (self.args.num_neighbors + 1)
            self.observation_space.append(spaces.Box(low=-1.5, high=50, shape=(obs_dim,), dtype=np.float32))
        
        self.action_space = spaces.Tuple(tuple(self.action_space))
        self.observation_space = spaces.Tuple(tuple(self.observation_space))

        self.action_id2w = {0: 'left', 1: 'right', 2: 'up', 3:'down', 4:'no_action'}
        self.action_w2id = {v:k for k,v in self.action_id2w.items()}

        

    def reset(self):
        '''
        Reset the environment
        '''
        self.num_prey = self.args.num_prey
        self.prey_captured = [False] * self.num_prey
        self.prey_sensed = [False] * self.num_prey
        self.prey_left = [i for i in range(self.num_prey)]
        self.episodes += 1
        self._create_robotarium()

    def step(self, actions_):
        '''
        Take a step into the environment given the action
        '''

        # Considering one step to be equivalent to 60 iters
        for iterations in range(self.args.update_frequency):
            
            x = self.robotarium.get_poses()

            if iterations == 0:
                self._update_poses(actions_)
                goals = self._generate_goal_positions()

            #uses the robotarium commands to get the velocities of each robot   
            #Only does this once every 10 steps because otherwise training is really slow 
            if iterations % 10 == 0 or self.args.robotarium:                    
                xi = self.uni_to_si_states(x)
                dxi = self.single_integrator_position_controller(xi, goals[:2][:])
                dxi = self.si_barrier_cert(dxi, xi)
                dxu = self.si_to_uni_dyn(dxi, x)
                self.robotarium.set_velocities(np.arange(self.num_robots), dxu)
            
            if self.show_figure:
                for i in range(x.shape[1]):
                    self.robot_markers[i].set_offsets(x[:2,i].T)

                    # Next two lines updates the marker sizes if the figure window size is changed. 
                    # They should be removed when submitting to the Robotarium.
                    self.robot_markers[i].set_sizes([determine_marker_size(self.robotarium, \
                                                        (self.predator_marker_size_m if i < self.args.predator else self.capture_marker_size_m))])
                #self.goal_marker.set_sizes([determine_marker_size(self.robotarium, self.goal_marker_size_m)])
                for i in range(len(self.prey_markers)):
                    if not self.prey_captured[i]:
                        self.prey_markers[i].set_sizes([determine_marker_size(self.robotarium, self.goal_marker_size_m)])
                    else:
                        self.prey_markers[i].set_sizes([0,0])

            self.robotarium.step()
        
        state_space = self._generate_state_space(x) 
        self._update_prey_status(state_space, actions_, self.agents.agents)
        return state_space
        

    def _update_prey_status(self, state_space, actions, agents):
        removeIndicies = []
        for prey in range(len(self.prey_loc)):
            sensed = False
            for agent in agents:
                if np.linalg.norm(state_space['poses'][:2, agent.index] - self.prey_loc[prey]) <= agent.sensing_radius:
                    self.prey_sensed[self.prey_left[prey]] = True
                    sensed = True
                    break
            if not sensed: #Agents can only capture the prey now when its being actively sensed
                self.prey_sensed[self.prey_left[prey]] = False

            if self.prey_sensed[self.prey_left[prey]]:
                for i in range(len(actions)):
                    if self.action_id2w[actions[i]]=='no_action' and np.linalg.norm(state_space['poses'][:2, agents[i].index] - self.prey_loc[prey]) <= agents[i].capture_radius:
                        self.num_prey -= 1
                        self.prey_captured[self.prey_left[prey]] = True
                        removeIndicies.append(prey)
                        break
        for i in range(len(removeIndicies)-1, -1, -1):
            del self.prey_loc[removeIndicies[i]]
            del self.prey_left[removeIndicies[i]]

    def _update_poses(self, actions):
        for i in range(self.num_robots):
            if self.action_id2w[actions[i]] == 'left':
                    self.agent_poses[i] = [max(self.agent_poses[i][0]-1, 0), self.agent_poses[i][1]]
            elif self.action_id2w[actions[i]] == 'right':
                    self.agent_poses[i] = [min(self.agent_poses[i][0]+1, self.width-1), self.agent_poses[i][1]]
            elif self.action_id2w[actions[i]] == 'up':
                    self.agent_poses[i] = [self.agent_poses[i][0], max(self.agent_poses[i][1]-1, 0)]
            elif self.action_id2w[actions[i]] == 'down':
                    self.agent_poses[i] = [self.agent_poses[i][0], min(self.agent_poses[i][1]+1, self.height-1)]
            else:
                    continue #if 'stop' or 'capture' the agent i's pose does not change

    def _generate_goal_positions(self):
        '''
        Using the positions from self.agent_poses as the robot goal locations on the grid,
        returns an array of the robotarium positions that it is trying to reach
        '''
        goal_z = [0] * self.num_robots
        goal_x = []
        goal_y = []
        for i in self.agent_poses:
            pose = self._get_real_width_height(i[0], i[1])
            goal_x.append(pose[0])
            goal_y.append(pose[1])

        return np.array([goal_x, goal_y, goal_z])

    def _get_real_width_height(self, x, y):
        '''
        Given a grid coordinate, returns the coordinate in the robotarium units
        '''
        x = (3 * x / self.width - 1.5) + (3 / self.width / 2)
        y = (2 * y / self.height - 1) + (2 / self.height / 2)
        return [x,y]
    
    def _create_robotarium(self):
        '''
        Creates a new instance of the robotarium
        Randomly initializes the prey in the right half and the agents in the left third of the Robotarium
        '''
        if self.first_run:
            self.first_run = False
        else:
            #self.robotarium.call_at_scripts_end() #TODO: check if this is needed and how it affects runtime
            del self.robotarium

        #generate initial robot locations
        #Assumes y can be anything but the x locations are within the left third of the robotarium
        initial_values = np.random.choice(2 * self.args.grid_size ** 2, self.num_robots, replace = False)
        for i in range(len(initial_values)):
            self.agent_poses[i] = [initial_values[i]%self.args.grid_size, int(initial_values[i]/self.args.grid_size)]

        initial_conditions = self._generate_goal_positions()
        if self.args.show_figure_frequency != -1 and self.episodes % self.args.show_figure_frequency == 0:
            self.show_figure = True
        else: 
            self.show_figure = False
        self.robotarium = robotarium.Robotarium(number_of_robots= self.num_robots, show_figure = self.show_figure, \
                                                initial_conditions=initial_conditions, sim_in_real_time=self.args.real_time)
        
        #setting the prey location to a random location in the right third of the grid
        self.prey_loc = []
        prey_loc = np.random.choice(2 * self.args.grid_size ** 2, self.num_prey, replace=False)
        for p in prey_loc:        
            self.prey_loc.append(self._get_real_width_height(p%self.args.grid_size + self.width*(2/3), int(p / self.args.grid_size)))

        x = self.robotarium.get_poses()

        if self.show_figure:
            marker_size_predator = determine_marker_size(self.robotarium, self.predator_marker_size_m)
            marker_size_capture = determine_marker_size(self.robotarium, self.capture_marker_size_m)
            marker_size_goal = determine_marker_size(self.robotarium,self.goal_marker_size_m)
            self.robot_markers = [self.robotarium.axes.scatter( \
                x[0,ii], x[1,ii], s=(marker_size_predator if ii < self.args.predator else marker_size_capture), marker='o', facecolors='none',edgecolors=self.CM(0 if ii < self.args.predator else 1),linewidth=self.line_width) 
                for ii in range(self.num_robots)]
            
            self.prey_markers = [self.robotarium.axes.scatter( \
                self.prey_loc[ii][0], self.prey_loc[ii][1], s=marker_size_goal, marker='.', facecolors=self.CM(2),edgecolors=self.CM(2),linewidth=self.line_width,zorder=-2)
                for ii in range(self.num_prey)]

        self.robotarium.step()

    def _generate_state_space(self, x):
        '''
        Generates a dictionary describing the state space of the robotarium
        x: Poses of all the robots
        '''
        state_space = {}
        state_space['poses'] = x
        state_space['num_prey'] = self.num_prey
        state_space['unseen_prey'] = len(self.prey_sensed) - sum(self.prey_sensed)
        state_space['prey'] = []
        for i in range(self.num_prey):
            state_space['prey'].append(np.array(self.prey_loc[i]).reshape((2,1)))
        
        return state_space


    def __del__(self):
        self.robotarium.call_at_scripts_end()
